"""Manual live check: POST /api/v1/search against the real IRSA archive (not run by pytest).

Usage (from the repo root):
    PERIGEE_DEV_MODE=1 .venv/bin/python -m backend.tests.api.live_search_check [ra dec fov limit] [--out FILE]

Default coordinate: Eps Ind A (330.8400, -56.7860), the science team's Gate-2
positive-path test position. Prints status, counts and the first descriptors.
"""

from __future__ import annotations

import json
import sys
import time

from fastapi.testclient import TestClient

from backend.main import app


def main(argv: list[str]) -> int:
    out = None
    if "--out" in argv:
        i = argv.index("--out")
        out = argv[i + 1]
        argv = argv[:i] + argv[i + 2 :]
    ra, dec, fov, limit = 330.8400, -56.7860, 6.0, 24
    if len(argv) >= 2:
        ra, dec = float(argv[0]), float(argv[1])
    if len(argv) >= 3:
        fov = float(argv[2])
    if len(argv) >= 4:
        limit = int(argv[3])
    client = TestClient(app)
    t0 = time.monotonic()
    r = client.post(
        "/api/v1/search",
        json={"schema_version": 1, "ra_deg": ra, "dec_deg": dec, "fov_arcmin": fov, "limit": limit},
    )
    elapsed = time.monotonic() - t0
    body = r.json()
    print(f"HTTP {r.status_code} in {elapsed:.2f}s")
    print(json.dumps({k: v for k, v in body.items() if k != "observations"}, indent=1))
    for o in body.get("observations", [])[:5]:
        print({k: v for k, v in o.items() if k != "frame_token"}, f"token_len={len(o['frame_token'])}")
    if out:
        with open(out, "w") as fh:
            json.dump(body, fh, indent=1)
        print(f"wrote {out}")
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
