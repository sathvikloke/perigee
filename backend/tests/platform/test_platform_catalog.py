"""Presets, cases and preset frame listing."""

import json
import shutil

from conftest import (
    FIXTURE_PRESETS,
    PRESET_IDS,
    REAL_CONTENT,
    build_content_root,
    load_real,
    make_client,
)

from backend.platform.catalog import CatalogStore


def assert_error(resp, status, code):
    assert resp.status_code == status
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert body["schema_version"] == 1
    assert isinstance(body["request_id"], str) and body["request_id"]
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["retryable"] is False
    return body


# -- presets ------------------------------------------------------------


def test_presets_lists_five_descriptors_in_authored_order(real_client):
    resp = real_client.get("/api/v1/presets")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == 1
    assert body["count"] == 5
    assert [p["preset_id"] for p in body["presets"]] == PRESET_IDS
    targets = load_real("targets.json")
    assert body["content_version"] == targets["content_version"]
    assert body["coordinate_conventions"] == targets["coordinate_conventions"]


def test_preset_descriptors_preserve_authored_fields_verbatim(real_client):
    presets = {p["id"]: p for p in real_client.get("/api/v1/presets").json()["presets"]}
    for target in load_real("targets.json")["targets"]:
        served = presets[target["id"]]
        for key, value in target.items():
            assert served[key] == value, (target["id"], key)
        assert served["preset_id"] == target["id"]
        # Only these serving fields are added.
        assert set(served) - set(target) == {"preset_id", "cases", "frames_available", "frame_count"}


def test_preset_case_associations(real_client):
    presets = {p["id"]: p for p in real_client.get("/api/v1/presets").json()["presets"]}
    assert presets["barnards_star"]["cases"] == [
        {"case_id": "moving_neighbor", "title": load_real("cases/moving_neighbor.json")["title"], "available": True}
    ]
    assert presets["epsilon_indi_b"]["cases"] == [
        {"case_id": "fair_comparison", "title": load_real("cases/fair_comparison.json")["title"], "available": True}
    ]
    for pid in ("wise_0855", "rw_aurigae", "r_draconis"):
        assert presets[pid]["cases"] == []


def test_presets_report_missing_frames_honestly_for_real_content(real_client):
    for preset in real_client.get("/api/v1/presets").json()["presets"]:
        if not (REAL_CONTENT / "presets" / preset["id"]).is_dir():
            assert preset["frames_available"] is False
            assert preset["frame_count"] == 0


def test_listed_case_without_file_is_marked_unavailable(tmp_path):
    root = build_content_root(tmp_path, with_fixture_presets=False)
    doc = json.loads((root / "targets.json").read_text())
    doc["targets"][2]["case_ids"] = ["coverage_is_not_detection"]  # test copy only
    (root / "targets.json").write_text(json.dumps(doc))
    presets = {p["id"]: p for p in make_client(CatalogStore(root)).get("/api/v1/presets").json()["presets"]}
    assert presets["wise_0855"]["cases"] == [
        {"case_id": "coverage_is_not_detection", "title": None, "available": False}
    ]


def test_presets_503_when_targets_missing_but_cases_still_served(tmp_path):
    root = build_content_root(tmp_path, with_fixture_presets=False)
    (root / "targets.json").unlink()
    client = make_client(CatalogStore(root))
    assert_error(client.get("/api/v1/presets"), 503, "CONTENT_UNAVAILABLE")
    assert_error(client.get("/api/v1/presets/epsilon_indi_b/frames"), 503, "CONTENT_UNAVAILABLE")
    assert client.get("/api/v1/cases/fair_comparison").status_code == 200


# -- cases --------------------------------------------------------------


def test_cases_served_verbatim(real_client):
    for case_id in ("fair_comparison", "moving_neighbor"):
        resp = real_client.get("/api/v1/cases/{}".format(case_id))
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json() == load_real("cases/{}.json".format(case_id))


def test_unknown_case_is_404_envelope(real_client):
    for case_id in ("coverage_is_not_detection", "FAIR_COMPARISON", "fair_comparison.json", "x" * 300):
        body = assert_error(real_client.get("/api/v1/cases/{}".format(case_id)), 404, "CASE_NOT_FOUND")
        assert body["error"]["details"]["available_case_ids"] == ["fair_comparison", "moving_neighbor"]


def test_case_with_mismatched_id_is_not_served(tmp_path):
    root = build_content_root(tmp_path, with_fixture_presets=False)
    shutil.copy2(root / "cases" / "fair_comparison.json", root / "cases" / "renamed.json")
    store = CatalogStore(root)
    assert store.case_ids() == ["fair_comparison", "moving_neighbor"]
    assert any("renamed.json" in issue for issue in store.load_issues)


# -- frames -------------------------------------------------------------


def test_unknown_preset_frames_404(real_client):
    for preset_id in ("pluto", "EPSILON_INDI_B", "epsilon_indi_b.json", "x" * 300):
        body = assert_error(
            real_client.get("/api/v1/presets/{}/frames".format(preset_id)), 404, "PRESET_NOT_FOUND"
        )
        assert body["error"]["details"]["available_preset_ids"] == PRESET_IDS


def test_known_preset_without_products_is_honestly_missing(tmp_path):
    client = make_client(CatalogStore(build_content_root(tmp_path, with_fixture_presets=False)))
    for preset_id in PRESET_IDS:
        resp = client.get("/api/v1/presets/{}/frames".format(preset_id))
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "missing"
        assert body["frames_available"] is False
        assert body["frames"] == [] and body["frame_count"] == 0
        assert "never synthesized" in body["reason"]
        assert body["source_dir"] == "backend/content/presets/{}".format(preset_id)


def test_fixture_frames_ordered_by_mjd_then_frame_key(fixture_client):
    resp = fixture_client.get("/api/v1/presets/epsilon_indi_b/frames")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready", body["warnings"]
    assert body["frames_available"] is True
    assert body["order"] == "mjd_then_frame_key"
    assert [f["frame_key"] for f in body["frames"]] == [
        "FIXTURE_0001_1_D3",  # mjd 100.5, derived from observation_id + detector
        "FIXTURE_0001_1_D6",  # mjd 100.5, tie broken by frame_key; from {"frame": ...} wrapper
        "FIXTURE_0002_1_D3",  # mjd 200.25
    ]
    assert body["frame_count"] == 3
    assert all(f["fixture"] is True for f in body["frames"])  # labeled synthetic


def test_fixture_frame_fields_preserved_and_image_rewritten(fixture_client, fixture_store):
    frames = {f["frame_key"]: f for f in fixture_client.get("/api/v1/presets/epsilon_indi_b/frames").json()["frames"]}
    original = json.loads((FIXTURE_PRESETS / "epsilon_indi_b" / "FIXTURE_0001_1_D3.json").read_text())
    first = frames["FIXTURE_0001_1_D3"]
    for key, value in original.items():
        if key != "image":
            assert first[key] == value
    image = first["image"]
    assert image["src"] == "/api/v1/assets/" + image["asset_id"]
    assert image["media_type"] == "image/png"
    assert (image["width"], image["height"]) == (4, 4)  # read from the PNG header
    asset = fixture_client.get(image["src"])
    assert asset.status_code == 200
    assert asset.headers["content-type"] == "image/png"
    assert asset.content == (FIXTURE_PRESETS / "epsilon_indi_b" / "FIXTURE_0001_1_D3.png").read_bytes()
    # An explicit null image stays null; an absent image stays absent (no PNG exists for it).
    assert frames["FIXTURE_0002_1_D3"]["image"] is None
    assert "image" not in frames["FIXTURE_0001_1_D6"]


def test_presets_reflect_fixture_frame_availability(fixture_client):
    presets = {p["id"]: p for p in fixture_client.get("/api/v1/presets").json()["presets"]}
    assert presets["epsilon_indi_b"]["frames_available"] is True
    assert presets["epsilon_indi_b"]["frame_count"] == 3
    assert presets["barnards_star"]["frames_available"] is False


def test_preset_dir_without_records_is_missing(fixture_root):
    (fixture_root / "presets" / "wise_0855").mkdir()
    (fixture_root / "presets" / "wise_0855" / "notes.json").write_text('{"kind": "not a frame"}')
    body = make_client(CatalogStore(fixture_root)).get("/api/v1/presets/wise_0855/frames").json()
    assert body["status"] == "missing"
    assert body["frames"] == []
    assert "no usable FrameRecord" in body["reason"]


def _write_record(path, key, mjd, image):
    obs, det = key.rsplit("_D", 1)
    path.write_text(json.dumps({
        "fixture": True, "frame_key": key, "frame_id": key, "observation_id": obs,
        "detector": int(det), "collection_id": "fixture_not_nasa",
        "observed_at_utc": "2000-01-01T00:00:00", "mjd": mjd,
        "source_url": "https://example.invalid/fixture.fits", "image": image,
    }))


def test_image_paths_outside_preset_are_never_handed_out(fixture_root):
    d = fixture_root / "presets" / "rw_aurigae"
    d.mkdir()
    shutil.copy2(FIXTURE_PRESETS / "epsilon_indi_b" / "FIXTURE_0001_1_D3.png", d / "own.png")
    _write_record(d / "a.json", "FIXTURE_A_D1", 1.0, {"src": "../epsilon_indi_b/FIXTURE_0001_1_D3.png"})
    _write_record(d / "b.json", "FIXTURE_B_D1", 2.0, {"src": "/etc/passwd"})
    _write_record(d / "c.json", "FIXTURE_C_D1", 3.0, {"src": "file:///etc/hosts"})
    _write_record(d / "d.json", "FIXTURE_D_D1", 4.0, {"src": "missing.png"})
    _write_record(d / "e.json", "FIXTURE_E_D1", 5.0, {"src": "own.png"})
    _write_record(d / "f.json", "FIXTURE_F_D1", 6.0, "own.png")
    body = make_client(CatalogStore(fixture_root)).get("/api/v1/presets/rw_aurigae/frames").json()
    frames = {f["frame_key"]: f for f in body["frames"]}
    assert body["status"] == "partial"
    for key in ("FIXTURE_A_D1", "FIXTURE_B_D1", "FIXTURE_C_D1", "FIXTURE_D_D1"):
        assert frames[key]["image"] is None
    assert frames["FIXTURE_E_D1"]["image"]["src"].startswith("/api/v1/assets/rw_aurigae--own--")
    assert frames["FIXTURE_F_D1"]["image"]["src"].startswith("/api/v1/assets/rw_aurigae--own--")
    assert len(body["warnings"]) == 4
    assert "/etc" not in json.dumps(body["frames"])


def test_png_named_after_frame_key_is_attached(fixture_root):
    d = fixture_root / "presets" / "r_draconis"
    d.mkdir()
    shutil.copy2(FIXTURE_PRESETS / "epsilon_indi_b" / "FIXTURE_0001_1_D3.png", d / "FIXTURE_X_D2.png")
    record = {"observation_id": "FIXTURE_X", "detector": 2, "mjd": 5.0, "fixture": True}
    (d / "manifest.json").write_text(json.dumps({"frames": [record]}))
    body = make_client(CatalogStore(fixture_root)).get("/api/v1/presets/r_draconis/frames").json()
    (frame,) = body["frames"]
    assert frame["frame_key"] == "FIXTURE_X_D2"
    assert frame["image"]["asset_id"].startswith("r_draconis--FIXTURE_X_D2--")
    # Contract fields the record lacks are reported, not invented.
    assert "frame_id" not in frame and "source_url" not in frame
    assert body["status"] == "partial"
    assert any("missing contract fields" in w for w in body["warnings"])


def test_records_without_mjd_sort_last_and_foreign_preset_records_skipped(fixture_root):
    d = fixture_root / "presets" / "barnards_star"
    d.mkdir()
    _write_record(d / "a.json", "FIXTURE_NOMJD_D1", None, None)
    _write_record(d / "b.json", "FIXTURE_LATE_D1", 99.0, None)
    foreign = {"frame_key": "FIXTURE_OTHER_D1", "preset_id": "wise_0855", "mjd": 1.0}
    (d / "c.json").write_text(json.dumps(foreign))
    (d / "bad.json").write_text("{not json")
    body = make_client(CatalogStore(fixture_root)).get("/api/v1/presets/barnards_star/frames").json()
    assert [f["frame_key"] for f in body["frames"]] == ["FIXTURE_LATE_D1", "FIXTURE_NOMJD_D1"]
    assert any("belongs to preset 'wise_0855'" in w for w in body["warnings"])
    assert any("bad.json: not valid JSON" in w for w in body["warnings"])


def test_real_case_frame_metadata_round_trips_through_loader(fixture_root):
    """Uses the science-verified frame metadata in the case files (real
    observation identities, no images) as a stand-in manifest in a temp dir,
    to check identity, frame_key convention and ordering on real values."""
    for case_id, preset_id in (("moving_neighbor", "barnards_star"), ("fair_comparison", "epsilon_indi_b")):
        case = load_real("cases/{}.json".format(case_id))
        d = fixture_root / "presets" / preset_id
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"frames": list(reversed(case["frames"]))}))
        body = make_client(CatalogStore(fixture_root)).get("/api/v1/presets/{}/frames".format(preset_id)).json()
        served = body["frames"]
        expected = sorted(case["frames"], key=lambda f: (f["mjd"], f["frame_key"]))
        assert [f["frame_key"] for f in served] == [f["frame_key"] for f in expected]
        for frame in served:
            assert frame["frame_key"] == "{}_D{}".format(frame["observation_id"], frame["detector"])
            original = next(f for f in case["frames"] if f["frame_key"] == frame["frame_key"])
            assert frame == original  # nothing added, removed or reworded
