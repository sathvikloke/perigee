"""Manual live check of the /frame FETCH path (not run by pytest).

search (real IRSA) -> pick one descriptor -> POST /api/v1/frame with its real token
-> the API fetches the real allowlisted IRSA cutout -> a FETCH PROBE stands in for
the processor. The probe only lists the FITS HDUs it received (via astropy) and
returns a fixture-labeled record with a placeholder PNG. It is NOT image processing
and its image is NOT sky data. When backend/data.process_frame exists, run with
``--real-processor`` to use it instead.

Usage (repo root):
    PERIGEE_DEV_MODE=1 .venv/bin/python -m backend.tests.api.live_frame_check [--index N] [--real-processor]
"""

from __future__ import annotations

import io
import json
import sys
import time
from dataclasses import replace

from fastapi.testclient import TestClient

from backend.main import app
from backend.routes._adapters import resolve_services

from .fixtures import fixture_processor

PROBE_REPORT: dict = {}


def fetch_probe(fits_bytes: bytes, meta: dict) -> dict:
    from astropy.io import fits  # inspection only

    with fits.open(io.BytesIO(fits_bytes)) as hdul:
        PROBE_REPORT["hdus"] = [
            {"name": h.name, "shape": list(h.data.shape) if getattr(h, "data", None) is not None and hasattr(h.data, "shape") else None}
            for h in hdul
        ]
        hdr = hdul["IMAGE"].header if "IMAGE" in hdul else hdul[0].header
        PROBE_REPORT["header"] = {k: hdr.get(k) for k in ("DETECTOR", "DATE-AVG", "MJD-AVG", "OBSID", "CTYPE1", "CTYPE2")}
    PROBE_REPORT["bytes"] = len(fits_bytes)
    PROBE_REPORT["sha256"] = meta["file_sha256"]
    PROBE_REPORT["cutout_url"] = meta["cutout_url"]
    out = fixture_processor(fits_bytes, meta)
    out["record"]["limitations"].append("FETCH PROBE: real archive bytes were fetched; no image processing was done.")
    return out


def main(argv: list[str]) -> int:
    index = int(argv[argv.index("--index") + 1]) if "--index" in argv else 0
    real = "--real-processor" in argv
    services = resolve_services()
    if not real:
        services = replace(services, processor=fetch_probe, processor_source="live_frame_check.fetch_probe")
    app.dependency_overrides[resolve_services] = lambda: services
    client = TestClient(app)
    s = client.post(
        "/api/v1/search",
        json={"schema_version": 1, "ra_deg": 330.84, "dec_deg": -56.786, "fov_arcmin": 6, "limit": 24},
    )
    print("search HTTP", s.status_code, s.json().get("status"), s.json().get("total_matches"))
    if s.status_code != 200 or not s.json()["observations"]:
        print(json.dumps(s.json(), indent=1))
        return 1
    obs = s.json()["observations"][index]
    print("frame for", obs["frame_key"], obs["collection_id"], obs["source_url"])
    t0 = time.monotonic()
    f = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": obs["frame_token"]})
    print(f"frame HTTP {f.status_code} in {time.monotonic() - t0:.2f}s")
    body = f.json()
    if f.status_code == 200:
        fr = body["frame"]
        fr["image"]["src"] = fr["image"]["src"][:48] + "..."
        print(json.dumps({k: fr[k] for k in ("frame_key", "detector", "observed_at_utc", "mjd", "provenance")}, indent=1))
        print("timing_ms", body.get("timing_ms"))
    else:
        print(json.dumps(body, indent=1))
    if PROBE_REPORT:
        print("FETCH PROBE (real bytes):", json.dumps(PROBE_REPORT, indent=1, default=str))
    return 0 if f.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
