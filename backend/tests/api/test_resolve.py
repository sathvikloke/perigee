"""Resolver contract and network boundaries, with no live network dependency."""
import httpx
import pytest
import asyncio

from backend.routes._resolver import MAX_RESOLVER_BYTES, SESAME_URL


def xml(name="NAME Barnard's star", ra="269.45207696", dec="4.69336497"):
    return f'<Sesame><Target><Resolver name="Sc=Simbad"><oname>{name}</oname><jradeg>{ra}</jradeg><jdedeg>{dec}</jdedeg><refPos>2020yCat.1350....0G</refPos></Resolver></Target></Sesame>'


def answer(harness, data, status=200, headers=None):
    harness.fetch_handler = lambda req: httpx.Response(status, content=data, headers=headers or {})


def test_barnard_uses_verified_finder_center_and_retains_catalog_epoch(client, harness):
    answer(harness, xml())
    response = client.post('/api/v1/resolve', json={"name": "Barnard’s Star"})
    assert response.status_code == 200
    result = response.json()
    assert result["name"] == "Barnard's Star"
    assert result["catalog_position"]["epoch_jyear"] == 2000
    assert result["search_center"] == {"ra_deg": 269.4462585584787, "dec_deg": 4.768324486236583, "epoch_jyear": 2026.0, "kind": "finder_prediction"}
    assert "not a detection" in result["note"]
    assert response.headers["cache-control"] == "no-store"
    assert result["source"] == "SIMBAD via CDS Sesame"
    assert harness.fetched == [SESAME_URL + "Barnard%27s%20Star"]


def test_epsilon_uses_its_own_propagated_center(client, harness):
    answer(harness, xml("* eps Ind B", "331.04414659", "-56.7828442"))
    r = client.post('/api/v1/resolve', json={"name": "Epsilon Indi B"}).json()
    assert r["search_center"]["ra_deg"] == 331.0966687831005
    assert r["search_center"]["dec_deg"] == -56.80064917516836


@pytest.mark.parametrize("name,ra,dec", [("NAME Barnard's star", "10", "20"), ("another object", "269.45207696", "4.69336497")])
def test_matching_name_or_position_alone_never_substitutes_a_preset(client, harness, name, ra, dec):
    answer(harness, xml(name, ra, dec))
    r = client.post('/api/v1/resolve', json={"name": "Anything"}).json()
    assert r["search_center"]["kind"] == "catalog_position"
    assert r["search_center"]["epoch_jyear"] == 2000
    assert "Moving stars" in r["note"]


def test_no_match_is_distinct_from_service_failure(client, harness):
    answer(harness, '<Sesame><Target><INFO>*** NNNothing found ***</INFO></Target></Sesame>')
    r = client.post('/api/v1/resolve', json={"name": "unknown"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "OBJECT_NOT_FOUND"
    answer(harness, '<Sesame><Target><INFO>Service unavailable</INFO></Target></Sesame>')
    assert client.post('/api/v1/resolve', json={"name": "unknown"}).status_code == 503


@pytest.mark.parametrize("data", ["<html>error</html>", "broken", xml(ra="NaN"), xml(dec="91"), xml(ra="360"), '<!DOCTYPE a [<!ENTITY x "test">]><Sesame>&x;</Sesame>', '<!DOCTYPE a [<!ENTITY x "test">]><Sesame>&x;</Sesame>'.encode("utf-16"), "x" * (MAX_RESOLVER_BYTES + 1)])
def test_rejects_malformed_unsafe_out_of_range_and_oversized_answers(client, harness, data):
    answer(harness, data)
    r = client.post('/api/v1/resolve', json={"name": "Barnard's Star"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"
    assert "broken" not in r.text


def test_fixed_host_encodes_entire_name_and_does_not_follow_redirects(client, harness):
    answer(harness, "", 302, {"location": "http://127.0.0.1/secret"})
    r = client.post('/api/v1/resolve', json={"name": "https://evil.test/a?x=1&other#fragment"})
    assert r.status_code == 503
    assert len(harness.fetched) == 1
    assert harness.fetched[0].startswith(SESAME_URL)
    assert "%26" in harness.fetched[0] and "%23" in harness.fetched[0]


def test_timeout_has_friendly_retryable_envelope(client, harness):
    def fail(req):
        raise httpx.ReadTimeout("private transport details", request=req)
    harness.fetch_handler = fail
    r = client.post('/api/v1/resolve', json={"name": "Barnard's Star"})
    assert r.status_code == 504
    assert r.json()["error"]["retryable"] is True
    assert "private" not in r.text


def test_total_deadline_covers_a_slow_response_body(client, harness, monkeypatch):
    monkeypatch.setattr("backend.routes._resolver.RESOLVER_TIMEOUT_S", 0.01)
    class SlowBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.sleep(0.1)
            yield xml().encode()
    harness.fetch_handler = lambda req: httpx.Response(200, stream=SlowBody())
    r = client.post('/api/v1/resolve', json={"name": "Barnard's Star"})
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "UPSTREAM_TIMEOUT"


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "  "}, {"name": "a" * 81}, {"name": "a\nb"}, {"name": 42}, {"name": "x", "url": "https://evil.test"}])
def test_invalid_requests_never_fetch(client, harness, body):
    assert client.post('/api/v1/resolve', json=body).status_code in (400, 422)
    assert harness.fetched == []
