"""Registration audit library (science/reviews/registration-audit/**).

Reviewer code. It does NOT import backend/data or tools/ingest. It reuses the
acceptance reviewer's helpers (science/reviews/acceptance/check_acceptance.py)
on purpose, so that the "legacy" Gaia rule audited here is byte-for-byte the
rule that produced the published 161-frame / 0.45 px headline.

Three things live here:

1. An instrumented copy of the legacy Gaia-seeded measurement that records
   *why* each catalog star is dropped (footprint, edge, non-finite window,
   low SNR, association radius, PNG window). It is checked against the legacy
   function star by star at run time.
2. A blind (catalog-free) source detector. Its eligibility rule (finite window,
   peak SNR) uses only the image, never the header WCS or the catalog, so the
   eligible set cannot shrink just because the registration is wrong.
3. A registration validator built on (2): offset voting against Gaia,
   a similarity (shift + rotation) fit, and explicit PASS / FAIL / UNKNOWN.
   Plus fixture helpers that move the image content by a known amount relative
   to its header (the deliberate negative control).

Units: "native px" are SPHEREx IMAGE pixels (about 6.1-6.2 arcsec); "display px"
are the published 256 px grid pixels (1.40625 arcsec).
"""

from __future__ import annotations

import csv
import math
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning

HERE = Path(__file__).resolve().parent
ACCEPTANCE = HERE.parent / "acceptance"
if str(ACCEPTANCE) not in sys.path:
    sys.path.insert(0, str(ACCEPTANCE))
import check_acceptance as acc  # noqa: E402  (legacy helpers, unmodified)

warnings.simplefilter("ignore", FITSFixedWarning)

INFORMATIONAL = {"SOURCE", "FULLSAMPLE"}

# Legacy (acceptance) parameters. Changing these here does not change the
# acceptance validator; they are the baseline of the sensitivity grid.
LEGACY = dict(snr_min=15.0, assoc_px=1.0, target_excl_arcsec=40.0, half=2, search=1)

# Validator thresholds. They were chosen from the distribution over the real
# frames (see README, "How the thresholds were set") before the fixtures were
# evaluated, and are deliberately loose so that real frames do not fail.
VALIDATOR = dict(
    snr_min=15.0,          # blind detection peak SNR (MAD units), same as legacy
    target_excl_arcsec=40.0,
    vote_radius_px=8.0,    # pairs considered when voting for a systematic offset
    tol_px=1.0,            # a detection supports an offset if within this of it
    min_support=3,         # fewer supporting detections -> UNKNOWN
    max_offset_px=0.6,     # |systematic offset| above this (and significant) -> FAIL
    offset_sigma=4.0,      # ... significance in units of sigma/sqrt(n)
    max_rot_deg=0.5,       # |rotation| above this (and significant) -> FAIL
    rot_sigma=3.0,
    min_rot_pairs=5,
    rot_grid_deg=tuple(float(x) for x in np.round(np.arange(-5.0, 5.01, 0.5), 2)),
    scan_min_rot_deg=1.0,  # rotation-scan rule: best rotation at least this large ...
    scan_min_gain=2,       # ... and supported by at least this many more detections than zero rotation
)
# Not used as a rule: an absolute "fraction of detections with a Gaia match" floor.
# On real RW Aur frames (Gaia cache cut at G<15, dusty field) only ~20-25% of
# SNR>=15 near-IR detections have a catalog entry, so such a floor would fail
# correct frames. Lost matches surface instead as a non-zero voted offset or,
# beyond the vote radius, as UNKNOWN (which is never treated as a pass).


# --------------------------------------------------------------------- frames


@dataclass
class Frame:
    key: str
    img: np.ndarray
    var: np.ndarray
    flg: np.ndarray
    names: dict
    wcs: WCS
    mjd: float
    detector: int
    scale_arcsec: float
    good: np.ndarray = field(init=False)
    adverse: np.ndarray = field(init=False)
    despiked: np.ndarray = field(init=False)

    def __post_init__(self):
        self.good = np.isfinite(self.img) & np.isfinite(self.var) & (self.var > 0)
        adv_bits = sum(1 << b for b, n in self.names.items() if n not in INFORMATIONAL)
        self.adverse = ((self.flg & adv_bits) != 0) | ~self.good
        self.despiked = acc.despike(self.img)

    @property
    def shape(self):
        return self.img.shape


def frame_from_hdul(hdul, key=None) -> Frame:
    ih = hdul["IMAGE"].header
    names = {int(k[4:]): hdul["FLAGS"].header[k].strip() for k in hdul["FLAGS"].header if k.startswith("MSKN")}
    w = WCS(ih, fobj=hdul)
    sc = float(np.mean([s.to_value("arcsec") for s in w.proj_plane_pixel_scales()]))
    return Frame(
        key=key or f"{ih['OBSID'].strip()}_D{int(ih['DETECTOR'])}",
        img=hdul["IMAGE"].data.astype(float),
        var=hdul["VARIANCE"].data.astype(float),
        flg=hdul["FLAGS"].data.astype(np.int64),
        names=names, wcs=w, mjd=float(ih["MJD-AVG"]), detector=int(ih["DETECTOR"]), scale_arcsec=sc,
    )


def load_frame(path, key=None) -> Frame:
    with fits.open(path) as hdul:
        return frame_from_hdul(hdul, key)


# -------------------------------------------------------------------- catalog


def read_catalog(path):
    """All rows of a cached Gaia CSV. Rows without proper motion (2-parameter
    solutions) are returned with full=False; the legacy check skips them."""
    rows = []
    if not Path(path).exists():
        return rows
    with open(path) as f:
        for r in csv.DictReader(f):
            full = all(r.values())
            rows.append({
                "source_id": int(r["source_id"]), "ra": float(r["ra"]), "dec": float(r["dec"]),
                "pmra": float(r["pmra"]) if r["pmra"] else 0.0, "pmdec": float(r["pmdec"]) if r["pmdec"] else 0.0,
                "ref_epoch": float(r["ref_epoch"]) if r["ref_epoch"] else 2016.0,
                "G": float(r["phot_g_mean_mag"]) if r["phot_g_mean_mag"] else float("nan"), "full": full,
            })
    return rows


def sky_sep_arcsec(ra1, dec1, ra2, dec2):
    return math.hypot((ra1 - ra2) * math.cos(math.radians(dec2)), dec1 - dec2) * 3600.0


def project_catalog(fr: Frame, cat, target_radec, target_excl_arcsec):
    """Propagate (legacy linear rule) and project every catalog star through the
    header WCS. Returns list of dicts with native x/y and bookkeeping."""
    out = []
    for s in cat:
        ra, dec = acc.gaia_at(s, fr.mjd)
        x, y = (float(v) for v in fr.wcs.all_world2pix([[ra, dec]], 0)[0])
        out.append({**s, "ra_t": ra, "dec_t": dec, "x": x, "y": y,
                    "sep_target": sky_sep_arcsec(ra, dec, *target_radec) if target_radec else float("inf"),
                    "near_target": bool(target_radec) and sky_sep_arcsec(ra, dec, *target_radec) < target_excl_arcsec})
    return out


# --------------------------------------------------------- forced measurement


def forced_measure(fr: Frame, x, y, half=2, search=1, snr_min=15.0):
    """Instrumented copy of check_acceptance.native_centroid.

    Returns (stage, result) where stage is one of
    'edge', 'nonfinite', 'low_snr', 'ok' and result carries centroid and SNR.
    With the legacy parameters 'ok' is returned exactly when the legacy function
    returns a value, with identical numbers (verified at run time)."""
    img, d = fr.img, fr.despiked
    ny, nx = img.shape
    if not (np.isfinite(x) and np.isfinite(y)):
        return "edge", None
    ix, iy = int(round(x)), int(round(y))
    m = half + 2
    if ix - m < 0 or iy - m < 0 or ix + m >= nx or iy + m >= ny:
        return "edge", None
    win = img[iy - m: iy + m + 1, ix - m: ix + m + 1]
    if not np.isfinite(win).all():
        return "nonfinite", None
    sub = d[iy - search: iy + search + 1, ix - search: ix + search + 1]
    dy, dx = np.unravel_index(np.argmax(sub), sub.shape)
    cx, cy = ix + dx - search, iy + dy - search
    if cx - half < 0 or cy - half < 0 or cx + half >= nx or cy + half >= ny:
        return "edge", None
    w = d[cy - half: cy + half + 1, cx - half: cx + half + 1]
    ring = d[max(cy - 6, 0): cy + 7, max(cx - 6, 0): cx + 7]
    bg = np.nanmedian(ring)
    mad = np.nanmedian(np.abs(ring - bg)) * 1.4826 + 1e-12
    snr = float((w.max() - bg) / mad)
    adverse_in_window = int(fr.adverse[cy - half: cy + half + 1, cx - half: cx + half + 1].sum())
    if (w.max() - bg) < snr_min * mad:
        return "low_snr", {"snr": snr, "adverse_in_window": adverse_in_window}
    wt = np.clip(w - bg, 0, None)
    yy, xx = np.mgrid[cy - half: cy + half + 1, cx - half: cx + half + 1]
    return "ok", {"cx": float((wt * xx).sum() / wt.sum()), "cy": float((wt * yy).sum() / wt.sum()), "snr": snr,
                  "adverse_in_window": adverse_in_window}


# ----------------------------------------------------------- blind detection


def blind_detect(fr: Frame, snr_min=15.0, half=2, min_sep=2.0):
    """Catalog-free, WCS-free detections. Eligibility = local maximum of the
    despiked image, finite (2*half+5)^2 raw window, peak SNR >= snr_min measured
    exactly as in forced_measure. Centroid = same 5x5 background-subtracted
    first moment."""
    img, d = fr.img, fr.despiked
    ny, nx = img.shape
    m = half + 2
    bg0 = np.nanmedian(d)
    cand = []
    with np.errstate(invalid="ignore"):
        for iy in range(m, ny - m):
            for ix in range(m, nx - m):
                v = d[iy, ix]
                if not np.isfinite(v) or v <= bg0:
                    continue
                nb = d[iy - 1: iy + 2, ix - 1: ix + 2]
                if v < np.nanmax(nb):
                    continue
                if not np.isfinite(img[iy - m: iy + m + 1, ix - m: ix + m + 1]).all():
                    continue
                w = d[iy - half: iy + half + 1, ix - half: ix + half + 1]
                ring = d[max(iy - 6, 0): iy + 7, max(ix - 6, 0): ix + 7]
                bg = np.nanmedian(ring)
                mad = np.nanmedian(np.abs(ring - bg)) * 1.4826 + 1e-12
                snr = float((v - bg) / mad)
                if snr < snr_min:
                    continue
                wt = np.clip(w - bg, 0, None)
                yy, xx = np.mgrid[iy - half: iy + half + 1, ix - half: ix + half + 1]
                cand.append({"x": float((wt * xx).sum() / wt.sum()), "y": float((wt * yy).sum() / wt.sum()),
                             "snr": snr, "peak_xy": [ix, iy],
                             "adverse_in_window": int(fr.adverse[iy - half: iy + half + 1, ix - half: ix + half + 1].sum())})
    cand.sort(key=lambda c: -c["snr"])
    keep = []
    for c in cand:
        if all(math.hypot(c["x"] - k["x"], c["y"] - k["y"]) >= min_sep for k in keep):
            keep.append(c)
    return keep


def detections_away_from_target(fr: Frame, dets, target_radec, excl_arcsec):
    if not target_radec or not dets:
        return dets
    out = []
    for dct in dets:
        ra, dec = (float(v) for v in fr.wcs.all_pix2world([[dct["x"], dct["y"]]], 0)[0])
        # A WCS error moves this sky position too; the exclusion radius (40") is
        # > 6 native px so a few-pixel registration error cannot re-admit the target.
        if sky_sep_arcsec(ra, dec, *target_radec) >= excl_arcsec:
            out.append(dct)
    return out


# ------------------------------------------------------------------ validator


def _support(dets, cats, off, tol):
    """For each detection, the catalog star whose (det - cat) is closest to `off`;
    supporting if within tol. Returns list of (det_index, cat_index, dx, dy)."""
    sup = []
    for i, dct in enumerate(dets):
        best = None
        for j, c in enumerate(cats):
            dx, dy = dct["x"] - c["x"], dct["y"] - c["y"]
            e = math.hypot(dx - off[0], dy - off[1])
            if e <= tol and (best is None or e < best[0]):
                best = (e, j, dx, dy)
        if best is not None:
            sup.append((i, best[1], best[2], best[3]))
    return sup


def _offsets(dets, cats):
    if not dets or not cats:
        return np.zeros((len(dets), len(cats), 2))
    d = np.array([[q["x"], q["y"]] for q in dets], float)
    c = np.array([[q["x"], q["y"]] for q in cats], float)
    return d[:, None, :] - c[None, :, :]


def _vote(dets, cats, R, tol):
    """Best common offset: each detection-catalog pair within R proposes its
    offset; the offset supported by most detections (within tol) wins; ties go
    to the smaller offset. Returns ((dx, dy), n_supporting_detections)."""
    D = _offsets(dets, cats)
    if D.size == 0:
        return (0.0, 0.0), 0
    zero = int((np.hypot(D[..., 0], D[..., 1]).min(axis=1) <= tol).sum())
    best, nb = (0.0, 0.0), zero
    props = D[np.hypot(D[..., 0], D[..., 1]) <= R]
    for off in props:
        e = np.hypot(D[..., 0] - off[0], D[..., 1] - off[1])
        n = int((e.min(axis=1) <= tol).sum())
        if n > nb or (n == nb and math.hypot(*off) < math.hypot(*best)):
            best, nb = (float(off[0]), float(off[1])), n
    return best, nb


def _rotate(cats, centre, th_deg):
    t = math.radians(th_deg)
    ct, st = math.cos(t), math.sin(t)
    out = []
    for c in cats:
        dx, dy = c["x"] - centre[0], c["y"] - centre[1]
        out.append({**c, "x": centre[0] + ct * dx - st * dy, "y": centre[1] + st * dx + ct * dy})
    return out


def similarity_fit(pairs, dets, cats, centre):
    """Least-squares p = [[a,-b],[b,a]] q + t about `centre` (native px).
    Returns rotation (deg), its 1-sigma, scale, translation and residual rms."""
    if len(pairs) < 3:
        return None
    A, y = [], []
    for i, j, _, _ in pairs:
        qx, qy = cats[j]["x"] - centre[0], cats[j]["y"] - centre[1]
        px, py = dets[i]["x"] - centre[0], dets[i]["y"] - centre[1]
        A.append([qx, -qy, 1, 0]); y.append(px)
        A.append([qy, qx, 0, 1]); y.append(py)
    A, y = np.array(A, float), np.array(y, float)
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ sol
    dof = max(len(y) - 4, 1)
    s2 = float(res @ res / dof)
    cov = s2 * np.linalg.pinv(A.T @ A)
    a, b, tx, ty = sol
    rot = math.degrees(math.atan2(b, a))
    k = math.hypot(a, b)
    sig_rot = math.degrees(math.sqrt(max(cov[0, 0] * b * b + cov[1, 1] * a * a, 0.0)) / (k * k)) if k else float("nan")
    return {"rotation_deg": rot, "rotation_sigma_deg": sig_rot, "scale": k, "shift_px": [float(tx), float(ty)],
            "rms_px": math.sqrt(s2), "n": len(pairs)}


def registration_verdict(fr: Frame, cat, target_radec, params=None, dets=None):
    """PASS / FAIL / UNKNOWN for one frame's header registration against Gaia,
    using blind detections as the eligible set (independent of the WCS)."""
    P = dict(VALIDATOR, **(params or {}))
    if dets is None:
        dets = blind_detect(fr, snr_min=P["snr_min"])
    dets = detections_away_from_target(fr, dets, target_radec, P["target_excl_arcsec"])
    ny, nx = fr.shape
    proj = project_catalog(fr, [c for c in cat if c["full"]], target_radec, P["target_excl_arcsec"])
    R = P["vote_radius_px"]
    cats = [c for c in proj if not c["near_target"] and -R <= c["x"] <= nx - 1 + R and -R <= c["y"] <= ny - 1 + R]
    out = {"n_detections": len(dets), "n_catalog_in_reach": len(cats)}
    tol = P["tol_px"]
    zero = _support(dets, cats, (0.0, 0.0), tol)
    out["zero_offset_matches"] = len(zero)
    # vote: every detection-catalog pair within R proposes an offset
    best_off, nsup = _vote(dets, cats, R, tol)
    best_sup = _support(dets, cats, best_off, tol) if nsup > len(zero) else zero
    if nsup <= len(zero):
        best_off = (0.0, 0.0)
    # refine: median of supporting offsets, then re-collect support (twice)
    for _ in range(2):
        if best_sup:
            best_off = (float(np.median([p[2] for p in best_sup])), float(np.median([p[3] for p in best_sup])))
            best_sup = _support(dets, cats, best_off, tol)
    out["best_offset_px"] = [best_off[0], best_off[1]]
    out["best_offset_abs_px"] = math.hypot(*best_off)
    out["best_support"] = len(best_sup)
    if best_sup:
        resid = np.array([[p[2] - best_off[0], p[3] - best_off[1]] for p in best_sup])
        sig = float(np.sqrt(np.mean(np.sum(resid ** 2, axis=1)) / 2.0)) if len(best_sup) > 1 else float("nan")
    else:
        sig = float("nan")
    out["per_axis_scatter_px"] = sig
    sig_floor = max(sig if np.isfinite(sig) else 0.3, 0.15)
    out["offset_significance"] = out["best_offset_abs_px"] / (sig_floor / math.sqrt(max(len(best_sup), 1)))
    fit = similarity_fit(best_sup, dets, cats, ((nx - 1) / 2.0, (ny - 1) / 2.0))
    out["similarity_fit"] = fit
    out["match_fraction_zero_offset"] = len(zero) / len(dets) if dets else None
    # rotation scan: rotate the projected catalog about the cutout centre and re-vote.
    centre = ((nx - 1) / 2.0, (ny - 1) / 2.0)
    scan = {}
    for th in P["rot_grid_deg"]:
        cr = _rotate(cats, centre, th)
        scan[th] = _vote(dets, cr, R, tol)
    s0 = scan[0.0][1]
    smax = max(v[1] for v in scan.values())
    plateau = [t for t, v in scan.items() if v[1] == smax]
    # the support plateau is flat over ~+-1.5 deg (tol / radius); use its centre,
    # then refine with a similarity fit on the pairs supporting that hypothesis
    th_best = 0.0 if 0.0 in plateau else float(np.mean(plateau))
    th_grid = min(P["rot_grid_deg"], key=lambda t: abs(t - th_best))
    cr = _rotate(cats, centre, th_grid)
    off_r = _vote(dets, cr, R, tol)[0]
    sup_r = _support(dets, cr, off_r, tol)
    fit_r = similarity_fit(sup_r, dets, cats, centre) if smax > s0 else None
    out["rotation_scan"] = {"support_at_zero": s0, "best_rotation_deg": th_best, "support_at_best": smax,
                            "plateau_deg": [min(plateau), max(plateau)],
                            "refit_rotation_deg": fit_r["rotation_deg"] if fit_r else None,
                            "refit_rotation_sigma_deg": fit_r["rotation_sigma_deg"] if fit_r else None}
    rot_est = fit_r["rotation_deg"] if fit_r else th_best

    reasons = []
    if len(dets) < P["min_support"] or len(best_sup) < P["min_support"]:
        verdict = "UNKNOWN"
        reasons.append(f"only {len(dets)} eligible detections / {len(best_sup)} supporting Gaia pairs "
                       f"(< {P['min_support']}): no independent star-based registration evidence")
    else:
        verdict = "PASS"
        if out["best_offset_abs_px"] > P["max_offset_px"] and out["offset_significance"] > P["offset_sigma"]:
            verdict = "FAIL"
            reasons.append(f"systematic offset {out['best_offset_abs_px']:.2f} native px "
                           f"({out['offset_significance']:.1f} sigma) between detections and Gaia")
        if fit and fit["n"] >= P["min_rot_pairs"] and abs(fit["rotation_deg"]) > P["max_rot_deg"] \
                and abs(fit["rotation_deg"]) > P["rot_sigma"] * fit["rotation_sigma_deg"]:
            verdict = "FAIL"
            reasons.append(f"rotation {fit['rotation_deg']:.2f} +/- {fit['rotation_sigma_deg']:.2f} deg")
        rs = out["rotation_scan"]
        if abs(rot_est) >= P["scan_min_rot_deg"] and rs["support_at_best"] >= rs["support_at_zero"] + P["scan_min_gain"]:
            verdict = "FAIL"
            reasons.append(f"rotating the catalog by {rot_est:+.1f} deg raises Gaia support from "
                           f"{rs['support_at_zero']} to {rs['support_at_best']} detections")
    if verdict == "UNKNOWN":
        rs = out["rotation_scan"]
        if rs["support_at_best"] >= P["min_support"] and rs["support_at_best"] >= rs["support_at_zero"] + P["scan_min_gain"] \
                and abs(rot_est) >= P["scan_min_rot_deg"]:
            verdict = "FAIL"
            reasons.append(f"too little support at zero rotation, but {rs['support_at_best']} detections match Gaia after "
                           f"rotating the catalog by {rot_est:+.1f} deg")
    out["verdict"] = verdict
    out["reasons"] = reasons
    return out


# ---------------------------------------------------------------- legacy rule


def legacy_gaia_rule(fr: Frame, cat, target_radec, gray=None, alpha=None, reg=None):
    """The acceptance validator's Gaia block, verbatim in logic, using its own
    functions. Returns the counts and the boolean it would contribute to
    'registration' (True unless >=1 PNG-qualified star and median > 2.5 display px)."""
    stars = []
    for s in cat:
        if not s["full"]:
            continue
        gra, gdec = acc.gaia_at(s, fr.mjd)
        if sky_sep_arcsec(gra, gdec, *target_radec) < 40:
            continue
        gx, gy = (float(v) for v in fr.wcs.all_world2pix([[gra, gdec]], 0)[0])
        nc = acc.native_centroid(fr.img, gx, gy)
        if nc is None:
            continue
        pc = None
        if gray is not None:
            dxp, dyp = acc.sky_to_display(gra, gdec, reg["center_ra_deg"], reg["center_dec_deg"], reg["fov_arcmin"], reg["width"])
            pc_ = acc.png_centroid(gray, alpha, dxp, dyp)
            pc = None if pc_ is None else (pc_[0] - dxp, pc_[1] - dyp)
        stars.append({"native_dx": nc[0] - gx, "native_dy": nc[1] - gy, "png": pc})
    pngs = [s for s in stars if s["png"] is not None and math.hypot(s["native_dx"], s["native_dy"]) < 1.0]
    med = float(np.median([math.hypot(*s["png"]) for s in pngs])) if pngs else None
    nat1 = [s for s in stars if math.hypot(s["native_dx"], s["native_dy"]) < 1.0]
    return {"n_native": len(stars), "n_within_1px": len(nat1), "n_png": len(pngs),
            "png_median_offset_display_px": med,
            "native_median_offset_px_within_1px": float(np.median([math.hypot(s["native_dx"], s["native_dy"]) for s in nat1])) if nat1 else None,
            "registration_ok": not (pngs and med > 2.5),
            "gaia_evidence_present": bool(pngs)}


# ------------------------------------------------------------------ fixtures


def bilinear_sample(a, xs, ys):
    """Bilinear interpolation of 2-D array `a` at float pixel coords; NaN outside
    or if any contributing pixel is NaN."""
    ny, nx = a.shape
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    tx, ty = xs - x0, ys - y0
    ok = (x0 >= 0) & (y0 >= 0) & (x0 + 1 < nx) & (y0 + 1 < ny)
    x0c, y0c = np.clip(x0, 0, nx - 2), np.clip(y0, 0, ny - 2)
    v = (a[y0c, x0c] * (1 - tx) * (1 - ty) + a[y0c, x0c + 1] * tx * (1 - ty)
         + a[y0c + 1, x0c] * (1 - tx) * ty + a[y0c + 1, x0c + 1] * tx * ty)
    # exact pixel hits (integer shifts) must not depend on the far neighbour
    exact = (tx == 0) & (ty == 0)
    v = np.where(exact, a[y0c, x0c], v)
    return np.where(ok | (exact & (x0 >= 0) & (y0 >= 0) & (x0 < nx) & (y0 < ny)), v, np.nan)


def misregister_arrays(img, var, flg, dx=0.0, dy=0.0, rot_deg=0.0):
    """Move the image content by (dx, dy) native px and rotate it by rot_deg
    (counter-clockwise in pixel coordinates, about the cutout centre), keeping
    the header unchanged. A star truly at p0 then sits at c + R(p0 - c) + (dx, dy)
    while the header still maps the sky to p0: a known registration error."""
    ny, nx = img.shape
    c = ((nx - 1) / 2.0, (ny - 1) / 2.0)
    yy, xx = np.mgrid[0:ny, 0:nx].astype(float)
    th = math.radians(rot_deg)
    # inverse map: output pixel p came from R^-1 (p - (dx,dy) - c) + c
    ux, uy = xx - dx - c[0], yy - dy - c[1]
    sx = math.cos(th) * ux + math.sin(th) * uy + c[0]
    sy = -math.sin(th) * ux + math.cos(th) * uy + c[1]
    new_img = bilinear_sample(img, sx, sy)
    new_var = bilinear_sample(var, sx, sy)
    ix, iy = np.rint(sx).astype(int), np.rint(sy).astype(int)
    inside = (ix >= 0) & (iy >= 0) & (ix < nx) & (iy < ny)
    new_flg = np.where(inside, flg[np.clip(iy, 0, ny - 1), np.clip(ix, 0, nx - 1)], 0)
    return new_img.astype(np.float32), new_var.astype(np.float32), new_flg.astype(np.int32)


def misregistered_hdul(raw_path, dx=0.0, dy=0.0, rot_deg=0.0):
    """Derived negative-control fixture: an in-memory copy of a real cutout with
    its pixels moved relative to the unchanged header. Never written into the
    product tree; tests write it only to a pytest tmp_path."""
    src = fits.open(raw_path)
    hd = fits.HDUList([h.copy() for h in src])
    src.close()
    img, var, flg = misregister_arrays(hd["IMAGE"].data.astype(float), hd["VARIANCE"].data.astype(float),
                                       hd["FLAGS"].data.astype(np.int64), dx, dy, rot_deg)
    hd["IMAGE"].data, hd["VARIANCE"].data, hd["FLAGS"].data = img, var, flg
    hd["IMAGE"].header["HISTORY"] = f"PERIGEE NEGATIVE CONTROL: pixels moved dx={dx} dy={dy} rot={rot_deg}deg vs header"
    return hd


def render_png_arrays(fr: Frame, reg, display_scale):
    """What processor A would publish for this (possibly misregistered) frame:
    nearest-neighbour resampling through the header WCS onto the record grid,
    with the record's stated stretch (same rule the acceptance check reconstructs)."""
    size = reg["width"]
    sra, sdec = acc.display_centers_to_sky(reg["center_ra_deg"], reg["center_dec_deg"], reg["fov_arcmin"], size)
    npx, npy = fr.wcs.all_world2pix(sra.ravel(), sdec.ravel(), 0, quiet=True)
    ix, iy = np.rint(npx.reshape(size, size)).astype(int), np.rint(npy.reshape(size, size)).astype(int)
    ny, nx = fr.shape
    on = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    ixc, iyc = np.clip(ix, 0, nx - 1), np.clip(iy, 0, ny - 1)
    good = on & fr.good[iyc, ixc]
    gray = np.zeros((size, size), int)
    gray[good] = acc.stretch(fr.img[iyc, ixc][good], display_scale["low"], display_scale["high"],
                             display_scale["asinh_softening"])
    alpha = np.where(good, 255, 0)
    return gray, alpha
