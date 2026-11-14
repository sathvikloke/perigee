"""Integrity of the packaged preset assets in backend/content/presets."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "content" / "presets"
PRESET_IDS = {"barnards_star", "epsilon_indi_b", "wise_0855", "rw_aurigae", "r_draconis"}


@pytest.fixture(scope="module")
def index():
    return json.loads((ROOT / "manifest.json").read_text())


def test_all_five_presets_present(index):
    assert {p["preset_id"] for p in index["presets"]} == PRESET_IDS


def test_every_asset_exists_and_matches_its_hash(index):
    for asset_id, a in index["assets"].items():
        data = (ROOT / a["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == a["sha256"], asset_id
        assert a["media_type"] == "image/png" and data[:8] == b"\x89PNG\r\n\x1a\n"


def test_no_unlisted_files(index):
    listed = {a["path"] for a in index["assets"].values()}
    on_disk = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.png")}
    assert on_disk == listed


def test_package_stays_small(index):
    assert index["asset_total_bytes"] < 8 * 1024 * 1024
    assert not list(ROOT.rglob("*.fits")) and not list(ROOT.rglob("*.fits.*"))


def _records(index):
    for p in index["presets"]:
        doc = json.loads((ROOT / p["frames_path"]).read_text())
        yield p, doc, doc["frames"]
        for s in p["comparison_sets"]:
            sdoc = json.loads((ROOT / s["path"]).read_text())
            yield p, sdoc, sdoc["frames"]


def test_records_reference_listed_assets_and_keep_provenance(index):
    for p, doc, frames in _records(index):
        assert doc["delivery"] == "curated"
        for r in frames:
            assert r["image"]["src"] == f"/api/v1/assets/{r['image']['asset_id']}"
            assert r["image"]["asset_id"] in index["assets"]
            if r["flag_image"]:
                assert r["flag_image"]["asset_id"] in index["assets"]
            assert r["source_url"].startswith("https://irsa.ipac.caltech.edu/ibe/data/spherex/")
            assert len(r["provenance"]["sha256"]) == 64
            assert r["quality"]["status"] in {"clear", "flagged", "not_covered", "unknown"}
            if r["quality"]["status"] == "clear":
                assert r["quality"]["valid_aperture_pixels"] >= 10
            if r["marker"]:
                assert r["marker"]["kind"] == "catalog_prediction"


def test_sequences_are_in_observation_order_on_one_grid(index):
    for p, doc, frames in _records(index):
        if doc.get("set_id"):
            continue  # case sets keep the case's A/B/C order
        times = [(r["mjd"], r["frame_key"]) for r in frames]
        assert times == sorted(times)
        assert len({json.dumps(r["registration"], sort_keys=True) for r in frames}) == 1


def test_sets_use_one_shared_stretch_and_exist_in_the_sequence(index):
    for p in index["presets"]:
        seq_keys = {r["frame_key"] for r in json.loads((ROOT / p["frames_path"]).read_text())["frames"]}
        for s in p["comparison_sets"]:
            sdoc = json.loads((ROOT / s["path"]).read_text())
            assert {r["case_ref"]: r["frame_key"] for r in sdoc["frames"]} == s["frame_keys"]
            assert set(s["frame_keys"].values()) <= seq_keys
            shared = [r for r in sdoc["frames"] if r["case_ref"] in sdoc["shared_scale"]["refs"]]
            keys = ("mode", "low", "high", "asinh_softening")  # background offset stays per frame
            scales = {tuple(r["display_scale"][k] for k in keys) for r in shared}
            assert len(shared) >= 2 and len(scales) == 1 and shared[0]["display_scale"]["mode"] == "shared"
            for r in sdoc["frames"]:
                if r not in shared:
                    assert r["display_scale"]["mode"] == "per_frame"
