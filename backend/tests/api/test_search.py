"""POST /api/v1/search protocol tests (fixture archive; no network)."""

from __future__ import annotations

import pytest

from backend.routes._archive import CollectionResult
from backend.routes.search import select_evenly
from backend.security.tokens import verify_token
from backend.security.upstream import UpstreamTimeout, UpstreamUnavailable

from .conftest import TEST_SECRET
from .fixtures import FakeSearch, fixture_descriptor

URL = "/api/v1/search"


def body(**kw):
    b = {"schema_version": 1, "ra_deg": 330.84, "dec_deg": -56.786}
    b.update(kw)
    return b


def assert_error(resp, status, code):
    assert resp.status_code == status, resp.text
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    assert data["schema_version"] == 1
    assert data["request_id"]
    assert data["error"]["code"] == code
    assert isinstance(data["error"]["retryable"], bool)
    return data


# ---------------------------------------------------------------- input validation


@pytest.mark.parametrize(
    "ra,dec",
    [
        (-0.0001, 0),
        (360, 0),
        (360.0, 0),
        (400, 0),
        (10, 90.0001),
        (10, -90.5),
        ("12.5", 0),
        ("12abc", 0),
        ("", 0),
        (True, 0),
        (None, 0),
        ([1], 0),
    ],
)
def test_invalid_coordinates_rejected(client, harness, ra, dec):
    data = assert_error(client.post(URL, json=body(ra_deg=ra, dec_deg=dec)), 422, "INVALID_COORDINATES")
    assert data["error"]["details"]["fields"]
    assert harness.search.calls == []  # nothing reached the archive


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_nan_and_infinity_rejected(client, harness, literal):
    raw = '{"schema_version":1,"ra_deg":%s,"dec_deg":0}' % literal
    resp = client.post(URL, content=raw, headers={"content-type": "application/json"})
    assert_error(resp, 422, "INVALID_COORDINATES")
    raw = '{"schema_version":1,"ra_deg":10,"dec_deg":0,"fov_arcmin":%s}' % literal
    resp = client.post(URL, content=raw, headers={"content-type": "application/json"})
    assert_error(resp, 422, "INVALID_FIELD_OF_VIEW")
    assert harness.search.calls == []


def test_missing_coordinates(client):
    assert_error(client.post(URL, json={"schema_version": 1, "ra_deg": 10}), 422, "INVALID_COORDINATES")


@pytest.mark.parametrize("fov", [1.99, 10.01, 0, -6, "6", 100])
def test_invalid_fov_not_clipped(client, harness, fov):
    assert_error(client.post(URL, json=body(fov_arcmin=fov)), 422, "INVALID_FIELD_OF_VIEW")
    assert harness.search.calls == []


@pytest.mark.parametrize("limit", [0, 49, -1, 2.5, "10", True])
def test_invalid_limit(client, limit):
    assert_error(client.post(URL, json=body(limit=limit)), 422, "INVALID_LIMIT")


@pytest.mark.parametrize(
    "cols", [[], ["spherex_dr2"], ["SPHEREX_DR1"], "spherex_dr1", ["https://evil.example/x"], ["spherex_dr1 OR 1=1"]]
)
def test_collection_allowlist(client, harness, cols):
    assert_error(client.post(URL, json=body(collection_ids=cols)), 422, "INVALID_COLLECTION")
    assert harness.search.calls == []


@pytest.mark.parametrize("sv", [2, 0, "1", None, 1.0, True])
def test_schema_version(client, sv):
    assert_error(client.post(URL, json=body(schema_version=sv)), 422, "UNSUPPORTED_SCHEMA_VERSION")


def test_unknown_field_rejected_not_ignored(client):
    # e.g. a typo'd "fov" must not silently fall back to the default field size
    assert_error(client.post(URL, json=body(fov=3)), 400, "INVALID_REQUEST")


def test_malformed_json_and_non_object(client):
    r = client.post(URL, content="{not json", headers={"content-type": "application/json"})
    assert_error(r, 400, "INVALID_REQUEST")
    assert_error(client.post(URL, json=[1, 2]), 400, "INVALID_REQUEST")


def test_boundaries_accepted(client, harness):
    harness.search = FakeSearch({})
    for b in [
        body(ra_deg=0, dec_deg=-90, fov_arcmin=2, limit=1),
        body(ra_deg=359.999999, dec_deg=90, fov_arcmin=10, limit=48),
    ]:
        r = client.post(URL, json=b)
        assert r.status_code == 200, r.text


# ---------------------------------------------------------------- status semantics


def test_ready_sorted_and_tokens_bound(client, harness):
    harness.search = FakeSearch(
        {
            "spherex_dr1": [
                fixture_descriptor("2026W18_1A_0516_1", 6, 61159.5),
                fixture_descriptor("2026W18_1A_0516_1", 3, 61159.5),
                fixture_descriptor("2025W17_4B_0077_2", 1, 60790.1, week="2025W17_4B"),
            ],
            "spherex_qr3": [fixture_descriptor("2026W39_2A_0597_4", 3, 61310.3, "spherex_qr3", "2026W39_2A")],
        }
    )
    r = client.post(URL, json=body(fov_arcmin=6, limit=24))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "ready"
    assert d["truncated"] is False and d["selection"] == "all"
    assert d["total_matches"] == 4 == d["returned_count"] == len(d["observations"])
    keys = [o["frame_key"] for o in d["observations"]]
    # mjd ascending, then frame_key: D3 before D6 at identical mjd
    assert keys == ["2025W17_4B_0077_2_D1", "2026W18_1A_0516_1_D3", "2026W18_1A_0516_1_D6", "2026W39_2A_0597_4_D3"]
    assert d["collections_queried"] == ["spherex_dr1", "spherex_qr3"]
    # the real coordinate reached the archive adapter, unmodified
    assert {(c["ra_deg"], c["dec_deg"]) for c in harness.search.calls} == {(330.84, -56.786)}
    for o in d["observations"]:
        claims = verify_token(TEST_SECRET, o["frame_token"])
        assert claims.source_url == o["source_url"]
        assert claims.frame_key == o["frame_key"]
        assert (claims.ra_deg, claims.dec_deg, claims.fov_arcmin) == (330.84, -56.786, 6.0)


def test_empty_is_successful_query_with_no_records(client, harness):
    harness.search = FakeSearch({"spherex_dr1": [], "spherex_qr3": []})
    r = client.post(URL, json=body())
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "empty"
    assert d["observations"] == [] and d["returned_count"] == 0 and d["total_matches"] == 0
    assert any("not a claim" in w for w in d["warnings"])  # scope, not all-mission absence


def test_upstream_failure_is_error_not_empty(client, harness):
    harness.search = FakeSearch(
        {
            "spherex_dr1": UpstreamUnavailable("502", status=502, reason="upstream_5xx"),
            "spherex_qr3": UpstreamUnavailable("502", status=502, reason="html_body"),
        }
    )
    d = assert_error(client.post(URL, json=body()), 502, "UPSTREAM_UNAVAILABLE")
    assert d["error"]["retryable"] is True
    assert d["error"]["details"]["collections_failed"] == ["spherex_dr1", "spherex_qr3"]


def test_upstream_timeout(client, harness):
    harness.search = FakeSearch(
        {"spherex_dr1": UpstreamTimeout("slow", reason="deadline"), "spherex_qr3": UpstreamTimeout("slow")}
    )
    assert_error(client.post(URL, json=body()), 504, "UPSTREAM_TIMEOUT")


def test_one_collection_failed_with_results_is_partial(client, harness):
    harness.search = FakeSearch(
        {
            "spherex_dr1": [fixture_descriptor("2026W18_1A_0516_1", 3, 61159.5)],
            "spherex_qr3": UpstreamUnavailable("502", status=502),
        }
    )
    r = client.post(URL, json=body())
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "partial"
    assert d["collections_failed"] == ["spherex_qr3"]
    assert d["returned_count"] == 1
    assert d["total_matches"] is None  # unknown, not "1"
    assert any("incomplete" in w for w in d["warnings"])


def test_one_failed_other_empty_is_error_not_empty(client, harness):
    harness.search = FakeSearch({"spherex_dr1": [], "spherex_qr3": UpstreamUnavailable("x", status=503)})
    d = assert_error(client.post(URL, json=body()), 502, "UPSTREAM_UNAVAILABLE")
    assert d["error"]["details"]["collections_succeeded_empty"] == ["spherex_dr1"]


def test_collection_subset_only_queries_selected(client, harness):
    harness.search = FakeSearch({"spherex_qr3": []})
    r = client.post(URL, json=body(collection_ids=["spherex_qr3", "spherex_qr3"]))
    assert r.status_code == 200
    assert [c["collection_id"] for c in harness.search.calls] == ["spherex_qr3"]
    assert r.json()["collections_queried"] == ["spherex_qr3"]


def test_truncation_evenly_spaced_and_flagged(client, harness):
    many = [fixture_descriptor(f"2026W18_1A_{i:04d}_1", 2, 61000.0 + i) for i in range(100)]
    harness.search = FakeSearch({"spherex_dr1": list(reversed(many)), "spherex_qr3": []})
    d = client.post(URL, json=body(limit=5)).json()
    assert d["status"] == "ready"
    assert d["truncated"] is True and d["selection"] == "evenly_spaced_in_time"
    assert d["total_matches"] == 100 and d["returned_count"] == 5
    mjds = [o["mjd"] for o in d["observations"]]
    assert mjds == sorted(mjds) and mjds[0] == 61000.0 and mjds[-1] == 61099.0


def test_overflow_is_partial_with_unknown_total(client, harness):
    # D1: the archive's record cap is a documented limit that interrupted retrieval.
    harness.search = FakeSearch(
        {"spherex_dr1": CollectionResult("spherex_dr1", [fixture_descriptor("a_1", 1, 1.0)], overflow=True), "spherex_qr3": []}
    )
    d = client.post(URL, json=body()).json()
    assert d["status"] == "partial"
    assert d["total_matches"] is None and d["truncated"] is True
    assert d["collections_capped"] == ["spherex_dr1"] and d["collections_failed"] == []
    assert any("maximum number of records for spherex_dr1" in w for w in d["warnings"])


def test_mixed_failure_and_overflow(client, harness):
    harness.search = FakeSearch(
        {
            "spherex_dr1": CollectionResult("spherex_dr1", [fixture_descriptor("a_1", 1, 1.0)], overflow=True),
            "spherex_qr3": UpstreamUnavailable("502", status=502, reason="upstream_5xx"),
        }
    )
    resp = client.post(URL, json=body())
    assert resp.status_code == 200
    d = resp.json()
    assert d["status"] == "partial" and d["returned_count"] == 1
    assert d["collections_failed"] == ["spherex_qr3"] and d["collections_capped"] == ["spherex_dr1"]
    assert d["total_matches"] is None and d["truncated"] is True
    assert any(w.startswith("Some collections could not be searched") for w in d["warnings"])
    assert any("maximum number of records" in w for w in d["warnings"])


def test_limit_subset_without_overflow_stays_ready(client, harness):
    many = [fixture_descriptor(f"2026W18_1A_{i:04d}_1", 2, 61000.0 + i) for i in range(10)]
    harness.search = FakeSearch({"spherex_dr1": many, "spherex_qr3": []})
    d = client.post(URL, json=body(limit=3)).json()
    assert d["status"] == "ready" and d["collections_capped"] == []
    assert d["truncated"] is True and d["total_matches"] == 10


def test_duplicate_frame_keys_across_releases_deduplicated(client, harness):
    harness.search = FakeSearch(
        {
            "spherex_dr1": [fixture_descriptor("2026W18_1A_0516_1", 3, 61159.5)],
            "spherex_qr3": [fixture_descriptor("2026W18_1A_0516_1", 3, 61159.5, "spherex_qr3")],
        }
    )
    d = client.post(URL, json=body()).json()
    assert [o["collection_id"] for o in d["observations"]] == ["spherex_dr1"]


def test_null_mjd_sorts_last_and_is_not_invented(client, harness):
    harness.search = FakeSearch(
        {"spherex_dr1": [fixture_descriptor("b_1", 1, None), fixture_descriptor("a_1", 1, 5.0)], "spherex_qr3": []}
    )
    d = client.post(URL, json=body()).json()
    assert [o["mjd"] for o in d["observations"]] == [5.0, None]


def test_missing_secret_is_explicit(client, harness):
    from dataclasses import replace

    harness.settings = replace(harness.settings, token_secret=None, token_secret_source="missing")
    assert_error(client.post(URL, json=body()), 503, "SERVICE_MISCONFIGURED")


def test_select_evenly_properties():
    items = [{"i": i} for i in range(10)]
    assert select_evenly(items, 20) == items
    assert select_evenly(items, 1) == [items[0]]
    picked = select_evenly(items, 4)
    assert picked[0] == items[0] and picked[-1] == items[-1] and len(picked) == 4


# ---------------------------------------------------------------------------
# Backend next pass B4: the guidance describes the real search (coverage of the
# query position, evenly spaced sample, limit up to 48); FOV does not narrow it.


def _many(n=40):
    return [fixture_descriptor(f"2026W18_1A_{i:04d}_1", 2, 61000.0 + i) for i in range(n)]


def test_subset_warning_describes_the_sample_not_a_narrower_search(client, harness):
    harness.search = FakeSearch({"spherex_dr1": _many(), "spherex_qr3": []})
    d = client.post(URL, json=body(limit=5)).json()
    assert d["status"] == "ready" and d["truncated"] is True and d["total_matches"] == 40
    w = [x for x in d["warnings"] if x.startswith("Showing 5 of 40")]
    assert len(w) == 1
    assert "evenly spaced in time from the earliest to the latest" in w[0]
    assert "Raising the limit (up to 48) shows more" in w[0]
    assert "the field of view sets the cutout size, not which images match" in w[0]
    for misleading in ("Narrow", "narrow", "smaller field"):
        assert all(misleading not in x for x in d["warnings"]), misleading


def test_capped_warning_does_not_suggest_a_smaller_field(client, harness):
    harness.search = FakeSearch(
        {"spherex_dr1": CollectionResult("spherex_dr1", _many(3), overflow=True), "spherex_qr3": []}
    )
    d = client.post(URL, json=body()).json()
    assert d["status"] == "partial" and d["total_matches"] is None and d["truncated"] is True
    capped = [x for x in d["warnings"] if "maximum number of records" in x]
    assert len(capped) == 1 and "not which images match" in capped[0]
    assert all("smaller field" not in x and "Narrow" not in x for x in d["warnings"])


def test_fov_does_not_change_which_observations_are_returned(client, harness):
    harness.search = FakeSearch({"spherex_dr1": _many(), "spherex_qr3": []})
    a = client.post(URL, json=body(fov_arcmin=2, limit=7)).json()
    b = client.post(URL, json=body(fov_arcmin=10, limit=7)).json()
    c = client.post(URL, json=body(fov_arcmin=10, limit=7)).json()
    ids = lambda d: [o["observation_id"] for o in d["observations"]]  # noqa: E731
    assert ids(a) == ids(b) == ids(c)  # deterministic, FOV-independent sample
    assert a["total_matches"] == b["total_matches"] == 40
    assert ids(a)[0] == "2026W18_1A_0000_1" and ids(a)[-1] == "2026W18_1A_0039_1"  # first and last kept
    assert a["query"]["fov_arcmin"] == 2 and b["query"]["fov_arcmin"] == 10


def test_archive_query_position_is_independent_of_fov():
    import asyncio

    import httpx

    from backend.routes import _archive

    from .test_platform_protocol import VOTABLE

    seen = []

    def handler(request):
        seen.append(sorted(request.url.params.multi_items()))
        return httpx.Response(200, content=VOTABLE, headers={"content-type": "text/xml"})

    async def run(fov):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await _archive.irsa_search_collection(
                client, ra_deg=83.822, dec_deg=-5.391, fov_arcmin=fov, collection_id="spherex_dr1", deadline_s=10
            )

    asyncio.run(run(2.0))
    asyncio.run(run(10.0))
    assert len(seen) == 2 and seen[0] == seen[1]
    pos = dict(seen[0])["POS"]
    assert pos == f"CIRCLE 83.822 -5.391 {_archive.SEARCH_RADIUS_DEG}"
