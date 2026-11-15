"""N6 descriptive measurements of the live routes against a mocked upstream.

    PERIGEE_DATA_ROOT=.../research/build_data .venv/bin/python qa/overnight-backend/n6_measure.py

Small samples on one laptop; descriptive only, NOT capacity guarantees. Network time is
excluded (the upstream is an in-process mock returning retained cutouts), so these are
route + processor costs. Writes qa/overnight-backend/n6_measurements.json.

* cold: fresh interpreter per run -> import of backend.main, first /frame, peak RSS
* warm: same process, repeated /frame and /search; per-call wall time
* processor peak Python allocation (tracemalloc) for one frame
* concurrency: 4 distinct frames sequential vs simultaneous through the ASGI app
* response sizes vs the 4 MB response cap and 2 MB PNG cap
"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
OUT = Path(__file__).resolve().parent

COLD_CHILD = r"""
import json, resource, sys, time
t0 = time.perf_counter()
sys.path.insert(0, sys.argv[1])
from fastapi.testclient import TestClient
from backend.main import app
from backend.routes._adapters import resolve_services
from backend.tests.api import test_route_parity as rp
from backend.tests.api.conftest import Harness
t_import = time.perf_counter() - t0
h = Harness(); app.dependency_overrides[resolve_services] = h.services
client = TestClient(app, raise_server_exceptions=False)
archive, rows, raws, (ra, dec) = rp.retained("epsilon_indi_b", {"2026W18_1A_0516_1_D3"})
rp.use_real_route(h, archive)
s = rp.search(client, ra, dec, 6.0)
t1 = time.perf_counter()
rec = rp.frame(client, s["observations"][0]["frame_token"])
t_first = time.perf_counter() - t1
t2 = time.perf_counter()
rec = rp.frame(client, s["observations"][0]["frame_token"])
t_second = time.perf_counter() - t2
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(json.dumps({"import_s": t_import, "first_frame_s": t_first, "second_frame_s": t_second,
                  "peak_rss_mb": rss / (1024 * 1024 if sys.platform == "darwin" else 1024)}))
"""


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def summary(xs):
    return {"n": len(xs), "min_ms": round(min(xs) * 1e3, 1), "p50_ms": round(pct(xs, 50) * 1e3, 1),
            "p90_ms": round(pct(xs, 90) * 1e3, 1), "max_ms": round(max(xs) * 1e3, 1),
            "mean_ms": round(statistics.mean(xs) * 1e3, 1)}


def main() -> None:
    if not os.environ.get("PERIGEE_DATA_ROOT"):
        raise SystemExit("set PERIGEE_DATA_ROOT to research/build_data")
    results: dict = {"note": "descriptive small-sample timings on one machine; mocked upstream (no network); not capacity guarantees"}
    versions = {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system()}
    for pkg in ("fastapi", "starlette", "pydantic", "httpx", "anyio", "numpy", "astropy", "pillow"):
        versions[pkg] = metadata.version(pkg)
    results["versions"] = versions

    cold = []
    for _ in range(3):
        r = subprocess.run([sys.executable, "-c", COLD_CHILD, str(REPO)], capture_output=True, text=True, cwd=REPO)
        if r.returncode != 0:
            raise SystemExit(r.stderr[-2000:])
        cold.append(json.loads(r.stdout.strip().splitlines()[-1]))
    results["cold"] = {
        "runs": [{k: round(v, 3) for k, v in c.items()} for c in cold],
        "basis": "fresh interpreter: import backend.main + first /frame (real processor A, retained Eps Ind B D3 cutout)",
    }

    from fastapi.testclient import TestClient

    from backend.data import process as proc
    from backend.main import app
    from backend.routes._adapters import resolve_services
    from backend.tests.api import test_route_parity as rp
    from backend.tests.api.conftest import Harness

    h = Harness()
    app.dependency_overrides[resolve_services] = h.services
    client = TestClient(app, raise_server_exceptions=False)

    warm = {}
    sizes = {}
    for cid, preset, key, _why, _st in rp.PARITY_CASES:
        archive, _rows, raws, (ra, dec) = rp.retained(preset, {key})
        rp.use_real_route(h, archive)
        s = rp.search(client, ra, dec, 6.0)
        tok = s["observations"][0]["frame_token"]
        rp.frame(client, tok)  # warm-up
        times = []
        for _ in range(10):
            t0 = time.perf_counter()
            r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
            times.append(time.perf_counter() - t0)
            assert r.status_code == 200
        warm[cid] = summary(times)
        rec = r.json()["frame"]
        sizes[cid] = {
            "response_bytes": len(r.content),
            "image_png_bytes": len(rp.base64.b64decode(rec["image"]["src"].split(",", 1)[1])),
            "flag_png_bytes": len(rp.base64.b64decode(rec["flag_image"]["src"].split(",", 1)[1])) if rec["flag_image"] else None,
            "raw_fits_bytes": len(raws[key]),
            "server_timing": r.headers.get("server-timing"),
        }
    results["warm_frame"] = warm
    results["sizes"] = sizes
    results["caps"] = {"MAX_RESPONSE_BYTES": 4_000_000, "MAX_PNG_BYTES": 2 * 1024 * 1024,
                       "PERIGEE_FRAME_MAX_BYTES_default": 24 * 1024 * 1024}

    # Processor-only Python peak allocation for one frame.
    key = "2026W18_1A_0516_1_D3"
    _a, _r, raws, (ra, dec) = rp.retained("epsilon_indi_b", {key})
    tracemalloc.start()
    t0 = time.perf_counter()
    proc.process_frame(raws[key], proc.FrameInput(query_ra_deg=ra, query_dec_deg=dec, fov_arcmin=10.0))
    t_proc = time.perf_counter() - t0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    results["processor_peak_python_alloc_mb_fov10"] = round(peak / 2**20, 2)
    results["processor_wall_ms_fov10_traced"] = round(t_proc * 1e3, 1)

    # Search over the full real cached SIA responses for Eps Ind B (DR1 + QR3 files).
    meta = Path(os.environ["PERIGEE_DATA_ROOT"]) / "metadata"
    vot = {c: (meta / f"epsilon_indi_b_{c}.xml").read_bytes() for c in ("spherex_dr1", "spherex_qr3")}
    rp.use_real_route(h, rp.ArchiveDouble(vot, {}))
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        r = client.post("/api/v1/search", json={"schema_version": 1, "ra_deg": ra, "dec_deg": dec, "limit": 48})
        times.append(time.perf_counter() - t0)
    body = r.json()
    results["warm_search_full_cached_sia"] = {**summary(times), "total_matches": body["total_matches"],
                                              "returned": body["returned_count"], "response_bytes": len(r.content),
                                              "sia_bytes": {c: len(v) for c, v in vot.items()}}

    # Concurrency: four distinct frames, sequential vs simultaneous.
    import httpx

    keys = ["2026W18_1A_0516_1_D3", "2026W18_1A_0516_1_D6", "2026W39_2A_0597_4_D3", "2026W17_1B_0162_4_D1"]
    archive, _rows, raws, (ra, dec) = rp.retained("epsilon_indi_b", set(keys))
    rp.use_real_route(h, archive)
    s = rp.search(client, ra, dec, 6.0)
    toks = [o["frame_token"] for o in s["observations"]]

    async def run(parallel):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=60) as c:
            async def one(t):
                r = await c.post("/api/v1/frame", json={"schema_version": 1, "frame_token": t})
                assert r.status_code == 200
            t0 = time.perf_counter()
            if parallel:
                await asyncio.gather(*(one(t) for t in toks))
            else:
                for t in toks:
                    await one(t)
            return time.perf_counter() - t0

    asyncio.run(run(False))  # warm
    seq = [asyncio.run(run(False)) for _ in range(5)]
    par = [asyncio.run(run(True)) for _ in range(5)]

    async def limiter_tokens():
        import anyio.to_thread

        return anyio.to_thread.current_default_thread_limiter().total_tokens

    results["concurrency_4_distinct_frames"] = {
        "sequential": summary(seq), "simultaneous": summary(par),
        "anyio_default_thread_limiter_tokens": asyncio.run(limiter_tokens()),
        "note": "No Perigee-configured concurrency limit exists; processor calls run in anyio's default "
                "thread pool (limiter above) per process. Vercel scales by instances.",
    }
    (OUT / "n6_measurements.json").write_text(json.dumps(results, indent=1) + "\n")
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
