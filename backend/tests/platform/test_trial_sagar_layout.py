"""Trial 24f: the catalog adapter for the perigee-data layout (PR #19).

Uses a copy of the real committed products (no synthesized frames), then tampers
with the copy's manifest to check that the adapter keeps the allowlist strict.
"""

import hashlib
import json
import shutil

from conftest import REAL_CONTENT, build_content_root, make_client

from backend.platform.catalog import CatalogStore

AID = "epsilon_indi_b.2026W18_1A_0516_1_D3.fair_comparison.image.v1"


def _root(tmp_path):
    root = build_content_root(tmp_path, with_fixture_presets=False)
    shutil.copytree(REAL_CONTENT / "presets", root / "presets")
    return root


def _rewrite_manifest(root, fn):
    path = root / "presets" / "manifest.json"
    doc = json.loads(path.read_text())
    fn(doc["assets"])
    path.write_text(json.dumps(doc))


def test_case_set_and_manifest_alias_serve(tmp_path):
    client = make_client(CatalogStore(_root(tmp_path)))
    body = client.get("/api/v1/presets/epsilon_indi_b/frames?case_id=fair_comparison").json()
    assert body["status"] == "ready" and body["frame_count"] == 3
    assert body["sets"] == ["case-fair_comparison"]
    assert {f["case_ref"]: f["display_scale"]["mode"] for f in body["frames"]} == {
        "A": "shared", "B": "shared", "C": "per_frame"}
    resp = client.get("/api/v1/assets/" + AID)
    expected = (REAL_CONTENT / "presets/epsilon_indi_b/img" / (AID.split(".", 1)[1] + ".png")).read_bytes()
    assert resp.status_code == 200 and resp.content == expected
    assert hashlib.sha256(resp.content).hexdigest() == json.loads(
        (REAL_CONTENT / "presets/manifest.json").read_text())["assets"][AID]["sha256"]


def test_wrong_declared_hash_is_not_registered(tmp_path):
    root = _root(tmp_path)
    _rewrite_manifest(root, lambda a: a[AID].update(sha256="0" * 64))
    store = CatalogStore(root)
    assert any(AID in s and "sha256" in s for s in store.load_issues)
    assert make_client(store).get("/api/v1/assets/" + AID).status_code == 404
    frames = store.get_frames("epsilon_indi_b", "fair_comparison")
    assert frames.status == "partial" and any("not an allowlisted PNG" in w for w in frames.warnings)


def test_alias_cannot_cross_presets_or_leave_root(tmp_path):
    root = _root(tmp_path)

    def tamper(a):
        a["barnards_star.X_D1.seq.image.v1"] = dict(a[AID])  # target owned by epsilon_indi_b
        a["epsilon_indi_b.Y_D1.seq.image.v1"] = dict(a[AID], path="../targets.json")

    _rewrite_manifest(root, tamper)
    store = CatalogStore(root)
    client = make_client(store)
    assert client.get("/api/v1/assets/barnards_star.X_D1.seq.image.v1").status_code == 404
    assert client.get("/api/v1/assets/epsilon_indi_b.Y_D1.seq.image.v1").status_code == 404
    assert len([s for s in store.load_issues if "not registered" in s]) == 2
