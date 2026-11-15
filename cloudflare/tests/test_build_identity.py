"""Build identity (B3): identical content gives the same identity; changed frontend or
catalog content is detectable; no timestamps; the source label is honest.

    .venv/bin/python -m pytest -q cloudflare/tests/test_build_identity.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / "frontend" / "dist"
CONTENT = REPO / "backend" / "content"

spec = importlib.util.spec_from_file_location("perigee_cf_build_id", REPO / "cloudflare" / "build.py")
cf_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf_build)

pytestmark = pytest.mark.skipif(
    not (DIST / "index.html").is_file() or not (DIST / "demo/perigee-demo.pdf").is_file(),
    reason="frontend/dist not built (cd frontend && npm run build)",
)


def _identity(out: Path, dist: Path = DIST, content: Path = CONTENT) -> dict:
    cf_build._build_into(out, dist, content)
    public_doc = json.loads((out / "public" / cf_build.IDENTITY_REL).read_text(encoding="utf-8"))
    info = json.loads((out / "build-info.json").read_text(encoding="utf-8"))
    assert info["identity"] == public_doc
    return public_doc


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    return _identity(tmp_path_factory.mktemp("id") / "build")


def test_identity_is_public_minimal_and_timestamp_free(base):
    assert base["schema_version"] == 1
    assert set(base) == {"schema_version", "release_digest", "source", "frontend", "catalog", "demo_pdf", "api"}
    text = json.dumps(base)
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", text), "no timestamps"
    for secret_word in ("secret", "token", "password", "PERIGEE_TOKEN"):
        assert secret_word not in text
    assert base["demo_pdf"]["media_type"] == "application/pdf"
    assert base["demo_pdf"]["sha256"] == cf_build._sha256((DIST / "demo/perigee-demo.pdf").read_bytes())
    assert base["frontend"]["index_html_sha256"] == cf_build._sha256((DIST / "index.html").read_bytes())
    assert base["frontend"]["entry_scripts"] and all(k.startswith("assets/index-") for k in base["frontend"]["entry_scripts"])
    assert base["catalog"]["content_version"] == json.loads((CONTENT / "targets.json").read_text())["content_version"]
    assert base["api"]["proxied_to"] == "https://perigee-liard.vercel.app"


def test_source_label_is_honest(base):
    src = base["source"]
    if src["commit"] is None:
        assert src["label"].startswith("unknown")
    elif src["tree_clean"] is True:
        assert src["label"] == src["commit"]
    else:
        assert src["label"].startswith(src["commit"] + "+")


def test_identical_content_has_identical_identity(base, tmp_path):
    again = _identity(tmp_path / "build")
    assert again["release_digest"] == base["release_digest"]
    assert again["frontend"] == base["frontend"] and again["catalog"] == base["catalog"]


def test_changed_frontend_changes_frontend_and_release_digest_only(base, tmp_path):
    dist = tmp_path / "dist"
    shutil.copytree(DIST, dist)
    (dist / "index.html").write_text((dist / "index.html").read_text() + "<!-- changed -->")
    changed = _identity(tmp_path / "build", dist=dist)
    assert changed["frontend"]["digest"] != base["frontend"]["digest"]
    assert changed["frontend"]["index_html_sha256"] != base["frontend"]["index_html_sha256"]
    assert changed["catalog"]["digest"] == base["catalog"]["digest"]
    assert changed["release_digest"] != base["release_digest"]


def test_changed_pdf_is_detected(base, tmp_path):
    dist = tmp_path / "dist"
    shutil.copytree(DIST, dist)
    with open(dist / "demo/perigee-demo.pdf", "ab") as f:
        f.write(b"\n%changed")
    changed = _identity(tmp_path / "build", dist=dist)
    assert changed["demo_pdf"]["sha256"] != base["demo_pdf"]["sha256"]
    assert changed["release_digest"] != base["release_digest"]


def test_changed_catalog_changes_catalog_and_release_digest_only(base, tmp_path):
    content = tmp_path / "content"
    shutil.copytree(CONTENT, content)
    case = content / "cases" / "fair_comparison.json"
    doc = json.loads(case.read_text(encoding="utf-8"))
    doc["title"] = doc["title"] + " (edited)"
    case.write_text(json.dumps(doc), encoding="utf-8")
    changed = _identity(tmp_path / "build", content=content)
    assert changed["catalog"]["digest"] != base["catalog"]["digest"]
    assert changed["frontend"]["digest"] == base["frontend"]["digest"]
    assert changed["release_digest"] != base["release_digest"]
