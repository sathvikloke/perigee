"""Exercise a running Perigee API over HTTP and write a JSON summary.

Usage: .venv/bin/python coordination/processor-compare/exercise_api.py http://127.0.0.1:8030 out.json
Live: makes one /search and three /frame calls against IRSA through the API.
"""
import json
import sys
import time

import httpx

base, out_path = sys.argv[1], sys.argv[2]
out = {}
c = httpx.Client(base_url=base, timeout=120)
r = c.get("/api/v1/health")
out["health"] = {"http": r.status_code, "body": r.json()}
r = c.get("/api/v1/presets")
b = r.json()
out["presets"] = {
    "http": r.status_code,
    "count": b.get("count"),
    "presets": [{k: p.get(k) for k in ("preset_id", "frames_available", "frame_count", "cases")} for p in b.get("presets", [])],
}


def frames(path):
    r = c.get(path)
    b = r.json()
    res = {"path": path, "http": r.status_code, "status": b.get("status"), "frames_available": b.get("frames_available"),
           "frame_count": b.get("frame_count"), "sets": b.get("sets"), "reason": b.get("reason"),
           "n_warnings": len(b.get("warnings") or []), "warnings_head": (b.get("warnings") or [])[:2]}
    ok = bad = none = 0
    for f in b.get("frames") or []:
        for fld in ("image", "flag_image"):
            im = f.get(fld)
            if not im:
                none += 1
                continue
            rr = c.get(im["src"])
            if rr.status_code == 200 and rr.headers.get("content-type") == "image/png":
                ok += 1
            else:
                bad += 1
    res.update(asset_urls_ok=ok, asset_urls_bad=bad, image_fields_missing=none,
               frame_keys=[f.get("frame_key") for f in b.get("frames") or []][:6])
    return res


out["eps_default"] = frames("/api/v1/presets/epsilon_indi_b/frames")
out["eps_fair_comparison"] = frames("/api/v1/presets/epsilon_indi_b/frames?case_id=fair_comparison")
out["barnard_moving_neighbor"] = frames("/api/v1/presets/barnards_star/frames?case_id=moving_neighbor")

t0 = time.monotonic()
r = c.post("/api/v1/search", json={"schema_version": 1, "ra_deg": 330.84, "dec_deg": -56.786, "fov_arcmin": 6.0, "limit": 24})
b = r.json()
out["search"] = {"http": r.status_code, "elapsed_s": round(time.monotonic() - t0, 2),
                 "n_obs": len(b.get("observations") or []),
                 "summary": {k: v for k, v in b.items() if k != "observations"}}
out["frames"] = []
for o in (b.get("observations") or [])[:3]:
    attempts = 0
    while True:  # IRSA intermittently answers 503; retry upstream errors up to 3 times
        attempts += 1
        t0 = time.monotonic()
        r = c.post("/api/v1/frame", json={"schema_version": 1, "frame_token": o["frame_token"]})
        el = time.monotonic() - t0
        if r.status_code != 502 or attempts >= 4:
            break
        time.sleep(3)
    fb = r.json()
    f = fb.get("frame") or {}
    out["frames"].append({
        "http": r.status_code, "attempts": attempts, "elapsed_s": round(el, 2), "frame_key": f.get("frame_key"), "error": fb.get("error"),
        "quality": (f.get("quality") or {}).get("status"), "wavelength_um": f.get("wavelength_um"),
        "fov_arcmin": (f.get("registration") or {}).get("fov_arcmin"),
        "image_src_prefix": ((f.get("image") or {}).get("src") or "")[:22],
        "image_src_len": len((f.get("image") or {}).get("src") or ""),
        "flag_src_len": len((f.get("flag_image") or {}).get("src") or ""),
        "flag_legend": (f.get("flag_image") or {}).get("legend"),
        "processing_version": (f.get("provenance") or {}).get("processing_version"),
        "record_keys": sorted(f.keys()),
    })
with open(out_path, "w") as fh:
    json.dump(out, fh, indent=1)
print(json.dumps(out, indent=1)[:7000])
