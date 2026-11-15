"""Live regression check against a running API (worker 23). Not run by pytest.

One real IRSA search (limit 1) and one real /frame: the frame must be HTTP 200
and validate against backend.models.frame.FrameResponse (defect 1: API/processor
seam). Also checks that unknown /api paths answer JSON (never the SPA HTML), and
that X-Request-ID is echoed in catalog and API error bodies (R7).

    PERIGEE_DEV_MODE=1 .venv/bin/python -m uvicorn backend.main:app --port 8050 &
    .venv/bin/python qa/regression/live_check.py --base http://127.0.0.1:8050 [--base http://localhost:5196]

Every --base is checked for the JSON-404 behaviour; only the first does the live
search + frame, so the archive sees exactly one search and one cutout per run
(plus at most two retries on a transient 502/503).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.models.frame import FrameResponse  # noqa: E402

QUERY = {"schema_version": 1, "ra_deg": 330.84, "dec_deg": -56.786, "fov_arcmin": 6, "limit": 1}


def check(results: list, name: str, ok: bool, evidence: str) -> None:
    results.append((name, ok, evidence))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {evidence}")


def json_404(results: list, client: httpx.Client, base: str) -> None:
    for path in ("/api/v1/__qa_unknown__", "/api/__qa_unknown__", "/api/v1/cases/__qa_none__"):
        r = client.get(base + path, headers={"X-Request-ID": "qa-23-rid"})
        ctype = r.headers.get("content-type", "")
        ok = r.status_code == 404 and ctype.startswith("application/json")
        body = r.json() if ok else {}
        rid_ok = body.get("request_id") == "qa-23-rid" == r.headers.get("x-request-id")
        check(results, f"unknown path JSON 404 {base}{path}", ok and rid_ok,
              f"{r.status_code} {ctype} request_id={body.get('request_id')} header={r.headers.get('x-request-id')}")


def live_frame(results: list, client: httpx.Client, base: str) -> None:
    t = time.monotonic()
    s = client.post(base + "/api/v1/search", json=QUERY, timeout=60)
    sj = s.json()
    check(results, "live /search 330.84,-56.786", s.status_code == 200 and sj.get("status") in ("ready", "partial"),
          f"{s.status_code} status={sj.get('status')} total={sj.get('total_matches')} {time.monotonic() - t:.1f}s")
    if not sj.get("observations"):
        check(results, "live /frame", False, "no observation to fetch")
        return
    obs = sj["observations"][0]
    t = time.monotonic()
    f = client.post(base + "/api/v1/frame", json={"schema_version": 1, "frame_token": obs["frame_token"]}, timeout=90)
    elapsed = time.monotonic() - t
    if f.status_code != 200:
        check(results, "live /frame 200 + FrameResponse", False, f"{f.status_code} {f.text[:300]}")
        return
    body = f.json()
    try:
        FrameResponse.model_validate(body)
        valid, err = True, ""
    except Exception as exc:  # noqa: BLE001
        valid, err = False, repr(exc)[:300]
    fr = body["frame"]
    reg = fr["registration"]
    ok = valid and isinstance(reg.get("scale_arcsec_per_px"), (int, float)) and "scale_arcsec_per_pixel" not in reg
    check(results, "live /frame 200 + FrameResponse", ok,
          f"{fr['frame_key']} {fr['quality']['status']} lambda={fr['wavelength_um']} "
          f"{fr['provenance']['processing_version']} scale={reg.get('scale_arcsec_per_px')} {elapsed:.1f}s "
          f"{len(f.content) // 1024} KB {err}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", action="append", default=[])
    ap.add_argument("--no-live", action="store_true", help="skip the IRSA search + frame")
    a = ap.parse_args()
    bases = a.base or ["http://127.0.0.1:8050"]
    results: list = []
    with httpx.Client() as client:
        h = client.get(bases[0] + "/api/v1/health").json()
        check(results, "health names processor A", "processor-a" in str(h["capabilities"].get("frame_processor")),
              str(h["capabilities"].get("frame_processor")))
        if not a.no_live:
            live_frame(results, client, bases[0])
        for b in bases:
            json_404(results, client, b)
    failed = [r for r in results if not r[1]]
    print(json.dumps({"checks": len(results), "failed": len(failed)}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
