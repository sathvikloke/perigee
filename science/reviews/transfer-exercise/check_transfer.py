"""Draft transfer exercise (B5): derive every number from shipped records and raw FITS.

DRAFT for science review. Not a shipped case. Nothing under backend/ is written.

Frames (all shipped in backend/content/presets/wise_0855/frames/, all on the
same fixed grid as the WISE 0855 preset):

  P = 2025W45_2A_0278_1_D2   2025-11-07, D2
  Q = 2025W46_1A_0108_1_D2   2025-11-10, D2
  R = 2026W20_1A_0214_1_D2   2026-05-11, D2

What it does, per frame:
  * reads the shipped FrameRecord (dates, wavelength at the marker, bandwidth,
    quality, per-frame display_scale, marker, provenance);
  * finds the raw cutout in research/build_data/manifest.json by obs_id +
    detector, hashes the raw file, and checks record sha256 == manifest sha256 ==
    sha256(file);
  * re-runs processor A (backend/data/process.py) on the raw FITS with the same
    inputs tools/ingest uses, and checks that the record fields and the PNG bytes
    reproduce;
  * re-runs it again with one shared stretch for P+Q (only to show what the
    per-frame stretch does; not proposed as a product);
  * a census of bright compact spots (native local maxima drawn white by each
    frame's own stretch): adverse FLAGS names, detector pixel (WCS key A),
    single-pixel test, nearest cached Gaia DR3 star (G < 17,
    science/reviews/acceptance/gaia/wise_0855.csv) and whether the other frames
    show something at the same sky position;
  * the grey level each frame's stretch gives the same sky value;
  * the WISE 0855 catalog-predicted shift between frames, and where the cached
    Gaia DR3 neighbour 5756956644387831296 falls relative to the marker.

None of this is photometry, a detection test or a measured proper motion.
Raw values are a reviewer check (single flagged pixel vs star-shaped source),
not learner-facing brightness numbers.

Usage (repository root):
    .venv/bin/python science/reviews/transfer-exercise/check_transfer.py \
        --data-root "/path/to/research/build_data"

Writes results.json and contact_sheet.png next to this file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image, ImageDraw

warnings.simplefilter("ignore")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from backend.data.process import (  # noqa: E402
    FrameInput,
    display_limits_from_values,
    flag_bit_names,
    grid_wcs,
    process_frame,
    sky_to_display_px,
)
from tools.ingest.ingest import target_input  # noqa: E402

PRESET = "wise_0855"
FRAMES = [("P", "2025W45_2A_0278_1_D2"), ("Q", "2025W46_1A_0108_1_D2"), ("R", "2026W20_1A_0214_1_D2")]
NEIGHBOUR = "5756956644387831296"  # Gaia DR3, G = 16.3 (science/reviews/targets row 8)
INFORMATIONAL = {"SOURCE", "FULLSAMPLE"}

REC_DIR = REPO / "backend/content/presets" / PRESET / "frames"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gaia_at(row, jyear):
    dt = jyear - float(row["ref_epoch"])
    pmra, pmdec = float(row["pmra"] or 0.0), float(row["pmdec"] or 0.0)  # 2-parameter Gaia rows: no PM
    dec = float(row["dec"]) + pmdec * dt / 3.6e6
    ra = float(row["ra"]) + pmra * dt / 3.6e6 / math.cos(math.radians(float(row["dec"])))
    return ra, dec


def mjd_to_jyear(mjd: float) -> float:
    return 2000.0 + (mjd - 51544.5) / 365.25


def native_flags_at(hdul, ra, dec):
    """Adverse FLAGS names at the native pixel containing (ra, dec)."""
    ih = hdul["IMAGE"].header
    cel = WCS(ih, fobj=hdul).celestial
    x, y = cel.all_world2pix([[ra, dec]], 0)[0]
    ix, iy = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
    fl = np.asarray(hdul["FLAGS"].data).astype(np.int64)
    names = flag_bit_names(hdul["FLAGS"].header)
    ny, nx = fl.shape
    if not (0 <= ix < nx and 0 <= iy < ny):
        return None
    v = int(fl[iy, ix])
    return sorted(n for b, n in names.items() if v >> b & 1 and n not in INFORMATIONAL)


def full_grid(hdul, gw, size):
    """Display-oriented (row 0 = north) grid of native values, NaN where the
    processor would leave the pixel transparent; same sampling as process.py."""
    ih = hdul["IMAGE"].header
    cel = WCS(ih, fobj=hdul).celestial
    img = np.asarray(hdul["IMAGE"].data, dtype=np.float64)
    var = np.asarray(hdul["VARIANCE"].data, dtype=np.float64)
    finite = np.isfinite(img) & np.isfinite(var) & (var > 0)
    gy, gx = np.mgrid[0:size, 0:size]
    ra_g, dec_g = gw.wcs_pix2world(gx.ravel().astype(float), gy.ravel().astype(float), 0)
    nxp, nyp = cel.all_world2pix(ra_g, dec_g, 0, quiet=True)
    ix = np.floor(nxp + 0.5).astype(np.int64).reshape(size, size)
    iy = np.floor(nyp + 0.5).astype(np.int64).reshape(size, size)
    ny, nx = img.shape
    ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    vals = np.full((size, size), np.nan)
    vals[ok] = np.where(finite[iy[ok], ix[ok]], img[iy[ok], ix[ok]], np.nan)
    return np.flipud(vals)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True, type=Path)
    a = ap.parse_args()
    root = a.data_root
    manifest = json.loads((root / "manifest.json").read_text())
    targets = json.loads((REPO / "backend/content/targets.json").read_text())
    tgt = next(t for t in targets["targets"] if t["id"] == PRESET)
    qc = tgt["query_center"]
    with open(REPO / "science/reviews/acceptance/gaia/wise_0855.csv") as f:
        gaia = list(csv.DictReader(f))

    out = {"preset": PRESET, "targets_content_version": targets["content_version"],
           "manifest_created_utc": manifest["created_utc"], "frames": {}}
    recs, raw, products = {}, {}, {}
    for ref, key in FRAMES:
        rec = json.loads((REC_DIR / f"{key}.json").read_text())
        recs[ref] = rec
        obs, det = rec["observation_id"], rec["detector"]
        ent = [e for e in manifest["files"] if e.get("obs_id") == obs and e.get("detector") == det
               and e.get("target_id") == PRESET and e.get("status") == "downloaded"]
        assert len(ent) == 1, (key, len(ent))
        ent = ent[0]
        path = root / ent["file"]
        file_sha = sha256_file(path)
        data = path.read_bytes()
        hdul = fits.open(path, memmap=False)
        raw[ref] = hdul
        ih = hdul["IMAGE"].header
        meta = FrameInput(
            query_ra_deg=qc["ra_deg"], query_dec_deg=qc["dec_deg"],
            fov_arcmin=float(tgt.get("default_fov_arcmin") or 6), target=target_input(tgt),
            source_url=ent["archive_url"], cutout_url=ent["source_url"], observation_id=obs,
            collection_id=ent["collection"], detector=det, retrieved_at_utc=manifest.get("created_utc"),
            retrieved_at_basis="Download-ledger creation time (manifest.json created_utc); per-file retrieval time not recorded.",
            expected_sha256=ent["sha256"])
        pf = process_frame(data, meta)
        products[ref] = (meta, data, pf)
        r2 = pf.record
        shipped_png = (REC_DIR / f"{key}.png").read_bytes()
        q = rec["quality"]
        out["frames"][ref] = {
            "frame_key": key,
            "observation_id": obs,
            "detector": det,
            "collection_id": rec["collection_id"],
            "header": {"OBSID": str(ih.get("OBSID")).strip(), "DETECTOR": int(ih["DETECTOR"]),
                       "DATE-AVG": ih.get("DATE-AVG"), "MJD-AVG": float(ih["MJD-AVG"])},
            "observed_at_utc": rec["observed_at_utc"],
            "mjd": rec["mjd"],
            "wavelength_um": rec["wavelength_um"],
            "bandwidth_um": rec["bandwidth_um"],
            "quality_status": q["status"],
            "quality_flag_names": q["flag_names"],
            "adverse_aperture_pixels": q["adverse_aperture_pixels"],
            "screened_pixels": q["screened_pixels"],
            "display_scale": {k: rec["display_scale"][k] for k in ("mode", "method", "low", "high", "unit")},
            "marker_xy": [rec["marker"]["x"], rec["marker"]["y"]],
            "grid_id": rec["registration"]["grid_id"],
            "source_url": rec["source_url"],
            "sha256": {"record": rec["provenance"]["sha256"], "manifest": ent["sha256"], "file": file_sha,
                       "all_equal": rec["provenance"]["sha256"] == ent["sha256"] == file_sha},
            "manifest_wavelength_um": ent.get("wavelength_um"),
            "reproduced": {
                "wavelength_um_equal_1e-9": abs(r2["wavelength_um"] - rec["wavelength_um"]) < 1e-9,
                "quality_equal": r2["quality"] == rec["quality"],
                "display_scale_equal": r2["display_scale"] == rec["display_scale"],
                "marker_equal": r2["marker"] == rec["marker"],
                "png_bytes_equal": pf.png_bytes == shipped_png,
            },
        }

    # Pairs: time, wavelength, stretch
    def pair(x, y):
        fx, fy = recs[x], recs[y]
        dlam = abs(fx["wavelength_um"] - fy["wavelength_um"])
        bw = min(fx["bandwidth_um"], fy["bandwidth_um"])
        mx, my = fx["marker"], fy["marker"]
        dpx = math.hypot(mx["x"] - my["x"], mx["y"] - my["y"])
        scale = fx["registration"]["scale_arcsec_per_px"]
        return {
            "days_apart": round(abs(fy["mjd"] - fx["mjd"]), 3),
            "delta_wavelength_um": round(dlam, 5),
            "delta_wavelength_over_bandwidth": round(dlam / bw, 3),
            "same_detector": fx["detector"] == fy["detector"],
            "stretch_high_ratio": round(fy["display_scale"]["high"] / fx["display_scale"]["high"], 3),
            "stretch_low_ratio": round(fy["display_scale"]["low"] / fx["display_scale"]["low"], 3),
            "predicted_marker_shift_display_px": round(dpx, 2),
            "predicted_marker_shift_arcsec": round(dpx * scale, 2),
            "same_grid": fx["registration"]["grid_id"] == fy["registration"]["grid_id"],
        }
    out["pairs"] = {"P-Q": pair("P", "Q"), "P-R": pair("P", "R"), "Q-R": pair("Q", "R")}

    # Shared stretch for P+Q (illustration only) and physical grid values
    vals = {r: products[r][2].grid_values for r in ("P", "Q", "R")}
    lo, hi = display_limits_from_values([vals["P"], vals["Q"]])
    shared = {}
    for r in ("P", "Q"):
        meta, data, _ = products[r]
        m2 = FrameInput(**{**meta.__dict__, "display_limits": (lo, hi), "display_limits_basis": "review only"})
        shared[r] = process_frame(data, m2)
    out["shared_stretch_P_Q"] = {"low": lo, "high": hi, "unit": "MJy / sr",
                                 "note": "Review illustration only; percentiles 1-99.5 of pooled P+Q grid values."}

    size = recs["P"]["registration"]["width"]
    gw = grid_wcs(qc["ra_deg"], qc["dec_deg"], recs["P"]["registration"]["fov_arcmin"], size)
    gp, gq = full_grid(raw["P"], gw, size), full_grid(raw["Q"], gw, size)
    for r, g in (("P", gp), ("Q", gq)):  # same pixels as the processor's grid_values
        assert np.isclose(np.sort(g[np.isfinite(g)]), np.sort(np.asarray(vals[r], float))).all(), r

    # Per-frame stretch: the grey level the shipped stretch gives to the same
    # physical value in each frame (exact; same formula as process._stretch).
    def grey_for(ref, v):
        ds = recs[ref]["display_scale"]
        t = min(max((v - ds["low"]) / (ds["high"] - ds["low"]), 0.0), 1.0)
        return round(255 * math.asinh(t * ds["asinh_softening"]) / math.asinh(ds["asinh_softening"]))
    probe = [0.5, 1.0, 2.0, 2.5]
    out["stretch_probe"] = {
        "values_MJy_sr": probe,
        "grey_level": {r: [grey_for(r, v) for v in probe] for r in ("P", "Q", "R")},
        "note": "Same sky value, different displayed grey: each shipped frame has its own stretch "
                "(display_scale.mode = per_frame). Rounding to 8-bit is approximate.",
    }

    # Census of bright compact spots (what a blinking learner notices), per frame.
    # A spot = native local maximum at or above that frame's display "high"
    # (i.e. drawn pure white by the shipped per-frame stretch) on the display grid.
    # For each: adverse native flags at the peak, detector pixel (WCS key A),
    # single-pixel test (peak vs brightest of its 8 neighbours), nearest cached
    # Gaia DR3 star at the frame epoch, and whether the other frames show
    # something bright within 1.5 native px (~9") of the same sky position.
    natives = {}
    for ref in ("P", "Q", "R"):
        h = raw[ref]
        ih = h["IMAGE"].header
        natives[ref] = {
            "img": np.asarray(h["IMAGE"].data, dtype=np.float64),
            "flg": np.asarray(h["FLAGS"].data).astype(np.int64),
            "names": flag_bit_names(h["FLAGS"].header),
            "cel": WCS(ih, fobj=h).celestial,
            "det": WCS(ih, key="A"),
        }

    def brightest_near(ref, ra, dec, rad=1.5):
        n = natives[ref]
        x, y = n["cel"].all_world2pix([[ra, dec]], 0)[0]
        ny, nx = n["img"].shape
        best = None
        for yy in range(int(math.floor(y - rad)), int(math.ceil(y + rad)) + 1):
            for xx in range(int(math.floor(x - rad)), int(math.ceil(x + rad)) + 1):
                if 0 <= xx < nx and 0 <= yy < ny and math.hypot(xx - x, yy - y) <= rad and np.isfinite(n["img"][yy, xx]):
                    v = float(n["img"][yy, xx])
                    best = v if best is None else max(best, v)
        return best

    overlays = {r: np.array(Image.open(REC_DIR / f"{recs[r]['frame_key']}.flags.png").convert("RGBA")) for r in ("P", "Q", "R")}
    spots = []
    for ref in ("P", "Q", "R"):
        n = natives[ref]
        img, ny, nx = n["img"], *n["img"].shape
        jyr = mjd_to_jyear(recs[ref]["mjd"])
        padded = np.pad(img, 1, constant_values=np.nan)
        for yy in range(ny):
            for xx in range(nx):
                v = img[yy, xx]
                if not (np.isfinite(v) and v >= recs[ref]["display_scale"]["high"]):
                    continue
                nb8 = np.delete(padded[yy:yy + 3, xx:xx + 3].ravel(), 4)  # edge pixels: missing neighbours = NaN
                if np.nanmax(nb8) >= v:
                    continue
                ra, dec = n["cel"].all_pix2world([[xx, yy]], 0)[0]
                dx, dy = sky_to_display_px(gw, size, ra, dec)
                if not (0 <= dx < size and 0 <= dy < size):
                    continue
                fv = int(n["flg"][yy, xx])
                adverse = sorted(nm for b, nm in n["names"].items() if fv >> b & 1 and nm not in INFORMATIONAL)
                dpx = n["det"].wcs_pix2world([[xx, yy]], 0)[0]
                gsep, gid, gmag = min(
                    (math.hypot((gaia_at(g, jyr)[0] - ra) * math.cos(math.radians(dec)), gaia_at(g, jyr)[1] - dec) * 3600,
                     g["source_id"], float(g["phot_g_mean_mag"])) for g in gaia)
                spots.append({
                    "frame": ref, "display_xy": [round(dx, 1), round(dy, 1)], "native_xy": [xx, yy],
                    "detector_xy": [int(round(dpx[0])), int(round(dpx[1]))],
                    "peak_MJy_sr": round(float(v), 2),
                    "peak_over_brightest_neighbour": round(float(v / np.nanmax(nb8)), 1) if np.nanmax(nb8) > 0 else None,
                    "adverse_flags_at_peak": adverse,
                    "shipped_flag_overlay_rgba": [int(c) for c in overlays[ref][int(dy), int(dx)]],
                    "nearest_gaia_dr3": {"id": gid, "G": round(gmag, 2), "sep_arcsec": round(gsep, 1)},
                    "brightest_within_9arcsec": {o: (round(b, 2) if (b := brightest_near(o, ra, dec)) is not None else None)
                                                 for o in ("P", "Q", "R") if o != ref},
                })
    used = sorted({f for sp in spots for f in sp["adverse_flags_at_peak"]} | set(recs["Q"]["quality"]["flag_names"]))
    fh = raw["Q"]["FLAGS"].header
    out["flag_descriptions_from_FITS_header"] = {
        str(fh[k]).strip(): str(fh.get("MSKD" + k[4:], "")).strip()
        for k in fh.keys() if k.startswith("MSKN") and str(fh[k]).strip() in used}
    out["spot_threshold"] = "native local maximum >= the frame's display_scale.high (drawn white)"
    out["bright_spots"] = spots
    unmatched = [s for s in spots if s["nearest_gaia_dr3"]["sep_arcsec"] > 9.0]
    out["bright_spots_without_gaia_match_within_9arcsec"] = unmatched

    # Marker neighbourhood: the Gaia neighbour, per frame
    nb = next(g for g in gaia if g["source_id"] == NEIGHBOUR)
    out["neighbour"] = {}
    for ref, key in FRAMES:
        rec = recs[ref]
        ra, dec = gaia_at(nb, mjd_to_jyear(rec["mjd"]))
        x, y = sky_to_display_px(gw, size, ra, dec)
        sep = math.hypot(x - rec["marker"]["x"], y - rec["marker"]["y"]) * rec["registration"]["scale_arcsec_per_px"]
        out["neighbour"][ref] = {"gaia_dr3": NEIGHBOUR, "G": float(nb["phot_g_mean_mag"]),
                                 "display_xy": [round(x, 2), round(y, 2)],
                                 "sep_from_marker_arcsec": round(sep, 2),
                                 "adverse_native_flags_at_neighbour": native_flags_at(raw[ref], ra, dec)}

    # Native flags of the screened pixels at the marker in Q (where PERSIST sits)
    (HERE / "results.json").write_text(json.dumps(out, indent=1) + "\n")

    # Contact sheet: shipped P, Q, R (per-frame stretch); P, Q shared stretch; flags overlays for P, Q
    tiles = []
    for ref in ("P", "Q", "R"):
        tiles.append((f"{ref} shipped (own stretch)", Image.open(REC_DIR / f"{recs[ref]['frame_key']}.png").convert("RGBA"),
                      Image.open(REC_DIR / f"{recs[ref]['frame_key']}.flags.png").convert("RGBA")))
    for ref in ("P", "Q"):
        tiles.append((f"{ref} shared P+Q stretch (review)", Image.open(io.BytesIO(shared[ref].png_bytes)).convert("RGBA"), None))
    z = 2
    W = size * z
    sheet = Image.new("RGB", (W * len(tiles) + 10 * (len(tiles) - 1), W * 2 + 40), (40, 40, 40))
    for i, (label, im, fl) in enumerate(tiles):
        base = Image.new("RGBA", im.size, (0, 0, 80, 255))
        base.alpha_composite(im)
        top = base.resize((W, W), Image.NEAREST).convert("RGB")
        x0 = i * (W + 10)
        sheet.paste(top, (x0, 20))
        if fl is not None:
            ov = base.copy()
            ov.alpha_composite(fl)
            sheet.paste(ov.resize((W, W), Image.NEAREST).convert("RGB"), (x0, W + 40))
        dr = ImageDraw.Draw(sheet)
        dr.text((x0 + 2, 4), label, fill=(255, 255, 255))
        ref = label[0]
        if fl is not None:
            for sp in unmatched:
                if sp["frame"] == ref:
                    sx, sy = sp["display_xy"][0] * z, sp["display_xy"][1] * z
                    dr.rectangle([x0 + sx - 10, 20 + sy - 10, x0 + sx + 10, 20 + sy + 10], outline=(255, 220, 0))
        mx, my = recs[ref]["marker"]["x"] * z, recs[ref]["marker"]["y"] * z
        for yoff in (20, W + 40) if fl is not None else (20,):
            dr.ellipse([x0 + mx - 12, yoff + my - 12, x0 + mx + 12, yoff + my + 12], outline=(255, 0, 255))
    ImageDraw.Draw(sheet).text((2, W + 24), "bottom: shipped image + shipped flag overlay (red = adverse flag, yellow = non-finite); magenta circle = catalog prediction; yellow box = bright spot with no Gaia DR3 star within 9 arcsec", fill=(220, 220, 220))
    sheet.save(HERE / "contact_sheet.png", optimize=True)
    print(json.dumps({k: out[k] for k in ("pairs", "bright_spots_without_gaia_match_within_9arcsec", "neighbour")}, indent=1))
    for ref in out["frames"]:
        f = out["frames"][ref]
        print(ref, f["frame_key"], f["sha256"]["all_equal"], f["reproduced"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
