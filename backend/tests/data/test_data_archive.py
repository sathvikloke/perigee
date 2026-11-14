"""Search and cutout retrieval with a fake HTTP layer (no network)."""
import pytest
from conftest import BARNARD_URL

from data import (
    HttpResponse,
    ObservationDescriptor,
    SearchQuery,
    UnsupportedData,
    UpstreamTimeout,
    UpstreamUnavailable,
    fetch_cutout,
    search_observations,
)
from data.archive import cutout_url, select_spread

EMPTY_VOTABLE = b"""<?xml version="1.0"?><VOTABLE version="1.4" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
<RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK"/><TABLE>
<FIELD name="obs_id" datatype="char" arraysize="*"/><FIELD name="access_url" datatype="char" arraysize="*"/>
<DATA><TABLEDATA></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>"""
HTML = b"<!DOCTYPE html><html><body>Scheduled maintenance</body></html>"


class FakeHttp:
    """Answers by collection name found in the URL. Records every call."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, url, *, timeout, max_bytes):
        self.calls.append(url)
        for key, ans in self.answers.items():
            if key in url:
                if isinstance(ans, Exception):
                    raise ans
                return ans
        raise AssertionError(f"unexpected URL {url}")


def ok(body):
    return HttpResponse(200, "text/xml", body, "https://irsa.ipac.caltech.edu/SIA")


def no_sleep(_):
    pass


def test_ready_search_parses_real_response(sia_bytes):
    http = FakeHttp({"spherex_qr3": ok(sia_bytes)})
    r = search_observations(SearchQuery.validated(269.45, 4.77, collection_ids=["spherex_qr3"]), http_get=http, sleep=no_sleep)
    assert r.status == "ready" and r.returned_count == 6 and r.total_matches == 6 and not r.truncated
    mjds = [o.mjd for o in r.observations]
    assert mjds == sorted(mjds)
    o = r.observations[0]
    assert o.frame_key == f"{o.observation_id}_D{o.detector}" and "_D" not in o.observation_id
    assert o.source_url.startswith("https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/")
    assert o.observed_at_utc.endswith("Z") and o.band_min_um < o.band_max_um
    d = r.to_dict()
    assert set(d["observations"][0]) == {"observation_id", "collection_id", "observed_at_utc", "mjd", "detector", "frame_key", "source_url"}
    assert d["collections_queried"][0]["status"] == "ok"


def test_empty_is_a_successful_query_with_no_rows():
    http = FakeHttp({"spherex_dr1": ok(EMPTY_VOTABLE), "spherex_qr3": ok(EMPTY_VOTABLE)})
    r = search_observations(SearchQuery.validated(10, 10), http_get=http, sleep=no_sleep)
    assert r.status == "empty" and r.returned_count == 0 and r.total_matches == 0


def test_one_collection_down_gives_partial_with_scope(sia_bytes):
    http = FakeHttp({"spherex_dr1": UpstreamUnavailable("503", details={"status": 503}), "spherex_qr3": ok(sia_bytes)})
    r = search_observations(SearchQuery.validated(269.45, 4.77), http_get=http, sleep=no_sleep)
    assert r.status == "partial" and r.returned_count == 6
    failed = [c for c in r.collections_queried if c.status == "failed"]
    assert [c.collection_id for c in failed] == ["spherex_dr1"]
    assert any("spherex_dr1" in w for w in r.warnings)


def test_html_page_with_200_is_a_failure_not_an_empty_table(sia_bytes):
    http = FakeHttp({"spherex_dr1": ok(HTML), "spherex_qr3": ok(sia_bytes)})
    r = search_observations(SearchQuery.validated(269.45, 4.77), http_get=http, sleep=no_sleep)
    assert r.status == "partial"


def test_all_collections_down_raises_instead_of_empty():
    http = FakeHttp({"spherex_dr1": UpstreamTimeout("t"), "spherex_qr3": UpstreamTimeout("t")})
    with pytest.raises(UpstreamTimeout):
        search_observations(SearchQuery.validated(10, 10), http_get=http, sleep=no_sleep)


def test_failure_plus_zero_rows_is_not_called_empty():
    http = FakeHttp({"spherex_dr1": UpstreamUnavailable("x"), "spherex_qr3": ok(EMPTY_VOTABLE)})
    with pytest.raises(UpstreamUnavailable):
        search_observations(SearchQuery.validated(10, 10), http_get=http, sleep=no_sleep)


def test_overflow_reported_as_partial_with_unknown_total(sia_bytes):
    body = sia_bytes.replace(b'name="QUERY_STATUS" value="OK"', b'name="QUERY_STATUS" value="OVERFLOW"')
    http = FakeHttp({"spherex_qr3": ok(body)})
    r = search_observations(SearchQuery.validated(269.45, 4.77, collection_ids=["spherex_qr3"]), http_get=http, sleep=no_sleep)
    assert r.status == "partial" and r.truncated and r.total_matches is None


def test_retries_are_bounded(sia_bytes):
    http = FakeHttp({"spherex_dr1": UpstreamUnavailable("503"), "spherex_qr3": ok(sia_bytes)})
    search_observations(SearchQuery.validated(269.45, 4.77), http_get=http, sleep=no_sleep)
    assert sum("spherex_dr1" in c for c in http.calls) == 4  # SEARCH_ATTEMPTS, then give up


def test_retries_stop_at_the_deadline():
    from data.archive import _with_retries

    calls, now = [], [0.0]

    def fail():
        calls.append(1)
        raise UpstreamUnavailable("502")

    def fake_sleep(s):
        now[0] += s

    with pytest.raises(UpstreamUnavailable):
        _with_retries(fail, attempts=10, backoff_s=1.0, sleep=fake_sleep, deadline=2.5, clock=lambda: now[0])
    assert len(calls) == 2  # waits 1 s, then a 2 s wait would cross the 2.5 s deadline


def test_non_retryable_errors_are_not_retried():
    from data.archive import _non_retryable, _with_retries

    calls = []

    def fail():
        calls.append(1)
        raise _non_retryable(404)

    with pytest.raises(UpstreamUnavailable):
        _with_retries(fail, attempts=4, backoff_s=0, sleep=no_sleep)
    assert len(calls) == 1


def test_limit_spreads_across_time(sia_bytes):
    http = FakeHttp({"spherex_qr3": ok(sia_bytes)})
    r = search_observations(SearchQuery.validated(269.45, 4.77, limit=3, collection_ids=["spherex_qr3"]), http_get=http, sleep=no_sleep)
    assert r.returned_count == 3 and r.total_matches == 6 and r.truncated and r.status == "ready"
    assert select_spread(list(range(10)), 4) == [0, 3, 6, 9]


def obs(url=BARNARD_URL, collection="spherex_dr1"):
    return ObservationDescriptor("2025W34_2B_0557_4", collection, None, None, 2, url)


def test_cutout_url_only_for_allowlisted_sources():
    u = cutout_url(BARNARD_URL, 269.4, 4.7, 0.1)
    assert u.startswith(BARNARD_URL + "?center=269.40000000%2C4.70000000&size=")
    for bad in ("https://evil.example/level2.fits", BARNARD_URL.replace("https://", "http://"), BARNARD_URL + "/../../x.fits", "file:///etc/passwd"):
        with pytest.raises(UnsupportedData):
            cutout_url(bad, 269.4, 4.7, 0.1)


def test_collection_must_match_the_file_release():
    with pytest.raises(UnsupportedData):
        fetch_cutout(obs(collection="spherex_qr3"), 269.4, 4.7, 6, http_get=FakeHttp({}), sleep=no_sleep)


def test_valid_cutout(barnard_bytes):
    http = FakeHttp({"level2_": HttpResponse(200, "image/fits", barnard_bytes, BARNARD_URL)})
    c = fetch_cutout(obs(), 269.4, 4.7, 6, http_get=http, sleep=no_sleep)
    assert c.data == barnard_bytes and len(c.sha256) == 64 and "size=0.15000" in c.url


def test_html_error_page_is_not_parsed_as_fits():
    http = FakeHttp({"level2_": HttpResponse(200, "text/html", HTML, BARNARD_URL)})
    with pytest.raises(UpstreamUnavailable):
        fetch_cutout(obs(), 269.4, 4.7, 6, http_get=http, sleep=no_sleep)


def test_truncated_fits_fails_clearly(barnard_bytes):
    http = FakeHttp({"level2_": HttpResponse(200, "image/fits", barnard_bytes[:10000], BARNARD_URL)})
    with pytest.raises(UnsupportedData):
        fetch_cutout(obs(), 269.4, 4.7, 6, http_get=http, sleep=no_sleep)


def test_503_retried_then_reported_retryable():
    http = FakeHttp({"level2_": UpstreamUnavailable("503", details={"status": 503})})
    with pytest.raises(UpstreamUnavailable) as e:
        fetch_cutout(obs(), 269.4, 4.7, 6, http_get=http, sleep=no_sleep)
    assert e.value.retryable and len(http.calls) == 2


def test_descriptor_round_trip_and_tampering():
    o = obs()
    pub = o.public_dict()
    assert ObservationDescriptor.from_public_dict(pub) == o
    assert ObservationDescriptor.from_public_dict({**pub, "frame_key": "ignored"}).frame_key == "2025W34_2B_0557_4_D2"
    for bad in ({**o.public_dict(), "source_url": "https://evil.example/x.fits"},
                {**o.public_dict(), "collection_id": "spherex_qr3"},
                {**o.public_dict(), "collection_id": "anything"},
                "not a dict"):
        with pytest.raises(UnsupportedData):
            ObservationDescriptor.from_public_dict(bad)
