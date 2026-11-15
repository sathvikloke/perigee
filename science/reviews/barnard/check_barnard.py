"""Barnard's Star moving_neighbor case review (parallel worker 10).

Read-only review tool. It does not import backend/ or tools/ingest. It checks the
moving_neighbor case against the original FITS cutouts and the published PNGs:

1. marker motion: catalog prediction re-derived (SIMBAD J2000 + Gaia DR3 row as a
   cross-check), projected with a hand-written north-up/east-left gnomonic grid;
2. surrounding-source stability: Gaia DR3 field stars centroided in the native
   image (mapped to the grid through the raw header WCS) and in the case PNGs;
3. visual glow shift: an intensity-weighted "glow centre" of the saturated star
   (non-finite core filled as white). This is a VISUAL proxy, not astrometry;
4. per-frame facts for all 34 retained frames, to rank alternative frame trios;
5. a small annotated contact sheet of A/B/C.

Usage (repository root):
    .venv/bin/python science/reviews/barnard/check_barnard.py \
        --data-root "/path/to/research/build_data"
Outputs: science/reviews/barnard/results.json and contact_sheet.png
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import warnings
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from PIL import Image, ImageDraw, ImageFont

warnings.simplefilter("ignore")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRESET = ROOT / "backend/content/presets/barnards_star"
GAIA_CSV = ROOT / "science/reviews/acceptance/gaia/barnards_star.csv"
CASE = ["2025W35_1A_0008_1_D3", "2026W12_1A_0610_2_D3", "2026W34_1A_0431_1_D3"]
SIZE, FOV_ARCMIN = 256, 6.0
SCALE = FOV_ARCMIN * 60 / SIZE  # arcsec per display px
BARNARD_GAIA_ID = "4472832130942575872"


# ---------------------------------------------------------------- geometry
def gnomonic(ra, dec, ra0, dec0):
    a, d, a0, d0 = map(np.radians, (ra, dec, ra0, dec0))
    cosc = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(a - a0)
    xi = np.cos(d) * np.sin(a - a0) / cosc
    eta = (np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(a - a0)) / cosc
    return xi, eta


def to_grid(ra, dec, ra0, dec0):
    """Display px, origin top-left corner, north up, east left."""
    s = math.radians(FOV_ARCMIN / 60.0) / SIZE
    xi, eta = gnomonic(ra, dec, ra0, dec0)
    return SIZE / 2.0 - xi / s, SIZE / 2.0 - eta / s


def predict_simbad(t, mjd):
    c = SkyCoord(ra=t["ra_j2000_deg"] * u.deg, dec=t["dec_j2000_deg"] * u.deg,
                 pm_ra_cosdec=t["pm_ra_cosdec_masyr"] * u.mas / u.yr,
                 pm_dec=t["pm_dec_masyr"] * u.mas / u.yr,
                 distance=(1000.0 / t["parallax_mas"]) * u.pc,
                 radial_velocity=t["radial_velocity_kms"] * u.km / u.s,
                 obstime=Time(t["reference_epoch_jyear"], format="jyear"))
    p = c.apply_space_motion(new_obstime=Time(mjd, format="mjd"))
    return float(p.ra.deg), float(p.dec.deg)


def gaia_at(s, mjd):
    dt = Time(mjd, format="mjd").jyear - s["ref_epoch"]
    dec = s["dec"] + s["pmdec"] * dt / 3.6e6
    ra = s["ra"] + s["pmra"] * dt / 3.6e6 / math.cos(math.radians(s["dec"]))
    return ra, dec


# ---------------------------------------------------------------- centroids
def native_star_centroid(img, x, y, half=2):
    """Background-subtracted first moment around the local max; None if unclean."""
    ny, nx = img.shape
    ix, iy = int(round(x)), int(round(y))
    if not (half + 6 <= ix < nx - half - 6 and half + 6 <= iy < ny - half - 6):
        return None
    sub = img[iy - 1: iy + 2, ix - 1: ix + 2]
    if not np.isfinite(sub).all():
        return None
    dy, dx = np.unravel_index(np.argmax(sub), sub.shape)
    cx, cy = ix + dx - 1, iy + dy - 1
    w = img[cy - half: cy + half + 1, cx - half: cx + half + 1]
    ring = img[cy - 6: cy + 7, cx - 6: cx + 7]
    if not np.isfinite(w).all():
        return None
    bg = np.nanmedian(ring)
    mad = 1.4826 * np.nanmedian(np.abs(ring - bg)) + 1e-12
    snr = (w.max() - bg) / mad
    # reject single-pixel spikes: a real star lifts a neighbour too
    nb = sorted(w[half - 1: half + 2, half - 1: half + 2].ravel())[-2]
    if snr < 15 or (nb - bg) < 0.15 * (w.max() - bg):
        return None
    wt = np.clip(w - bg, 0, None)
    yy, xx = np.mgrid[cy - half: cy + half + 1, cx - half: cx + half + 1]
    return float((wt * xx).sum() / wt.sum()), float((wt * yy).sum() / wt.sum()), float(snr)


def glow_centre_native(img, x, y, r=4.0, iters=6):
    """Visual glow centre of a saturated star: non-finite pixels inside r count as
    the window maximum (they are saturated, not empty). Not an astrometric fit."""
    ny, nx = img.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    cx, cy = x, y
    for _ in range(iters):
        d = np.hypot(xx - cx, yy - cy)
        win = d <= r
        ann = (d > r + 2) & (d <= r + 6) & np.isfinite(img)
        bg = np.median(img[ann])
        v = img.copy()
        top = np.nanmax(np.where(win, img, np.nan))
        v[win & ~np.isfinite(img)] = top
        w = np.clip(np.where(win, v, 0) - bg, 0, None)
        cx, cy = float((w * xx).sum() / w.sum()), float((w * yy).sum() / w.sum())
    return cx, cy, int((np.hypot(xx - x, yy - y) <= 3) .__and__(~np.isfinite(img)).sum())


def glow_centre_png(gray, alpha, x, y, half=7, iters=6):
    """Same visual proxy on the published PNG: transparent pixels inside the window
    are treated as white (they are the saturated core)."""
    g = gray.astype(float).copy()
    cx, cy = x, y
    for _ in range(iters):
        ix, iy = int(math.floor(cx)), int(math.floor(cy))
        win = g[iy - half: iy + half + 1, ix - half: ix + half + 1].copy()
        a = alpha[iy - half: iy + half + 1, ix - half: ix + half + 1]
        win[a == 0] = 255.0
        bg = np.median(g[iy - 20: iy + 21, ix - 20: ix + 21][alpha[iy - 20: iy + 21, ix - 20: ix + 21] > 0])
        w = np.clip(win - bg, 0, None)
        yy, xx = np.mgrid[iy - half: iy + half + 1, ix - half: ix + half + 1]
        cx = float((w * (xx + 0.5)).sum() / w.sum())
        cy = float((w * (yy + 0.5)).sum() / w.sum())
    return cx, cy


def png_star_centroid(gray, alpha, x, y, half=4):
    ix, iy = int(math.floor(x)), int(math.floor(y))
    if ix - 12 < 0 or iy - 12 < 0 or ix + 13 > SIZE or iy + 13 > SIZE:
        return None
    big = gray[iy - 12: iy + 13, ix - 12: ix + 13].astype(float)
    if (alpha[iy - 12: iy + 13, ix - 12: ix + 13] == 0).any():
        return None
    bg = np.median(big)
    w = np.clip(gray[iy - half: iy + half + 1, ix - half: ix + half + 1].astype(float) - bg, 0, None)
    if w.sum() <= 0:
        return None
    yy, xx = np.mgrid[iy - half: iy + half + 1, ix - half: ix + half + 1]
    return float((w * (xx + 0.5)).sum() / w.sum()), float((w * (yy + 0.5)).sum() / w.sum())


# ---------------------------------------------------------------- main
def raw_path(raw_dir, key):
    obs, det = key.rsplit("_D", 1)
    hits = glob.glob(str(raw_dir / f"level2_{obs}D{det}_spx_*.fits"))
    assert len(hits) == 1, (key, hits)
    return hits[0]


def load_gaia():
    with GAIA_CSV.open() as f:
        rows = [r for r in csv.DictReader(f) if all(r.values())]
    stars = [{k: (r[k] if k == "source_id" else float(r[k])) for k in r} for r in rows]
    return stars


def analyse_frame(key, raw_dir, tgt, gaia, q):
    hd = fits.open(raw_path(raw_dir, key))
    ih = hd["IMAGE"].header
    img = hd["IMAGE"].data.astype(float)
    w = WCS(ih)
    mjd = float(ih["MJD-AVG"])
    ra0, dec0 = q["ra_deg"], q["dec_deg"]
    ra_s, dec_s = predict_simbad(tgt, mjd)
    mx, my = to_grid(ra_s, dec_s, ra0, dec0)
    barn = next(s for s in gaia if s["source_id"] == BARNARD_GAIA_ID)
    gx, gy = to_grid(*gaia_at(barn, mjd), ra0, dec0)
    nxp, nyp = w.all_world2pix(ra_s, dec_s, 0)
    gcx, gcy, nf3 = glow_centre_native(img, float(nxp), float(nyp))
    gra, gdec = w.all_pix2world(gcx, gcy, 0)
    glx, gly = to_grid(float(gra), float(gdec), ra0, dec0)
    stars = []
    for s in gaia:
        if s["source_id"] == BARNARD_GAIA_ID:
            continue
        sra, sdec = gaia_at(s, mjd)
        sx, sy = w.all_world2pix(sra, sdec, 0)
        c = native_star_centroid(img, float(sx), float(sy))
        if c is None or math.hypot(c[0] - sx, c[1] - sy) > 1.0:
            continue
        cra, cdec = w.all_pix2world(c[0], c[1], 0)
        dx, dy = to_grid(float(cra), float(cdec), ra0, dec0)
        ex, ey = to_grid(sra, sdec, ra0, dec0)
        stars.append({"source_id": s["source_id"], "G": s["phot_g_mean_mag"],
                      "grid_expected": [ex, ey], "grid_measured": [dx, dy],
                      "resid_px": [dx - ex, dy - ey], "snr": c[2]})
    res = np.array([s["resid_px"] for s in stars]) if stars else np.zeros((0, 2))
    return {
        "frame_key": key, "date_avg": ih["DATE-AVG"], "mjd": mjd, "detector": int(ih["DETECTOR"]),
        "marker_simbad": [mx, my], "marker_gaia_dr3": [gx, gy],
        "glow_native_to_grid": [glx, gly],
        "nonfinite_within_3_native_px": nf3,
        "field_stars_n": len(stars),
        "field_star_median_resid_px": res.mean(0).tolist() if len(stars) == 0 else np.median(res, 0).tolist(),
        "field_star_rms_resid_px": float(np.sqrt((res ** 2).sum(1).mean())) if len(stars) else None,
        "field_stars": stars,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    args = ap.parse_args()
    data = Path(args.data_root)
    raw_dir = data / "raw/barnards_star"
    manifest = json.loads((data / "manifest.json").read_text())
    tgt = next(t for t in manifest["targets"] if t["id"] == "barnards_star")
    q = {"ra_deg": tgt["query_ra_deg"], "dec_deg": tgt["query_dec_deg"]}
    gaia = load_gaia()

    # ---- all 34 retained frames (per-frame records for wavelength/flags)
    frames = {}
    for f in sorted((PRESET / "frames").glob("*_D?.json")):
        r = json.loads(f.read_text())
        a = analyse_frame(r["frame_key"], raw_dir, tgt, gaia, q)
        a.update({"wavelength_um": r["wavelength_um"], "collection_id": r["collection_id"],
                  "quality": {k: r["quality"][k] for k in ("status", "screened_pixels",
                              "adverse_aperture_pixels", "nonfinite_aperture_pixels", "flag_names")},
                  "processor_marker": [r["marker"]["x"], r["marker"]["y"]]})
        frames[r["frame_key"]] = a

    # ---- case set: PNG-level checks (shared stretch)
    case = {}
    pngs = {}
    for ref, key in zip("ABC", CASE):
        rec = json.loads((PRESET / "case-moving_neighbor" / f"{key}.json").read_text())
        im = np.array(Image.open(PRESET / "case-moving_neighbor" / f"{key}.png").convert("LA"))
        gray, alpha = im[..., 0], im[..., 1]
        pngs[ref] = (gray, alpha, rec)
        m = (rec["marker"]["x"], rec["marker"]["y"])
        gl = glow_centre_png(gray, alpha, *m)
        flags = np.array(Image.open(PRESET / "case-moving_neighbor" / f"{key}.flags.png").convert("RGBA"))
        case[ref] = {"frame_key": key, "marker": list(m), "glow_png": list(gl),
                     "transparent_px_total": int((alpha == 0).sum()),
                     "transparent_px_within_10px_of_marker": int(sum(
                         1 for yy, xx in zip(*np.nonzero(alpha == 0)) if math.hypot(xx + .5 - m[0], yy + .5 - m[1]) <= 10)),
                     "flag_overlay_nonzero_px": int((flags[..., 3] > 0).sum()),
                     "registration": rec["registration"]["grid_id"],
                     "display_scale": [rec["display_scale"]["low"], rec["display_scale"]["high"]]}
    # field stars centroided in PNGs: stars found in all three frames
    common = None
    for ref in "ABC":
        ids = {s["source_id"] for s in frames[case[ref]["frame_key"]]["field_stars"]}
        common = ids if common is None else common & ids
    png_ref = []
    for sid in sorted(common or []):
        row = {"source_id": sid}
        for ref in "ABC":
            fs = next(s for s in frames[case[ref]["frame_key"]]["field_stars"] if s["source_id"] == sid)
            row["G"] = fs["G"]
            gray, alpha, _ = pngs[ref]
            row[ref] = png_star_centroid(gray, alpha, *fs["grid_expected"])
        if all(row[r] for r in "ABC"):
            row["shift_AB_px"] = [row["B"][0] - row["A"][0], row["B"][1] - row["A"][1]]
            row["shift_AC_px"] = [row["C"][0] - row["A"][0], row["C"][1] - row["A"][1]]
            png_ref.append(row)

    # two Gaia stars closer than 5 display px land in one blob: keep the brighter only
    png_ref.sort(key=lambda r: r["G"])
    kept = []
    for r in png_ref:
        if all(math.hypot(r["A"][0] - k["A"][0], r["A"][1] - k["A"][1]) > 5 for k in kept):
            kept.append(r)
    png_ref = sorted(kept, key=lambda r: r["A"][1])

    def d(a, b):
        return [b[0] - a[0], b[1] - a[1], math.hypot(b[0] - a[0], b[1] - a[1])]

    summary = {
        "grid_arcsec_per_px": SCALE,
        "marker_shift_AB": d(case["A"]["marker"], case["B"]["marker"]),
        "marker_shift_AC": d(case["A"]["marker"], case["C"]["marker"]),
        "glow_png_shift_AB": d(case["A"]["glow_png"], case["B"]["glow_png"]),
        "glow_png_shift_AC": d(case["A"]["glow_png"], case["C"]["glow_png"]),
        "glow_native_shift_AB": d(frames[CASE[0]]["glow_native_to_grid"], frames[CASE[1]]["glow_native_to_grid"]),
        "glow_native_shift_AC": d(frames[CASE[0]]["glow_native_to_grid"], frames[CASE[2]]["glow_native_to_grid"]),
        "marker_simbad_vs_processor_max_px": max(math.hypot(f["marker_simbad"][0] - f["processor_marker"][0],
                                                             f["marker_simbad"][1] - f["processor_marker"][1]) for f in frames.values()),
        "marker_simbad_vs_gaia_dr3_max_px": max(math.hypot(f["marker_simbad"][0] - f["marker_gaia_dr3"][0],
                                                            f["marker_simbad"][1] - f["marker_gaia_dr3"][1]) for f in frames.values()),
        "png_reference_stars": png_ref,
    }
    if png_ref:
        ab = np.array([r["shift_AB_px"] for r in png_ref])
        ac = np.array([r["shift_AC_px"] for r in png_ref])
        summary["png_reference_star_median_shift_AB"] = np.median(ab, 0).tolist()
        summary["png_reference_star_median_shift_AC"] = np.median(ac, 0).tolist()
        summary["png_reference_star_max_abs_shift_px"] = float(np.abs(np.vstack([ab, ac])).max())

    out = {"case": case, "summary": summary, "frames": frames}
    (HERE / "results.json").write_text(json.dumps(out, indent=1, default=float))
    contact_sheet(pngs, case, png_ref)

    # ---- console report
    print(f"grid {SCALE:.5f} arcsec/px")
    for k in ("marker_shift_AB", "marker_shift_AC", "glow_png_shift_AB", "glow_png_shift_AC",
              "glow_native_shift_AB", "glow_native_shift_AC"):
        v = summary[k]
        print(f"{k:24s} dx={v[0]:+.2f} dy={v[1]:+.2f} |d|={v[2]:.2f} px = {v[2]*SCALE:.2f}\"")
    print("marker SIMBAD vs processor max px", round(summary["marker_simbad_vs_processor_max_px"], 4))
    print("marker SIMBAD vs Gaia DR3 max px", round(summary["marker_simbad_vs_gaia_dr3_max_px"], 3))
    print("PNG ref stars in A,B,C:", len(png_ref), "median AB", summary.get("png_reference_star_median_shift_AB"),
          "AC", summary.get("png_reference_star_median_shift_AC"), "max", summary.get("png_reference_star_max_abs_shift_px"))
    for ref in "ABC":
        c = case[ref]
        f = frames[c["frame_key"]]
        print(ref, c["frame_key"], "transparent", c["transparent_px_total"], "near marker", c["transparent_px_within_10px_of_marker"],
              "nstars", f["field_stars_n"], "med resid", np.round(f["field_star_median_resid_px"], 2), "rms", round(f["field_star_rms_resid_px"] or -1, 2))
    print("\nkey det date lam nf3 nstars rms glow-marker(dx,dy) marker_y")
    for k, f in frames.items():
        gm = np.subtract(f["glow_native_to_grid"], f["marker_simbad"])
        print(k, f["detector"], f["date_avg"][:10], f"{f['wavelength_um']:.3f}", f["nonfinite_within_3_native_px"],
              f["field_stars_n"], None if f["field_star_rms_resid_px"] is None else round(f["field_star_rms_resid_px"], 2),
              np.round(gm, 2), round(f["marker_simbad"][1], 2))


def contact_sheet(pngs, case, png_ref, half=32, zoom=4):
    """Top row: full A/B/C grids with labelled Gaia reference stars. Bottom row:
    64x64 display-px crops around the star at 4x, with the catalog marker and a
    fixed guide line through marker A. Non-finite (transparent) pixels in blue."""
    W, pad, top, gap, foot = SIZE, 8, 36, 10, 56
    sheet = Image.new("RGB", (3 * W + 4 * pad, top + W + gap + W + foot), (24, 24, 28))
    dr = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
    yA = case["A"]["marker"][1]
    cx, cy = int(round(case["A"]["marker"][0])), int(round(yA)) - 4
    for i, ref in enumerate("ABC"):
        gray, alpha, rec = pngs[ref]
        rgb = np.stack([gray] * 3, -1).astype(np.uint8)
        rgb[alpha == 0] = (0, 90, 200)
        x0 = pad + i * (W + pad)
        sheet.paste(Image.fromarray(rgb), (x0, top))
        dr.rectangle([x0 + cx - half, top + cy - half, x0 + cx + half, top + cy + half], outline=(0, 220, 120))
        for n, r in enumerate(png_ref, 1):
            sx, sy = x0 + r[ref][0], top + r[ref][1]
            dr.ellipse([sx - 7, sy - 7, sx + 7, sy + 7], outline=(255, 200, 0), width=1)
            dr.text((sx + 8, sy - 7), f"R{n}", fill=(255, 200, 0), font=font)
        dr.text((x0, 4), f"{ref}  {rec['frame_key']}", fill=(235, 235, 235), font=font)
        dr.text((x0, 19), f"{rec['observed_at_utc'][:10]}   {rec['wavelength_um']:.3f} um   detector {rec['detector']}",
                fill=(170, 170, 170), font=font)
        crop = rgb[cy - half: cy + half, cx - half: cx + half]
        y1 = top + W + gap
        sheet.paste(Image.fromarray(crop).resize((W, W), Image.NEAREST), (x0, y1))

        def P(x, y):
            return x0 + (x - (cx - half)) * zoom, y1 + (y - (cy - half)) * zoom
        _, gy = P(0, yA)
        dr.line([(x0, gy), (x0 + W, gy)], fill=(0, 220, 120), width=1)
        mx, my = P(*case[ref]["marker"])
        for a, b in (((-12, 0), (-5, 0)), ((5, 0), (12, 0)), ((0, -12), (0, -5)), ((0, 5), (0, 12))):
            dr.line([(mx + a[0], my + a[1]), (mx + b[0], my + b[1])], fill=(255, 60, 200), width=2)
    ft = top + 2 * W + gap + 6
    dr.text((pad, ft), "Top: full 6' grid (256 px, 1.406\"/px), north up, east left, shared stretch. "
            "Yellow R1-R6: Gaia DR3 field stars. Green box: zoom region.", fill=(220, 220, 220), font=font)
    dr.text((pad, ft + 15), "Bottom: 4x zoom. Magenta cross: catalog prediction (not a detection). "
            "Green line: fixed at A's marker.", fill=(220, 220, 220), font=font)
    dr.text((pad, ft + 30), "Blue: non-finite saturated pixels (transparent in the shipped PNG; "
            "flagged, not empty sky).", fill=(220, 220, 220), font=font)
    sheet.save(HERE / "contact_sheet.png", optimize=True)


if __name__ == "__main__":
    main()
