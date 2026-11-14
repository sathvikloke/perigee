"""Per-frame numbers for the six case frames, processor A vs Sagar, plus product sizes.

Usage: .venv/bin/python coordination/processor-compare/compare_numbers.py \
          --a backend/content/presets --sagar <sagar>/backend/content/presets --out numbers.json
"""
import argparse
import json
import math
from pathlib import Path

CASES = {
    ("epsilon_indi_b", "fair_comparison"): ["2026W18_1A_0516_1_D3", "2026W39_2A_0597_4_D3", "2026W18_1A_0516_1_D6"],
    ("barnards_star", "moving_neighbor"): ["2025W35_1A_0008_1_D3", "2026W12_1A_0610_2_D3", "2026W34_1A_0431_1_D3"],
}

ap = argparse.ArgumentParser()
ap.add_argument("--a", required=True)
ap.add_argument("--sagar", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
A, S = Path(a.a), Path(a.sagar)
smanifest = json.loads((S / "manifest.json").read_text())["assets"]


def sizes(root):
    files = [p for p in root.rglob("*") if p.is_file()]
    by = lambda ext: sum(p.stat().st_size for p in files if p.suffix == ext)
    return {"files": len(files), "png_files": sum(p.suffix == ".png" for p in files),
            "json_files": sum(p.suffix == ".json" for p in files),
            "png_bytes": by(".png"), "json_bytes": by(".json"), "other_bytes": sum(p.stat().st_size for p in files if p.suffix not in (".png", ".json")),
            "total_bytes": sum(p.stat().st_size for p in files)}


rows = []
for (preset, case), keys in CASES.items():
    arecs = {r["frame_key"]: r for r in json.loads((A / preset / f"case-{case}" / "frames.json").read_text())["frames"]}
    srecs = {r["frame_key"]: r for r in json.loads((S / preset / "sets" / f"{case}.json").read_text())["frames"]}
    for k in keys:
        ra, rs = arecs[k], srecs[k]

        def side(r, png_path, flag_path):
            q, reg, m, ds = r["quality"], r["registration"], r["marker"] or {}, r["display_scale"]
            return {
                "case_ref": r.get("case_ref"),
                "wavelength_um": r["wavelength_um"], "bandwidth_um": r["bandwidth_um"], "mjd": r["mjd"],
                "observed_at_utc": r["observed_at_utc"],
                "status": q["status"], "valid": q.get("valid_aperture_pixels"), "adverse": q.get("adverse_aperture_pixels"),
                "screened": q.get("screened_pixels"), "nonfinite": q.get("nonfinite_aperture_pixels"),
                "flag_names": q.get("flag_names"),
                "marker_xy": [m.get("x"), m.get("y")],
                "grid_center": [reg["center_ra_deg"], reg["center_dec_deg"]], "fov_arcmin": reg["fov_arcmin"],
                "scale_arcsec_per_px": reg["scale_arcsec_per_px"], "grid_id": reg.get("grid_id"),
                "resample": reg.get("method"),
                "stretch": {"mode": ds["mode"], "low": ds["low"], "high": ds["high"], "soft": ds["asinh_softening"],
                            "background_offset": ds.get("background_offset")},
                "png_bytes": png_path.stat().st_size, "flag_png_bytes": flag_path.stat().st_size if flag_path else None,
            }

        sa = side(ra, A / preset / f"case-{case}" / f"{k}.png", A / preset / f"case-{case}" / f"{k}.flags.png")
        ss = side(rs, S / smanifest[rs["image"]["asset_id"]]["path"],
                  S / smanifest[rs["flag_image"]["asset_id"]]["path"] if rs.get("flag_image") else None)
        # marker in arcsec from grid centre, comparable across the two grid scales
        for sd in (sa, ss):
            sd["marker_offset_from_centre_arcsec"] = [round((sd["marker_xy"][0] - 128) * sd["scale_arcsec_per_px"], 3),
                                                      round((sd["marker_xy"][1] - 128) * sd["scale_arcsec_per_px"], 3)]
        rows.append({"case": case, "frame_key": k, "A": sa, "sagar": ss,
                     "diff": {"wavelength_um": rs["wavelength_um"] - ra["wavelength_um"],
                              "bandwidth_um": rs["bandwidth_um"] - ra["bandwidth_um"],
                              "mjd": rs["mjd"] - ra["mjd"],
                              "status_equal": sa["status"] == ss["status"],
                              "valid_adverse_equal": [sa["valid"], sa["adverse"]] == [ss["valid"], ss["adverse"]],
                              "marker_offset_arcsec_diff": [round(ss["marker_offset_from_centre_arcsec"][i] - sa["marker_offset_from_centre_arcsec"][i], 3) for i in (0, 1)],
                              "grid_center_equal": sa["grid_center"] == ss["grid_center"]}})

motion = {}
for who, recs in (("A", [r["A"] for r in rows if r["case"] == "moving_neighbor"]), ("sagar", [r["sagar"] for r in rows if r["case"] == "moving_neighbor"])):
    a0 = recs[0]["marker_xy"]
    motion[who] = [{"to": i, "display_px": round(math.hypot(r["marker_xy"][0] - a0[0], r["marker_xy"][1] - a0[1]), 2),
                    "arcsec": round(math.hypot(r["marker_xy"][0] - a0[0], r["marker_xy"][1] - a0[1]) * r["scale_arcsec_per_px"], 2)}
                   for i, r in zip("BC", recs[1:])]

out = {"rows": rows, "moving_neighbor_marker_motion": motion, "sizes": {"A": sizes(A), "sagar": sizes(S)}}
Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
for r in rows:
    print(r["frame_key"], r["case"], r["A"]["case_ref"], r["sagar"]["case_ref"], json.dumps(r["diff"]))
    for who in ("A", "sagar"):
        s = r[who]
        print(f"  {who:5s} wl={s['wavelength_um']:.9f} mjd={s['mjd']} {s['status']} v/a={s['valid']}/{s['adverse']} scr={s['screened']} nf={s['nonfinite']} "
              f"flags={s['flag_names']} mk={s['marker_xy']} off\"={s['marker_offset_from_centre_arcsec']} fov={s['fov_arcmin']} sc={s['scale_arcsec_per_px']} "
              f"png={s['png_bytes']} flagpng={s['flag_png_bytes']} stretch={s['stretch']['mode']} {s['stretch']['low']:.4g}..{s['stretch']['high']:.4g}")
print(json.dumps(motion))
print(json.dumps(out["sizes"], indent=1))
