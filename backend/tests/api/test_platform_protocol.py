"""Health, JSON errors on unknown /api routes, request IDs, tokens, settings, VOTable parsing."""

from __future__ import annotations

import pytest

from backend.routes._archive import mjd_to_iso, parse_votable, rows_to_descriptors
from backend.security import config
from backend.security.tokens import ExpiredToken, InvalidToken, issue_token, verify_token
from backend.security.upstream import UpstreamUnavailable, is_allowed_source_url

SECRET = b"k" * 40


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    d = r.json()
    assert d["schema_version"] == 1 and d["status"] == "ok"
    assert d["capabilities"]["search"] is True and d["capabilities"]["frame"] is True
    assert "secret" not in r.text.lower().replace("token_signing", "")


@pytest.mark.parametrize(
    "method,path",
    [("GET", "/api/v1/nope"), ("GET", "/api/v1/"), ("GET", "/api/whatever"), ("POST", "/api/v1/jobs/1"), ("GET", "/api/v1/search")],
)
def test_unknown_api_routes_are_json(client, method, path):
    r = client.request(method, path)
    assert r.status_code in (404, 405)
    assert r.headers["content-type"].startswith("application/json")
    assert "<html" not in r.text.lower()
    assert r.json()["error"]["code"] in ("NOT_FOUND", "METHOD_NOT_ALLOWED")


def test_request_id_header_echo(client):
    r = client.get("/api/v1/health", headers={"X-Request-ID": "client-abc-1"})
    assert r.headers["x-request-id"] == "client-abc-1" == r.json()["request_id"]
    r = client.get("/api/v1/health", headers={"X-Request-ID": "<script>"})
    assert r.headers["x-request-id"] != "<script>"


# ------------------------------------------------------------------ tokens


def _issue(**kw):
    base = dict(
        source_url="https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/W/v/3/x.fits",
        observation_id="o",
        detector=3,
        collection_id="spherex_dr1",
        frame_key="o_D3",
        mjd=1.0,
        observed_at_utc=None,
        ra_deg=1.0,
        dec_deg=2.0,
        fov_arcmin=6.0,
        ttl_s=100,
        now=1000,
    )
    base.update(kw)
    return issue_token(SECRET, **base)


def test_token_roundtrip_and_expiry_boundary():
    tok, exp = _issue()
    assert exp == 1100
    c = verify_token(SECRET, tok, now=1099)
    assert (c.ra_deg, c.dec_deg, c.fov_arcmin, c.detector) == (1.0, 2.0, 6.0, 3)
    with pytest.raises(ExpiredToken):
        verify_token(SECRET, tok, now=1100)


def test_token_flip_any_signature_char():
    tok, _ = _issue()
    prefix, body, sig = tok.split(".")
    flipped = sig[:-2] + ("A" if sig[-2] != "A" else "B") + sig[-1]
    with pytest.raises(InvalidToken):
        verify_token(SECRET, f"{prefix}.{body}.{flipped}", now=1000)


# ------------------------------------------------------------------ settings


def test_dev_secret_never_in_production(monkeypatch):
    monkeypatch.delenv("PERIGEE_TOKEN_SECRET", raising=False)
    monkeypatch.setenv("PERIGEE_DEV_MODE", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")
    s = config.load_settings()
    assert s.token_secret is None and s.token_secret_source == "missing"
    monkeypatch.setenv("VERCEL_ENV", "preview")
    assert config.load_settings().token_secret_source == "dev_fallback"
    monkeypatch.delenv("PERIGEE_DEV_MODE")
    assert config.load_settings().token_secret is None


def test_short_secret_refused(monkeypatch):
    monkeypatch.delenv("PERIGEE_DEV_MODE", raising=False)
    monkeypatch.setenv("PERIGEE_TOKEN_SECRET", "short")
    s = config.load_settings()
    assert s.token_secret is None and s.token_secret_source == "too_short"
    monkeypatch.setenv("PERIGEE_TOKEN_SECRET", "x" * 32)
    assert config.load_settings().token_secret_source == "env"


# ------------------------------------------------------------------ allowlist


@pytest.mark.parametrize(
    "url,ok",
    [
        ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W18_1B/l2b-v27-2026-196/6/level2_2025W18_1B_0081_1D6_spx_l2b-v27-2026-196.fits", True),
        ("https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/2026W39_2A/l2b-v27-2026-271/3/level2_x.fits", True),
        ("http://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/a.fits", False),
        ("https://irsa.ipac.caltech.edu.evil.com/ibe/data/spherex/dr1/level2/a.fits", False),
        ("https://user@irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/a.fits", False),
        ("https://irsa.ipac.caltech.edu:8443/ibe/data/spherex/dr1/level2/a.fits", False),
        ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/../../../etc.fits", False),
        ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/a.fits?center=1,2", False),
        ("https://irsa.ipac.caltech.edu/ibe/data/wise/allwise/a.fits", False),
        ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1_deep/level2/a.fits", False),
        ("file:///etc/passwd", False),
    ],
)
def test_source_allowlist(url, ok):
    assert is_allowed_source_url(url) is ok


# ------------------------------------------------------------------ VOTable parsing

# Derived fixture: two rows in the shape of a real IRSA SIA v2 SPHEREx response
# (fields trimmed); values copied from research/build_data/metadata (not a live result).
VOTABLE = b"""<?xml version="1.0" encoding="utf-8"?>
<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
 <RESOURCE type="results">
  <INFO name="QUERY_STATUS" value="OK"/>
  <TABLE>
   <FIELD name="obs_id" datatype="char" arraysize="*"/>
   <FIELD name="access_url" datatype="char" arraysize="*"/>
   <FIELD name="energy_bandpassname" datatype="char" arraysize="*"/>
   <FIELD name="obs_publisher_did" datatype="char" arraysize="*"/>
   <FIELD name="t_min" datatype="double"/>
   <FIELD name="em_min" datatype="double"/>
   <FIELD name="em_max" datatype="double"/>
   <FIELD name="obs_collection" datatype="char" arraysize="*"/>
   <FIELD name="dataproduct_type" datatype="char" arraysize="*"/>
   <DATA><TABLEDATA>
    <TR><TD>2025W18_1B_0081_1</TD><TD>https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W18_1B/l2b-v27-2026-196/6/level2_2025W18_1B_0081_1D6_spx_l2b-v27-2026-196.fits</TD><TD>SPHEREx-D6</TD><TD>ivo://irsa.ipac/spherex_dr1?2025W18_1B_0081_1/D6</TD><TD>60794.063320</TD><TD>4.41150e-06</TD><TD>5.00960e-06</TD><TD>spherex_dr1</TD><TD>image</TD></TR>
    <TR><TD>bad</TD><TD>https://evil.example/x.fits</TD><TD></TD><TD></TD><TD></TD><TD></TD><TD></TD><TD>spherex_dr1</TD><TD>image</TD></TR>
   </TABLEDATA></DATA>
  </TABLE>
 </RESOURCE>
</VOTABLE>"""


def test_votable_to_descriptors():
    rows, overflow = parse_votable(VOTABLE)
    assert len(rows) == 2 and overflow is False
    descs, skipped = rows_to_descriptors(rows, "spherex_dr1")
    assert skipped == 1
    (d,) = descs
    assert d["frame_key"] == "2025W18_1B_0081_1_D6" and d["detector"] == 6
    assert d["mjd"] == 60794.06332 and d["time_basis"] == "sia_t_min"
    assert d["observed_at_utc"].startswith("2025-04-29T01:31")
    assert d["detector_wavelength_range_um"] == [4.4115, 5.0096]


def test_votable_error_and_overflow():
    err = VOTABLE.replace(b'value="OK"', b'value="ERROR"')
    with pytest.raises(UpstreamUnavailable):
        parse_votable(err)
    _, overflow = parse_votable(VOTABLE.replace(b'value="OK"', b'value="OVERFLOW"'))
    assert overflow is True
    with pytest.raises(UpstreamUnavailable):
        parse_votable(b"<html><body>502 Proxy Error</body></html>")
    with pytest.raises(UpstreamUnavailable):
        parse_votable(b"not xml")


def _run_sia(responses):
    import asyncio

    import httpx

    from backend.routes import _archive

    seen = []

    def handler(req):
        seen.append(req)
        return responses[min(len(seen) - 1, len(responses) - 1)]

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await _archive.irsa_search_collection(
                c, ra_deg=330.84, dec_deg=-56.786, fov_arcmin=6, collection_id="spherex_dr1", deadline_s=10
            )

    return asyncio.run(go()), seen


def test_sia_retries_transient_502_then_succeeds(monkeypatch):
    import httpx

    from backend.routes import _archive

    monkeypatch.setattr(_archive, "SIA_RETRY_BACKOFF_S", 0.0)
    html502 = httpx.Response(502, text="<html>Proxy Error</html>", headers={"content-type": "text/html"})
    ok = httpx.Response(200, content=VOTABLE, headers={"content-type": "application/x-votable+xml"})
    result, seen = _run_sia([html502, html502, ok])
    assert len(seen) == 3 and len(result.descriptors) == 1
    q = seen[0].url.params
    assert q["COLLECTION"] == "spherex_dr1" and q["POS"] == "CIRCLE 330.84 -56.786 0.001"
    assert seen[0].url.host == "irsa.ipac.caltech.edu" and seen[0].url.path == "/SIA"


def test_sia_gives_up_after_bounded_attempts(monkeypatch):
    import httpx

    from backend.routes import _archive

    monkeypatch.setattr(_archive, "SIA_RETRY_BACKOFF_S", 0.0)
    html200 = httpx.Response(200, text="<!DOCTYPE html><html>err</html>", headers={"content-type": "text/html"})
    with pytest.raises(UpstreamUnavailable) as ei:
        _run_sia([html200])
    assert ei.value.attempts == _archive.SIA_MAX_ATTEMPTS
    # non-transient (400) is not retried
    with pytest.raises(UpstreamUnavailable) as ei:
        _run_sia([httpx.Response(400, text="bad")])
    assert ei.value.attempts == 1


def test_mjd_to_iso():
    assert mjd_to_iso(51544.5) == "2000-01-01T12:00:00.000Z"
    assert mjd_to_iso(None) is None and mjd_to_iso(float("nan")) is None
