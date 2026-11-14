"""Offline checks for the deployed-release smoke script (no network).

The script's value is telling an access restriction apart from an app defect,
never accepting SPA HTML at an API route, and never passing without actually
exercising the live frame path. All tested with a fake host (httpx.MockTransport).
"""

from __future__ import annotations

import base64
import io
import json

import httpx
import pytest
from PIL import Image

from backend.platform import smoke

SPA = '<!doctype html><html><body><div id="root"></div></body></html>'
BASE = "https://perigee-test.vercel.app"


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def _session(handler, secret: str | None = None) -> smoke.Session:
    return smoke.Session(_client(handler), BASE, secret)


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("LA", (4, 3), (128, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _status(res: smoke.Results) -> dict[str, str]:
    return {n: s for n, s, _ in res.rows}


# ------------------------------------------------------------------ Suhrit's original checks


def test_vercel_authentication_redirect_is_access_not_defect():
    def handler(req):
        return httpx.Response(302, headers={"location": "https://vercel.com/sso-api?url=x"})

    res = smoke.Results()
    assert smoke.check_access(res, _session(handler)) is False
    assert "Vercel Authentication" in res.rows[0][2]


def test_spa_html_at_api_route_fails_json_404_check():
    def handler(req):  # misordered rewrites: everything gets index.html
        return httpx.Response(200, text=SPA, headers={"content-type": "text/html"})

    res = smoke.Results()
    s = _session(handler)
    smoke.check_routing(res, s)
    smoke.check_health(res, s)
    assert all(status == "FAIL" for _, status, _ in res.rows)
    assert "SPA HTML swallowed" in res.rows[0][2]


def test_dev_fallback_signing_is_reported_as_failure():
    def handler(req):
        return httpx.Response(200, json={"status": "ok", "capabilities": {"token_signing": "dev_fallback"}})

    res = smoke.Results()
    smoke.check_health(res, _session(handler))
    assert _status(res)["health token signing from env secret"] == "FAIL"


def test_refuses_unrelated_perigee_vercel_app():
    assert smoke.main(["--base", "https://perigee.vercel.app", "--no-live"]) == 1


# ------------------------------------------------------------------ live path must really run


def _live_handler(search_body, frame_body=None, frame_status=200):
    def handler(req):
        if req.url.path == "/api/v1/search":
            return httpx.Response(200, json=search_body)
        if req.url.path == "/api/v1/frame":
            return httpx.Response(frame_status, json=frame_body or {})
        return httpx.Response(404, json={})

    return handler


def _search(observations):
    q = smoke.NON_PRESET_QUERY
    return {"status": "ready", "query": {"ra_deg": q["ra_deg"], "dec_deg": q["dec_deg"]},
            "observations": observations, "total_matches": len(observations), "collections_queried": ["spherex_dr1"]}


def _frame(src):
    return {"frame": {"observation_id": "2025W36_2B_0338_1", "frame_key": "2025W36_2B_0338_1_D2",
                      "quality": {"status": "clear"}, "wavelength_um": 1.5, "image": {"src": src}}}


OBS = [{"observation_id": "2025W36_2B_0338_1", "frame_token": "tok"}]


def test_empty_search_is_a_failure_not_a_silent_pass():
    res = smoke.Results()
    smoke.check_live(res, _session(_live_handler(_search([]))))
    st = _status(res)
    assert st["live non-preset /search"] == "FAIL"
    assert st["live /frame"] == "FAIL" and "not attempted" in res.rows[-1][2]


def test_observation_without_frame_token_is_not_usable():
    res = smoke.Results()
    smoke.check_live(res, _session(_live_handler(_search([{"observation_id": "x"}]))))
    assert _status(res)["live /frame"] == "FAIL"


def test_live_frame_passes_only_with_a_decodable_png():
    good = "data:image/png;base64," + base64.b64encode(_png()).decode()
    res = smoke.Results()
    smoke.check_live(res, _session(_live_handler(_search(OBS), _frame(good))))
    assert set(_status(res).values()) == {"PASS"}

    for bad in ("data:image/png;base64,iVBORw0KGgoAAAA",  # PNG signature, truncated
                "data:image/png;base64,!!!notbase64",
                "data:image/jpeg;base64," + base64.b64encode(_png()).decode(),
                None):
        res = smoke.Results()
        smoke.check_live(res, _session(_live_handler(_search(OBS), _frame(bad))))
        assert _status(res)["live /frame"] == "FAIL", bad


# ------------------------------------------------------------------ malformed responses and network errors


def test_invalid_json_is_a_fail_row_not_a_crash():
    def handler(req):
        return httpx.Response(200, content=b"{not json", headers={"content-type": "application/json"})

    res = smoke.Results()
    s = _session(handler)
    smoke.check_health(res, s)
    smoke.check_catalog(res, s)
    smoke.check_live(res, s)
    st = _status(res)
    for name in ("health body", "presets body", "live non-preset /search"):
        assert st[name] == "FAIL", name
    assert "PASS" not in {st[n] for n in st if n != "health is JSON" and n != "presets is JSON"}
    assert any("not valid JSON" in ev for _, _, ev in res.rows)


def test_json_array_where_object_expected_fails():
    def handler(req):
        return httpx.Response(200, json=[1, 2, 3])

    res = smoke.Results()
    smoke.check_catalog(res, _session(handler))
    assert _status(res)["presets body"] == "FAIL"


def _patch_client(monkeypatch, handler):
    real = httpx.Client

    def factory(*a, **kw):
        kw["transport"] = httpx.MockTransport(handler)
        return real(*a, **kw)

    monkeypatch.setattr(smoke.httpx, "Client", factory)


def test_unreachable_host_exits_1_with_message(monkeypatch, capsys):
    def handler(req):
        raise httpx.ConnectError("name resolution failed", request=req)

    _patch_client(monkeypatch, handler)
    assert smoke.main(["--base", BASE, "--no-live"]) == 1
    out = capsys.readouterr().out
    assert "network error: ConnectError" in out and "could not be reached" in out


def test_timeout_mid_run_exits_1(monkeypatch, capsys):
    def handler(req):
        if req.url.path in ("/", "/api/v1/health") and req.method == "GET" and not req.url.query:
            if req.url.path == "/":
                return httpx.Response(200, text=SPA, headers={"content-type": "text/html"})
            return httpx.Response(200, json={"status": "ok", "capabilities": {"token_signing": "env"}})
        raise httpx.ReadTimeout("slow", request=req)

    _patch_client(monkeypatch, handler)
    assert smoke.main(["--base", BASE, "--no-live"]) == 1
    assert "ReadTimeout" in capsys.readouterr().out


# ------------------------------------------------------------------ bypass header scope


def test_bypass_header_only_sent_to_deployment_origin():
    seen: list[tuple[str, str | None]] = []

    def handler(req):
        seen.append((req.url.host, req.headers.get("x-vercel-protection-bypass")))
        if req.url.path == "/api/v1/presets":
            return httpx.Response(200, json={"presets": [{"id": p} for p in smoke.PRESET_IDS]})
        if req.url.path == "/api/v1/presets/barnards_star/frames":
            return httpx.Response(200, json={"frames": [{"image": {"src": "https://evil.example/steal.png"}}]})
        return httpx.Response(200, json={"case_id": "fair_comparison", "limitations": ["x"]})

    res = smoke.Results()
    smoke.check_catalog(res, _session(handler, secret="s3cret"))
    assert all(host == "perigee-test.vercel.app" for host, _ in seen), seen
    assert all(h == "s3cret" for _, h in seen)
    assert _status(res)["preset image asset is PNG"] == "FAIL"
    assert "not on the deployment origin" in dict((n, e) for n, _, e in res.rows)["preset image asset is PNG"]


def test_session_never_attaches_bypass_to_other_hosts():
    sent: list[tuple[str, int | None, str | None]] = []

    def handler(req):
        sent.append((req.url.host, req.url.port, req.headers.get("x-vercel-protection-bypass")))
        return httpx.Response(200)

    s = _session(handler, secret="s3cret")
    res = smoke.Results()
    s.request(res, "same", "GET", "/x")
    s.request(res, "abs-same", "GET", BASE + "/y")
    s.request(res, "other", "GET", "https://cdn.example/z.png")
    s.request(res, "port", "GET", "https://perigee-test.vercel.app:8443/z")
    assert [h for _, _, h in sent] == ["s3cret", "s3cret", None, None]  # other host and other port: no header


def test_same_origin_rules():
    assert smoke.same_origin("https://perigee-test.vercel.app:443/a", BASE)
    assert smoke.same_origin("https://PERIGEE-TEST.vercel.app./a", BASE)
    assert not smoke.same_origin("http://perigee-test.vercel.app/a", BASE)
    assert not smoke.same_origin("https://perigee-test.vercel.app:8443/a", BASE)
    assert not smoke.same_origin("https://perigee-test.vercel.app.evil.example/a", BASE)


def test_png_asset_must_decode():
    def handler(req):
        if req.url.path == "/api/v1/presets":
            return httpx.Response(200, json={"presets": [{"id": p} for p in smoke.PRESET_IDS]})
        if req.url.path == "/api/v1/presets/barnards_star/frames":
            return httpx.Response(200, json={"frames": [{"image": {"src": "/api/v1/assets/a.png"}}]})
        if req.url.path == "/api/v1/assets/a.png":
            return httpx.Response(200, content=b"\x89PNG\r\n\x1a\ngarbage", headers={"content-type": "image/png"})
        return httpx.Response(200, json={"case_id": "fair_comparison", "limitations": ["x"]})

    res = smoke.Results()
    smoke.check_catalog(res, _session(handler))
    assert _status(res)["preset image asset is PNG"] == "FAIL"


# ------------------------------------------------------------------ base URL validation


@pytest.mark.parametrize("raw", [
    "https://perigee.vercel.app",
    "https://PERIGEE.Vercel.App",
    "https://perigee.vercel.app.",
    "https://perigee.vercel.app:443",
    "https://perigee.vercel.app./",
    "http://perigee.vercel.app",
    "perigee.vercel.app",
])
def test_unrelated_app_refused_in_every_spelling(raw):
    with pytest.raises(smoke.BaseURLError):
        smoke.validate_base(raw)
    assert smoke.main(["--base", raw, "--no-live"]) == 1


@pytest.mark.parametrize("raw", [
    "http://example.com",               # plain http off loopback
    "ftp://perigee-x.vercel.app",
    "https://user:pw@perigee-x.vercel.app",
    "https://perigee-x.vercel.app/api",  # not an origin
    "https://perigee-x.vercel.app/?q=1",
    "https://perigee-x.vercel.app:99999",
    "https://",
])
def test_bad_base_urls_refused(raw):
    with pytest.raises(smoke.BaseURLError):
        smoke.validate_base(raw)


def test_good_base_urls_normalized():
    assert smoke.validate_base("https://Perigee-git-x-sathviklokes-projects.vercel.app/") == \
        "https://perigee-git-x-sathviklokes-projects.vercel.app"
    assert smoke.validate_base("https://myperigee.vercel.app") == "https://myperigee.vercel.app"
    assert smoke.validate_base("http://127.0.0.1:8095") == "http://127.0.0.1:8095"
    assert smoke.validate_base("http://localhost:8000/") == "http://localhost:8000"
    assert smoke.validate_base("https://perigee-sathviklokes-projects.vercel.app.") == \
        "https://perigee-sathviklokes-projects.vercel.app"


def test_bypass_secret_is_never_printed(monkeypatch, capsys):
    monkeypatch.setenv("VERCEL_AUTOMATION_BYPASS_SECRET", "do-not-print-me")

    def handler(req):
        return httpx.Response(404, json={})

    _patch_client(monkeypatch, handler)
    smoke.main(["--base", BASE, "--bypass", "--no-live"])
    assert "do-not-print-me" not in capsys.readouterr().out


# ------------------------------------------------------------------ CI wiring (PR #36 review)

REPO = __import__("pathlib").Path(__file__).resolve().parents[3]


def _pins(path):
    out = {}
    for line in (REPO / path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "==" in line:
            name, ver = line.split("==", 1)
            out[name.strip().lower()] = ver.strip()
    return out


def test_smoke_requirements_cover_imports_and_match_backend_pins():
    smoke_pins = _pins("backend/platform/requirements-smoke.txt")
    backend_pins = _pins("backend/requirements.txt")
    assert set(smoke_pins) == {"httpx", "pillow"}  # smoke.py imports httpx and PIL (png_problem)
    for name, ver in smoke_pins.items():
        assert backend_pins.get(name) == ver, (name, ver, backend_pins.get(name))


def test_workflows_pin_actions_to_full_shas_and_install_smoke_pins():
    import re

    for wf in ("release-smoke.yml", "deploy-check.yml"):
        text = (REPO / ".github/workflows" / wf).read_text(encoding="utf-8")
        uses = re.findall(r"uses:\s*([^\s#]+)", text)
        assert uses, wf
        for u in uses:
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", u), (wf, u)
        assert "persist-credentials: false" in text, wf
    rs = (REPO / ".github/workflows/release-smoke.yml").read_text(encoding="utf-8")
    assert "requirements-smoke.txt" in rs
    assert "${{ github.event.deployment" not in rs.split("steps:", 1)[1].split("run: |", 1)[1]  # payload only via env
