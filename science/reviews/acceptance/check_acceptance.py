"""Independent acceptance check of processor products against the original FITS.

Reviewer tool (science/reviews/acceptance/**). It does NOT import backend/data
or tools/ingest. Every expected value is re-derived here from:

* the original FITS cutouts and manifest.json in research/build_data (read only),
* the target astrometry in manifest.json (not targets.json),
* Gaia DR3 stars cached in ./gaia/*.csv (absolute registration control),
* the case JSON on the science branch (git show), for case-level agreement.

Independent pieces (deliberately not the processor's code paths):
* display grid: hand-written gnomonic (TAN) projection, north up / east left,
  origin at the PNG top-left corner (no astropy grid WCS);
* wavelength: (a) astropy key-W WCS with sip=None, (b) a hand-written bilinear
  lookup of the WCS-WAVE table (FITS Paper III -TAB);
* flags: own MSKN/MSKM decode, own aperture;
* image: full re-sampling of every display pixel and re-application of the
  stated stretch, compared byte-for-byte with the published PNG;
* stars: Gaia DR3 positions propagated to each frame's MJD-AVG, centroided in
  the native image and in the published PNG.

Usage (repository root):
    .venv/bin/python science/reviews/acceptance/check_acceptance.py \
        --data-root "/path/to/research/build_data" \
        --products backend/content/presets \
        --science-ref origin/codex/sathvik-science \
        --out science/reviews/acceptance/results.json
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import io
import json
import math
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS, FITSFixedWarning
from PIL import Image

warnings.simplefilter("ignore", FITSFixedWarning)
warnings.simplefilter("ignore")
from astropy import log as _alog  # noqa: E402

_alog.setLevel("ERROR")

HERE = Path(__file__).resolve().parent
INFORMATIONAL = {"SOURCE", "FULLSAMPLE"}
APERTURE_R = 2.5  # native px, the radius the authored cases were screened with
SELECTED = [
    # (preset, set, frame_key, why)
    ("epsilon_indi_b", "case-fair_comparison", "2026W18_1A_0516_1_D3", "fair_comparison A"),
    ("epsilon_indi_b", "case-fair_comparison", "2026W39_2A_0597_4_D3", "fair_comparison B"),
    ("epsilon_indi_b", "case-fair_comparison", "2026W18_1A_0516_1_D6", "fair_comparison C (MWIR D6)"),
    ("barnards_star", "case-moving_neighbor", "2025W35_1A_0008_1_D3", "moving_neighbor A"),
    ("barnards_star", "case-moving_neighbor", "2026W12_1A_0610_2_D3", "moving_neighbor B"),
    ("barnards_star", "case-moving_neighbor", "2026W34_1A_0431_1_D3", "moving_neighbor C"),
    ("epsilon_indi_b", "frames", "2025W17_4B_0077_2_D1", "not_covered (SWIR, edge cutout)"),
    ("r_draconis", "frames", "2025W27_2A_0331_1_D4", "not_covered (MWIR D4); CASE_SELECTION defect-1 frame"),
    ("rw_aurigae", "frames", "2025W37_1A_0069_1_D2", "not_covered (SWIR); defect-1 frame"),
    ("r_draconis", "frames", "2026W01_2A_0426_1_D3", "R Dra saturated (21/21 non-finite)"),
    ("r_draconis", "frames", "2025W29_2A_0288_1_D4", "R Dra saturated, MWIR D4"),
    ("wise_0855", "frames", "2026W19_1A_0227_1_D1", "WISE 0855 SWIR, same exposure as next"),
    ("wise_0855", "frames", "2026W19_1A_0227_1_D4", "WISE 0855 MWIR D4"),
]


# ----------------------------------------------------------------- geometry


def gnomonic(ra, dec, ra0, dec0):
    """Standard coordinates (xi east, eta north) in radians."""
    a, d, a0, d0 = map(np.radians, (ra, dec, ra0, dec0))
    cosc = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(a - a0)
    xi = np.cos(d) * np.sin(a - a0) / cosc
    eta = (np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(a - a0)) / cosc
    return xi, eta


def inv_gnomonic(xi, eta, ra0, dec0):
    a0, d0 = np.radians(ra0), np.radians(dec0)
    rho = np.hypot(xi, eta)
    c = np.arctan(rho)
    with np.errstate(invalid="ignore", divide="ignore"):
        dec = np.arcsin(np.cos(c) * np.sin(d0) + np.where(rho > 0, eta * np.sin(c) * np.cos(d0) / rho, 0))
        ra = a0 + np.arctan2(xi * np.sin(c), rho * np.cos(d0) * np.cos(c) - eta * np.sin(d0) * np.sin(c))
    return np.degrees(ra) % 360.0, np.degrees(dec)


def sky_to_display(ra, dec, ra0, dec0, fov_arcmin, size):
    """Display px, origin = top-left corner of PNG; north up (y down = south), east left."""
    s = math.radians(fov_arcmin / 60.0) / size
    xi, eta = gnomonic(ra, dec, ra0, dec0)
    return size / 2.0 - xi / s, size / 2.0 - eta / s


def display_centers_to_sky(ra0, dec0, fov_arcmin, size):
    s = math.radians(fov_arcmin / 60.0) / size
    j, i = np.mgrid[0:size, 0:size]  # j = row from top, i = column from left
    xi = -((i + 0.5) - size / 2.0) * s
    eta = (size / 2.0 - (j + 0.5)) * s
    return inv_gnomonic(xi, eta, ra0, dec0)


# ----------------------------------------------------------------- spectral


def wave_astropy(ih, hdul, x, y):
    sw = WCS(header=ih, fobj=hdul, key="W")
    sw.sip = None
    v = sw.pixel_to_world_values(x, y)
    return float(v[0]), float(v[1])


def wave_manual(ih, hdul, x, y):
    """Hand-written -TAB bilinear lookup (FITS Paper III s6.1), 0-based x, y."""
    t = hdul[ih["PS1_0W"].strip()].data[0]
    X = np.asarray(t["X"], float)
    Y = np.asarray(t["Y"], float)
    V = np.asarray(t["VALUES"], float)  # (ny_ctrl, nx_ctrl, 2) after TDIM (2,9,14)
    if V.shape != (Y.size, X.size, 2):
        V = V.reshape(Y.size, X.size, 2)
    psi = []
    for ax, p in ((1, x), (2, y)):
        p1 = p + 1.0  # FITS 1-based pixel
        cd = float(ih.get(f"CDELT{ax}W", 1.0))
        crp = float(ih[f"CRPIX{ax}W"])
        crv = float(ih[f"CRVAL{ax}W"])
        psi.append(cd * (p1 - crp) + crv)
    px, py = psi
    if not (X[0] <= px <= X[-1] and Y[0] <= py <= Y[-1]):
        return None, None, (px, py)
    fx = np.interp(px, X, np.arange(X.size))
    fy = np.interp(py, Y, np.arange(Y.size))
    i0, j0 = int(min(math.floor(fx), X.size - 2)), int(min(math.floor(fy), Y.size - 2))
    tx, ty = fx - i0, fy - j0
    out = (
        V[j0, i0] * (1 - tx) * (1 - ty)
        + V[j0, i0 + 1] * tx * (1 - ty)
        + V[j0 + 1, i0] * (1 - tx) * ty
        + V[j0 + 1, i0 + 1] * tx * ty
    )
    return float(out[0]), float(out[1]), (px, py)


# ----------------------------------------------------------------- helpers


def predict(tgt, mjd):
    c = SkyCoord(
        ra=tgt["ra_j2000_deg"] * u.deg,
        dec=tgt["dec_j2000_deg"] * u.deg,
        pm_ra_cosdec=(tgt["pm_ra_cosdec_masyr"] or 0) * u.mas / u.yr,
        pm_dec=(tgt["pm_dec_masyr"] or 0) * u.mas / u.yr,
        distance=(1000.0 / tgt["parallax_mas"]) * u.pc,
        radial_velocity=(tgt.get("radial_velocity_kms") or 0) * u.km / u.s,
        obstime=Time(tgt["reference_epoch_jyear"], format="jyear"),
    )
    p = c.apply_space_motion(new_obstime=Time(mjd, format="mjd"))
    # crude linear control (no perspective acceleration)
    dt = (Time(mjd, format="mjd").jyear - tgt["reference_epoch_jyear"])
    dec_l = tgt["dec_j2000_deg"] + (tgt["pm_dec_masyr"] or 0) * dt / 3.6e6
    ra_l = tgt["ra_j2000_deg"] + (tgt["pm_ra_cosdec_masyr"] or 0) * dt / 3.6e6 / math.cos(math.radians(tgt["dec_j2000_deg"]))
    return float(p.ra.deg), float(p.dec.deg), ra_l, dec_l


def stretch(v, lo, hi, soft):
    t = np.clip((v - lo) / (hi - lo), 0, 1)
    return np.round(np.arcsinh(t * soft) / np.arcsinh(soft) * 255.0).astype(int)


def load_gaia(preset):
    p = HERE / "gaia" / f"{preset}.csv"
    if not p.exists():
        return []
    with p.open() as f:
        # 2-parameter Gaia solutions (no proper motion) are skipped rather than assumed static
        return [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f) if all(r.values())]


def gaia_at(star, mjd):
    dt = Time(mjd, format="mjd").jyear - star["ref_epoch"]
    dec = star["dec"] + star["pmdec"] * dt / 3.6e6
    ra = star["ra"] + star["pmra"] * dt / 3.6e6 / math.cos(math.radians(star["dec"]))
    return ra, dec


def despike(img):
    """Replace isolated single-pixel spikes (cosmic rays / hot pixels) by the
    median of their 4 neighbours, so they cannot capture a star centroid. A real
    star (PSF FWHM ~1.2 native px) always lifts at least one neighbour."""
    out = img.copy()
    p = np.pad(img, 1, mode="edge")
    nb = np.stack([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]])
    bg = np.nanmedian(img)
    with np.errstate(invalid="ignore"):
        spike = (img - bg) > 6 * (np.nanmax(nb, axis=0) - bg).clip(min=1e-6)
    out[spike] = np.nanmedian(nb, axis=0)[spike]
    return out


def native_centroid(img, x, y, half=2):
    ny, nx = img.shape
    ix, iy = int(round(x)), int(round(y))
    if ix - half - 2 < 0 or iy - half - 2 < 0 or ix + half + 2 >= nx or iy + half + 2 >= ny:
        return None
    win = img[iy - half - 2: iy + half + 3, ix - half - 2: ix + half + 3]
    if not np.isfinite(win).all():
        return None
    img = despike(img)
    # recentre on the local max within +-1 px
    sub = img[iy - 1: iy + 2, ix - 1: ix + 2]
    dy, dx = np.unravel_index(np.argmax(sub), sub.shape)
    cx, cy = ix + dx - 1, iy + dy - 1
    if cx - half < 0 or cy - half < 0 or cx + half >= nx or cy + half >= ny:
        return None
    w = img[cy - half: cy + half + 1, cx - half: cx + half + 1]
    bg_ring = img[max(cy - 6, 0): cy + 7, max(cx - 6, 0): cx + 7]
    bg = np.nanmedian(bg_ring)
    mad = np.nanmedian(np.abs(bg_ring - bg)) * 1.4826 + 1e-12
    if (w.max() - bg) < 15 * mad:
        return None
    wt = np.clip(w - bg, 0, None)
    yy, xx = np.mgrid[cy - half: cy + half + 1, cx - half: cx + half + 1]
    return float((wt * xx).sum() / wt.sum()), float((wt * yy).sum() / wt.sum()), float((w.max() - bg) / mad)


def png_centroid(gray, alpha, x, y, half=8):
    size = gray.shape[0]
    ix, iy = int(math.floor(x)), int(math.floor(y))
    if ix - 16 < 0 or iy - 16 < 0 or ix + 17 > size or iy + 17 > size:
        return None
    big = gray[iy - 16: iy + 17, ix - 16: ix + 17].astype(float)
    bal = alpha[iy - 16: iy + 17, ix - 16: ix + 17]
    if (bal == 0).any():
        return None
    bg = np.median(big)
    w = gray[iy - half: iy + half + 1, ix - half: ix + half + 1].astype(float) - bg
    w = np.clip(w, 0, None)
    if w.sum() <= 0:
        return None
    yy, xx = np.mgrid[iy - half: iy + half + 1, ix - half: ix + half + 1]
    # pixel centres are at +0.5 in the corner-origin convention
    return float((w * (xx + 0.5)).sum() / w.sum()), float((w * (yy + 0.5)).sum() / w.sum())


def git_show(ref, path):
    return subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True, check=True).stdout


# ----------------------------------------------------------------- main check


def check_one(rec, png_path, flags_path, raw_path, mrec, tgt, all_records_in_set):
    out = {"frame_key": rec["frame_key"], "checks": {}, "evidence": {}}
    C, E = out["checks"], out["evidence"]
    raw = Path(raw_path).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    hdul = fits.open(io.BytesIO(raw))
    ih = hdul["IMAGE"].header
    img = hdul["IMAGE"].data.astype(float)
    var = hdul["VARIANCE"].data.astype(float)
    flg = hdul["FLAGS"].data.astype(np.int64)
    ny, nx = img.shape
    cel = WCS(ih, fobj=hdul)
    reg = rec["registration"]
    ra0, dec0, fov, size = reg["center_ra_deg"], reg["center_dec_deg"], reg["fov_arcmin"], reg["width"]

    # ---- 3. time
    date_avg, mjd_avg = ih["DATE-AVG"], float(ih["MJD-AVG"])
    t_consistent = abs(Time(date_avg, format="isot", scale="utc").mjd - mjd_avg) * 86400 < 0.01
    C["time"] = (rec["observed_at_utc"].rstrip("Z") == date_avg and rec["mjd"] == mjd_avg and t_consistent
                 and ih.get("TIMESYS", "UTC").strip() == "UTC")
    E["time"] = {"DATE-AVG": date_avg, "MJD-AVG": mjd_avg, "record": [rec["observed_at_utc"], rec["mjd"]],
                 "DATE-OBS": ih["DATE-OBS"], "date_vs_mjd_consistent": t_consistent}

    # ---- target prediction + native position (header TAN-SIP)
    pra, pdec, lra, ldec = predict(tgt, mjd_avg)
    x, y = (float(v) for v in cel.all_world2pix([[pra, pdec]], 0)[0])
    inside = 0 <= x <= nx - 1 and 0 <= y <= ny - 1
    mx, my = sky_to_display(pra, pdec, ra0, dec0, fov, size)
    lx, ly = sky_to_display(lra, ldec, ra0, dec0, fov, size)
    E["target"] = {"pred_radec": [pra, pdec], "native_xy": [x, y], "native_shape": [ny, nx], "inside": inside,
                   "display_xy_independent": [mx, my], "display_xy_linear_pm_control": [lx, ly]}

    # ---- 1. sky registration
    reg_ok = True
    notes = []
    m = rec["marker"]
    if m is None or m["kind"] != "catalog_prediction":
        reg_ok = False
        notes.append("marker missing or not catalog_prediction")
    else:
        dm = math.hypot(m["x"] - mx, m["y"] - my)
        E["marker_minus_independent_px"] = dm
        E["marker_radec_minus_independent_arcsec"] = math.hypot(
            (m["ra_deg"] - pra) * math.cos(math.radians(pdec)), m["dec_deg"] - pdec) * 3600
        if dm > 0.05:
            reg_ok = False
            notes.append(f"marker differs from independent prediction by {dm:.3f} display px")
    if abs(rec["sampled_position"]["native_x"] - x) > 1e-3 or abs(rec["sampled_position"]["native_y"] - y) > 1e-3:
        reg_ok = False
        notes.append("sampled native position differs")
    # grid identity across the set
    keys = ("center_ra_deg", "center_dec_deg", "fov_arcmin", "width", "height", "projection", "orientation", "grid_id")
    same = all(all(r["registration"][k] == reg[k] for k in keys) for r in all_records_in_set)
    E["grid_identical_across_set"] = same
    reg_ok &= same
    # orientation sanity on the independent grid: 1' N and 1' E of centre
    nxp, nyp = sky_to_display(ra0, dec0 + 1 / 60, ra0, dec0, fov, size)
    exp_, eyp = sky_to_display(ra0 + (1 / 60) / math.cos(math.radians(dec0)), dec0, ra0, dec0, fov, size)
    E["orientation_probe"] = {"1arcmin_north_xy": [nxp, nyp], "1arcmin_east_xy": [exp_, eyp]}
    pc = cel.wcs.get_pc() * np.array(cel.wcs.cdelt)[:, None]
    E["native_parity_det"] = float(np.linalg.det(pc))  # sign flips between SWIR and MWIR arrays

    # full-image reconstruction (registration + stretch together)
    sra, sdec = display_centers_to_sky(ra0, dec0, fov, size)
    npx, npy = cel.all_world2pix(sra.ravel(), sdec.ravel(), 0, quiet=True)
    npx, npy = npx.reshape(size, size), npy.reshape(size, size)
    ix, iy = np.rint(npx).astype(int), np.rint(npy).astype(int)
    on = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    ixc, iyc = np.clip(ix, 0, nx - 1), np.clip(iy, 0, ny - 1)
    vals = img[iyc, ixc]
    good_native = np.isfinite(img) & np.isfinite(var) & (var > 0)
    good = on & good_native[iyc, ixc]
    ds = rec["display_scale"]
    exp_gray = np.zeros((size, size), int)
    exp_gray[good] = stretch(vals[good], ds["low"], ds["high"], ds["asinh_softening"])
    exp_alpha = np.where(good, 255, 0)
    pim = np.asarray(Image.open(png_path))
    gray, alpha = pim[..., 0].astype(int), pim[..., 1].astype(int)
    alpha_match = float((alpha == exp_alpha).mean())
    both = (alpha == 255) & (exp_alpha == 255)
    gdiff = np.abs(gray - exp_gray)[both]
    E["png_reconstruction"] = {
        "png_mode": Image.open(png_path).mode,
        "alpha_match_fraction": alpha_match,
        "gray_exact_fraction": float((gdiff == 0).mean()) if gdiff.size else None,
        "gray_within_1_fraction": float((gdiff <= 1).mean()) if gdiff.size else None,
        "gray_max_abs_diff": int(gdiff.max()) if gdiff.size else None,
        "opaque_pixels": int(both.sum()),
    }
    # mirrored reconstruction as a negative control: an X-flip error would match this instead
    flipped = np.fliplr(exp_gray)
    bothf = (alpha == 255) & (np.fliplr(exp_alpha) == 255)
    E["png_reconstruction"]["mirrored_control_exact_fraction"] = (
        float((np.abs(gray - flipped)[bothf] == 0).mean()) if bothf.any() else None)
    recon_ok = alpha_match > 0.995 and gdiff.size and (gdiff <= 1).mean() > 0.995
    reg_ok &= bool(recon_ok)
    out["_grid_values"] = vals[good]

    # Gaia stars: native centroid vs header WCS, PNG centroid vs independent grid
    stars = []
    for s in load_gaia(rec["preset_id"]):
        gra, gdec = gaia_at(s, mjd_avg)
        sep_t = math.hypot((gra - pra) * math.cos(math.radians(pdec)), gdec - pdec) * 3600
        if sep_t < 40:  # skip the target itself and its saturated halo
            continue
        gx, gy = (float(v) for v in cel.all_world2pix([[gra, gdec]], 0)[0])
        nc = native_centroid(img, gx, gy)
        if nc is None:
            continue
        dxp, dyp = sky_to_display(gra, gdec, ra0, dec0, fov, size)
        pc_ = png_centroid(gray, alpha, dxp, dyp)
        stars.append({
            "gaia": int(s["source_id"]), "G": s["phot_g_mean_mag"], "snr_peak_mad": round(nc[2], 1),
            "native_dx": nc[0] - gx, "native_dy": nc[1] - gy,
            "png_dx": None if pc_ is None else pc_[0] - dxp, "png_dy": None if pc_ is None else pc_[1] - dyp,
        })
    if stars:
        ndr = [math.hypot(s["native_dx"], s["native_dy"]) for s in stars]
        # Only stars that are unambiguously identified in the native image (native centroid
        # within 1 native px of Gaia) are used to test the PNG; others are blends, ghosts or
        # halo structure and say nothing about the processor.
        pngs = [s for s in stars if s["png_dx"] is not None and math.hypot(s["native_dx"], s["native_dy"]) < 1.0]
        E["gaia"] = {
            "n_native": len(stars),
            "native_median_offset_px": float(np.median(ndr)),
            "native_median_dx_dy": [float(np.median([s["native_dx"] for s in stars])), float(np.median([s["native_dy"] for s in stars]))],
            "n_png": len(pngs),
            "png_median_dx_dy_display_px": [float(np.median([s["png_dx"] for s in pngs])), float(np.median([s["png_dy"] for s in pngs]))] if pngs else None,
            "png_median_offset_display_px": float(np.median([math.hypot(s["png_dx"], s["png_dy"]) for s in pngs])) if pngs else None,
            "stars": stars,
        }
        if pngs and E["gaia"]["png_median_offset_display_px"] > 2.5:
            reg_ok = False
            notes.append("Gaia stars offset in PNG")
    else:
        E["gaia"] = None
    C["registration"] = bool(reg_ok)
    E["registration_notes"] = notes

    # ---- 2. wavelength
    if inside:
        wa, ba = wave_astropy(ih, hdul, x, y)
        wm, bm, psi = wave_manual(ih, hdul, x, y)
        E["wavelength"] = {"astropy_W_sip_none": [wa, ba], "manual_tab": [wm, bm], "tab_psi": psi,
                           "record": [rec["wavelength_um"], rec["bandwidth_um"]]}
        C["wavelength"] = (rec["wavelength_um"] is not None and abs(rec["wavelength_um"] - wa) < 1e-6
                           and abs(rec["bandwidth_um"] - ba) < 1e-6 and wm is not None and abs(wm - wa) < 1e-5)
    else:
        try:
            wa, ba = wave_astropy(ih, hdul, x, y)
        except Exception:
            wa = ba = None
        E["wavelength"] = {"would_be_extrapolated_um": wa, "record": [rec["wavelength_um"], rec["bandwidth_um"]],
                           "location_text": rec["wavelength_location"]}
        C["wavelength"] = rec["wavelength_um"] is None and rec["bandwidth_um"] is None

    # ---- 4. flags
    names = {}
    mask_ok = True
    for k in hdul["FLAGS"].header:
        if k.startswith("MSKN"):
            n = int(k[4:])
            names[n] = hdul["FLAGS"].header[k].strip()
            mm = hdul["FLAGS"].header.get(f"MSKM{k[4:]}")
            if mm is not None and mm != (1 << n):
                mask_ok = False
    named_bits = sum(1 << b for b in names)
    undocumented = int(((flg & ~named_bits) != 0).sum())
    q = rec["quality"]
    if inside:
        yy, xx = np.mgrid[0:ny, 0:nx]
        ap = (xx - x) ** 2 + (yy - y) ** 2 <= APERTURE_R ** 2
        nonfin = ap & ~good_native
        adv_bits = sum(1 << b for b, n in names.items() if n not in INFORMATIONAL)
        adverse = ap & (((flg & adv_bits) != 0) | ~good_native)
        counts = {n: int((ap & (((flg >> b) & 1) == 1)).sum()) for b, n in names.items()}
        counts = {k: v for k, v in counts.items() if v}
        exp_status = "flagged" if adverse.sum() else "clear"
        mine = {"screened": int(ap.sum()), "adverse": int(adverse.sum()), "valid": int((ap & ~adverse).sum()),
                "nonfinite": int(nonfin.sum()), "status": exp_status, "counts": counts}
        C["flags"] = (q["status"] == exp_status and q["covered"] is True and q["screened_pixels"] == mine["screened"]
                      and q["adverse_aperture_pixels"] == mine["adverse"] and q["valid_aperture_pixels"] == mine["valid"]
                      and q["nonfinite_aperture_pixels"] == mine["nonfinite"] and q["flag_counts"] == counts
                      and set(q["flag_names"]) == {k for k in counts if k not in INFORMATIONAL}
                      and not (set(q["flag_names"]) & INFORMATIONAL) and mask_ok)
        if mine["nonfinite"] and q["status"] != "flagged":
            C["flags"] = False
    else:
        mine = {"status": "not_covered"}
        C["flags"] = (q["status"] == "not_covered" and q["covered"] is False and q["valid_aperture_pixels"] is None
                      and q["adverse_aperture_pixels"] is None and q["screened_pixels"] is None)
    E["flags"] = {"independent": mine, "record": {k: q[k] for k in ("status", "screened_pixels", "valid_aperture_pixels",
                  "adverse_aperture_pixels", "nonfinite_aperture_pixels", "flag_names", "flag_counts")},
                  "msk_masks_consistent": mask_ok, "pixels_with_unnamed_bits_in_image": undocumented}
    # flag overlay reconstruction
    if flags_path and Path(flags_path).exists():
        adv_bits = sum(1 << b for b, n in names.items() if n not in INFORMATIONAL)
        f_s = flg[iyc, ixc]
        exp_rgba = np.zeros((size, size, 4), int)
        exp_rgba[on & ((f_s & adv_bits) != 0)] = (255, 64, 64, 150)
        exp_rgba[on & ~good_native[iyc, ixc]] = (255, 200, 0, 200)
        fpng = np.asarray(Image.open(flags_path)).astype(int)
        E["flag_overlay_match_fraction"] = float((fpng == exp_rgba).all(axis=2).mean())

    # ---- 5. absent coverage (geometric only)
    margin = min(x, nx - 1 - x, y, ny - 1 - y)
    C["coverage"] = (q["status"] == "not_covered") == (not inside) and q["covered"] == inside
    E["coverage"] = {"inside": inside, "signed_margin_native_px": margin}

    # ---- 6. display stretch (mode labels and photometry wording checked by caller)
    E["display_scale"] = {k: ds[k] for k in ("mode", "method", "low", "high", "basis")}

    # ---- 7. provenance
    pv = rec["provenance"]
    lim_text = " ".join(rec["limitations"]).lower()
    prov = {
        "sha_raw": sha, "sha_record": pv["sha256"], "sha_manifest": mrec.get("sha256"),
        "source_url_eq_manifest_archive_url": rec["source_url"] == mrec["archive_url"] == pv["original_url"],
        "cutout_url_eq_manifest_source_url": pv["cutout_url"] == mrec["source_url"],
        "collection_eq_manifest": rec["collection_id"] == mrec["collection"],
        "marker_kind": None if m is None else m["kind"],
        "marker_label": None if m is None else m.get("label"),
        "limitations_mention": {w: (w in lim_text) for w in ("not photometry", "not a detection", "catalog prediction", "adds no resolution")},
        "header_obsid_detector": [ih["OBSID"].strip(), int(ih["DETECTOR"])],
        "frame_key_ok": rec["frame_key"] == f"{ih['OBSID'].strip()}_D{int(ih['DETECTOR'])}",
    }
    E["provenance"] = prov
    C["provenance"] = (sha == pv["sha256"] == mrec.get("sha256") and prov["source_url_eq_manifest_archive_url"]
                       and prov["cutout_url_eq_manifest_source_url"] and prov["collection_eq_manifest"]
                       and prov["frame_key_ok"] and (m is None or m["kind"] == "catalog_prediction")
                       and all(prov["limitations_mention"].values()))
    hdul.close()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--products", default="backend/content/presets")
    ap.add_argument("--science-ref", default="origin/codex/sathvik-science")
    ap.add_argument("--out", default=str(HERE / "results.json"))
    ap.add_argument("--all", action="store_true", help="check every product record, not only the selected set")
    a = ap.parse_args(argv)
    data = Path(a.data_root)
    manifest = json.loads((data / "manifest.json").read_text())
    targets = {t["id"]: t for t in manifest["targets"]}
    mby = {f"{r['obs_id']}_D{r['detector']}": r for r in manifest["files"] if r.get("status") == "downloaded"}
    prod = Path(a.products)

    sets = {}
    for fj in sorted(glob.glob(str(prod / "*" / "*" / "frames.json"))):
        d = json.loads(Path(fj).read_text())
        sets[(d["preset_id"], d["set"])] = d

    todo = []
    if a.all:
        for (p, s), d in sets.items():
            for r in d["frames"]:
                todo.append((p, s, r["frame_key"], ""))
    else:
        todo = SELECTED

    results, grid_vals = [], {}
    for preset, set_name, key, why in todo:
        d = sets[(preset, set_name)]
        rec = next(r for r in d["frames"] if r["frame_key"] == key)
        per_file = json.loads((prod / preset / set_name / f"{key}.json").read_text())
        base = prod / preset / set_name / key
        mrec = mby[key]
        # query centre in the record must equal the manifest/targets query centre
        t = targets[preset]
        out = check_one(rec, f"{base}.png", f"{base}.flags.png", data / mrec["file"], mrec, t, d["frames"])
        out["evidence"]["per_file_json_equals_index"] = per_file == rec
        out["evidence"]["query_center_matches_manifest"] = (
            abs(rec["registration"]["center_ra_deg"] - t["query_ra_deg"]) < 1e-12
            and abs(rec["registration"]["center_dec_deg"] - t["query_dec_deg"]) < 1e-12)
        out["checks"]["registration"] &= out["evidence"]["query_center_matches_manifest"]
        out.update(preset=preset, set=set_name, why=why,
                   processing_version=rec["provenance"]["processing_version"], status=rec["quality"]["status"])
        grid_vals[(preset, set_name, key)] = out.pop("_grid_values")
        results.append(out)

    # ---- stretch: shared limits must be the pooled percentiles of the stated group
    for out in results:
        rec = next(r for r in sets[(out["preset"], out["set"])]["frames"] if r["frame_key"] == out["frame_key"])
        ds = rec["display_scale"]
        if ds["mode"] == "shared":
            group = [k for k in sets[(out["preset"], out["set"])]["frames"]
                     if k["display_scale"]["mode"] == "shared" and k["display_scale"]["low"] == ds["low"]]
            gkeys = [k["frame_key"] for k in group]
            pooled = []
            for k in gkeys:
                gv = grid_vals.get((out["preset"], out["set"], k))
                pooled.append(gv)
            if all(p is not None for p in pooled):
                lo, hi = np.percentile(np.concatenate(pooled), (1.0, 99.5))
                out["evidence"]["stretch_limits_recomputed"] = [float(lo), float(hi)]
                ok = abs(lo - ds["low"]) < 1e-6 * max(1, abs(lo)) and abs(hi - ds["high"]) < 1e-6 * max(1, abs(hi))
                ok &= all(k in ds["basis"] for k in gkeys)
            else:
                ok = None
            out["evidence"]["stretch_group"] = gkeys
        else:
            gv = grid_vals[(out["preset"], out["set"], out["frame_key"])]
            lo, hi = np.percentile(gv, (1.0, 99.5))
            out["evidence"]["stretch_limits_recomputed"] = [float(lo), float(hi)]
            ok = (abs(lo - ds["low"]) < 1e-6 * max(1, abs(lo)) and abs(hi - ds["high"]) < 1e-6 * max(1, abs(hi))
                  and "not directly comparable" in ds["basis"]
                  and any("not directly comparable" in l for l in rec["limitations"]))
        recon = out["evidence"]["png_reconstruction"]
        out["checks"]["stretch"] = bool(ok) and recon["gray_within_1_fraction"] is not None and recon["gray_within_1_fraction"] > 0.995

    # ---- case agreement (decision 6) against the case JSON on the science branch
    case_rows = {}
    for cid in ("fair_comparison", "moving_neighbor"):
        try:
            case = json.loads(git_show(a.science_ref, f"backend/content/cases/{cid}.json"))
        except Exception as exc:  # pragma: no cover
            case_rows[cid] = {"error": repr(exc)}
            continue
        for f in case["frames"]:
            r = next((o for o in results if o["frame_key"] == f["frame_key"] and o["set"] == f"case-{cid}"), None)
            rec = next(x for x in sets[(case["target_id"], f"case-{cid}")]["frames"] if x["frame_key"] == f["frame_key"])
            case_rows[f["frame_key"]] = {
                "ref": f["ref"],
                "wavelength_abs_diff": abs(rec["wavelength_um"] - f["wavelength_um"]),
                "bandwidth_abs_diff": abs(rec["bandwidth_um"] - f["bandwidth_um"]),
                "date_equal_ignoring_Z": rec["observed_at_utc"].rstrip("Z") == f["observed_at_utc"],
                "date_string_equal_verbatim": rec["observed_at_utc"] == f["observed_at_utc"],
                "mjd_equal": rec["mjd"] == f["mjd"],
                "status_equal": rec["quality"]["status"] == f["expected_quality_status"],
                "sha_equal": rec["provenance"]["sha256"] == f["sha256_of_retained_cutout"],
                "url_equal": rec["source_url"] == f["source_url"],
                "marker_xy": [rec["marker"]["x"], rec["marker"]["y"]],
            }
            if r is not None:
                r["checks"]["case_match"] = (case_rows[f["frame_key"]]["wavelength_abs_diff"] <= 1e-4
                                             and case_rows[f["frame_key"]]["date_equal_ignoring_Z"]
                                             and case_rows[f["frame_key"]]["mjd_equal"]
                                             and case_rows[f["frame_key"]]["status_equal"]
                                             and case_rows[f["frame_key"]]["sha_equal"]
                                             and case_rows[f["frame_key"]]["url_equal"])

    # ---- moving_neighbor marker motion vs case text; gate-2 coordinate epoch
    mn = [o for o in results if o["set"] == "case-moving_neighbor"]
    motion = None
    if len(mn) == 3:
        xy = {o["frame_key"]: o["evidence"]["target"]["display_xy_independent"] for o in mn}
        ks = [o["frame_key"] for o in mn]
        A = xy[ks[0]]
        scale = sets[("barnards_star", "case-moving_neighbor")]["frames"][0]["registration"]["scale_arcsec_per_px"]
        motion = {k: {"dx": xy[k][0] - A[0], "dy": xy[k][1] - A[1],
                      "display_px": math.hypot(xy[k][0] - A[0], xy[k][1] - A[1]),
                      "arcsec": math.hypot(xy[k][0] - A[0], xy[k][1] - A[1]) * scale} for k in ks[1:]}
        motion["display_scale_arcsec_per_px"] = scale
    # Gaia DR3 6412595290592307840 (eps Ind A), epoch J2016.0, fetched from the ESA Gaia TAP service
    eps_a = SkyCoord(ra=330.8724078795965 * u.deg, dec=-56.79725466122902 * u.deg,
                     pm_ra_cosdec=3966.6605387484133 * u.mas / u.yr, pm_dec=-2536.1919868044724 * u.mas / u.yr,
                     distance=(1000 / 274.8431415216296) * u.pc, radial_velocity=-40.4267 * u.km / u.s,
                     obstime=Time(2016.0, format="jyear"))
    gate = {}
    q = SkyCoord(330.84 * u.deg, -56.786 * u.deg)
    for ep in (2000.0, 2025.5, 2026.0, 2026.9):
        p = eps_a.apply_space_motion(new_obstime=Time(ep, format="jyear"))
        gate[str(ep)] = {"ra": float(p.ra.deg), "dec": float(p.dec.deg),
                         "sep_from_330.84_-56.786_arcsec": float(SkyCoord(p.ra, p.dec).separation(q).arcsec)}

    summary_cols = ["registration", "wavelength", "time", "flags", "coverage", "stretch", "provenance", "case_match"]
    matrix = [{"frame_key": o["frame_key"], "preset": o["preset"], "set": o["set"], "why": o["why"], "status": o["status"],
               **{c: o["checks"].get(c) for c in summary_cols}} for o in results]
    out = {"processor_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
           "matrix": matrix, "case_rows": case_rows, "moving_neighbor_marker_motion": motion,
           "gate2_eps_ind_a": gate, "frames": results}
    Path(a.out).write_text(json.dumps(out, indent=1, default=float) + "\n")
    fails = [(m["frame_key"], c) for m in matrix for c in summary_cols if m[c] is False]
    print(json.dumps({"n": len(matrix), "fails": fails, "motion": motion, "gate2": gate}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
