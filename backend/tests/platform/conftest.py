"""Shared fixtures for catalog/asset platform tests.

``fixtures/presets/`` holds a SYNTHETIC test fixture (tiny generated PNG and
hand-written FrameRecord JSON). It is not NASA/SPHEREx output and is never
part of the served content bundle; tests copy it into a temporary content root.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.platform.catalog import CatalogStore, get_catalog_store  # noqa: E402
from backend.routes import catalog as catalog_routes  # noqa: E402

REAL_CONTENT = REPO_ROOT / "backend" / "content"
FIXTURE_PRESETS = Path(__file__).resolve().parent / "fixtures" / "presets"
PRESET_IDS = ["barnards_star", "epsilon_indi_b", "wise_0855", "rw_aurigae", "r_draconis"]


def make_client(store: CatalogStore) -> TestClient:
    """Throwaway app mounting the catalog router exactly as main.py will."""
    app = FastAPI()
    app.include_router(catalog_routes.router, prefix="/api/v1")
    app.dependency_overrides[get_catalog_store] = lambda: store
    return TestClient(app)


def build_content_root(tmp_path: Path, with_fixture_presets: bool = True) -> Path:
    """Copy the real authored content (read-only source) plus, optionally,
    the synthetic fixture presets into a temporary content root."""
    root = tmp_path / "content"
    root.mkdir()
    shutil.copy2(REAL_CONTENT / "targets.json", root / "targets.json")
    shutil.copytree(REAL_CONTENT / "cases", root / "cases")
    if with_fixture_presets:
        shutil.copytree(FIXTURE_PRESETS, root / "presets")
    return root


def load_real(name: str):
    return json.loads((REAL_CONTENT / name).read_text())


@pytest.fixture
def real_store() -> CatalogStore:
    return CatalogStore(REAL_CONTENT)


@pytest.fixture
def real_client(real_store) -> TestClient:
    return make_client(real_store)


@pytest.fixture
def fixture_root(tmp_path) -> Path:
    return build_content_root(tmp_path)


@pytest.fixture
def fixture_store(fixture_root) -> CatalogStore:
    return CatalogStore(fixture_root)


@pytest.fixture
def fixture_client(fixture_store) -> TestClient:
    return make_client(fixture_store)
