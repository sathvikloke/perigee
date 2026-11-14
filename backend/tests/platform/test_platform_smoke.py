"""Offline checks for the deployed-release smoke script (no network).

The script's value is telling an access restriction apart from an app defect,
and never accepting SPA HTML at an API route. Both are tested with a fake host.
"""

from __future__ import annotations

import httpx

from backend.platform import smoke

SPA = '<!doctype html><html><body><div id="root"></div></body></html>'


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_vercel_authentication_redirect_is_access_not_defect():
    def handler(req):
        return httpx.Response(302, headers={"location": "https://vercel.com/sso-api?url=x"})

    res = smoke.Results()
    with _client(handler) as c:
        assert smoke.check_access(res, c, "https://example.test") is False
    assert "Vercel Authentication" in res.rows[0][2]


def test_spa_html_at_api_route_fails_json_404_check():
    def handler(req):  # misordered rewrites: everything gets index.html
        return httpx.Response(200, text=SPA, headers={"content-type": "text/html"})

    res = smoke.Results()
    with _client(handler) as c:
        smoke.check_routing(res, c, "https://example.test")
        smoke.check_health(res, c, "https://example.test")
    assert all(status == "FAIL" for _, status, _ in res.rows)
    assert "SPA HTML swallowed" in res.rows[0][2]


def test_dev_fallback_signing_is_reported_as_failure():
    def handler(req):
        body = {"status": "ok", "capabilities": {"token_signing": "dev_fallback"}}
        return httpx.Response(200, json=body)

    res = smoke.Results()
    with _client(handler) as c:
        smoke.check_health(res, c, "https://example.test")
    by_name = {n: s for n, s, _ in res.rows}
    assert by_name["health token signing from env secret"] == "FAIL"


def test_refuses_unrelated_perigee_vercel_app():
    assert smoke.main(["--base", "https://perigee.vercel.app", "--no-live"]) == 1
