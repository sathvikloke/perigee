"""Time and summarise the *live* processor path (the callable API A resolves through
backend.routes._adapters) over every retained cutout, offline.

Run once per checkout (each has its own backend/data), then diff the two outputs:
    cd <checkout> && <venv>/bin/python <this file> --data-root <build_data> --out <json>

meta is built the way routes/frames.py builds it for a live query: grid centred on the
preset query centre, 6 arcmin, 256 px, no marker target.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from backend.routes import _adapters  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--data-root", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--fov", type=float, default=6.0)
a = ap.parse_args()
data = Path(a.data_root)
man = json.loads((data / "manifest.json").read_text())
targets = {t["id"]: t for t in man["targets"]}
_adapters.reset_services_cache()
proc, src = _adapters._find(_adapters.PROCESSOR_LOCATIONS)
if proc is None:
    proc, src = _adapters.processor_a_adapter()
rows, total = [], 0.0
for f in man["files"]:
    if f.get("status") != "downloaded":
        continue
    raw = (data / f["file"]).read_bytes()
    t = targets[f["target_id"]]
    key = f"{f['obs_id']}_D{f['detector']}"
    meta = {
        "meta_version": 1, "observation_id": f["obs_id"], "detector": f["detector"], "frame_key": key,
        "collection_id": f["collection"], "source_url": f["archive_url"], "cutout_url": f["source_url"],
        "descriptor_mjd": None, "descriptor_observed_at_utc": None,
        "query": {"ra_deg": t["query_ra_deg"], "dec_deg": t["query_dec_deg"], "fov_arcmin": a.fov},
        "grid": {"width": 256, "height": 256, "center_ra_deg": t["query_ra_deg"], "center_dec_deg": t["query_dec_deg"],
                 "fov_arcmin": a.fov, "orientation": "north_up_east_left"},
        "marker_target": None, "wavelength_location": "Query center (RA, Dec) of this live search",
        "retrieved_at_utc": "2026-11-14T00:00:00Z", "file_sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw),
    }
    t0 = time.perf_counter()
    try:
        out = proc(raw, meta)
        err = None
    except Exception as exc:  # noqa: BLE001
        out, err = None, f"{type(exc).__name__}: {exc}"
    dt = time.perf_counter() - t0
    total += dt
    r = (out or {}).get("record") or {}
    q = r.get("quality") or {}
    rows.append({"frame_key": key, "seconds": round(dt, 4), "error": err,
                 "status": q.get("status"), "valid": q.get("valid_aperture_pixels"), "adverse": q.get("adverse_aperture_pixels"),
                 "wavelength_um": r.get("wavelength_um"), "mjd": r.get("mjd"), "observed_at_utc": r.get("observed_at_utc"),
                 "png_bytes": len(out["image_png"]) if out else None,
                 "flag_png_bytes": len(out["flag_png"]) if out and out.get("flag_png") else None})
res = {"processor": src, "n": len(rows), "total_s": round(total, 2), "mean_s": round(total / len(rows), 4),
       "max_s": max(r["seconds"] for r in rows), "errors": [r for r in rows if r["error"]], "rows": rows}
Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))
