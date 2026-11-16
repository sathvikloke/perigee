"""N6: local resilience of the live routes against a mocked upstream.

Unlike test_search.py / test_frame.py (which script the archive adapter's *result*),
these run the real IRSA SIA adapter and the real bounded fetch against an
``httpx.MockTransport`` that misbehaves at the HTTP level: slow, dripping, oversized,
malformed or failing, per collection. They check that the configured time and byte
limits are actually enforced (wall clock, bytes pulled), that partial stays partial
and unavailable never becomes a false empty, that repeated and simultaneous
requests stay independent, and that error envelopes keep their status, code,
retryability and request ID. Never touches the network.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from backend.main import app
from backend.routes import _adapters
from backend.routes._archive import SEARCH_RADIUS_DEG, SIA_MAX_ATTEMPTS, SIA_MAX_BYTES, SIA_MAXREC
from backend.models.search import LIMIT_MAX
from backend.routes.search import select_evenly

from . import test_route_parity as rp
from .test_frame import make_token
from .test_route_parity import SYN_KEY, SYN_URL, ArchiveDouble, png_sha, synthetic_votable, use_real_route

syn = rp.syn
DATA_ROOT = os.environ.get("PERIGEE_DATA_ROOT")
SIA_PATH = "/SIA"


def syn_token(ra=None, dec=None, fov=6.0, **over):
    c_ra, c_dec = syn.CENTER
    return make_token(
        ra_deg=c_ra if ra is None else ra, dec_deg=c_dec if dec is None else dec, fov_arcmin=fov,
        observation_id="2099W01_1A_0001_1", detector=3, frame_key=SYN_KEY, source_url=SYN_URL, mjd=61000.4993, **over,
    )


def post_frame(client, token, rid="n6-frame"):
    return client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": token}, headers={"X-Request-ID": rid})


def post_search(client, rid="n6-search", **over):
    ra, dec = syn.CENTER
    body = {"schema_version": 1, "ra_deg": ra, "dec_deg": dec, "fov_arcmin": 6.0, "limit": 24, **over}
    return client.post("/api/v1/search", json=body, headers={"X-Request-ID": rid})


def envelope(resp, status, code, rid, retryable=None):
    """The documented error contract: status, JSON envelope, code, request id echo, no-store."""
    assert resp.status_code == status, resp.text[:600]
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.headers["cache-control"] == "no-store"
    body = resp.json()
    assert body["schema_version"] == 1 and body["error"]["code"] == code
    assert body["request_id"] == resp.headers["x-request-id"] == rid
    if retryable is not None:
        assert body["error"]["retryable"] is retryable
    return body


class Upstream:
    """Per-path behaviour for the mocked IRSA: SIA per collection, cutouts by path."""

    def __init__(self, sia=None, data=None):
        self.sia = sia or {}
        self.data = data
        self.sia_calls: dict[str, int] = {}
        self.data_calls = 0
        self.in_flight = 0
        self.max_in_flight = 0

    async def __call__(self, request: httpx.Request):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if request.url.path == SIA_PATH:
                col = request.url.params["COLLECTION"]
                self.sia_calls[col] = self.sia_calls.get(col, 0) + 1
                behaviour = self.sia.get(col, rp.EMPTY_VOTABLE)
            else:
                self.data_calls += 1
                behaviour = self.data
            if callable(behaviour):
                behaviour = behaviour(request)
                if asyncio.iscoroutine(behaviour):
                    behaviour = await behaviour
            if isinstance(behaviour, bytes):
                ctype = "text/xml" if request.url.path == SIA_PATH else "application/fits"
                return httpx.Response(200, content=behaviour, headers={"content-type": ctype})
            return behaviour
        finally:
            self.in_flight -= 1


def install(harness, up: Upstream, **settings):
    use_real_route(harness, ArchiveDouble({}, {}))
    harness.fetch_handler = up
    harness.settings = replace(harness.settings, **settings)


async def never(_request):
    await asyncio.sleep(60)
    raise AssertionError("deadline was not enforced")


class Counter:
    """Async byte stream that records how much of it the client actually pulled."""

    def __init__(self, chunk: bytes, count: int, delay: float = 0.0, head: bytes = b""):
        self.chunk, self.count, self.delay, self.head = chunk, count, delay, head
        self.pulled = 0

    async def __aiter__(self):
        if self.head:
            self.pulled += len(self.head)
            yield self.head
        for _ in range(self.count):
            if self.delay:
                await asyncio.sleep(self.delay)
            self.pulled += len(self.chunk)
            yield self.chunk


# --------------------------------------------------------------------------- normal path (control)


def test_normal_frame_and_search_through_real_adapters(client, harness):
    raw = syn.make_fits()
    up = Upstream(sia={"spherex_dr1": synthetic_votable()}, data=raw)
    install(harness, up)
    r = post_search(client)
    assert r.status_code == 200 and r.json()["status"] == "ready" and r.json()["returned_count"] == 1
    tok = r.json()["observations"][0]["frame_token"]
    f = post_frame(client, tok)
    assert f.status_code == 200 and f.json()["frame"]["quality"]["status"] == "clear"
    assert up.sia_calls == {"spherex_dr1": 1, "spherex_qr3": 1} and up.data_calls == 1


# --------------------------------------------------------------------------- time limits


def test_frame_upstream_that_never_answers_hits_the_fetch_deadline(client, harness):
    install(harness, Upstream(data=never), frame_budget_s=2.0)
    t0 = time.monotonic()
    body = envelope(post_frame(client, syn_token(), rid="n6-t1"), 504, "UPSTREAM_TIMEOUT", "n6-t1", retryable=True)
    elapsed = time.monotonic() - t0
    assert body["error"]["details"] == {"stage": "fetch", "reason": "deadline"}
    assert elapsed < 2.0 * 0.6 + 1.0, elapsed  # fetch share of the frame budget, plus slack


def test_frame_dripping_body_is_cut_by_the_overall_deadline(client, harness):
    """Each chunk arrives well inside the read timeout; only the overall deadline stops it."""
    drip = Counter(b"x" * 1024, count=200, delay=0.1, head=b"SIMPLE  =")
    install(harness, Upstream(data=lambda req: httpx.Response(200, content=drip)), frame_budget_s=2.0,
            upstream_read_timeout_s=5.0)
    t0 = time.monotonic()
    envelope(post_frame(client, syn_token(), rid="n6-t2"), 504, "UPSTREAM_TIMEOUT", "n6-t2", retryable=True)
    assert time.monotonic() - t0 < 2.0 * 0.6 + 1.0
    assert drip.pulled < 200 * 1024  # stopped mid-stream


def test_processor_over_budget_is_a_bounded_processing_failure(client, harness):
    install(harness, Upstream(data=syn.make_fits()), frame_budget_s=1.5)

    def slow(data, meta):
        time.sleep(3.0)
        return {}

    harness.processor = slow
    t0 = time.monotonic()
    body = envelope(post_frame(client, syn_token(), rid="n6-t3"), 500, "PROCESSING_FAILED", "n6-t3", retryable=True)
    assert body["error"]["details"] == {"stage": "process", "reason": "budget"}
    assert time.monotonic() - t0 < 1.5 + 1.0


def test_search_archive_that_never_answers_is_a_timeout_not_empty(client, harness):
    install(harness, Upstream(sia={"spherex_dr1": never, "spherex_qr3": never}), search_budget_s=1.5)
    t0 = time.monotonic()
    body = envelope(post_search(client, rid="n6-t4"), 504, "UPSTREAM_TIMEOUT", "n6-t4", retryable=True)
    assert time.monotonic() - t0 < 1.5 + 1.0
    assert body["error"]["details"]["collections_failed"] == ["spherex_dr1", "spherex_qr3"]
    assert body["error"]["details"]["reasons"] == {"spherex_dr1": "deadline", "spherex_qr3": "deadline"}


def test_search_one_collection_slow_is_partial(client, harness):
    install(harness, Upstream(sia={"spherex_dr1": synthetic_votable(), "spherex_qr3": never}), search_budget_s=1.5)
    r = post_search(client)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "partial" and d["collections_failed"] == ["spherex_qr3"]
    assert d["total_matches"] is None and d["returned_count"] == 1


# --------------------------------------------------------------------------- byte limits


def test_frame_declared_oversize_is_refused_before_reading(client, harness):
    body = Counter(b"x" * 4096, count=100, head=b"SIMPLE  =")
    install(harness, Upstream(data=lambda req: httpx.Response(200, content=body, headers={"content-length": str(10**9)})),
            frame_fetch_max_bytes=64 * 1024)
    d = envelope(post_frame(client, syn_token(), rid="n6-b1"), 502, "UNSUPPORTED_DATA", "n6-b1")
    assert d["error"]["details"]["reason"] == "content_length_cap"
    assert body.pulled <= 4096 + 9  # at most the first buffered chunk


def test_frame_undeclared_oversize_stops_at_the_cap(client, harness):
    body = Counter(b"x" * 4096, count=10_000, head=b"SIMPLE  =")  # ~40 MB if read fully
    install(harness, Upstream(data=lambda req: httpx.Response(200, content=body)), frame_fetch_max_bytes=64 * 1024)
    d = envelope(post_frame(client, syn_token(), rid="n6-b2"), 502, "UNSUPPORTED_DATA", "n6-b2")
    assert d["error"]["details"] == {"stage": "fetch", "reason": "stream_cap", "max_bytes": 64 * 1024}
    assert body.pulled <= 64 * 1024 + 4096 + 9  # never more than cap + one chunk in memory


def test_search_oversized_votable_fails_that_collection_only(client, harness):
    huge = Counter(b"<!-- padding -->" * 4096, count=SIA_MAX_BYTES // (16 * 4096) + 50, head=b'<?xml version="1.0"?>')
    install(harness, Upstream(sia={"spherex_dr1": synthetic_votable(),
                                   "spherex_qr3": lambda req: httpx.Response(200, content=huge,
                                                                            headers={"content-type": "text/xml"})}))
    r = post_search(client)
    assert r.status_code == 200 and r.json()["status"] == "partial"
    assert r.json()["collections_failed"] == ["spherex_qr3"]
    assert huge.pulled <= SIA_MAX_BYTES + 16 * 4096 + 64


# --------------------------------------------------------------------------- malformed and failing upstreams


@pytest.mark.parametrize(
    "bad,reason",
    [
        (b"<VOTABLE><RESOURCE type='results'><TABLE>", "votable_parse"),  # cut-off XML
        (b'<?xml version="1.0"?><html><body>maintenance</body></html>', "not_votable"),
        (b"<!DOCTYPE html><html><body>Proxy Error</body></html>", "html_body"),
        (b'<VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE type="results">'
         b'<INFO name="QUERY_STATUS" value="ERROR">bad</INFO></RESOURCE></VOTABLE>', "query_status_error"),
    ],
    ids=["truncated_xml", "not_votable", "html_200", "query_status_error"],
)
def test_malformed_archive_answers_never_become_empty(client, harness, bad, reason):
    # Both collections malformed: an error envelope, never "empty".
    install(harness, Upstream(sia={"spherex_dr1": bad, "spherex_qr3": bad}), search_budget_s=3.0)
    d = envelope(post_search(client, rid="n6-m1"), 502, "UPSTREAM_UNAVAILABLE", "n6-m1", retryable=True)
    assert d["error"]["details"]["reasons"] == {"spherex_dr1": reason, "spherex_qr3": reason}
    # One malformed, one good with a match: partial, total unknown.
    install(harness, Upstream(sia={"spherex_dr1": synthetic_votable(), "spherex_qr3": bad}), search_budget_s=3.0)
    r = post_search(client)
    assert r.status_code == 200 and r.json()["status"] == "partial" and r.json()["total_matches"] is None
    # One malformed, one good but empty: still an error, not a false empty.
    install(harness, Upstream(sia={"spherex_dr1": rp.EMPTY_VOTABLE, "spherex_qr3": bad}), search_budget_s=3.0)
    d = envelope(post_search(client, rid="n6-m2"), 502, "UPSTREAM_UNAVAILABLE", "n6-m2")
    assert d["error"]["details"]["collections_succeeded_empty"] == ["spherex_dr1"]


def test_persistent_archive_5xx_is_retried_a_bounded_number_of_times(client, harness):
    up = Upstream(sia={"spherex_dr1": synthetic_votable(),
                       "spherex_qr3": lambda req: httpx.Response(503, text="busy")})
    install(harness, up, search_budget_s=10.0)
    r = post_search(client)
    assert r.status_code == 200 and r.json()["status"] == "partial"
    assert up.sia_calls["spherex_dr1"] == 1
    assert 2 <= up.sia_calls["spherex_qr3"] <= SIA_MAX_ATTEMPTS


def test_archive_overflow_with_no_rows_is_partial_not_empty(client, harness):
    overflow = (b'<VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE type="results">'
                b'<INFO name="QUERY_STATUS" value="OVERFLOW"/><TABLE><FIELD name="obs_id"/>'
                b"<DATA><TABLEDATA/></DATA></TABLE></RESOURCE></VOTABLE>")
    install(harness, Upstream(sia={"spherex_dr1": overflow}))
    d = post_search(client).json()
    assert d["status"] == "partial" and d["collections_capped"] == ["spherex_dr1"] and d["total_matches"] is None


@pytest.mark.parametrize(
    "response,status,code,reason",
    [
        (lambda req: httpx.Response(200, text="<!doctype html><p>err</p>", headers={"content-type": "text/html"}),
         502, "UPSTREAM_UNAVAILABLE", "html_body"),
        (lambda req: httpx.Response(200, json={"error": "x"}), 502, "UNSUPPORTED_DATA", "not_fits"),
        (lambda req: httpx.Response(200, content=b"SIMPLE  =" + b"\x00" * 3000), 422, "UNSUPPORTED_DATA", None),
        (lambda req: httpx.Response(200, content=syn.make_fits()[: 3 * 2880 + 1440]), 422, "UNSUPPORTED_DATA", None),
        (lambda req: httpx.Response(429, text="slow down"), 502, "UPSTREAM_UNAVAILABLE", "upstream_rate_limited"),
        (lambda req: httpx.Response(404, text="gone"), 502, "UPSTREAM_UNAVAILABLE", "upstream_404"),
    ],
    ids=["html_200", "json_not_fits", "fits_magic_garbage", "truncated_fits", "rate_limited", "not_found"],
)
def test_bad_cutouts_keep_their_documented_status(client, harness, response, status, code, reason):
    install(harness, Upstream(data=response))
    d = envelope(post_frame(client, syn_token(), rid="n6-c"), status, code, "n6-c")
    if reason:
        assert d["error"]["details"]["reason"] == reason
    assert "Traceback" not in json.dumps(d) and "/Users" not in json.dumps(d)


# --------------------------------------------------------------------------- tokens and request ids


def test_token_and_validation_errors_keep_status_payload_and_request_id(client, harness):
    install(harness, Upstream(data=syn.make_fits()))
    good = syn_token()
    prefix, payload, sig = good.split(".")
    cases = [
        (syn_token(ttl=60, now=time.time() - 3600), 400, "TOKEN_EXPIRED", False),
        (f"{prefix}.{payload}.{sig[:-2]}AA", 400, "INVALID_FRAME_TOKEN", False),
        (make_token(secret=b"another-secret-of-sufficient-length-0123456789"), 400, "INVALID_FRAME_TOKEN", False),
        ("not-a-token", 400, "INVALID_FRAME_TOKEN", False),
    ]
    for i, (tok, status, code, retryable) in enumerate(cases):
        rid = f"n6-tok-{i}"
        d = envelope(post_frame(client, tok, rid=rid), status, code, rid, retryable=retryable)
        if code == "TOKEN_EXPIRED":
            assert d["error"]["details"]["action"] == "refresh_search"
    harness_calls = harness.fetch_handler.data_calls
    assert harness_calls == 0  # no upstream access for any rejected token
    # A client request id that is not plain is replaced, never echoed.
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": "x"}, headers={"X-Request-ID": "bad id\n"})
    assert r.json()["request_id"] == r.headers["x-request-id"] != "bad id\n"
    # Validation errors on both routes carry the request id too.
    envelope(client.post("/api/v1/frame", json={"schema_version": 1}, headers={"X-Request-ID": "n6-v1"}),
             400, "INVALID_FRAME_TOKEN", "n6-v1")  # missing token field
    envelope(post_search(client, rid="n6-v2", fov_arcmin=11.0), 422, "INVALID_FIELD_OF_VIEW", "n6-v2")


# --------------------------------------------------------------------------- repetition and concurrency


def test_repeated_identical_request_refetches_and_is_identical(client, harness):
    up = Upstream(data=syn.make_fits(sources=((20.0, 30.0, 5.0),)))
    install(harness, up)
    tok = syn_token()
    a = post_frame(client, tok, rid="n6-r1").json()["frame"]
    b = post_frame(client, tok, rid="n6-r2").json()["frame"]
    assert up.data_calls == 2  # no backend frame cache
    for rec in (a, b):
        rec["provenance"].pop("retrieved_at")
    assert a == b
    assert png_sha(a["image"]["src"]) == png_sha(b["image"]["src"])


def test_simultaneous_distinct_requests_do_not_cross_talk(harness):
    """Four distinct frames in flight at once through the ASGI app: each answer follows
    its own token, and equals the same request made alone."""
    raws = {3: syn.make_fits(sources=((20.0, 35.0, 8.0),)), 6: syn.make_fits(detector=6, sources=((40.0, 22.0, 4.0),))}

    async def cutout(req):
        await asyncio.sleep(0.05)  # keep requests overlapping
        det = 6 if "D6_spx" in req.url.path else 3
        return httpx.Response(200, content=raws[det], headers={"content-type": "application/fits"})

    up = Upstream(data=cutout)
    install(harness, up)
    ra, dec = syn.CENTER

    def tok(det, fov):
        url = SYN_URL.replace("/3/", f"/{det}/").replace("D3_spx", f"D{det}_spx")
        return make_token(ra_deg=ra, dec_deg=dec, fov_arcmin=fov, observation_id="2099W01_1A_0001_1", detector=det,
                          frame_key=f"2099W01_1A_0001_1_D{det}", source_url=url)

    jobs = [(3, 2.0), (3, 10.0), (6, 2.0), (6, 10.0)]

    async def run(parallel: bool):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            async def one(i, det, fov):
                r = await c.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok(det, fov)},
                                 headers={"X-Request-ID": f"n6-p{i}"})
                assert r.status_code == 200, r.text[:300]
                assert r.json()["request_id"] == f"n6-p{i}"
                return r.json()["frame"]
            if parallel:
                return await asyncio.gather(*(one(i, d, f) for i, (d, f) in enumerate(jobs)))
            return [await one(i, d, f) for i, (d, f) in enumerate(jobs)]

    alone = asyncio.run(run(parallel=False))
    up.max_in_flight = 0
    together = asyncio.run(run(parallel=True))
    assert up.max_in_flight >= 2, "requests did not overlap"
    for (det, fov), a, b in zip(jobs, alone, together):
        assert b["detector"] == det and b["registration"]["fov_arcmin"] == fov
        assert b["registration"]["grid_id"] == a["registration"]["grid_id"]
        assert png_sha(b["image"]["src"]) == png_sha(a["image"]["src"])
    assert len({png_sha(f["image"]["src"]) for f in together}) == 4


# --------------------------------------------------------------------------- configured limits


def test_default_archive_timeouts_allow_slow_valid_sia_responses(monkeypatch):
    # Real DR1/QR3 searches returned valid VOTables after 21.3/21.0 seconds.
    # The old 20-second transport timeout discarded both before parsing.
    for name in ("PERIGEE_UPSTREAM_READ_TIMEOUT_S", "PERIGEE_SEARCH_BUDGET_S"):
        monkeypatch.delenv(name, raising=False)
    _adapters.reset_services_cache()
    try:
        services = _adapters.resolve_services()
        client = services.http_client_factory()
        assert client.timeout.read == 40.0
        assert client.timeout.read < services.settings.search_budget_s == 50.0
        # Leave room for parsing/serialization inside the hosted function limit.
        assert services.settings.search_budget_s < 60.0
        asyncio.run(client.aclose())
    finally:
        _adapters.reset_services_cache()


def test_limits_come_from_the_environment_and_reach_the_client(monkeypatch):
    monkeypatch.setenv("PERIGEE_FRAME_MAX_BYTES", "12345")
    monkeypatch.setenv("PERIGEE_FRAME_BUDGET_S", "7.5")
    monkeypatch.setenv("PERIGEE_SEARCH_BUDGET_S", "3.25")
    monkeypatch.setenv("PERIGEE_UPSTREAM_CONNECT_TIMEOUT_S", "1.5")
    monkeypatch.setenv("PERIGEE_UPSTREAM_READ_TIMEOUT_S", "2.5")
    _adapters.reset_services_cache()
    try:
        s = _adapters.resolve_services()
        assert (s.settings.frame_fetch_max_bytes, s.settings.frame_budget_s, s.settings.search_budget_s) == (12345, 7.5, 3.25)
        client = s.http_client_factory()
        assert client.timeout.connect == 1.5 and client.timeout.read == 2.5
        assert client.follow_redirects is False  # each hop is re-checked by bounded_get instead
        asyncio.run(client.aclose())
    finally:
        _adapters.reset_services_cache()
    # Unparseable values fall back to the documented defaults rather than disabling a limit.
    monkeypatch.setenv("PERIGEE_FRAME_MAX_BYTES", "lots")
    from backend.security.config import load_settings

    assert load_settings().frame_fetch_max_bytes == 24 * 1024 * 1024


# --------------------------------------------------------------------------- search radius and the 48 cap (real cached SIA)

needs_data = pytest.mark.skipif(
    not DATA_ROOT or not (Path(DATA_ROOT) / "metadata").is_dir(), reason="needs PERIGEE_DATA_ROOT cached SIA responses"
)


@needs_data
@pytest.mark.parametrize("preset", ["epsilon_indi_b", "barnards_star"])
def test_fixed_radius_and_48_cap_with_temporal_sampling_on_real_sia(client, harness, preset):
    meta = Path(DATA_ROOT) / "metadata"
    votables = {c: (meta / f"{preset}_{c}.xml").read_bytes() for c in ("spherex_dr1", "spherex_qr3")}
    up = Upstream(sia=dict(votables))
    install(harness, up)
    target = next(t for t in json.loads((Path(DATA_ROOT) / "manifest.json").read_text())["targets"] if t["id"] == preset)
    ra, dec = target["query_ra_deg"], target["query_dec_deg"]
    seen_params = []
    orig = up.__call__

    async def spy(request):
        if request.url.path == SIA_PATH:
            seen_params.append(dict(request.url.params))
        return await orig(request)

    harness.fetch_handler = spy
    results = {}
    for fov in (2.0, 10.0):
        r = client.post("/api/v1/search", json={"schema_version": 1, "ra_deg": ra, "dec_deg": dec, "fov_arcmin": fov,
                                                "limit": LIMIT_MAX})
        assert r.status_code == 200
        results[fov] = r.json()
    # Fixed 3.6" coverage cone and MAXREC, whatever the field of view.
    assert {p["POS"] for p in seen_params} == {f"CIRCLE {ra!r} {dec!r} {SEARCH_RADIUS_DEG}"}
    assert SEARCH_RADIUS_DEG * 3600 == pytest.approx(3.6)
    assert {p["MAXREC"] for p in seen_params} == {str(SIA_MAXREC)}
    a, b = results[2.0], results[10.0]
    assert [o["frame_key"] for o in a["observations"]] == [o["frame_key"] for o in b["observations"]]
    # The cached responses hold more than 48 level-2 images: an evenly spaced time sample of 48.
    from backend.routes._archive import parse_votable, rows_to_descriptors

    merged, seen = [], set()
    for col in ("spherex_dr1", "spherex_qr3"):
        rows, _ = parse_votable(votables[col])
        for d in rows_to_descriptors(rows, col)[0]:
            if d["frame_key"] not in seen:
                seen.add(d["frame_key"])
                merged.append(d)
    merged.sort(key=lambda d: (d["mjd"] is None, d["mjd"] or 0.0, d["frame_key"]))
    assert len(merged) > LIMIT_MAX
    assert a["status"] == "ready" and a["total_matches"] == len(merged)
    assert a["returned_count"] == LIMIT_MAX and a["truncated"] is True and a["selection"] == "evenly_spaced_in_time"
    assert [o["frame_key"] for o in a["observations"]] == [d["frame_key"] for d in select_evenly(merged, LIMIT_MAX)]
    assert a["observations"][0]["frame_key"] == merged[0]["frame_key"]
    assert a["observations"][-1]["frame_key"] == merged[-1]["frame_key"]
    assert any(w.startswith(f"Showing {LIMIT_MAX} of {len(merged)} matching images") for w in a["warnings"])
