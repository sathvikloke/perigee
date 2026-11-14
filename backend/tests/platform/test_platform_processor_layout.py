"""Catalog against the processor's output layout (tools/ingest/ingest.py):
presets/<preset>/<set>/{<frame_key>.png,.flags.png,.json,frames.json} where
frames.json carries {"frames": [...], "assets": {alias_id: path}}.

All records and PNGs here are SYNTHETIC FIXTURES, not NASA output."""

import json
import shutil

import pytest
from conftest import FIXTURE_PRESETS, build_content_root, make_client

from backend.platform.catalog import CatalogStore

PNG = FIXTURE_PRESETS / "epsilon_indi_b" / "FIXTURE_0001_1_D3.png"
PREFIX = "/api/v1/assets/"


def _record(key, mjd, set_name, stretch):
    obs, det = key.rsplit("_D", 1)
    alias = "epsilon_indi_b.{}.{}".format(set_name, key)
    return {
        "fixture": True,
        "schema_version": 1,
        "frame_id": key,
        "frame_key": key,
        "observation_id": obs,
        "detector": int(det),
        "collection_id": "fixture_not_nasa",
        "observed_at_utc": "2000-01-01T00:00:00Z",
        "mjd": mjd,
        "source_url": "https://example.invalid/{}.fits".format(key),
        "image": {"src": PREFIX + alias + ".png", "width": 4, "height": 4, "media_type": "image/png"},
        "flag_image": {"src": PREFIX + alias + ".flags.png", "width": 4, "height": 4,
                       "media_type": "image/png", "legend": {"adverse_flag": [255, 64, 64, 150]}},
        "display_scale": {"mode": stretch},
        "preset_id": "epsilon_indi_b",
    }


def _write_set(preset_dir, set_name, records):
    d = preset_dir / set_name
    d.mkdir(parents=True)
    assets = {}
    for rec in records:
        key = rec["frame_key"]
        shutil.copy2(PNG, d / (key + ".png"))
        shutil.copy2(PNG, d / (key + ".flags.png"))
        (d / (key + ".json")).write_text(json.dumps(rec))
        base = "epsilon_indi_b.{}.{}".format(set_name, key)
        assets[base + ".png"] = "epsilon_indi_b/{}/{}.png".format(set_name, key)
        assets[base + ".flags.png"] = "epsilon_indi_b/{}/{}.flags.png".format(set_name, key)
    (d / "frames.json").write_text(json.dumps({
        "schema_version": 1, "preset_id": "epsilon_indi_b", "set": set_name,
        "assets": assets, "frames": records,
    }))


@pytest.fixture
def layout_root(tmp_path):
    root = build_content_root(tmp_path, with_fixture_presets=False)
    preset_dir = root / "presets" / "epsilon_indi_b"
    _write_set(preset_dir, "frames", [_record("FIXTURE_K_D3", 10.0, "frames", "per_frame")])
    _write_set(preset_dir, "case-fair_comparison", [
        _record("FIXTURE_L_D3", 20.0, "case-fair_comparison", "shared"),
        _record("FIXTURE_K_D3", 10.0, "case-fair_comparison", "shared"),
    ])
    return root


@pytest.fixture
def layout_client(layout_root):
    return make_client(CatalogStore(layout_root))


def test_default_listing_prefers_preset_set_and_dedupes(layout_client):
    body = layout_client.get("/api/v1/presets/epsilon_indi_b/frames").json()
    assert body["status"] == "ready", body["warnings"]
    assert body["case_id"] is None
    assert [f["frame_key"] for f in body["frames"]] == ["FIXTURE_K_D3", "FIXTURE_L_D3"]
    assert body["frames"][0]["display_scale"]["mode"] == "per_frame"  # from the "frames" set
    assert body["sets"] == ["frames", "case-fair_comparison"]


def test_case_listing_uses_case_set_only(layout_client):
    body = layout_client.get("/api/v1/presets/epsilon_indi_b/frames?case_id=fair_comparison").json()
    assert body["status"] == "ready", body["warnings"]
    assert body["case_id"] == "fair_comparison"
    assert [f["frame_key"] for f in body["frames"]] == ["FIXTURE_K_D3", "FIXTURE_L_D3"]
    assert all(f["display_scale"]["mode"] == "shared" for f in body["frames"])
    assert body["sets"] == ["case-fair_comparison"]


def test_case_listing_unknown_or_foreign_case_is_404(layout_client):
    for case_id in ("moving_neighbor", "nope", "../x"):
        resp = layout_client.get("/api/v1/presets/epsilon_indi_b/frames", params={"case_id": case_id})
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CASE_NOT_FOUND"
        assert resp.json()["error"]["details"]["available_case_ids"] == ["fair_comparison"]


def test_case_listing_without_products_is_missing(layout_client):
    body = layout_client.get("/api/v1/presets/barnards_star/frames?case_id=moving_neighbor").json()
    assert body["status"] == "missing" and body["frames"] == []


def test_alias_src_rewritten_to_canonical_versioned_asset(layout_client):
    frame = layout_client.get("/api/v1/presets/epsilon_indi_b/frames").json()["frames"][0]
    for field in ("image", "flag_image"):
        image = frame[field]
        assert image["src"] == PREFIX + image["asset_id"]
        assert image["asset_id"].startswith("epsilon_indi_b--frames-FIXTURE_K_D3")
        resp = layout_client.get(image["src"])
        assert resp.status_code == 200 and resp.headers["content-type"] == "image/png"
        assert "immutable" in resp.headers["cache-control"]
    assert frame["flag_image"]["legend"] == {"adverse_flag": [255, 64, 64, 150]}  # preserved


def test_processor_alias_urls_still_serve_but_revalidate(layout_client):
    resp = layout_client.get(PREFIX + "epsilon_indi_b.frames.FIXTURE_K_D3.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == PNG.read_bytes()
    assert "must-revalidate" in resp.headers["cache-control"]


def test_presets_report_case_frame_availability(layout_client):
    presets = {p["id"]: p for p in layout_client.get("/api/v1/presets").json()["presets"]}
    assert presets["epsilon_indi_b"]["frames_available"] is True
    assert presets["epsilon_indi_b"]["frame_count"] == 2
    assert presets["epsilon_indi_b"]["cases"][0]["frames_available"] is True
    assert presets["barnards_star"]["cases"][0]["frames_available"] is False


def test_manifest_aliases_cannot_widen_the_allowlist(layout_root, tmp_path):
    outside = tmp_path / "secret.png"
    shutil.copy2(PNG, outside)
    other = layout_root / "presets" / "wise_0855"
    other.mkdir()
    shutil.copy2(PNG, other / "w.png")
    manifest = layout_root / "presets" / "epsilon_indi_b" / "evil.json"
    manifest.write_text(json.dumps({"assets": {
        "evil.outside.png": str(outside),
        "evil.traverse.png": "../../../secret.png",
        "evil.other.png": "wise_0855/w.png",
        "evil.missing.png": "epsilon_indi_b/frames/nope.png",
        "../evil.png": "epsilon_indi_b/frames/FIXTURE_K_D3.png",
        "evil.json.html": "epsilon_indi_b/frames/FIXTURE_K_D3.png",
    }}))
    store = CatalogStore(layout_root)
    client = make_client(store)
    for alias in ("evil.outside.png", "evil.traverse.png", "evil.other.png", "evil.missing.png", "evil.json.html"):
        assert client.get(PREFIX + alias).status_code == 404
    assert sum("evil.json: asset alias" in i for i in store.load_issues) == 6


def test_unknown_alias_in_record_is_dropped_with_warning(layout_root):
    d = layout_root / "presets" / "epsilon_indi_b" / "frames"
    rec = _record("FIXTURE_M_D3", 30.0, "frames", "per_frame")
    rec["image"]["src"] = PREFIX + "epsilon_indi_b.frames.does_not_exist.png"
    del rec["flag_image"]
    (d / "FIXTURE_M_D3.json").write_text(json.dumps(rec))
    body = make_client(CatalogStore(layout_root)).get("/api/v1/presets/epsilon_indi_b/frames").json()
    frame = next(f for f in body["frames"] if f["frame_key"] == "FIXTURE_M_D3")
    assert frame["image"] is None
    assert body["status"] == "partial"
    assert any("does_not_exist" in w for w in body["warnings"])
