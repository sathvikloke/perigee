"""Allowlisted asset index and /assets/{asset_id} serving."""

import hashlib
import os
import re

import pytest
from conftest import FIXTURE_PRESETS, make_client

from backend.platform.catalog import CatalogStore
from backend.platform.catalog_assets import (
    MAX_ASSET_BYTES,
    AssetIndex,
    is_valid_asset_id,
    png_dimensions,
)

FIXTURE_PNG = FIXTURE_PRESETS / "epsilon_indi_b" / "FIXTURE_0001_1_D3.png"


def test_index_contains_only_allowlisted_files_with_versioned_ids(fixture_store):
    entries = fixture_store.assets.entries()
    rel = sorted(e.relative_path for e in entries)
    assert rel == sorted([
        "epsilon_indi_b/FIXTURE_0001_1_D3.json",
        "epsilon_indi_b/FIXTURE_0001_1_D3.png",
        "epsilon_indi_b/a_later_frame.json",
        "epsilon_indi_b/provenance.json",
        "epsilon_indi_b/wrapped_frame.json",
    ])
    for e in entries:
        assert is_valid_asset_id(e.asset_id)
        assert re.match(r"^epsilon_indi_b--[A-Za-z0-9_-]+--[0-9a-f]{12}\.(png|json)$", e.asset_id)
        assert e.asset_id.split("--")[-1].split(".")[0] == e.sha256[:12]
        assert e.media_type == ("image/png" if e.relative_path.endswith(".png") else "application/json")


def test_png_asset_served_with_media_type_and_cache_headers(fixture_client, fixture_store):
    (entry,) = fixture_store.assets.for_preset("epsilon_indi_b", "image/png")
    resp = fixture_client.get("/api/v1/assets/" + entry.asset_id)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert "immutable" in resp.headers["cache-control"]
    assert resp.headers["etag"] == '"{}"'.format(hashlib.sha256(FIXTURE_PNG.read_bytes()).hexdigest())
    assert resp.content == FIXTURE_PNG.read_bytes()
    assert png_dimensions(resp.content) == (4, 4)


def test_json_asset_served_as_application_json(fixture_client, fixture_store):
    entry = next(e for e in fixture_store.assets.entries() if e.relative_path.endswith("provenance.json"))
    resp = fixture_client.get("/api/v1/assets/" + entry.asset_id)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"
    assert resp.json()["fixture"] is True


@pytest.mark.parametrize("asset_id", [
    "nope.png",
    "epsilon_indi_b--FIXTURE_0001_1_D3--000000000000.png",  # wrong version
    "targets.json",
    "..",
    "...png",
    "epsilon_indi_b--..--x.png",
    "%2e%2e%2ftargets.json",
    "..%2F..%2Ftargets.json",
    "..%5C..%5Ctargets.json",
    "%2Fetc%2Fpasswd",
    "epsilon_indi_b%2FFIXTURE_0001_1_D3.png",
    "epsilon_indi_b/FIXTURE_0001_1_D3.png",
    "..%252F..%252Ftargets.json",
    "FIXTURE_0001_1_D3.png%00.png",
])
def test_unknown_or_traversal_asset_ids_get_json_404(fixture_client, asset_id):
    resp = fixture_client.get("/api/v1/assets/" + asset_id)
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert b"coordinate_conventions" not in resp.content  # targets.json never leaks
    assert b"PNG" not in resp.content
    body = resp.json()
    if "error" in body:  # matched the catalog route
        assert body["error"]["code"] == "ASSET_NOT_FOUND"
        assert body["schema_version"] == 1


@pytest.mark.parametrize("value", ["", "a" * 300, "../x.png", "a/b.png", "a\\b.png", "a%2fb.png", "x.fits", "x.html", "/x.png"])
def test_is_valid_asset_id_rejects_unsafe(value):
    assert not is_valid_asset_id(value)


def test_symlinks_and_disallowed_files_are_never_indexed(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.json"
    secret.write_text('{"secret": true}')
    (outside / "img.png").write_bytes(FIXTURE_PNG.read_bytes())

    root = tmp_path / "presets"
    preset = root / "epsilon_indi_b"
    preset.mkdir(parents=True)
    (preset / "real.png").write_bytes(FIXTURE_PNG.read_bytes())
    os.symlink(secret, preset / "link_out.json")
    os.symlink(preset / "real.png", preset / "link_in.png")
    os.symlink(outside, preset / "linked_dir")
    os.symlink(outside, root / "linked_preset")
    (preset / "raw.fits").write_bytes(b"SIMPLE  =                    T")
    (preset / "page.html").write_text("<html></html>")
    (preset / ".hidden.png").write_bytes(FIXTURE_PNG.read_bytes())
    (preset / "huge.png").write_bytes(b"\x00" * (MAX_ASSET_BYTES + 1))

    index = AssetIndex(root)
    assert [e.relative_path for e in index.entries()] == ["epsilon_indi_b/real.png"]
    assert any("link_out.json" in s for s in index.skipped)
    assert any("link_in.png" in s for s in index.skipped)
    assert any("huge.png" in s for s in index.skipped)
    assert all("secret" not in e.relative_path for e in index.entries())


def test_asset_changed_after_indexing_is_not_served(fixture_root):
    store = CatalogStore(fixture_root)
    client = make_client(store)
    (entry,) = store.assets.for_preset("epsilon_indi_b", "image/png")
    png_path = fixture_root / "presets" / "epsilon_indi_b" / "FIXTURE_0001_1_D3.png"
    png_path.write_bytes(png_path.read_bytes() + b"tampered")
    resp = client.get("/api/v1/assets/" + entry.asset_id)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ASSET_NOT_FOUND"


def test_asset_replaced_by_symlink_after_indexing_is_not_served(fixture_root, tmp_path):
    store = CatalogStore(fixture_root)
    (entry,) = store.assets.for_preset("epsilon_indi_b", "image/png")
    png_path = fixture_root / "presets" / "epsilon_indi_b" / "FIXTURE_0001_1_D3.png"
    copy = tmp_path / "copy.png"
    copy.write_bytes(png_path.read_bytes())
    png_path.unlink()
    os.symlink(copy, png_path)
    assert make_client(store).get("/api/v1/assets/" + entry.asset_id).status_code == 404


def test_missing_presets_root_gives_empty_index(tmp_path):
    index = AssetIndex(tmp_path / "does_not_exist")
    assert len(index) == 0 and index.skipped == []
