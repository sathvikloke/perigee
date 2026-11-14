"""Worker 14 review checks: each test pins one reproduced defect (see REVIEW.md).

No network. Upstream behaviour is scripted with httpx.MockTransport.
"""

from __future__ import annotations

import gzip
import time

import httpx
import pytest

from backend.routes._archive import irsa_search_collection
from backend.security import config
from backend.security.upstream import _is_allowed_fetch_url, is_allowed_source_url

from .fixtures import fixture_descriptor
from .test_frame import DESC, err, make_token, post

SEARCH = "/api/v1/search"
FITS = b"SIMPLE  =" + b" " * 2871


def _fits_ok(req: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=FITS, headers={"content-type": "application/fits"})


# R1 -- IRSA cutouts fail with fast transient 503s; one retry recovers the frame.


def test_r1_transient_cutout_503_is_retried(client, harness):
    calls = []

    def flaky(req):
        calls.append(req)
        if len(calls) == 1:
            return httpx.Response(503, text="<html>Service Unavailable</html>", headers={"content-type": "text/html"})
        return _fits_ok(req)

    harness.fetch_handler = flaky
    r = post(client, make_token())
    assert r.status_code == 200, r.text
    assert len(harness.fetched) == 2


def test_r1_persistent_503_is_bounded_and_reports_attempts(client, harness):
    harness.fetch_handler = lambda req: httpx.Response(503, text="busy")
    t = time.monotonic()
    d = err(post(client, make_token()), 502, "UPSTREAM_UNAVAILABLE")
    assert time.monotonic() - t < harness.settings.frame_budget_s
    assert d["error"]["details"]["attempts"] == len(harness.fetched) == 3


def test_r1_404_is_not_retried(client, harness):
    harness.fetch_handler = lambda req: httpx.Response(404, text="nope")
    err(post(client, make_token()), 502, "UPSTREAM_UNAVAILABLE")
    assert len(harness.fetched) == 1


# R2 -- validation error details were unbounded (17 MB error for a 4 MB body).


def test_r2_validation_error_details_are_bounded(client):
    body = "{" + ",".join(f'"k{i}":0' for i in range(5000)) + "}"
    r = client.post(SEARCH, content=body, headers={"content-type": "application/json"})
    assert r.status_code == 400
    details = r.json()["error"]["details"]
    assert len(details["fields"]) <= 20 and details["fields_total"] > 5000
    assert len(r.content) < 10_000


# R3 -- a corrupt Content-Encoding body (httpx.DecodingError) escaped classification.


def _bad_gzip(req):
    return httpx.Response(200, content=b"\x00not gzip", headers={"content-encoding": "gzip"})


def test_r3_corrupt_gzip_cutout_is_upstream_error_not_500(client, harness):
    harness.fetch_handler = _bad_gzip
    d = err(post(client, make_token()), 502, "UPSTREAM_UNAVAILABLE")
    assert d["error"]["details"]["reason"] == "DecodingError"


_VOTABLE = """<?xml version="1.0"?>
<VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE type="results">
<INFO name="QUERY_STATUS" value="OK"/><TABLE>
<FIELD name="obs_id"/><FIELD name="access_url"/><FIELD name="t_min"/>
<FIELD name="obs_publisher_did"/><FIELD name="dataproduct_type"/><FIELD name="obs_collection"/>
<DATA><TABLEDATA><TR><TD>{obs}</TD><TD>{url}</TD><TD>61159.5</TD><TD>ivo://x/{obs}/D3</TD>
<TD>image</TD><TD>spherex_dr1</TD></TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>"""


def test_r3_corrupt_gzip_in_one_collection_keeps_partial_search(client, harness):
    good = _VOTABLE.format(obs=DESC["observation_id"], url=DESC["source_url"]).encode()

    def sia(req):
        if req.url.params.get("COLLECTION") == "spherex_dr1":
            return httpx.Response(200, content=gzip.compress(good),
                                  headers={"content-encoding": "gzip", "content-type": "text/xml"})
        return _bad_gzip(req)

    harness.search = irsa_search_collection
    harness.fetch_handler = sia
    r = client.post(SEARCH, json={"schema_version": 1, "ra_deg": 330.84, "dec_deg": -56.786})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "partial" and j["collections_failed"] == ["spherex_qr3"]
    assert [o["observation_id"] for o in j["observations"]] == [DESC["observation_id"]]


# R4 -- urlsplit drops tab/CR/LF that httpx rejects: allowlisted URL -> 500.

_GOOD = fixture_descriptor("2026W18_1A_0516_1", 3, None)["source_url"]


@pytest.mark.parametrize(
    "url",
    [
        _GOOD.replace("level2_", "level2_\t"),
        _GOOD.replace("level2_", "level2_\n"),
        " " + _GOOD,
    ],
)
def test_r4_unsafe_characters_are_not_allowlisted(url):
    assert not is_allowed_source_url(url)
    assert not _is_allowed_fetch_url(url + "?center=1,1&size=0.1", "data")


def test_r4_token_with_control_char_source_is_rejected_before_fetch(client, harness):
    harness.fetch_handler = _fits_ok
    token = make_token(source_url=_GOOD.replace("level2_", "level2_\t"))
    err(post(client, token), 400, "INVALID_FRAME_TOKEN")
    assert harness.fetched == []


# R5 -- the frame response could exceed Vercel's 4.5 MB response limit.


def test_r5_oversized_frame_response_is_a_json_error(client, harness):
    base = harness.processor

    def big(data, meta):
        out = base(data, meta)
        out["image_png"] = out["image_png"] + b"\x00" * 1_900_000
        out["flag_png"] = out["image_png"]
        return out

    harness.processor = big
    harness.fetch_handler = _fits_ok
    d = err(post(client, make_token()), 500, "PROCESSING_FAILED")
    assert d["error"]["details"]["reason"] == "response_too_large"


# R6 -- the public dev secret was accepted as PERIGEE_TOKEN_SECRET in production.


def test_r6_dev_secret_refused_on_hosted_deployments(monkeypatch):
    monkeypatch.delenv("PERIGEE_DEV_MODE", raising=False)
    monkeypatch.delenv("PERIGEE_ENV", raising=False)
    monkeypatch.setenv("PERIGEE_TOKEN_SECRET", config._DEV_SECRET)
    for env in ("production", "preview"):  # D3: Preview is hosted too
        monkeypatch.setenv("VERCEL_ENV", env)
        s = config.load_settings()
        assert s.token_secret is None and s.token_secret_source == "dev_secret_refused"
    # Locally (no VERCEL_ENV, or `vercel dev`) the value is merely a long string.
    for env in ("", "development"):
        monkeypatch.setenv("VERCEL_ENV", env)
        assert config.load_settings().token_secret_source == "env"
