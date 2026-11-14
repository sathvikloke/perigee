"""Run the science acceptance review (science/reviews/acceptance/check_acceptance.py)
against Sagar's processor products (origin/codex/sagar-data, PR #19).

This is a *minimal adaptation*, not a new review. Every geometry/wavelength/flag/Gaia
helper is imported unchanged from check_acceptance.py (``ca``); nothing is imported
from Sagar's backend/data or tools/ingest. The per-record body mirrors
``ca.check_one`` with these bridges, each marked ``BRIDGE`` below:

  B1 layout     <preset>/frames.json -> set "frames"; <preset>/sets/<case>.json ->
                set "case-<case>"; PNG paths from presets/manifest.json via image.asset_id.
  B2 resample   Sagar states "bilinear resample of intensity (finite neighbours only;
                source pixels without a value stay empty)" (A: nearest neighbour).
                Re-implemented here from that sentence: bilinear over finite neighbours,
                empty where the nearest source pixel is non-finite, inside = [-0.5, n-0.5].
  B3 stretch    Sagar subtracts display_scale.background_offset, then
                asinh((v-low)/soft)/asinh((high-low)/soft). That equals ca.stretch with
                softening' = (high-low)/soft. Limits re-derived: per_frame low = med-2*sigma,
                high = p99.9, soft = 4*sigma (sigma = 1.4826*MAD of offset-subtracted
                display pixels); shared = median of the group's own per-frame limits
                (set-level shared_scale.rule). Offset = median of the valid display pixels.
  B4 quality    Sagar's quality block has no screened_pixels, nonfinite_aperture_pixels or
                flag_counts. Status/covered/valid/adverse/flag_names are checked; the
                missing fields are reported as absent, not as failures.
  B5 coverage   Sagar treats [-0.5, n-0.5] as on-image (pixel edge); A's checker uses pixel
                centres [0, n-1]. Both are evaluated and the difference reported.
  B6 sampled    Sagar records have no ``sampled_position``; that sub-check is skipped.
  B7 overlay    Sagar's flag overlay is hatched magenta (230,40,200, alpha 200/70 on a
                3-px diagonal stripe), drawn where adverse & inside & intensity finite.
  B8 wording    ca checks literal phrases ("not photometry", "not a detection",
                "catalog prediction", "adds no resolution") in ``limitations``. The literal
                result is kept; a bridged semantic check is reported alongside.

Usage (repository root of the integration branch):
    .venv/bin/python coordination/processor-compare/check_sagar_acceptance.py \
        --data-root ".../research/build_data" --products <sagar>/backend/content/presets \
        --out /tmp/acceptance_sagar_all.json [--all]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "science" / "reviews" / "acceptance"))
import check_acceptance as ca  # noqa: E402


# ------------------------------------------------------------- B2 / B3 helpers


def bilinear_sagar_rule(img, x, y):
    """Bilinear over finite neighbours; empty where the nearest source pixel is
    non-finite or the position is outside [-0.5, n-0.5]."""
    ny, nx = img.shape
    inside = np.isfinite(x) & np.isfinite(y) & (x >= -0.5) & (x <= nx - 0.5) & (y >= -0.5) & (y <= ny - 0.5)
    xc, yc = np.clip(x, 0, nx - 1), np.clip(y, 0, ny - 1)
    x0 = np.clip(np.floor(xc).astype(int), 0, nx - 2)
    y0 = np.clip(np.floor(yc).astype(int), 0, ny - 2)
    tx, ty = xc - x0, yc - y0
    acc = np.zeros(x.shape)
    ws = np.zeros(x.shape)
    for dx, dy, w in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)), (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        v = img[y0 + dy, x0 + dx]
        ok = np.isfinite(v) & (w > 0)
        acc += np.where(ok, np.nan_to_num(v) * w, 0)
        ws += np.where(ok, w, 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(ws > 1e-6, acc / ws, np.nan)
    xn = np.clip(np.round(xc).astype(int), 0, nx - 1)
    yn = np.clip(np.round(yc).astype(int), 0, ny - 1)
    out[~np.isfinite(img[yn, xn])] = np.nan
    out[~inside] = np.nan
    return out


def sagar_limits(v):
    v = v[np.isfinite(v)]
    sig = 1.4826 * np.median(np.abs(v - np.median(v)))
    med = float(np.median(v))
    return med - 2 * sig, float(np.percentile(v, 99.9)), 4 * sig


def stretch_sagar(v, lo, hi, soft):
    s = np.clip(np.arcsinh((v - lo) / soft) / np.arcsinh((hi - lo) / soft), 0, 1)
    return np.floor(s * 255 + 0.5).astype(int)


# ------------------------------------------------------------------- loader (B1)


def load_sets(prod: Path):
    manifest = json.loads((prod / "manifest.json").read_text())
    assets = manifest["assets"]
    sets = {}
    for fj in sorted(prod.glob("*/frames.json")):
        d = json.loads(fj.read_text())
        sets[(d["preset_id"], "frames")] = d
    for sj in sorted(prod.glob("*/sets/*.json")):
        if sj.name.endswith(".registration.json"):
            continue
        d = json.loads(sj.read_text())
        sets[(d["preset_id"], "case-" + d["set_id"])] = d
    return sets, assets


def asset_path(prod, assets, img):
    if not img or not img.get("asset_id"):
        return None
    a = assets.get(img["asset_id"])
    return None if a is None else prod / a["path"]


# ------------------------------------------------------------------- per record


def check_one(rec, png_path, flags_path, raw_path, mrec, tgt, set_records, preset):
    out = {"frame_key": rec["frame_key"], "checks": {}, "evidence": {}, "bridges": []}
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

    # 3. time (unchanged)
    date_avg, mjd_avg = ih["DATE-AVG"], float(ih["MJD-AVG"])
    t_ok = abs(Time(date_avg, format="isot", scale="utc").mjd - mjd_avg) * 86400 < 0.01
    C["time"] = (rec["observed_at_utc"].rstrip("Z") == date_avg and rec["mjd"] == mjd_avg and t_ok
                 and ih.get("TIMESYS", "UTC").strip() == "UTC")

    pra, pdec, _, _ = ca.predict(tgt, mjd_avg)
    x, y = (float(v) for v in cel.all_world2pix([[pra, pdec]], 0)[0])
    inside_centre = 0 <= x <= nx - 1 and 0 <= y <= ny - 1          # ca's rule
    inside_edge = -0.5 <= x <= nx - 0.5 and -0.5 <= y <= ny - 0.5    # BRIDGE B5 (Sagar's rule)
    mx, my = ca.sky_to_display(pra, pdec, ra0, dec0, fov, size)
    E["target"] = {"native_xy": [x, y], "inside_pixel_centres": inside_centre, "inside_pixel_edges": inside_edge,
                   "display_xy_independent": [mx, my]}

    # 1. registration
    reg_ok, notes = True, []
    m = rec.get("marker")
    if m is None or m.get("kind") != "catalog_prediction":
        reg_ok = False
        notes.append("marker missing or not catalog_prediction")
    else:
        dm = math.hypot(m["x"] - mx, m["y"] - my)
        E["marker_minus_independent_px"] = dm
        if dm > 0.05:  # Sagar rounds marker x/y to 0.01 px; tolerance unchanged
            reg_ok = False
            notes.append(f"marker differs by {dm:.3f} display px")
    out["bridges"].append("B6: no sampled_position in record; sub-check skipped")
    keys = ("center_ra_deg", "center_dec_deg", "fov_arcmin", "width", "height", "projection", "orientation", "grid_id")
    same = all(all(r["registration"][k] == reg[k] for k in keys) for r in set_records)
    E["grid_identical_across_set"] = same
    reg_ok &= same

    # BRIDGE B2: reconstruct with Sagar's stated resampling
    sra, sdec = ca.display_centers_to_sky(ra0, dec0, fov, size)
    npx, npy = cel.all_world2pix(sra.ravel(), sdec.ravel(), 0, quiet=True)
    npx, npy = npx.reshape(size, size), npy.reshape(size, size)
    vals = bilinear_sagar_rule(img, npx, npy)
    good = np.isfinite(vals)
    ds = rec["display_scale"]
    offset_indep = float(np.median(vals[good]))
    shown = vals - ds["background_offset"]
    exp_gray = np.zeros((size, size), int)
    exp_gray[good] = stretch_sagar(shown[good], ds["low"], ds["high"], ds["asinh_softening"])
    exp_alpha = np.where(good, 255, 0)
    pim = np.asarray(Image.open(png_path))
    gray, alpha = pim[..., 0].astype(int), pim[..., 1].astype(int)
    alpha_match = float((alpha == exp_alpha).mean())
    both = (alpha == 255) & (exp_alpha == 255)
    gdiff = np.abs(gray - exp_gray)[both]
    flipped = np.fliplr(exp_gray)
    bothf = (alpha == 255) & (np.fliplr(exp_alpha) == 255)
    E["png_reconstruction"] = {
        "png_mode": Image.open(png_path).mode, "png_bytes": Path(png_path).stat().st_size,
        "alpha_match_fraction": alpha_match,
        "gray_exact_fraction": float((gdiff == 0).mean()) if gdiff.size else None,
        "gray_within_1_fraction": float((gdiff <= 1).mean()) if gdiff.size else None,
        "gray_max_abs_diff": int(gdiff.max()) if gdiff.size else None,
        "mirrored_control_exact_fraction": float((np.abs(gray - flipped)[bothf] == 0).mean()) if bothf.any() else None,
        "opaque_pixels": int(both.sum()),
    }
    recon_ok = alpha_match > 0.995 and gdiff.size and (gdiff <= 1).mean() > 0.995
    reg_ok &= bool(recon_ok)
    out["_shown"] = vals[good] - offset_indep
    E["background_offset"] = {"record": ds["background_offset"], "independent_median": offset_indep}

    # Gaia (unchanged helpers)
    stars = []
    for s in ca.load_gaia(preset):
        gra, gdec = ca.gaia_at(s, mjd_avg)
        if math.hypot((gra - pra) * math.cos(math.radians(pdec)), gdec - pdec) * 3600 < 40:
            continue
        gx, gy = (float(v) for v in cel.all_world2pix([[gra, gdec]], 0)[0])
        nc = ca.native_centroid(img, gx, gy)
        if nc is None:
            continue
        dxp, dyp = ca.sky_to_display(gra, gdec, ra0, dec0, fov, size)
        pc_ = ca.png_centroid(gray, alpha, dxp, dyp)
        stars.append({"native_d": math.hypot(nc[0] - gx, nc[1] - gy),
                      "png_d": None if pc_ is None else math.hypot(pc_[0] - dxp, pc_[1] - dyp)})
    pngs = [s["png_d"] for s in stars if s["png_d"] is not None and s["native_d"] < 1.0]
    E["gaia"] = {"n_native": len(stars), "n_png": len(pngs),
                 "png_median_offset_display_px": float(np.median(pngs)) if pngs else None,
                 "png_median_offset_arcsec": float(np.median(pngs)) * fov * 60 / size if pngs else None}
    if pngs and np.median(pngs) > 2.5:
        reg_ok = False
        notes.append("Gaia stars offset in PNG")
    C["registration"] = bool(reg_ok)
    C["gaia"] = None if not pngs else bool(np.median(pngs) <= 2.5)
    E["registration_notes"] = notes

    # 2. wavelength (unchanged; Sagar's coverage rule decides null vs value)
    if inside_edge:
        wa, ba = ca.wave_astropy(ih, hdul, x, y)
        wm, _, _ = ca.wave_manual(ih, hdul, min(max(x, 0), nx - 1), min(max(y, 0), ny - 1))
        E["wavelength"] = {"independent": [wa, ba], "record": [rec["wavelength_um"], rec["bandwidth_um"]]}
        C["wavelength"] = (rec["wavelength_um"] is not None and abs(rec["wavelength_um"] - wa) < 1e-6
                           and abs(rec["bandwidth_um"] - ba) < 1e-6 and wm is not None and abs(wm - wa) < 1e-5)
    else:
        C["wavelength"] = rec["wavelength_um"] is None and rec["bandwidth_um"] is None

    # 4. flags (BRIDGE B4)
    names = {int(k[4:]): hdul["FLAGS"].header[k].strip() for k in hdul["FLAGS"].header if k.startswith("MSKN")}
    good_native = np.isfinite(img) & np.isfinite(var) & (var > 0)
    q = rec["quality"]
    if inside_edge:
        yy, xx = np.mgrid[0:ny, 0:nx]
        ap = (xx - x) ** 2 + (yy - y) ** 2 <= ca.APERTURE_R ** 2
        named_bits = sum(1 << b for b in names)
        adv_bits = sum(1 << b for b, n in names.items() if n not in ca.INFORMATIONAL) | (~named_bits & 0x7FFFFFFF)
        adverse = ap & (((flg & adv_bits) != 0) | ~good_native)
        counts = {n: int((ap & (((flg >> b) & 1) == 1)).sum()) for b, n in names.items()}
        counts = {k: v for k, v in counts.items() if v}
        st = "flagged" if adverse.sum() else ("clear" if int((ap & ~adverse).sum()) >= 10 else "unknown")
        mine = {"status": st, "screened": int(ap.sum()), "adverse": int(adverse.sum()),
                "valid": int((ap & ~adverse).sum()), "nonfinite": int((ap & ~good_native).sum())}
        C["flags"] = (q["status"] == st and q["covered"] is True and q["adverse_aperture_pixels"] == mine["adverse"]
                      and q["valid_aperture_pixels"] == mine["valid"]
                      and set(q["flag_names"]) == {k for k in counts if k not in ca.INFORMATIONAL})
    else:
        mine = {"status": "not_covered"}
        C["flags"] = (q["status"] == "not_covered" and q["covered"] is False
                      and q["valid_aperture_pixels"] is None and q["adverse_aperture_pixels"] is None)
    E["flags"] = {"independent": mine, "record": {k: q.get(k) for k in ("status", "valid_aperture_pixels", "adverse_aperture_pixels", "flag_names")},
                  "fields_absent_in_record": [k for k in ("screened_pixels", "nonfinite_aperture_pixels", "flag_counts") if k not in q]}

    # BRIDGE B7: flag overlay
    if flags_path and Path(flags_path).exists():
        named_bits = sum(1 << b for b in names)
        adv_bits = sum(1 << b for b, n in names.items() if n not in ca.INFORMATIONAL) | (~named_bits & 0x7FFFFFFF)
        ixn, iyn = np.rint(npx).astype(int), np.rint(npy).astype(int)
        on = (ixn >= 0) & (ixn <= nx - 1) & (iyn >= 0) & (iyn <= ny - 1)
        f_s = flg[np.clip(iyn, 0, ny - 1), np.clip(ixn, 0, nx - 1)]
        draw = on & ((f_s & adv_bits) != 0) & good
        jj, ii = np.mgrid[0:size, 0:size]
        stripe = ((ii + jj) // 3) % 2 == 0
        exp_rgba = np.zeros((size, size, 4), int)
        exp_rgba[..., 0], exp_rgba[..., 1], exp_rgba[..., 2] = 230, 40, 200
        exp_rgba[..., 3] = np.where(draw & stripe, 200, np.where(draw, 70, 0))
        fpng = np.asarray(Image.open(flags_path).convert("RGBA")).astype(int)
        # compare alpha (colour is irrelevant where alpha is 0)
        E["flag_overlay_alpha_match_fraction"] = float((fpng[..., 3] == exp_rgba[..., 3]).mean())

    # 5. coverage (B5)
    C["coverage"] = (q["status"] == "not_covered") == (not inside_edge) and q["covered"] == inside_edge
    E["coverage_rule_disagrees_with_ca"] = inside_centre != inside_edge

    # 7. provenance (B8)
    pv = rec["provenance"]
    lim = " ".join(rec["limitations"]).lower()
    literal = {w: (w in lim) for w in ("not photometry", "not a detection", "catalog prediction", "adds no resolution")}
    label = (m or {}).get("label", "").lower() if m else ""
    semantic = {
        "not photometry": "not for measuring brightness" in lim,
        "not a detection": "not a detection" in label or "not a detection" in lim,
        "catalog prediction": (m is None) or "catalog prediction" in label,
        "adds no resolution": "does not add telescope resolution" in lim,
    }
    E["provenance"] = {"limitations_literal_ca": literal, "limitations_semantic_bridged": semantic,
                       "sha_ok": sha == pv["sha256"] == mrec.get("sha256"),
                       "source_url_ok": rec["source_url"] == mrec["archive_url"] == pv["original_url"],
                       "cutout_url_ok": pv["cutout_url"] == mrec["source_url"],
                       "frame_key_ok": rec["frame_key"] == f"{ih['OBSID'].strip()}_D{int(ih['DETECTOR'])}"}
    P = E["provenance"]
    base_ok = (P["sha_ok"] and P["source_url_ok"] and P["cutout_url_ok"] and P["frame_key_ok"]
               and rec["collection_id"] == mrec["collection"] and (m is None or m["kind"] == "catalog_prediction"))
    C["provenance"] = bool(base_ok and all(semantic.values()))
    C["provenance_literal_ca_wording"] = bool(base_ok and all(literal.values()))
    E["query_center_matches_manifest"] = (abs(ra0 - tgt["query_ra_deg"]) < 1e-12 and abs(dec0 - tgt["query_dec_deg"]) < 1e-12)
    C["registration"] &= E["query_center_matches_manifest"]
    hdul.close()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--products", required=True)
    ap.add_argument("--science-ref", default="origin/codex/sathvik-science")
    ap.add_argument("--out", required=True)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    data, prod = Path(a.data_root), Path(a.products)
    manifest = json.loads((data / "manifest.json").read_text())
    targets = {t["id"]: t for t in manifest["targets"]}
    mby = {f"{r['obs_id']}_D{r['detector']}": r for r in manifest["files"] if r.get("status") == "downloaded"}
    sets, assets = load_sets(prod)
    if a.all:
        todo = [(p, s, r["frame_key"], "") for (p, s), d in sets.items() for r in d["frames"]]
    else:
        todo = [t for t in ca.SELECTED]
    results, shown = [], {}
    for preset, set_name, key, why in todo:
        d = sets[(preset, set_name)]
        rec = next(r for r in d["frames"] if r["frame_key"] == key)
        o = check_one(rec, asset_path(prod, assets, rec["image"]), asset_path(prod, assets, rec.get("flag_image")),
                      data / mby[key]["file"], mby[key], targets[preset], d["frames"], preset)
        o.update(preset=preset, set=set_name, why=why, status=rec["quality"]["status"])
        shown[(preset, set_name, key)] = o.pop("_shown")
        results.append(o)

    # 6. stretch (BRIDGE B3)
    for o in results:
        d = sets[(o["preset"], o["set"])]
        rec = next(r for r in d["frames"] if r["frame_key"] == o["frame_key"])
        ds = rec["display_scale"]
        bo = o["evidence"]["background_offset"]
        offset_ok = abs(bo["record"] - bo["independent_median"]) < 1e-6 * max(1, abs(bo["record"]))
        lo, hi, soft = sagar_limits(shown[(o["preset"], o["set"], o["frame_key"])])
        if ds["mode"] == "per_frame":
            ok = (abs(lo - ds["low"]) < 1e-6 * max(1, abs(lo)) and abs(hi - ds["high"]) < 1e-6 * max(1, abs(hi))
                  and abs(soft - ds["asinh_softening"]) < 1e-6 * max(1, soft)
                  and "not comparable" in ds["basis"].lower())
            o["evidence"]["stretch_recomputed"] = [lo, hi, soft]
        else:
            refs = set(d.get("shared_scale", {}).get("refs", []))
            group = [r for r in d["frames"] if r.get("case_ref") in refs]
            lims = []
            for r in group:
                k = (o["preset"], o["set"], r["frame_key"])
                if k not in shown:
                    lims = None
                    break
                lims.append(sagar_limits(shown[k]))
            if lims:
                med = np.median(np.array(lims), axis=0)
                ok = all(abs(med[i] - ds[f]) < 1e-6 * max(1, abs(med[i])) for i, f in enumerate(("low", "high", "asinh_softening")))
                o["evidence"]["stretch_recomputed_shared"] = med.tolist()
            else:
                ok = None
        recon = o["evidence"]["png_reconstruction"]
        o["checks"]["stretch"] = bool(ok and offset_ok) and recon["gray_within_1_fraction"] is not None and recon["gray_within_1_fraction"] > 0.995

    # case agreement (unchanged logic)
    for cid in ("fair_comparison", "moving_neighbor"):
        case = json.loads(ca.git_show(a.science_ref, f"backend/content/cases/{cid}.json"))
        for f in case["frames"]:
            r = next((o for o in results if o["frame_key"] == f["frame_key"] and o["set"] == f"case-{cid}"), None)
            if r is None:
                continue
            rec = next(x for x in sets[(case["target_id"], f"case-{cid}")]["frames"] if x["frame_key"] == f["frame_key"])
            r["checks"]["case_match"] = (abs(rec["wavelength_um"] - f["wavelength_um"]) <= 1e-4
                                         and rec["observed_at_utc"].rstrip("Z") == f["observed_at_utc"]
                                         and rec["mjd"] == f["mjd"] and rec["quality"]["status"] == f["expected_quality_status"]
                                         and rec["provenance"]["sha256"] == f["sha256_of_retained_cutout"]
                                         and rec["source_url"] == f["source_url"])
            r["evidence"]["case_ref_record"] = rec.get("case_ref")
            r["evidence"]["case_ref_expected"] = f["ref"]

    cols = ["registration", "gaia", "wavelength", "time", "flags", "coverage", "stretch", "provenance",
            "provenance_literal_ca_wording", "case_match"]
    matrix = [{"frame_key": o["frame_key"], "preset": o["preset"], "set": o["set"], "status": o["status"],
               **{c: o["checks"].get(c) for c in cols}} for o in results]
    out = {"matrix": matrix, "frames": results}
    Path(a.out).write_text(json.dumps(out, indent=1, default=float) + "\n")
    summary = {c: {"pass": sum(m[c] is True for m in matrix), "fail": sum(m[c] is False for m in matrix),
                   "unknown_or_na": sum(m[c] is None for m in matrix)} for c in cols}
    fails = [(m["preset"], m["set"], m["frame_key"], c) for m in matrix for c in cols if m[c] is False]
    print(json.dumps({"n": len(matrix), "summary": summary, "fails": fails}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
