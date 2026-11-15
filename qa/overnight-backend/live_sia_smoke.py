"""The single bounded live archive smoke for N5 (run by hand, never by pytest).

    PERIGEE_DEV_MODE=1 .venv/bin/python qa/overnight-backend/live_sia_smoke.py

One POST /api/v1/search through the local candidate app (real IRSA adapter, real network),
DR1 only, at the Eps Ind B preset centre: one SIA request (the adapter retries a fast
transient 5xx a bounded number of times). No cutout is fetched and the public
Perigee origin is not used. Prints the outcome and whether the retained frames of
that position appear in the live answer.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

RA, DEC = 331.0966687831005, -56.80064917516836
EXPECT = {"2026W18_1A_0516_1_D3", "2026W18_1A_0516_1_D6"}


def main() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    t0 = time.monotonic()
    r = client.post("/api/v1/search", json={"schema_version": 1, "ra_deg": RA, "dec_deg": DEC, "fov_arcmin": 6.0,
                                            "limit": 48, "collection_ids": ["spherex_dr1"]},
                    headers={"X-Request-ID": "n5-live-smoke"})
    elapsed = time.monotonic() - t0
    body = r.json()
    out = {"started_utc": started, "http_status": r.status_code, "elapsed_s": round(elapsed, 2),
           "server_timing": r.headers.get("server-timing")}
    if r.status_code == 200:
        keys = {o["frame_key"] for o in body["observations"]}
        out.update({k: body[k] for k in ("status", "returned_count", "total_matches", "truncated", "selection",
                                          "collections_failed", "collections_capped")})
        out["search_radius_deg"] = body["query"]["search_radius_deg"]
        out["retained_frames_in_returned_sample"] = sorted(EXPECT & keys)
        out["first"] = body["observations"][0]["frame_key"] if body["observations"] else None
        out["last"] = body["observations"][-1]["frame_key"] if body["observations"] else None
    else:
        out["error"] = body.get("error")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
