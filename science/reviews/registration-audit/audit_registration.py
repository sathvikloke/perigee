"""N3 registration and astrometric-validity audit for processor A products.

Reviewer tool. Reads (never writes) the raw cutouts and manifest in
research/build_data, the published products in backend/content/presets and the
cached Gaia DR3 controls in science/reviews/acceptance/gaia. Writes small JSON /
CSV / PNG outputs to --out-dir, which must be empty or absent.

    DATA="/path/to/research/build_data"
    rm -rf science/reviews/registration-audit/results
    .venv/bin/python science/reviews/registration-audit/audit_registration.py \
        --data-root "$DATA" --out-dir science/reviews/registration-audit/results

Outputs are deterministic (no timestamps), so a rerun can be diffed against the
committed results.
"""

from __future__ import annotations

import argparse
import collections
import csv
import glob
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regcheck as rc  # noqa: E402
from regcheck import acc  # noqa: E402

GAIA_DIR = HERE.parent / "acceptance" / "gaia"
FIXTURE_FRAMES = [  # (preset, frame_key, why)
    ("barnards_star", "2025W35_1A_0008_1_D3", "moving_neighbor A, SWIR D3, many field stars"),
    ("wise_0855", "2026W19_1A_0227_1_D4", "MWIR D4"),
    ("epsilon_indi_b", "2026W18_1A_0516_1_D3", "fair_comparison A (same exposure as C), few stars"),
]
FIXTURE_PERTURBATIONS = [  # (label, dx, dy, rot_deg)  native px / degrees
    ("identity", 0.0, 0.0, 0.0),
    ("shift_0.5px_x", 0.5, 0.0, 0.0),
    ("shift_1px_x", 1.0, 0.0, 0.0),
    ("shift_2px_y", 0.0, 2.0, 0.0),
    ("shift_5px_x", 5.0, 0.0, 0.0),
    ("rot_1deg", 0.0, 0.0, 1.0),
    ("rot_3deg", 0.0, 0.0, 3.0),
]
FAIR_C = "2026W18_1A_0516_1_D6"
FAIR_A = "2026W18_1A_0516_1_D3"
MN_CASE = ["2025W35_1A_0008_1_D3", "2026W12_1A_0610_2_D3", "2026W34_1A_0431_1_D3"]


def q(vals, ps=(5, 16, 50, 84, 90, 95, 99)):
    vals = np.asarray([v for v in vals if v is not None and np.isfinite(v)], float)
    if vals.size == 0:
        return {"n": 0}
    out = {"n": int(vals.size), "min": float(vals.min()), "max": float(vals.max()), "mean": float(vals.mean())}
    out.update({f"p{p}": float(np.percentile(vals, p)) for p in ps})
    return out


def r6(x):
    if isinstance(x, float):
        return round(x, 6) if np.isfinite(x) else None
    if isinstance(x, dict):
        return {k: r6(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r6(v) for v in x]
    if isinstance(x, (np.floating,)):
        return r6(float(x))
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def dump(path, obj):
    Path(path).write_text(json.dumps(r6(obj), indent=1, sort_keys=False) + "\n")


def write_csv(path, rows, cols):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------- loading


def load_inputs(data_root, products):
    manifest = json.loads((data_root / "manifest.json").read_text())
    targets = {t["id"]: t for t in manifest["targets"]}
    files = [f for f in manifest["files"] if f.get("status") == "downloaded"]
    mby = {f"{f['obs_id']}_D{f['detector']}": f for f in files}
    records = []
    for fj in sorted(glob.glob(str(products / "*" / "*" / "frames.json"))):
        d = json.loads(Path(fj).read_text())
        for r in d["frames"]:
            records.append({"preset": d["preset_id"], "set": d["set"], "rec": r,
                            "png": products / d["preset_id"] / d["set"] / f"{r['frame_key']}.png"})
    return manifest, targets, files, mby, records


def png_arrays(path):
    pim = np.asarray(Image.open(path))
    return pim[..., 0].astype(int), pim[..., 1].astype(int)


# ------------------------------------------------------------------ inventory


def inventory(manifest, files, records):
    shas = collections.Counter(f["sha256"] for f in files)
    frames_recs = [r for r in records if r["set"] == "frames"]
    case_recs = [r for r in records if r["set"] != "frames"]
    frames_sha = {r["rec"]["provenance"]["sha256"]: r["rec"]["frame_key"] for r in frames_recs}
    copies = []
    for r in case_recs:
        s = r["rec"]["provenance"]["sha256"]
        copies.append({"preset": r["preset"], "set": r["set"], "frame_key": r["rec"]["frame_key"],
                       "same_raw_as_frames_record": frames_sha.get(s) == r["rec"]["frame_key"]})
    return {
        "manifest_file_entries": len(manifest["files"]),
        "manifest_status_counts": dict(collections.Counter(f.get("status") for f in manifest["files"])),
        "unique_raw_cutouts": len(files),
        "unique_raw_sha256": len(shas),
        "duplicate_raw_sha256": sum(1 for v in shas.values() if v > 1),
        "unique_exposures_obsid": len({f["obs_id"] for f in files}),
        "raw_cutouts_per_target": dict(sorted(collections.Counter(f["target_id"] for f in files).items())),
        "raw_cutouts_per_detector": {f"D{k}": v for k, v in sorted(collections.Counter(f["detector"] for f in files).items())},
        "exposures_with_n_detector_cutouts": dict(sorted(collections.Counter(
            collections.Counter(f["obs_id"] for f in files).values()).items())),
        "product_records": len(records),
        "product_records_frames_sets": len(frames_recs),
        "product_records_case_copies": len(case_recs),
        "case_copies": copies,
        "every_raw_cutout_has_one_frames_record": sorted(frames_sha.values()) == sorted(
            f"{f['obs_id']}_D{f['detector']}" for f in files) and len(frames_sha) == len(frames_recs),
        "note": "Case records are re-renders (different display stretch) of raw cutouts that also have a frames record; "
                "they are not independent observations. D1-D3 and D4-D6 cutouts of one exposure are simultaneous "
                "views through different detectors (separate WCS), so they are distinct frames but not distinct epochs.",
    }


# --------------------------------------------------------------- star funnel


def frame_stars(fr, cat_rows, target_radec, gray, alpha, reg, half=2, search=1, excl=40.0):
    """Gaia-seeded measurement of every catalog star in one frame. Returns per-star
    dicts carrying the stage reached (no SNR / association thresholds applied
    yet; those are applied by `stage_of`)."""
    ny, nx = fr.shape
    proj = rc.project_catalog(fr, cat_rows, target_radec, excl)
    allpos = [(p["x"], p["y"]) for p in proj]
    stars = []
    for i, p in enumerate(proj):
        s = {"gaia": p["source_id"], "G": p["G"], "full": p["full"], "x": p["x"], "y": p["y"],
             "sep_target_arcsec": p["sep_target"]}
        nn = min((math.hypot(p["x"] - a, p["y"] - b) for j, (a, b) in enumerate(allpos) if j != i), default=float("inf"))
        s["nearest_catalog_neighbour_px"] = nn
        if not p["full"]:
            s["pre"] = "two_parameter"
        elif p["near_target"]:
            s["pre"] = "near_target"
        elif not (0 <= p["x"] <= nx - 1 and 0 <= p["y"] <= ny - 1):
            s["pre"] = "outside_footprint"
        else:
            stage, res = rc.forced_measure(fr, p["x"], p["y"], half=half, search=search, snr_min=-np.inf)
            s["pre"] = stage  # 'edge' | 'nonfinite' | 'ok'
            if stage == "ok":
                s.update(snr=res["snr"], adverse_in_window=res["adverse_in_window"],
                         native_dx=res["cx"] - p["x"], native_dy=res["cy"] - p["y"])
                s["native_r"] = math.hypot(s["native_dx"], s["native_dy"])
                dxp, dyp = acc.sky_to_display(p["ra_t"], p["dec_t"], reg["center_ra_deg"], reg["center_dec_deg"],
                                              reg["fov_arcmin"], reg["width"])
                pc = acc.png_centroid(gray, alpha, dxp, dyp) if gray is not None else None
                s["png_ok"] = pc is not None
                if pc is not None:
                    s["png_dx"], s["png_dy"] = pc[0] - dxp, pc[1] - dyp
                    s["png_r"] = math.hypot(s["png_dx"], s["png_dy"])
        stars.append(s)
    return stars


def stage_of(s, snr_min=15.0, assoc=1.0):
    if s["pre"] != "ok":
        return s["pre"]
    if s["snr"] < snr_min:
        return "low_snr"
    if s["native_r"] >= assoc:
        return "association"
    if not s.get("png_ok"):
        return "png_window"
    return "retained"


FUNNEL_STAGES = ["two_parameter", "near_target", "outside_footprint", "edge", "nonfinite", "low_snr",
                 "association", "png_window", "retained"]


def is_ambiguous(s, assoc=1.0, half=2, search=1):
    # another catalog star within reach of the centroid window -> the measured
    # light may belong to either; the catalog is magnitude-limited, so fainter
    # unlisted neighbours are not covered by this test.
    return s["nearest_catalog_neighbour_px"] <= max(assoc, 1.0) + half + search


def funnel_row(key, preset, det, stars, snr_min=15.0, assoc=1.0):
    c = collections.Counter(stage_of(s, snr_min, assoc) for s in stars)
    row = {"frame_key": key, "preset": preset, "detector": det, "catalog_rows": len(stars)}
    for st in FUNNEL_STAGES:
        row[st] = c.get(st, 0)
    row["attempted"] = sum(c.get(k, 0) for k in ("nonfinite", "low_snr", "association", "png_window", "retained"))
    row["snr_eligible"] = sum(c.get(k, 0) for k in ("association", "png_window", "retained"))
    row["native_matched"] = c.get("png_window", 0) + c.get("retained", 0)
    ret = [s for s in stars if stage_of(s, snr_min, assoc) == "retained"]
    row["retained_ambiguous"] = sum(is_ambiguous(s, assoc) for s in ret)
    row["retained_adverse_flag_in_window"] = sum(1 for s in ret if s["adverse_in_window"] > 0)
    row["median_native_r_px"] = float(np.median([s["native_r"] for s in ret])) if ret else None
    row["median_png_r_display_px"] = float(np.median([s["png_r"] for s in ret])) if ret else None
    elig = [s for s in stars if stage_of(s, snr_min, assoc) in ("association", "png_window", "retained")]
    row["max_snr_attempted"] = max((s["snr"] for s in stars if s["pre"] == "ok"), default=None)
    row["median_native_r_eligible_px"] = float(np.median([s["native_r"] for s in elig])) if elig else None
    return row


def dominant_reason(row):
    """Name the stage at which the last candidate star was lost (frames with no retained star)."""
    if row["retained"]:
        return None
    counts = (f"catalog {row['catalog_rows']}: outside {row['outside_footprint']}, near target {row['near_target']}, "
              f"edge {row['edge']}, non-finite {row['nonfinite']}, low SNR {row['low_snr']}, "
              f"association {row['association']}, PNG window {row['png_window']}")
    if row["attempted"] == 0:
        why = "no catalog star has a complete measurement window inside the cutout"
    elif row["snr_eligible"] == 0:
        why = f"no attempted star reaches peak SNR 15 (max {row['max_snr_attempted']:.1f})"
    elif row["native_matched"] == 0:
        why = "every SNR-eligible centroid lies >= 1 native px from Gaia (blend, halo or registration)"
    else:
        why = "native matches exist but every PNG window contains transparent (non-finite) pixels"
    return f"{why} [{counts}]"


# --------------------------------------------------------------------- blind


def scrambled(cat_proj, nx, ny, k):
    """Catalog rotated by k*90 deg about the cutout centre: same density and
    magnitudes, no true counterparts. Used for the chance-match rate."""
    cx, cy = (nx - 1) / 2.0, (ny - 1) / 2.0
    out = []
    for c in cat_proj:
        dx, dy = c["x"] - cx, c["y"] - cy
        for _ in range(k):
            dx, dy = -dy, dx
        out.append({**c, "x": cx + dx, "y": cy + dy})
    return out


def nearest(det, cats):
    ds = sorted(math.hypot(det["x"] - c["x"], det["y"] - c["y"]) for c in cats)
    return ds


# ---------------------------------------------------------------------- main


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--products", default="backend/content/presets")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    data = Path(a.data_root)
    prod = Path(a.products)
    out = Path(a.out_dir)
    if out.exists() and any(out.iterdir()):
        sys.exit(f"--out-dir {out} is not empty; run from a clean output directory")
    out.mkdir(parents=True, exist_ok=True)

    manifest, targets, files, mby, records = load_inputs(data, prod)
    inv = inventory(manifest, files, records)
    cats = {p: rc.read_catalog(GAIA_DIR / f"{p}.csv") for p in targets}
    frames_rec = {r["rec"]["frame_key"]: r for r in records if r["set"] == "frames"}
    case_recs = [r for r in records if r["set"] != "frames"]

    frames, preds = {}, {}
    for f in sorted(files, key=lambda f: (f["target_id"], f["obs_id"], f["detector"])):
        key = f"{f['obs_id']}_D{f['detector']}"
        fr = rc.load_frame(data / f["file"], key)
        frames[key] = (f["target_id"], fr)
        pra, pdec, _, _ = acc.predict(targets[f["target_id"]], fr.mjd)
        preds[key] = (pra, pdec)

    # ---------------- 1. funnel at legacy parameters (+ identity check vs legacy)
    stars_by = {}
    legacy_mismatch = 0
    legacy_checked = 0
    funnel = []
    for key, (preset, fr) in frames.items():
        R = frames_rec[key]
        gray, alpha = png_arrays(R["png"])
        st = frame_stars(fr, cats[preset], preds[key], gray, alpha, R["rec"]["registration"])
        stars_by[key] = st
        # star-by-star equality with the unmodified legacy centroid
        for s in st:
            if s["pre"] in ("ok", "edge", "nonfinite"):
                legacy_checked += 1
                nc = acc.native_centroid(fr.img, s["x"], s["y"])
                mine_ok = s["pre"] == "ok" and s["snr"] >= 15.0
                if (nc is None) != (not mine_ok) or (nc is not None and (abs(nc[0] - s["x"] - s["native_dx"]) > 1e-9
                                                                           or abs(nc[1] - s["y"] - s["native_dy"]) > 1e-9)):
                    legacy_mismatch += 1
        row = funnel_row(key, preset, fr.detector, st)
        row["no_star_check_reason"] = dominant_reason(row)
        funnel.append(row)
    fcols = ["frame_key", "preset", "detector", "catalog_rows"] + FUNNEL_STAGES[:3] + ["attempted"] + FUNNEL_STAGES[3:6] + \
        ["snr_eligible", "association", "native_matched", "png_window", "retained", "retained_ambiguous",
         "retained_adverse_flag_in_window", "max_snr_attempted", "median_native_r_eligible_px", "median_native_r_px",
         "median_png_r_display_px", "no_star_check_reason"]
    fcols = list(dict.fromkeys(fcols))
    write_csv(out / "funnel_per_frame.csv", funnel, fcols)

    # case copies: same native stars, PNG stage re-run on the case PNG
    case_rows = []
    for r in case_recs:
        key = r["rec"]["frame_key"]
        preset, fr = frames[key]
        gray, alpha = png_arrays(r["png"])
        st = frame_stars(fr, cats[preset], preds[key], gray, alpha, r["rec"]["registration"])
        row = funnel_row(key, preset, fr.detector, st)
        case_rows.append({"set": r["set"], "frame_key": key, "retained": row["retained"],
                          "median_png_r_display_px": row["median_png_r_display_px"],
                          "frames_record_retained": next(x["retained"] for x in funnel if x["frame_key"] == key)})

    tot = {k: int(sum(r[k] for r in funnel)) for k in ["catalog_rows"] + FUNNEL_STAGES + ["attempted", "snr_eligible", "native_matched", "retained_ambiguous", "retained_adverse_flag_in_window"]}
    no_check = [{"frame_key": r["frame_key"], "preset": r["preset"], "detector": r["detector"],
                 "catalog_rows": r["catalog_rows"], "max_snr_attempted": r["max_snr_attempted"],
                 "reason": r["no_star_check_reason"]} for r in funnel if r["retained"] == 0]
    n_checked_unique = sum(1 for r in funnel if r["retained"] > 0)
    n_checked_records = n_checked_unique + sum(1 for c in case_rows if c["retained"] > 0)
    funnel_summary = {
        "parameters": rc.LEGACY,
        "stage_definitions": {
            "catalog_rows": "rows in the cached Gaia DR3 CSV for the preset (G<15 Barnard/RW Aur, G<17 others; r=0.075 deg)",
            "two_parameter": "no proper motion in Gaia; skipped (not assumed static)",
            "near_target": "propagated position within 40 arcsec of the catalog-predicted target (target and its halo)",
            "outside_footprint": "projects outside the native cutout through the header WCS",
            "attempted": "inside footprint and not near target, minus edge (measurement window fits)",
            "edge": "measurement window (7x7 native px around the rounded position) leaves the cutout",
            "nonfinite": "measurement window contains a non-finite pixel",
            "low_snr": "peak - local median < 15 x MAD (eligibility; applied BEFORE association)",
            "snr_eligible": "attempted measurements that pass the SNR cut",
            "association": "SNR-eligible but native centroid >= 1 native px from Gaia (dropped by the legacy rule)",
            "png_window": "native match, but the PNG 33x33 box has transparent pixels or leaves the grid",
            "retained": "used in the published PNG residual headline",
        },
        "eligibility_note": "The SNR cut is evaluated in a window centred on the Gaia-predicted position (forced "
                            "photometry). It precedes the 1 px association cut, but it is not independent of the "
                            "registration: if the header were off by >~3 native px the star would leave the window and "
                            "fail the SNR cut, so it would vanish silently instead of being counted as a mismatch. "
                            "blind_matching.json uses a WCS-free eligibility to close this gap.",
        "totals_over_unique_frames": tot,
        "unique_frames": len(funnel),
        "unique_frames_with_retained_star": n_checked_unique,
        "unique_frames_without_star_check": len(no_check),
        "records_with_retained_star_incl_case_copies": n_checked_records,
        "records_total": len(records),
        "legacy_identity_check": {"stars_compared": legacy_checked, "mismatches": legacy_mismatch},
        "case_copies": case_rows,
        "frames_without_independent_star_check": no_check,
    }
    dump(out / "funnel_summary.json", funnel_summary)

    # ---------------- 2. residuals
    srows = []
    for key, st in stars_by.items():
        preset, fr = frames[key]
        for s in st:
            sg = stage_of(s)
            if sg not in ("association", "png_window", "retained"):
                continue
            srows.append({
                "frame_key": key, "preset": preset, "detector": fr.detector, "band": "SWIR" if fr.detector <= 3 else "MWIR",
                "gaia_source_id": s["gaia"], "G": s["G"], "stage": sg, "snr": s["snr"],
                "adverse_flag_in_window": s["adverse_in_window"] > 0, "ambiguous": is_ambiguous(s),
                "sep_target_arcsec": s["sep_target_arcsec"],
                "native_dx_px": s["native_dx"], "native_dy_px": s["native_dy"], "native_r_px": s["native_r"],
                "native_r_arcsec": s["native_r"] * fr.scale_arcsec,
                "png_dx_display_px": s.get("png_dx"), "png_dy_display_px": s.get("png_dy"),
                "png_r_display_px": s.get("png_r"),
                "png_r_arcsec": None if s.get("png_r") is None else s["png_r"] * 1.40625,
            })
    write_csv(out / "residual_stars.csv", srows, list(srows[0].keys()))
    ret = [r for r in srows if r["stage"] == "retained"]
    elig = srows

    def strat(rows, keyf, field):
        groups = collections.defaultdict(list)
        for r in rows:
            groups[keyf(r)].append(r[field])
        return {str(k): q(v, (50, 90)) for k, v in sorted(groups.items(), key=lambda kv: str(kv[0]))}

    snr_bin = lambda r: "15-30" if r["snr"] < 30 else ("30-100" if r["snr"] < 100 else ">=100")  # noqa: E731
    per_frame_png = [r["median_png_r_display_px"] for r in funnel if r["median_png_r_display_px"] is not None]
    nat_scale = q([fr.scale_arcsec for _, fr in frames.values()], (50,))
    residual_summary = {
        "important": "These are residuals of stars that survived the selection funnel (SNR >= 15, centroid within "
                     "1 native px of Gaia, clean PNG window). The 1 px association cut truncates the native "
                     "distribution by construction, so a median over these matches is NOT a global accuracy bound "
                     f"for all {len(records)} products. {len(no_check)} of {len(funnel)} unique frames have no retained star at all.",
        "units": {"native_px_arcsec_summary": nat_scale, "display_px_arcsec": 1.40625,
                  "native_px_in_display_px": nat_scale.get("p50", float("nan")) / 1.40625},
        "retained_matches": {
            "n_stars": len(ret), "n_frames": len({r["frame_key"] for r in ret}),
            "native_r_px": q([r["native_r_px"] for r in ret]),
            "native_r_arcsec": q([r["native_r_arcsec"] for r in ret]),
            "png_r_display_px": q([r["png_r_display_px"] for r in ret]),
            "png_r_arcsec": q([r["png_r_arcsec"] for r in ret]),
            "median_vector_native_px": [float(np.median([r["native_dx_px"] for r in ret])), float(np.median([r["native_dy_px"] for r in ret]))],
            "median_vector_png_display_px": [float(np.median([r["png_dx_display_px"] for r in ret])), float(np.median([r["png_dy_display_px"] for r in ret]))],
        },
        "retained_unambiguous_only": {
            "n_stars": sum(1 for r in ret if not r["ambiguous"]),
            "png_r_display_px": q([r["png_r_display_px"] for r in ret if not r["ambiguous"]]),
            "native_r_arcsec": q([r["native_r_arcsec"] for r in ret if not r["ambiguous"]]),
        },
        "png_tail_over_2_display_px": {
            "n": sum(1 for r in ret if r["png_r_display_px"] > 2),
            "catalog_ambiguous": sum(1 for r in ret if r["png_r_display_px"] > 2 and r["ambiguous"]),
            "note": "The legacy PNG centroid uses a 17x17 display px window (about 4 native px); a catalog neighbour "
                    "within ~4 native px pulls it. 'ambiguous' = another cached Gaia star within 4 native px.",
        },
        "per_frame_median_png_r_display_px_unique_frames": q(per_frame_png, (50, 90, 95)),
        "legacy_headline_reproduced": {
            "description": "median over records (incl. 5 case copies) of each record's median PNG offset; the published "
                           "headline was 0.45 display px over 161 records, worst 2.0",
            "value": None,  # filled below
        },
        "snr_eligible_before_association": {
            "n_stars": len(elig),
            "native_r_px": q([r["native_r_px"] for r in elig]),
            "fraction_dropped_by_1px_association": sum(1 for r in elig if r["stage"] == "association") / len(elig),
            "note": "Still bounded at ~3 native px by the forced window (search +-1 px, 5x5 centroid). See blind_matching.json for an unbounded view.",
        },
        "strata_retained_png_r_display_px": {
            "detector": strat(ret, lambda r: f"D{r['detector']}", "png_r_display_px"),
            "band": strat(ret, lambda r: r["band"], "png_r_display_px"),
            "preset": strat(ret, lambda r: r["preset"], "png_r_display_px"),
            "adverse_flag_in_centroid_window": strat(ret, lambda r: r["adverse_flag_in_window"], "png_r_display_px"),
            "catalog_ambiguous": strat(ret, lambda r: r["ambiguous"], "png_r_display_px"),
            "snr_bin": strat(ret, snr_bin, "png_r_display_px"),
            "within_90arcsec_of_target": strat(ret, lambda r: r["sep_target_arcsec"] < 90, "png_r_display_px"),
        },
        "strata_retained_native_r_arcsec": {
            "band": strat(ret, lambda r: r["band"], "native_r_arcsec"),
            "detector": strat(ret, lambda r: f"D{r['detector']}", "native_r_arcsec"),
        },
    }
    # reproduce the record-level headline (frames + case copies)
    rec_meds = per_frame_png + [c["median_png_r_display_px"] for c in case_rows if c["median_png_r_display_px"] is not None]
    residual_summary["legacy_headline_reproduced"]["value"] = {"n_records": len(rec_meds), "median": float(np.median(rec_meds)),
                                                               "max": float(np.max(rec_meds))}
    dump(out / "residual_summary.json", residual_summary)

    # ---------------- 3. sensitivity (forced mode)
    sens = []

    def summarise(label, stars_map, snr_min, assoc, extra=None):
        ret_ = []
        nfr = 0
        amb = 0
        elig_ = 0
        for key, st in stars_map.items():
            rr = [s for s in st if stage_of(s, snr_min, assoc) == "retained"]
            elig_ += sum(1 for s in st if stage_of(s, snr_min, assoc) in ("association", "png_window", "retained"))
            nfr += bool(rr)
            amb += sum(is_ambiguous(s, assoc) for s in rr)
            ret_ += rr
        row = {"label": label, "snr_min": snr_min, "assoc_native_px": assoc, **(extra or {}),
               "snr_eligible": elig_, "retained": len(ret_), "retained_fraction_of_eligible": len(ret_) / elig_ if elig_ else None,
               "frames_with_retained": nfr, "retained_ambiguous": amb,
               "native_r_px_p50": float(np.median([s["native_r"] for s in ret_])) if ret_ else None,
               "native_r_px_p90": float(np.percentile([s["native_r"] for s in ret_], 90)) if ret_ else None,
               "png_r_display_px_p50": float(np.median([s["png_r"] for s in ret_])) if ret_ else None,
               "png_r_display_px_p90": float(np.percentile([s["png_r"] for s in ret_], 90)) if ret_ else None}
        sens.append(row)

    for snr_min in (5.0, 10.0, 15.0, 25.0, 50.0):
        for assoc in (0.5, 1.0, 1.5, 2.0, 3.0):
            summarise("grid", stars_by, snr_min, assoc, {"half": 2, "target_excl_arcsec": 40.0})
    for half in (1, 3):
        alt = {}
        for key, (preset, fr) in frames.items():
            R = frames_rec[key]
            g, al = png_arrays(R["png"])
            alt[key] = frame_stars(fr, cats[preset], preds[key], g, al, R["rec"]["registration"], half=half)
        summarise(f"centroid_half_{half}", alt, 15.0, 1.0, {"half": half, "target_excl_arcsec": 40.0})
    for excl in (20.0, 80.0):
        alt = {}
        for key, (preset, fr) in frames.items():
            R = frames_rec[key]
            g, al = png_arrays(R["png"])
            alt[key] = frame_stars(fr, cats[preset], preds[key], g, al, R["rec"]["registration"], excl=excl)
        summarise(f"target_excl_{int(excl)}", alt, 15.0, 1.0, {"half": 2, "target_excl_arcsec": excl})
    write_csv(out / "sensitivity.csv", sens, list(dict.fromkeys(k for r in sens for k in r)))

    # ---------------- 4. blind (WCS-free eligibility) matching + chance rate
    radii = (0.5, 1.0, 1.5, 2.0, 3.0, 5.0)
    blind_rows = []
    agg = {"n_detections": 0, **{f"matched_r{r}": 0 for r in radii}, **{f"chance_r{r}": 0.0 for r in radii},
           **{f"ambiguous_r{r}": 0 for r in radii}}
    verdicts = []
    nn_true, nn_chance = [], []
    for key, (preset, fr) in frames.items():
        ny, nx = fr.shape
        dets = rc.blind_detect(fr, snr_min=15.0)
        dets = rc.detections_away_from_target(fr, dets, preds[key], 40.0)
        proj = [c for c in rc.project_catalog(fr, [c for c in cats[preset] if c["full"]], preds[key], 40.0)
                if not c["near_target"]]
        row = {"frame_key": key, "preset": preset, "detector": fr.detector, "n_detections": len(dets)}
        for d in dets:
            ds = nearest(d, proj)
            nn_true.append(ds[0] if ds else float("inf"))
            for k in (1, 2, 3):
                dsc = nearest(d, scrambled(proj, nx, ny, k))
                nn_chance.append(dsc[0] if dsc else float("inf"))
            for r in radii:
                m = sum(1 for x in ds if x <= r)
                row[f"matched_r{r}"] = row.get(f"matched_r{r}", 0) + (m >= 1)
                row[f"ambiguous_r{r}"] = row.get(f"ambiguous_r{r}", 0) + (m >= 2)
                ch = np.mean([sum(1 for x in nearest(d, scrambled(proj, nx, ny, k)) if x <= r) >= 1 for k in (1, 2, 3)])
                row[f"chance_r{r}"] = row.get(f"chance_r{r}", 0.0) + float(ch)
        for kk in agg:
            agg[kk] += row.get(kk, 0)
        blind_rows.append(row)
        v = rc.registration_verdict(fr, cats[preset], preds[key], dets=rc.blind_detect(fr, snr_min=15.0))
        verdicts.append({"frame_key": key, "preset": preset, "detector": fr.detector, "verdict": v["verdict"],
                         "n_detections": v["n_detections"], "zero_offset_matches": v["zero_offset_matches"],
                         "best_support": v["best_support"], "best_offset_dx_px": v["best_offset_px"][0],
                         "best_offset_dy_px": v["best_offset_px"][1], "best_offset_abs_px": v["best_offset_abs_px"],
                         "offset_significance": v["offset_significance"],
                         "rotation_deg": v["similarity_fit"]["rotation_deg"] if v["similarity_fit"] else None,
                         "rotation_sigma_deg": v["similarity_fit"]["rotation_sigma_deg"] if v["similarity_fit"] else None,
                         "legacy_retained": next(x["retained"] for x in funnel if x["frame_key"] == key),
                         "reasons": " | ".join(v["reasons"])})
    write_csv(out / "validator_real_frames.csv", verdicts, list(verdicts[0].keys()))
    vc = collections.Counter(v["verdict"] for v in verdicts)
    passed = [v for v in verdicts if v["verdict"] == "PASS"]
    blind_summary = {
        "method": "Blind detections (local maxima of the despiked image, finite 7x7 window, peak SNR >= 15 MAD; no "
                  "catalog, no WCS) more than 40\" from the target, matched to every Gaia star projected through the "
                  "header WCS. Chance rate: the same detections matched to the catalog rotated by 90/180/270 deg "
                  "about the cutout centre (same density, no true counterparts).",
        "totals": agg,
        "matched_fraction_by_radius": {str(r): agg[f"matched_r{r}"] / agg["n_detections"] for r in radii},
        "chance_fraction_by_radius": {str(r): agg[f"chance_r{r}"] / agg["n_detections"] for r in radii},
        "ambiguous_fraction_by_radius": {str(r): agg[f"ambiguous_r{r}"] / agg["n_detections"] for r in radii},
        "nearest_gaia_distance_px": q(nn_true, (25, 50, 75, 90)),
        "nearest_gaia_distance_px_chance": q(nn_chance, (25, 50, 75, 90)),
        "interpretation": "Unmatched detections are expected: the cached catalog stops at G=15 (Barnard, RW Aur) or "
                          "G=17, so red or faint near-IR sources have no entry. Widening the radius adds matches at "
                          "roughly the chance rate shown, i.e. they are not secure identifications.",
        "validator_on_real_frames": {
            "verdict_counts": dict(vc),
            "pass_best_offset_abs_px": q([v["best_offset_abs_px"] for v in passed], (50, 90, 95)),
            "pass_offset_significance": q([v["offset_significance"] for v in passed], (50, 90, 95)),
            "pass_abs_rotation_deg": q([abs(v["rotation_deg"]) for v in passed if v["rotation_deg"] is not None], (50, 90, 95)),
            "pass_rotation_z": q([abs(v["rotation_deg"]) / v["rotation_sigma_deg"] for v in passed
                                  if v["rotation_deg"] is not None and v["rotation_sigma_deg"]], (50, 90, 95)),
            "thresholds": rc.VALIDATOR,
            "legacy_vs_validator": dict(collections.Counter(
                f"legacy_{'checked' if v['legacy_retained'] else 'none'}__validator_{v['verdict']}" for v in verdicts)),
        },
    }
    write_csv(out / "blind_matching_per_frame.csv", blind_rows, list(dict.fromkeys(k for r in blind_rows for k in r)))
    dump(out / "blind_matching.json", blind_summary)

    # ---------------- 5. negative control (derived fixtures; separate from real results)
    neg = {"description": "Derived fixtures: the pixels of a real cutout are moved by a known amount relative to its "
                          "unchanged header (shift in native px, or rotation about the cutout centre), and the PNG is "
                          "re-rendered from the moved pixels exactly as processor A would. This is what a wrong header "
                          "registration looks like to every check that trusts the header. Not real observations; "
                          "nothing is written to the product tree.",
           "runs": []}
    with tempfile.TemporaryDirectory() as td:
        for preset, key, why in FIXTURE_FRAMES:
            f = mby[key]
            R = frames_rec[key]
            for label, dx, dy, rot in FIXTURE_PERTURBATIONS:
                hd = rc.misregistered_hdul(data / f["file"], dx, dy, rot)
                fr = rc.frame_from_hdul(hd, key)
                gray, alpha = rc.render_png_arrays(fr, R["rec"]["registration"], R["rec"]["display_scale"])
                fx_fits = Path(td) / f"{key}_{label}.fits"
                fx_png = Path(td) / f"{key}_{label}.png"
                hd.writeto(fx_fits)
                Image.fromarray(np.stack([gray, alpha], -1).astype(np.uint8), mode="LA").save(fx_png)
                full = acc.check_one(R["rec"], str(fx_png), None, str(fx_fits), f, targets[preset], [R["rec"]])
                leg = rc.legacy_gaia_rule(fr, cats[preset], preds[key], gray, alpha, R["rec"]["registration"])
                v = rc.registration_verdict(fr, cats[preset], preds[key])
                fit = v["similarity_fit"] or {}
                neg["runs"].append({
                    "frame_key": key, "why": why, "perturbation": label, "injected_dx_px": dx, "injected_dy_px": dy,
                    "injected_rot_deg": rot,
                    "legacy_acceptance_check_one_registration": bool(full["checks"]["registration"]),
                    "legacy_png_reconstruction_alpha_match": full["evidence"]["png_reconstruction"]["alpha_match_fraction"],
                    "legacy_gaia_n_native": leg["n_native"], "legacy_gaia_n_png": leg["n_png"],
                    "legacy_png_median_offset_display_px": leg["png_median_offset_display_px"],
                    "legacy_gaia_evidence_present": leg["gaia_evidence_present"],
                    "validator_verdict": v["verdict"], "validator_reasons": v["reasons"],
                    "validator_n_detections": v["n_detections"], "validator_zero_offset_matches": v["zero_offset_matches"],
                    "validator_best_support": v["best_support"], "validator_recovered_offset_px": v["best_offset_px"],
                    "validator_recovered_rot_deg": fit.get("rotation_deg"), "validator_rot_sigma_deg": fit.get("rotation_sigma_deg"),
                })
                hd.close()
    dump(out / "negative_control.json", neg)

    # ---------------- 6. fair_comparison C
    dump(out / "fair_comparison_c.json", fair_comparison_c(frames, preds, cats, stars_by, funnel, targets))

    # ---------------- 7. Barnard separation
    bar = barnard(frames, preds, frames_rec, records, stars_by, verdicts, targets)
    dump(out / "barnard_separation.json", bar)

    # ---------------- 8. inventory + run info
    inv["frames_without_independent_star_check_legacy"] = [r["frame_key"] for r in no_check]
    inv["frames_validator_verdicts"] = dict(vc)
    dump(out / "inventory.json", inv)
    import astropy
    import PIL
    run = {"command": "audit_registration.py --data-root <research/build_data> --out-dir <empty dir>",
           "python": sys.version.split()[0], "numpy": np.__version__, "astropy": astropy.__version__, "pillow": PIL.__version__,
           "manifest_sha256": sha256(data / "manifest.json"),
           "gaia_csv_sha256": {p.name: sha256(p) for p in sorted(GAIA_DIR.glob("*.csv"))},
           "products_frames_json_sha256": {str(Path(p).relative_to(prod)): sha256(p)
                                           for p in sorted(glob.glob(str(prod / "*" / "*" / "frames.json")))}}
    dump(out / "run_info.json", run)

    import plots
    plots.residual_plot(out / "residual_stars.csv", out / "residuals.png")
    plots.negative_control_plot(out / "negative_control.json", out / "negative_control.png")
    print(json.dumps(r6({"inventory": {k: inv[k] for k in ("unique_raw_cutouts", "unique_exposures_obsid", "product_records",
                                                              "product_records_case_copies")},
                         "funnel_totals": tot, "unique_frames_with_retained_star": n_checked_unique,
                         "records_with_retained_star": n_checked_records,
                         "legacy_identity_mismatches": legacy_mismatch,
                         "retained_png_r_display_px": residual_summary["retained_matches"]["png_r_display_px"],
                         "headline": residual_summary["legacy_headline_reproduced"]["value"],
                         "validator": dict(vc)}), indent=1))
    return 0


# ----------------------------------------------------------- fair_comparison C


def fair_comparison_c(frames, preds, cats, stars_by, funnel, targets):
    preset, frC = frames[FAIR_C]
    _, frA = frames[FAIR_A]
    out = {"frame_key": FAIR_C, "same_exposure_sibling": FAIR_A,
           "same_time": frA.mjd == frC.mjd}
    fr_row = next(r for r in funnel if r["frame_key"] == FAIR_C)
    out["legacy_funnel"] = {k: fr_row[k] for k in ("catalog_rows", "near_target", "outside_footprint", "attempted", "edge",
                                                   "nonfinite", "low_snr", "snr_eligible", "retained", "max_snr_attempted")}
    # SNR of every attempted catalog star in C, and what lower thresholds would admit
    att = [s for s in stars_by[FAIR_C] if s["pre"] == "ok"]
    out["attempted_catalog_stars"] = [{"gaia": s["gaia"], "G": s["G"], "snr": s["snr"], "native_r_px": s["native_r"],
                                       "ambiguous": is_ambiguous(s), "adverse_in_window": s["adverse_in_window"]}
                                      for s in sorted(att, key=lambda s: -s["snr"])]
    out["lower_snr_thresholds"] = {}
    for t in (10.0, 8.0, 5.0):
        sel = [s for s in att if s["snr"] >= t]
        out["lower_snr_thresholds"][str(t)] = {
            "n_eligible": len(sel), "n_within_1px": sum(1 for s in sel if s["native_r"] < 1.0),
            "native_r_px": [s["native_r"] for s in sel]}
    # same stars in A (Gaia-checked sibling)
    a_ret = [s for s in stars_by[FAIR_A] if stage_of(s) == "retained"]
    out["sibling_A_retained"] = {"n": len(a_ret), "median_native_r_px": float(np.median([s["native_r"] for s in a_ret])) if a_ret else None}
    vA = rc.registration_verdict(frA, cats[preset], preds[FAIR_A])
    vC = rc.registration_verdict(frC, cats[preset], preds[FAIR_C])
    out["validator"] = {"A": {k: vA[k] for k in ("verdict", "n_detections", "best_support", "best_offset_px")},
                        "C": {k: vC[k] for k in ("verdict", "n_detections", "best_support", "best_offset_px", "reasons")}}

    # relative control 1: the target itself, centroided in A and C, mapped to sky by each header
    def target_centroid(fr, pred):
        x, y = (float(v) for v in fr.wcs.all_world2pix([[pred[0], pred[1]]], 0)[0])
        st, res = rc.forced_measure(fr, x, y, snr_min=-np.inf)
        if st != "ok":
            return {"stage": st}
        ra, dec = (float(v) for v in fr.wcs.all_pix2world([[res["cx"], res["cy"]]], 0)[0])
        return {"stage": st, "snr": res["snr"], "adverse_in_window": res["adverse_in_window"],
                "native_offset_from_prediction_px": [res["cx"] - x, res["cy"] - y],
                "sky_offset_from_prediction_arcsec": [(ra - pred[0]) * math.cos(math.radians(pred[1])) * 3600, (dec - pred[1]) * 3600],
                "ra": ra, "dec": dec}
    tA, tC = target_centroid(frA, preds[FAIR_A]), target_centroid(frC, preds[FAIR_C])
    rel = {"A": tA, "C": tC}
    if tA.get("stage") == "ok" and tC.get("stage") == "ok":
        dra = (tC["ra"] - tA["ra"]) * math.cos(math.radians(tA["dec"])) * 3600
        ddec = (tC["dec"] - tA["dec"]) * 3600
        rel["C_minus_A_sky_arcsec"] = [dra, ddec]
        rel["C_minus_A_abs_arcsec"] = math.hypot(dra, ddec)
        rel["C_minus_A_abs_native_px"] = math.hypot(dra, ddec) / frC.scale_arcsec
    out["relative_control_target"] = rel

    # relative control 2: field sources detected in both A (SNR>=15) and C (SNR>=8), matched on sky
    detA = rc.detections_away_from_target(frA, rc.blind_detect(frA, snr_min=15.0), preds[FAIR_A], 40.0)
    detC = rc.detections_away_from_target(frC, rc.blind_detect(frC, snr_min=8.0), preds[FAIR_C], 40.0)

    def sky(fr, d):
        return tuple(float(v) for v in fr.wcs.all_pix2world([[d["x"], d["y"]]], 0)[0])
    pairs = []
    for dc in detC:
        rc_, dc_ = sky(frC, dc)
        cands = []
        for da in detA:
            ra_, de_ = sky(frA, da)
            sep = rc.sky_sep_arcsec(rc_, dc_, ra_, de_)
            if sep <= frC.scale_arcsec:  # 1 native px
                cands.append((sep, da, ((rc_ - ra_) * math.cos(math.radians(de_)) * 3600, (dc_ - de_) * 3600)))
        if cands:
            cands.sort(key=lambda c: c[0])
            pairs.append({"C_snr": dc["snr"], "A_snr": cands[0][1]["snr"], "sep_arcsec": cands[0][0],
                          "dra_arcsec": cands[0][2][0], "ddec_arcsec": cands[0][2][1], "ambiguous": len(cands) > 1})
    out["relative_control_field"] = {
        "A_detections_snr15": len(detA), "C_detections_snr8": len(detC), "matched_within_1_native_px": len(pairs),
        "pairs": pairs,
        "median_C_minus_A_arcsec": [float(np.median([p["dra_arcsec"] for p in pairs])), float(np.median([p["ddec_arcsec"] for p in pairs]))] if pairs else None,
        "note": "C detections at SNR 8 are below the legacy 15 threshold; a 1 native px sky match radius with few "
                "sources can include chance pairs, so this is a consistency indication, not an identification.",
    }
    # calibration: same-detector-pair offsets for other exposures where both frames have validator support
    cal = []
    by_obs = collections.defaultdict(dict)
    for key, (p, fr) in frames.items():
        by_obs[key.rsplit("_D", 1)[0]][fr.detector] = key
    for obs, dd in sorted(by_obs.items()):
        for d1 in (1, 2, 3):
            if d1 in dd and d1 + 3 in dd:
                k1, k2 = dd[d1], dd[d1 + 3]
                p1, f1 = frames[k1]
                _, f2 = frames[k2]
                t1, t2 = target_centroid(f1, preds[k1]), target_centroid(f2, preds[k2])
                if t1.get("stage") == "ok" and t2.get("stage") == "ok" and t1["snr"] >= 15 and t2["snr"] >= 15 \
                        and t1["adverse_in_window"] == 0 and t2["adverse_in_window"] == 0:
                    dra = (t2["ra"] - t1["ra"]) * math.cos(math.radians(t1["dec"])) * 3600
                    cal.append({"obs": obs, "pair": f"D{d1}/D{d1 + 3}", "preset": p1,
                                "target_sky_diff_arcsec": math.hypot(dra, (t2["dec"] - t1["dec"]) * 3600)})
    out["calibration_same_exposure_target_pairs"] = {"n": len(cal), "abs_arcsec": q([c["target_sky_diff_arcsec"] for c in cal], (50, 90, 95)),
                                                     "pairs": cal,
                                                     "selection": "both centroids SNR >= 15 with no adverse flag in the 5x5 window"}
    out["verdict"] = "unknown"
    out["verdict_reason"] = (
        "No Gaia DR3 field star reaches the legacy SNR 15 in C (4.94 um), and the WCS-free validator finds too few "
        "detections, so no independent field-star registration check exists for this frame. Header-WCS "
        "reconstruction of the PNG is not independent validation. The relative controls (the target centroid in C vs "
        "its Gaia-checked same-exposure sibling A, and field sources common to A and C) are consistency checks on the "
        "same instant through a different detector; they do not replace an independent reference.")
    return out


# --------------------------------------------------------------------- Barnard


def glow_proxy(gray, alpha, x, y, half=7, iters=6):
    """Visual saturated-glow proxy (same definition as science/reviews/barnard):
    transparent (non-finite, saturated) pixels in the window count as white.
    Not an astrometric measurement."""
    g = gray.astype(float).copy()
    cx, cy = x, y
    for _ in range(iters):
        ix, iy = int(math.floor(cx)), int(math.floor(cy))
        win = g[iy - half: iy + half + 1, ix - half: ix + half + 1].copy()
        a = alpha[iy - half: iy + half + 1, ix - half: ix + half + 1]
        win[a == 0] = 255.0
        box = g[iy - 20: iy + 21, ix - 20: ix + 21]
        abox = alpha[iy - 20: iy + 21, ix - 20: ix + 21]
        bg = np.median(box[abox > 0])
        w = np.clip(win - bg, 0, None)
        yy, xx = np.mgrid[iy - half: iy + half + 1, ix - half: ix + half + 1]
        cx = float((w * (xx + 0.5)).sum() / w.sum())
        cy = float((w * (yy + 0.5)).sum() / w.sum())
    return cx, cy


def barnard(frames, preds, frames_rec, records, stars_by, verdicts, targets):
    rows = []
    for key, (preset, fr) in frames.items():
        if preset != "barnards_star":
            continue
        R = frames_rec[key]
        rec = R["rec"]
        reg = rec["registration"]
        mx, my = rec["marker"]["x"], rec["marker"]["y"]
        ix, iy = acc.sky_to_display(*preds[key], reg["center_ra_deg"], reg["center_dec_deg"], reg["fov_arcmin"], reg["width"])
        gray, alpha = png_arrays(R["png"])
        prox = {h: glow_proxy(gray, alpha, mx, my, half=h) for h in (5, 7, 10)}
        nx_, ny_ = (float(v) for v in fr.wcs.all_world2pix([[preds[key][0], preds[key][1]]], 0)[0])
        yy, xx = np.mgrid[0:fr.shape[0], 0:fr.shape[1]]
        core_nonfinite = int(((np.hypot(xx - nx_, yy - ny_) <= 3) & ~fr.good).sum())
        ret = [s for s in stars_by[key] if stage_of(s) == "retained"]
        v = next(v for v in verdicts if v["frame_key"] == key)
        rows.append({
            "frame_key": key, "mjd": fr.mjd, "detector": fr.detector,
            "marker_display_xy": [mx, my], "marker_minus_independent_prediction_display_px": math.hypot(mx - ix, my - iy),
            "quality_status": rec["quality"]["status"], "core_nonfinite_native_px_r3": core_nonfinite,
            "glow_proxy_minus_marker_display_px": {str(h): [p[0] - mx, p[1] - my] for h, p in prox.items()},
            "field_retained_stars": len(ret),
            "field_median_png_r_display_px": float(np.median([s["png_r"] for s in ret])) if ret else None,
            "field_median_png_vector_display_px": [float(np.median([s["png_dx"] for s in ret])), float(np.median([s["png_dy"] for s in ret]))] if ret else None,
            "validator_verdict": v["verdict"], "validator_offset_native_px": [v["best_offset_dx_px"], v["best_offset_dy_px"]],
        })
    prox7 = np.array([r["glow_proxy_minus_marker_display_px"]["7"] for r in rows])
    case = {}
    case_recs = {r["rec"]["frame_key"]: r for r in records if r["set"] == "case-moving_neighbor"}
    for k in MN_CASE:
        r = case_recs[k]
        g, al = png_arrays(r["png"])
        mx, my = r["rec"]["marker"]["x"], r["rec"]["marker"]["y"]
        case[k] = {"marker": [mx, my], "glow_proxy_h7": list(glow_proxy(g, al, mx, my, half=7))}
    A = MN_CASE[0]
    motion = {}
    for k in MN_CASE[1:]:
        md = np.subtract(case[k]["marker"], case[A]["marker"])
        pd = np.subtract(case[k]["glow_proxy_h7"], case[A]["glow_proxy_h7"])
        motion[f"A_to_{k}"] = {"marker_shift_display_px": [float(md[0]), float(md[1])], "marker_shift_abs_display_px": float(np.hypot(*md)),
                               "marker_shift_arcsec": float(np.hypot(*md)) * 1.40625,
                               "glow_proxy_shift_display_px": [float(pd[0]), float(pd[1])], "glow_proxy_shift_abs_display_px": float(np.hypot(*pd))}
    t = targets["barnards_star"]
    return {
        "layers": {
            "1_propagated_marker": "Catalog prediction: manifest SIMBAD J2000 astrometry propagated with astropy apply_space_motion "
                                   "to MJD-AVG and projected on the display grid. Independent of these images. Annual parallax "
                                   f"(amplitude {t['parallax_mas'] / 1000:.3f} arcsec = {t['parallax_mas'] / 1000 / 1.40625:.2f} display px) "
                                   "is NOT modelled: the marker can be off the apparent position by up to that amount, and "
                                   "epoch-to-epoch comparisons by up to about twice it.",
            "2_visual_glow_proxy": "Intensity-weighted centre of the saturated glow on the published PNG, transparent (non-finite) "
                                   "core counted as white. A visual aid only: the core is saturated and non-finite, so no "
                                   "centroid, proper motion or precision astrometry is supported.",
            "3_surrounding_star_residuals": "Gaia DR3 field stars (>40\" from the target) centroided in the native image and the "
                                            "PNG: this is the registration evidence for the frame.",
        },
        "frames": rows,
        "summary": {
            "n_frames": len(rows),
            "marker_minus_independent_prediction_display_px_max": max(r["marker_minus_independent_prediction_display_px"] for r in rows),
            "glow_proxy_minus_marker_h7_display_px": {"median_dx_dy": [float(np.median(prox7[:, 0])), float(np.median(prox7[:, 1]))],
                                                      "std_dx_dy": [float(np.std(prox7[:, 0])), float(np.std(prox7[:, 1]))],
                                                      "max_abs": float(np.max(np.hypot(prox7[:, 0], prox7[:, 1])))},
            "glow_proxy_method_dependence_display_px": q([math.hypot(np.subtract(r["glow_proxy_minus_marker_display_px"]["10"], r["glow_proxy_minus_marker_display_px"]["5"])[0],
                                                                     np.subtract(r["glow_proxy_minus_marker_display_px"]["10"], r["glow_proxy_minus_marker_display_px"]["5"])[1]) for r in rows], (50, 90)),
            "frames_with_nonfinite_core": sum(1 for r in rows if r["core_nonfinite_native_px_r3"] > 0),
            "field_frames_with_retained_star": sum(1 for r in rows if r["field_retained_stars"]),
            "field_median_png_r_display_px_per_frame": q([r["field_median_png_r_display_px"] for r in rows if r["field_median_png_r_display_px"] is not None], (50, 90)),
            "validator_verdicts": dict(collections.Counter(r["validator_verdict"] for r in rows)),
        },
        "moving_neighbor_case": {"frames": case, "motion": motion,
                                 "statement": "Marker shift is a catalog prediction; the glow proxy shift is a visual "
                                              "consistency check only. Neither is a measured proper motion."},
    }


if __name__ == "__main__":
    sys.exit(main())
