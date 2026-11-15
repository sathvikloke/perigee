"""The Cloudflare export must equal what the FastAPI app serves.

Builds the bundle into a temporary directory with cloudflare/build.py and
compares every exported catalog document and asset against the real FastAPI
app (``backend.main:app``) through ``TestClient``. It also records FastAPI's
behaviour for a table of normal and hostile requests into
``cloudflare/build/route-expectations.json`` (when that build exists), which
the Worker tests (cloudflare/test/worker.test.mjs) replay against the Worker.

Run from the repository root with backend/requirements-dev.txt installed and
frontend/dist built::

    .venv/bin/python -m pytest -q cloudflare/tests
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / "frontend" / "dist"
DEFAULT_BUILD = REPO / "cloudflare" / "build"

spec = importlib.util.spec_from_file_location("perigee_cf_build", REPO / "cloudflare" / "build.py")
cf_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf_build)

from backend.main import app  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (DIST / "index.html").is_file() or not (DIST / "demo/perigee-demo.pdf").is_file(),
    reason="frontend/dist not built (cd frontend && npm run build)",
)

# (method, path) pairs replayed against FastAPI here and against the Worker in Node.
ROUTE_CASES = [
    ("GET", "/api/v1/presets"),
    ("GET", "/api/v1/presets?x=1&case_id=fair_comparison"),
    ("HEAD", "/api/v1/presets"),
    ("POST", "/api/v1/presets"),
    ("DELETE", "/api/v1/presets"),
    ("GET", "/api/v1/presets/"),
    ("GET", "/api"),
    ("GET", "/api/"),
    ("GET", "/api/v1"),
    ("GET", "/api/v1/"),
    ("GET", "/api/v2/presets"),
    ("GET", "/api/v1/cases/fair_comparison"),
    ("GET", "/api/v1/cases/moving_neighbor"),
    ("GET", "/api/v1/cases/wise_0855_quality_trap"),
    ("GET", "/api/v1/cases/fair%5Fcomparison"),
    ("GET", "/api/v1/cases/nope"),
    ("GET", "/api/v1/cases/"),
    ("GET", "/api/v1/cases/__proto__"),
    ("GET", "/api/v1/cases/constructor"),
    ("GET", "/api/v1/cases/..%2Fpresets"),
    ("GET", "/api/v1/cases/fair_comparison/extra"),
    ("GET", "/api/v1/presets/epsilon_indi_b/frames"),
    ("GET", "/api/v1/presets/barnards_star/frames"),
    ("GET", "/api/v1/presets/wise_0855/frames"),
    ("GET", "/api/v1/presets/rw_aurigae/frames"),
    ("GET", "/api/v1/presets/r_draconis/frames"),
    ("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id=fair_comparison"),
    ("GET", "/api/v1/presets/barnards_star/frames?case_id=moving_neighbor"),
    ("GET", "/api/v1/presets/wise_0855/frames?case_id=wise_0855_quality_trap"),
    ("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id=moving_neighbor"),
    ("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id="),
    ("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id=zzz&case_id=fair_comparison"),
    ("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id=fair_comparison&case_id=zzz"),
    ("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id=__proto__"),
    ("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id=..%2F..%2Fcases%2Ffair_comparison"),
    ("GET", "/api/v1/presets/r_draconis/frames?case_id=fair_comparison"),
    ("GET", "/api/v1/presets/nope/frames"),
    ("GET", "/api/v1/presets/__proto__/frames"),
    ("GET", "/api/v1/presets/epsilon_indi_b"),
    ("GET", "/api/v1/presets/epsilon_indi_b/frames/"),
    ("POST", "/api/v1/presets/epsilon_indi_b/frames"),
    ("GET", "/api/v1/assets/nope.png"),
    ("GET", "/api/v1/assets/__proto__"),
    ("GET", "/api/v1/assets/..%2F..%2Fmain.py"),
    ("GET", "/api/v1/assets/..%252F..%252Fmain.py"),
    ("GET", "/api/v1/assets/%2e%2e%2fbackend%2fmain.py"),
    ("GET", "/api/v1/assets/x%00.png"),
    ("GET", "/api/v1/assets/%E0%A4%A"),
    ("GET", "/api/v1/assets/a/b.png"),
    ("POST", "/api/v1/assets/nope.png"),
    ("GET", "/api/__perigee/catalog-manifest.json"),
    ("GET", "/api/v1/presets.json"),
    ("GET", "/api/v1/cases/fair_comparison.json"),
    ("GET", "/api/v1/search"),
    ("PUT", "/api/v1/frame"),
    ("GET", "/api/v1/frame"),
    ("HEAD", "/api/v1/health"),
    ("POST", "/api/v1/health"),
    ("GET", "/api/v1/health/"),
    ("GET", "/api/v1/search/"),
]


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("cf") / "build"
    info = cf_build._build_into(out, DIST, REPO / "backend" / "content")
    manifest = json.loads((out / "public" / cf_build.MANIFEST_REL).read_text(encoding="utf-8"))
    return out, info, manifest


@pytest.fixture(scope="session")
def client():
    return TestClient(app, follow_redirects=False)


def _doc(out: Path, rel: str):
    return json.loads((out / "public" / rel).read_text(encoding="utf-8"))


def test_counts_and_frontend_copied(built):
    out, info, manifest = built
    assert info["counts"]["presets"] == 5
    assert info["counts"]["cases"] == 3
    assert (out / "public" / "index.html").read_bytes() == (DIST / "index.html").read_bytes()
    assert (out / "public" / "demo/perigee-demo.pdf").read_bytes() == (DIST / "demo/perigee-demo.pdf").read_bytes()
    assert not list((out / "public").rglob("*.fits*")), "raw FITS must never be exported"


def test_presets_document_matches_api(built, client):
    out, _, manifest = built
    assert _doc(out, manifest["presets_document"]) == client.get("/api/v1/presets").json()


def test_cases_match_api(built, client):
    out, _, manifest = built
    assert sorted(manifest["cases"]) == ["fair_comparison", "moving_neighbor", "wise_0855_quality_trap"]
    for cid, rel in manifest["cases"].items():
        assert _doc(out, rel) == client.get(f"/api/v1/cases/{cid}").json()


def test_frames_and_case_frames_match_api(built, client):
    out, _, manifest = built
    assert len(manifest["presets"]) == 5
    for pid, p in manifest["presets"].items():
        assert _doc(out, p["frames"]) == client.get(f"/api/v1/presets/{pid}/frames").json()
        for cid, rel in p["cases"].items():
            r = client.get(f"/api/v1/presets/{pid}/frames", params={"case_id": cid})
            assert r.status_code == 200 and _doc(out, rel) == r.json()
    assert set(manifest["presets"]["epsilon_indi_b"]["cases"]) == {"fair_comparison"}
    assert set(manifest["presets"]["barnards_star"]["cases"]) == {"moving_neighbor"}
    assert set(manifest["presets"]["wise_0855"]["cases"]) == {"wise_0855_quality_trap"}


def test_every_asset_matches_api_bytes_hash_and_type(built, client):
    out, _, manifest = built
    assert len(manifest["assets"]) > 500
    for aid, a in manifest["assets"].items():
        data = (out / "public" / a["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == a["sha256"]
        r = client.get(f"/api/v1/assets/{aid}")
        assert r.status_code == 200 and r.content == data, aid
        assert r.headers["content-type"].split(";")[0] == a["media_type"]
        assert r.headers["etag"] == f'"{a["sha256"]}"'
        assert ("immutable" in r.headers["cache-control"]) == a["canonical"]


def test_wise_0855_label_is_corrected_in_export(built):
    out, _, manifest = built
    frames = _doc(out, manifest["presets"]["wise_0855"]["frames"])["frames"]
    assert len(frames) == 34
    assert all("Kirkpatrick et al. 2021, 20 pc census" in f["marker"]["source"] for f in frames)
    assert not any("CatWISE2020 (2021ApJS" in f["marker"]["source"] for f in frames)


def test_record_route_expectations_for_worker(client):
    """FastAPI's answers for ROUTE_CASES; replayed against the Worker in Node."""
    rows = []
    for method, path in ROUTE_CASES:
        r = client.request(method, path)
        ctype = (r.headers.get("content-type") or "").split(";")[0] or None
        code = None
        if ctype == "application/json" and r.content:
            body = r.json()
            code = body.get("error", {}).get("code") if isinstance(body, dict) else None
        loc = r.headers.get("location")
        rows.append({
            "method": method,
            "path": path,
            "status": r.status_code,
            "content_type": ctype,
            "error_code": code,
            "location": loc.replace("http://testserver", "") if loc else None,
        })
    # Sanity: the catalog is never answered with the SPA's HTML.
    assert all(row["content_type"] != "text/html" for row in rows)
    if DEFAULT_BUILD.is_dir():
        (DEFAULT_BUILD / "route-expectations.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
