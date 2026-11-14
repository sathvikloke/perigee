"""POST /api/v1/frame protocol tests (fixture fetch + fixture processor; no network)."""

from __future__ import annotations

import base64
import json
from dataclasses import replace

import httpx
import pytest

from backend.security.tokens import issue_token

from .conftest import TEST_SECRET
from .fixtures import fixture_descriptor

URL = "/api/v1/frame"
DESC = fixture_descriptor("2026W18_1A_0516_1", 3, 61159.5)


def make_token(secret=TEST_SECRET, ttl=3600, now=None, **over):
    kw = dict(
        source_url=DESC["source_url"],
        observation_id=DESC["observation_id"],
        detector=DESC["detector"],
        collection_id=DESC["collection_id"],
        frame_key=DESC["frame_key"],
        mjd=DESC["mjd"],
        observed_at_utc=None,
        ra_deg=330.84,
        dec_deg=-56.786,
        fov_arcmin=6.0,
        ttl_s=ttl,
        now=now,
    )
    kw.update(over)
    return issue_token(secret, **kw)[0]


def post(client, token):
    return client.post(URL, json={"schema_version": 1, "frame_token": token})


def err(resp, status, code):
    assert resp.status_code == status, resp.text
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["error"]["code"] == code
    return resp.json()


def test_happy_path_fixture_frame(client, harness):
    r = post(client, make_token())
    assert r.status_code == 200, r.text
    f = r.json()["frame"]
    assert f["frame_key"] == "2026W18_1A_0516_1_D3" and f["detector"] == 3
    assert f["source_url"] == DESC["source_url"] == f["provenance"]["original_url"]
    assert f["provenance"]["data_origin"] == "fixture"  # labeled; never shown as sky data
    assert f["image"]["src"].startswith("data:image/png;base64,")
    assert base64.b64decode(f["image"]["src"].split(",", 1)[1]).startswith(b"\x89PNG")
    assert f["flag_image"] is None
    assert f["quality"]["valid_aperture_pixels"] is None  # unknown stays null, not 0
    # fetched exactly one allowlisted cutout centered on the signed query
    assert len(harness.fetched) == 1
    fetched = httpx.URL(harness.fetched[0])
    assert str(fetched.copy_with(query=None)) == DESC["source_url"]
    assert fetched.params["center"] == "330.84,-56.786"
    assert float(fetched.params["size"]) == pytest.approx(6.0 * 1.5 / 60)
    assert f["provenance"]["cutout_url"] == harness.fetched[0]
    assert len(f["provenance"]["sha256"]) == 64


def _tamper_payload(token: str, mutate) -> str:
    prefix, body, sig = token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    mutate(payload)
    new_body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{prefix}.{new_body}.{sig}"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p["d"].__setitem__("src", "https://evil.example/x.fits"),
        lambda p: p["d"].__setitem__("src", "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/other.fits"),
        lambda p: p["q"].__setitem__("ra", 10.0),
        lambda p: p.__setitem__("exp", p["exp"] + 10**6),
        lambda p: p["d"].__setitem__("det", 6),
    ],
)
def test_tampered_token_rejected_before_fetch(client, harness, mutate):
    err(post(client, _tamper_payload(make_token(), mutate)), 400, "INVALID_FRAME_TOKEN")
    assert harness.fetched == []


@pytest.mark.parametrize(
    "token",
    ["", "x", "pf1.abc", "pf1.abc.def", "pf2." + "a" * 20 + "." + "b" * 20, "pf1.!!!.???", "a.b.c.d", "x" * 5000],
)
def test_malformed_tokens(client, harness, token):
    err(post(client, token), 400, "INVALID_FRAME_TOKEN")
    assert harness.fetched == []


def test_wrong_secret_rejected(client, harness):
    err(post(client, make_token(secret=b"another-secret-another-secret-0000000")), 400, "INVALID_FRAME_TOKEN")


def test_signature_swap_rejected(client):
    a, b = make_token(), make_token(ra_deg=1.0)
    pa, pb = a.split("."), b.split(".")
    err(post(client, f"{pa[0]}.{pb[1]}.{pa[2]}"), 400, "INVALID_FRAME_TOKEN")


def test_expired_token_distinct(client, harness):
    tok = make_token(ttl=60, now=1_000_000)
    d = err(post(client, tok), 400, "TOKEN_EXPIRED")
    assert d["error"]["details"]["action"] == "refresh_search"
    assert harness.fetched == []


def test_tampered_and_expired_reports_invalid(client):
    tok = _tamper_payload(make_token(ttl=60, now=1_000_000), lambda p: p["q"].__setitem__("ra", 2.0))
    err(post(client, tok), 400, "INVALID_FRAME_TOKEN")


def test_authentic_token_with_non_allowlisted_source(client, harness):
    tok = make_token(source_url="https://example.com/level2_x.fits")
    err(post(client, tok), 400, "INVALID_FRAME_TOKEN")
    assert harness.fetched == []


def test_request_validation(client):
    err(client.post(URL, json={"schema_version": 1}), 400, "INVALID_FRAME_TOKEN")
    err(client.post(URL, json={"schema_version": 1, "frame_token": 5}), 400, "INVALID_FRAME_TOKEN")
    err(client.post(URL, json={"schema_version": 2, "frame_token": make_token()}), 422, "UNSUPPORTED_SCHEMA_VERSION")
    err(client.post(URL, json={"schema_version": 1, "frame_token": make_token(), "source_url": "x"}), 400, "INVALID_REQUEST")


# ------------------------------------------------------------ upstream vs processing


@pytest.mark.parametrize("status", [500, 502, 503])
def test_upstream_5xx(client, harness, status):
    harness.fetch_handler = lambda req: httpx.Response(status, text="<html>Proxy Error</html>", headers={"content-type": "text/html"})
    d = err(post(client, make_token()), 502, "UPSTREAM_UNAVAILABLE")
    assert d["error"]["retryable"] is True


def test_upstream_html_with_200(client, harness):
    harness.fetch_handler = lambda req: httpx.Response(200, text="<!DOCTYPE html><html>oops</html>", headers={"content-type": "text/html"})
    err(post(client, make_token()), 502, "UPSTREAM_UNAVAILABLE")


def test_upstream_404_not_retryable(client, harness):
    harness.fetch_handler = lambda req: httpx.Response(404, text="nope")
    d = err(post(client, make_token()), 502, "UPSTREAM_UNAVAILABLE")
    assert d["error"]["retryable"] is False


def test_upstream_timeout(client, harness):
    def boom(req):
        raise httpx.ReadTimeout("slow", request=req)

    harness.fetch_handler = boom
    err(post(client, make_token()), 504, "UPSTREAM_TIMEOUT")


def test_upstream_connect_error(client, harness):
    def boom(req):
        raise httpx.ConnectError("refused", request=req)

    harness.fetch_handler = boom
    err(post(client, make_token()), 502, "UPSTREAM_UNAVAILABLE")


def test_redirect_outside_allowlist_not_followed(client, harness):
    harness.fetch_handler = lambda req: httpx.Response(302, headers={"location": "https://evil.example/x.fits"})
    err(post(client, make_token()), 502, "UPSTREAM_UNAVAILABLE")
    assert len(harness.fetched) == 1


def test_byte_cap(client, harness):
    harness.settings = replace(harness.settings, frame_fetch_max_bytes=1000)
    harness.fetch_handler = lambda req: httpx.Response(200, content=b"SIMPLE  =" + b"x" * 5000)
    err(post(client, make_token()), 502, "UNSUPPORTED_DATA")


def test_not_fits_is_unsupported_data(client, harness):
    harness.fetch_handler = lambda req: httpx.Response(200, content=b"\x00\x01binary", headers={"content-type": "application/octet-stream"})
    err(post(client, make_token()), 502, "UNSUPPORTED_DATA")


def test_processor_unsupported(client, harness):
    class UnsupportedFitsError(Exception):
        pass

    def proc(data, meta):
        raise UnsupportedFitsError("no IMAGE extension")

    harness.processor = proc
    d = err(post(client, make_token()), 422, "UNSUPPORTED_DATA")
    assert "no IMAGE" not in json.dumps(d)  # internal message not leaked


def test_processor_crash_is_processing_failed(client, harness):
    def proc(data, meta):
        raise RuntimeError("secret internal path /Users/x")

    harness.processor = proc
    d = err(post(client, make_token()), 500, "PROCESSING_FAILED")
    assert "/Users" not in json.dumps(d)


def test_processor_bad_output_is_processing_failed(client, harness):
    harness.processor = lambda data, meta: {"record": {"quality": {}}, "image_png": b"\x89PNG\r\n\x1a\n"}
    err(post(client, make_token()), 500, "PROCESSING_FAILED")
    harness.processor = lambda data, meta: {"record": {}, "image_png": b"GIF89a"}
    err(post(client, make_token()), 500, "PROCESSING_FAILED")


def test_processor_cannot_change_identity(client, harness):
    from .fixtures import fixture_processor

    def proc(data, meta):
        out = fixture_processor(data, meta)
        out["record"]["source_url"] = "https://evil.example/x"
        out["record"]["frame_key"] = "other"
        return out

    harness.processor = proc
    f = post(client, make_token()).json()["frame"]
    assert f["source_url"] == DESC["source_url"] and f["frame_key"] == DESC["frame_key"]


def test_processor_missing_is_explicit_and_skips_fetch(client, harness):
    harness.processor = None
    err(post(client, make_token()), 503, "PROCESSOR_UNAVAILABLE")
    assert harness.fetched == []
