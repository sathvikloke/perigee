"""Search/frame orchestration under failure (candidate B): budgets, partials, retries, mapping."""

from __future__ import annotations

import asyncio
import dataclasses
import time

import httpx
import pytest

from backend.models import FrameResponse, SearchResponse
from backend.routes.frames import ProcessorOutput, ProcessorRejected
from backend.routes.search import evenly_spaced

from .conftest import HTML_502, fake_fits, png_bytes, sia_row, votable

OK = {"schema_version": 1, "ra_deg": 330.84, "dec_deg": -56.786, "fov_arcmin": 6}
VOT = {"content-type": "application/x-votable+xml"}


def vot(rows, status="OK"):
    return lambda r: httpx.Response(200, content=votable(rows, status), headers=VOT)


def html502(r):
    return httpx.Response(502, content=HTML_502, headers={"content-type": "text/html"})


def slow(seconds):
    async def h(r):
        await asyncio.sleep(seconds)
        return httpx.Response(200, content=votable([]), headers=VOT)
    return h


ROWS_DR1 = [sia_row("2026W18_1A_0516_1", 3, 61159.50335), sia_row("2025W17_4B_0017_1", 2, 60789.85),
            sia_row("2026W18_1A_0516_1", 6, 61159.50335)]
ROWS_QR3 = [sia_row("2026W39_2A_0597_4", 3, 61310.3, "spherex_qr3")]


def test_ready_sorted_by_mjd_then_key_and_signed(client, archive):
    archive.on("spherex_dr1", vot(ROWS_DR1))
    archive.on("spherex_qr3", vot(ROWS_QR3))
    r = client.post("/api/v1/search", json=OK)
    assert r.status_code == 200, r.text
    body = SearchResponse.model_validate(r.json())
    assert body.status == "ready" and body.total_matches == 4 and not body.truncated
    keys = [o.frame_key for o in body.observations]
    assert keys == ["2025W17_4B_0017_1_D2", "2026W18_1A_0516_1_D3", "2026W18_1A_0516_1_D6", "2026W39_2A_0597_4_D3"]
    o = body.observations[0]
    assert o.time_basis == "sia_t_min" and o.observed_at_utc.startswith("2025-04-24T20:")
    assert o.detector_wavelength_range_um == [2.2, 3.8]
    assert all(x.frame_token.startswith("pb1.") for x in body.observations)


def test_partial_when_one_collection_returns_html_502(client, archive):
    archive.on("spherex_dr1", vot(ROWS_DR1))
    archive.on("spherex_qr3", html502)
    r = client.post("/api/v1/search", json=OK)
    body = r.json()
    assert r.status_code == 200 and body["status"] == "partial"
    assert body["collections_failed"] == ["spherex_qr3"] and body["returned_count"] == 3
    assert any("spherex_qr3" in w for w in body["warnings"])
    assert body["total_matches"] is None  # unknown: a collection failed
    # bounded retries for the transient 502: 1 attempt + upstream_retries (4)
    assert sum("spherex_qr3" in c for c in archive.calls) == 5


def test_transient_502_then_success_is_ready(client, archive):
    seen = {"n": 0}

    def flaky(r):
        seen["n"] += 1
        return html502(r) if seen["n"] == 1 else vot(ROWS_QR3)(r)

    archive.on("spherex_dr1", vot(ROWS_DR1))
    archive.on("spherex_qr3", flaky)
    body = client.post("/api/v1/search", json=OK).json()
    assert body["status"] == "ready" and body["returned_count"] == 4 and seen["n"] == 2


def test_all_collections_502_is_upstream_unavailable(client, archive):
    archive.on("spherex_dr1", html502)
    archive.on("spherex_qr3", html502)
    r = client.post("/api/v1/search", json=OK)
    assert r.status_code == 502
    e = r.json()["error"]
    assert e["code"] == "UPSTREAM_UNAVAILABLE" and e["retryable"] is True
    assert e["details"]["reasons"] == {"spherex_dr1": "unavailable", "spherex_qr3": "unavailable"}


def test_all_collections_timeout_is_504_within_budget(client, archive):
    client.holder["settings"] = dataclasses.replace(client.holder["settings"], request_budget_s=1.5)
    archive.on("spherex_dr1", slow(30))
    archive.on("spherex_qr3", slow(30))
    t0 = time.monotonic()
    r = client.post("/api/v1/search", json=OK)
    elapsed = time.monotonic() - t0
    assert r.status_code == 504 and r.json()["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert elapsed < 3.0  # soft budget honored, not the 30 s upstream delay


def test_timeout_on_one_collection_is_partial(client, archive):
    client.holder["settings"] = dataclasses.replace(client.holder["settings"], request_budget_s=1.5)
    archive.on("spherex_dr1", vot(ROWS_DR1))
    archive.on("spherex_qr3", slow(30))
    body = client.post("/api/v1/search", json=OK).json()
    assert body["status"] == "partial" and body["collections_failed"] == ["spherex_qr3"]


def test_failed_plus_empty_is_error_not_empty(client, archive):
    archive.on("spherex_dr1", vot([]))
    archive.on("spherex_qr3", html502)
    r = client.post("/api/v1/search", json=OK)
    assert r.status_code == 502
    assert r.json()["error"]["details"]["collections_succeeded_empty"] == ["spherex_dr1"]


def test_genuinely_empty(client, archive):
    archive.on("spherex_dr1", vot([]))
    archive.on("spherex_qr3", vot([]))
    body = client.post("/api/v1/search", json=OK).json()
    assert body["status"] == "empty" and body["observations"] == [] and body["total_matches"] == 0
    assert any("not a claim" in w for w in body["warnings"])


def test_overflow_is_partial_with_unknown_total(client, archive):
    archive.on("spherex_dr1", vot(ROWS_DR1, status="OVERFLOW"))
    archive.on("spherex_qr3", vot(ROWS_QR3))
    body = client.post("/api/v1/search", json=OK).json()
    assert body["status"] == "partial" and body["total_matches"] is None and body["truncated"]


def test_limit_selects_evenly_spaced_in_time(client, archive):
    rows = [sia_row(f"2026W18_1A_{i:04d}_1", 1 + i % 6, 61000 + i) for i in range(30)]
    archive.on("spherex_dr1", vot(rows))
    archive.on("spherex_qr3", vot([]))
    body = client.post("/api/v1/search", json={**OK, "limit": 5}).json()
    assert body["returned_count"] == 5 and body["total_matches"] == 30
    assert body["selection"] == "evenly_spaced_in_time" and body["truncated"]
    mjds = [o["mjd"] for o in body["observations"]]
    assert mjds[0] == 61000 and mjds[-1] == 61029 and mjds == sorted(mjds)
    assert evenly_spaced(3, 5) == [0, 1, 2] and evenly_spaced(10, 1) == [0]


def test_rows_with_foreign_urls_are_not_signed(client, archive):
    bad = sia_row("2026W18_1A_0516_1", 4, 61159.5)
    bad["access_url"] = "https://evil.example/ibe/data/spherex/dr1/x.fits"
    archive.on("spherex_dr1", vot([bad] + ROWS_DR1[:1]))
    archive.on("spherex_qr3", vot([]))
    body = client.post("/api/v1/search", json=OK).json()
    assert [o["frame_key"] for o in body["observations"]] == ["2026W18_1A_0516_1_D3"]
    assert any("ignored" in w for w in body["warnings"])


def test_oversized_sia_response_is_refused(client, archive):
    client.holder["settings"] = dataclasses.replace(client.holder["settings"], max_search_bytes=1000)
    archive.on("spherex_dr1", vot(ROWS_DR1 * 10))
    archive.on("spherex_qr3", vot(ROWS_DR1 * 10))
    r = client.post("/api/v1/search", json=OK)
    assert r.status_code == 502 and r.json()["error"]["details"]["reasons"]["spherex_dr1"] == "too_large"


def test_redirect_off_allowlist_is_blocked(client, archive):
    archive.on("spherex_dr1", lambda r: httpx.Response(302, headers={"location": "https://evil.example/x"}))
    archive.on("spherex_qr3", vot(ROWS_QR3))
    body = client.post("/api/v1/search", json=OK).json()
    assert body["status"] == "partial" and body["collections_failed"] == ["spherex_dr1"]
    assert not any("evil.example" in c for c in archive.calls)


# ----------------------------------------------------------------------------- frame


def _token(client, archive):
    archive.on("spherex_dr1", vot(ROWS_DR1[:1]))
    archive.on("spherex_qr3", vot([]))
    return client.post("/api/v1/search", json=OK).json()["observations"][0]["frame_token"]


class FakeProcessor:
    name = "fake-processor/0"

    def __init__(self, exc=None):
        self.exc = exc
        self.calls = 0

    def __call__(self, fits_bytes, job):
        self.calls += 1
        if self.exc:
            raise self.exc
        return ProcessorOutput(record=_record(job), png_bytes=png_bytes(), flag_png_bytes=None)


def _record(job):
    return {
        "frame_id": f"{job.observation_id}_D{job.detector}", "frame_key": f"{job.observation_id}_D{job.detector}",
        "observation_id": job.observation_id, "detector": job.detector, "collection_id": job.collection_id,
        "observed_at_utc": "2026-04-29T12:05:47.874", "mjd": 61159.504026317, "source_url": job.source_url,
        "wavelength_um": 2.3232, "bandwidth_um": 0.0577, "wavelength_location": "query center",
        "image": {"src": None, "width": 4, "height": 4, "media_type": "image/png"}, "flag_image": None,
        "registration": {"center_ra_deg": job.query_ra_deg, "center_dec_deg": job.query_dec_deg,
                         "fov_arcmin": job.fov_arcmin, "scale_arcsec_per_px": 1.40625,
                         "orientation": "north_up_east_left", "method": "nearest_neighbour"},
        "quality": {"status": "unknown", "covered": None, "valid_aperture_pixels": None,
                    "adverse_aperture_pixels": None, "flag_names": [], "notes": []},
        "display_scale": {"mode": "per_frame", "method": "asinh", "low": 0.0, "high": 1.0},
        "marker": None,
        "provenance": {"retrieved_at": job.retrieved_at_utc, "original_url": job.source_url,
                       "sha256": "0" * 64, "processing_version": "fake", "acknowledgments": []},
        "limitations": ["fixture processor"],
    }


def fits_ok(r):
    return httpx.Response(200, content=fake_fits(), headers={"content-type": "image/fits"})


def test_frame_success_with_adapter(client, archive, processor_slot):
    processor_slot["p"] = FakeProcessor()
    tok = _token(client, archive)
    archive.on("cutout", fits_ok)
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
    assert r.status_code == 200, r.text
    resp = FrameResponse.model_validate(r.json())
    f = resp.frame
    assert f.frame_key == "2026W18_1A_0516_1_D3" and f.image.src.startswith("data:image/png;base64,")
    assert f.registration.scale_arcsec_per_pixel == 1.40625
    assert f.display_scale.comparable_brightness is False
    assert f.provenance.data_origin == "nasa_archive" and "center=" in f.provenance.cutout_url
    cut = [c for c in archive.calls if "center=" in c][0]
    assert "size=0.155563" in cut  # 6' * sqrt(2) * 1.1


def test_frame_invalid_token_never_fetches(client, archive, processor_slot):
    processor_slot["p"] = FakeProcessor()
    tok = _token(client, archive)
    n = len(archive.calls)
    bad = tok[:-2] + ("AA" if not tok.endswith("AA") else "BB")
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": bad})
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_FRAME_TOKEN"
    assert len(archive.calls) == n


def test_frame_expired_token(client, archive, processor_slot, monkeypatch):
    processor_slot["p"] = FakeProcessor()
    tok = _token(client, archive)
    real = time.time
    monkeypatch.setattr("backend.routes.frames.time.time", lambda: real() + 7 * 3600)
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
    assert r.status_code == 400
    e = r.json()["error"]
    assert e["code"] == "TOKEN_EXPIRED" and e["details"]["action"] == "refresh_search"


def test_frame_processor_missing_is_503_before_fetch(client, archive):
    tok = _token(client, archive)
    n = len(archive.calls)
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
    assert r.status_code == 503 and r.json()["error"]["code"] == "PROCESSOR_UNAVAILABLE"
    assert len(archive.calls) == n


@pytest.mark.parametrize("handler,status,code", [
    (html502, 502, "UPSTREAM_UNAVAILABLE"),
    (lambda r: httpx.Response(200, content=b"<html>oops</html>", headers={"content-type": "text/html"}),
     502, "UPSTREAM_UNAVAILABLE"),
    (lambda r: httpx.Response(200, content=b"not a fits file", headers={"content-type": "image/fits"}),
     422, "UNSUPPORTED_DATA"),
    (lambda r: httpx.Response(429), 503, "UPSTREAM_UNAVAILABLE"),
    (lambda r: httpx.Response(404), 502, "UPSTREAM_UNAVAILABLE"),
])
def test_frame_upstream_mapping(client, archive, processor_slot, handler, status, code):
    processor_slot["p"] = FakeProcessor()
    tok = _token(client, archive)
    archive.on("cutout", handler)
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
    assert r.status_code == status and r.json()["error"]["code"] == code
    assert processor_slot["p"].calls == 0


def test_frame_upstream_timeout_within_budget(client, archive, processor_slot):
    processor_slot["p"] = FakeProcessor()
    tok = _token(client, archive)
    client.holder["settings"] = dataclasses.replace(client.holder["settings"], request_budget_s=1.5)

    async def hang(r):
        await asyncio.sleep(30)
        return fits_ok(r)

    archive.on("cutout", hang)
    t0 = time.monotonic()
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
    assert r.status_code == 504 and r.json()["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert time.monotonic() - t0 < 3.0


def test_frame_budget_reserve_blocks_processing(client, archive, processor_slot):
    processor_slot["p"] = FakeProcessor()
    tok = _token(client, archive)
    client.holder["settings"] = dataclasses.replace(client.holder["settings"], request_budget_s=5.0,
                                                    processing_reserve_s=4.9)

    async def slowish(r):
        await asyncio.sleep(0.3)
        return fits_ok(r)

    archive.on("cutout", slowish)
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
    assert r.status_code == 504 and r.json()["error"]["details"]["reason"] == "budget_exhausted_before_processing"
    assert processor_slot["p"].calls == 0


class UnsupportedDataError(Exception):
    pass


@pytest.mark.parametrize("exc,status,code", [
    (UnsupportedDataError("no IMAGE"), 422, "UNSUPPORTED_DATA"),
    (ProcessorRejected("failed", "x"), 500, "PROCESSING_FAILED"),
    (ValueError("boom"), 500, "PROCESSING_FAILED"),
])
def test_frame_processor_failures(client, archive, processor_slot, exc, status, code):
    from backend.routes.frames import ProcessFrameAdapter

    class Mod:
        __name__ = "fake"
        PROCESSING_VERSION = "fake/1"

        class FrameInput:
            def __init__(self, **kw):
                self.kw = kw

        @staticmethod
        def process_frame(b, meta):
            raise exc

    processor_slot["p"] = ProcessFrameAdapter(Mod)
    tok = _token(client, archive)
    archive.on("cutout", fits_ok)
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
    assert r.status_code == status and r.json()["error"]["code"] == code
    assert "Traceback" not in r.text and "boom" not in r.text


def test_frame_contract_mismatch_is_processing_failed(client, archive, processor_slot):
    class Broken(FakeProcessor):
        def __call__(self, fits_bytes, job):
            out = super().__call__(fits_bytes, job)
            del out.record["quality"]
            return out

    processor_slot["p"] = Broken()
    tok = _token(client, archive)
    archive.on("cutout", fits_ok)
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
    assert r.status_code == 500 and r.json()["error"]["details"]["reason"] == "contract_mismatch"
