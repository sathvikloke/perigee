"""Checks against the six retained ORIGINAL case cutouts.

Skipped unless PERIGEE_DATA_ROOT points at research/build_data (raw FITS are
never committed). Expected values are copied from the science-owned case files
backend/content/cases/{fair_comparison,moving_neighbor}.json (content version
*-2026-11-14a) and target astrometry from backend/content/targets.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.data.process import FrameInput, TargetInput, inspect_fits, process_frame  # noqa: E402

ROOT = os.environ.get("PERIGEE_DATA_ROOT")
pytestmark = pytest.mark.skipif(not ROOT or not Path(ROOT, "manifest.json").exists(),
                                reason="PERIGEE_DATA_ROOT with retained FITS not available")

TARGETS = {
    "epsilon_indi_b": dict(
        query=(331.0966687831005, -56.80064917516836),
        target=TargetInput(331.04414658852124, -56.78284419511611, 2000.0, 3981.977, -2466.832, 270.658, None,
                           name="Epsilon Indi B"),
    ),
    "barnards_star": dict(
        query=(269.4462585584787, 4.768324486236583),
        target=TargetInput(269.4520769586187, 4.69336496657667, 2000.0, -801.551, 10362.394, 546.9759, -110.11,
                           name="Barnard's Star"),
    ),
}

# (preset, frame_key, collection, observed_at_utc, wavelength_um, quality, sha256)
CASE_FRAMES = [
    ("epsilon_indi_b", "2026W18_1A_0516_1_D3", "spherex_dr1", "2026-04-29T12:05:47.874", 2.3232, "clear",
     "3781422675f53d0af5d4b9fd3bd26497a0c6b1309766570c3c8370b6735afb1f"),
    ("epsilon_indi_b", "2026W39_2A_0597_4_D3", "spherex_qr3", "2026-09-27T07:44:24.312", 2.3220, "clear",
     "378fcf34fb43033c05964581b03f33431cbc7da64bcd41ce4b0d791f98fd1b0b"),
    ("epsilon_indi_b", "2026W18_1A_0516_1_D6", "spherex_dr1", "2026-04-29T12:05:47.874", 4.9399, "clear",
     "74e32a3c1d7f8b7fddfb4e44ff02c5baa1256ffe35a1b8d0047aec4c92783f85"),
    ("barnards_star", "2025W35_1A_0008_1_D3", "spherex_dr1", "2025-08-25T00:50:31.845", 2.0062, "flagged",
     "e7c0a6f7c4c69cebc5b8fd5b7db21c0ddbc5e4046dd9d7ba3b6a424d99770562"),
    ("barnards_star", "2026W12_1A_0610_2_D3", "spherex_dr1", "2026-03-19T09:06:02.748", 2.0123, "flagged",
     "9f047b3b75bbc8db69ea5d7c4d4f525860f6de0980829e3dd467b1ee13c55fa5"),
    ("barnards_star", "2026W34_1A_0431_1_D3", "spherex_qr3", "2026-08-19T04:57:42.053", 2.0284, "flagged",
     "ea3ecdd6d0742276767228a051b7fdbea2ed04181bde6e40701aa608753ec032"),
]


@pytest.fixture(scope="module")
def ledger():
    m = json.loads(Path(ROOT, "manifest.json").read_text())
    return {f"{r['obs_id']}_D{r['detector']}": r for r in m["files"] if r.get("status") == "downloaded"}


@pytest.mark.parametrize("preset,key,coll,when,wl,status,sha", CASE_FRAMES, ids=[c[1] for c in CASE_FRAMES])
def test_case_frame_matches_case_json(ledger, preset, key, coll, when, wl, status, sha):
    rec_l = ledger[key]
    b = Path(ROOT, rec_l["file"]).read_bytes()
    t = TARGETS[preset]
    rec = process_frame(b, FrameInput(
        query_ra_deg=t["query"][0], query_dec_deg=t["query"][1], target=t["target"],
        source_url=rec_l["archive_url"], observation_id=rec_l["obs_id"], collection_id=rec_l["collection"],
        detector=rec_l["detector"], expected_sha256=sha)).record
    assert rec["frame_key"] == key
    assert rec["collection_id"] == coll
    assert rec["observed_at_utc"] == when + "Z"
    assert rec["wavelength_um"] == pytest.approx(wl, abs=1e-4)
    assert rec["quality"]["status"] == status
    assert rec["provenance"]["sha256"] == sha
    assert rec["marker"]["kind"] == "catalog_prediction"


def test_real_header_layout(ledger):
    b = Path(ROOT, ledger["2026W18_1A_0516_1_D3"]["file"]).read_bytes()
    info = inspect_fits(b)
    assert [e["name"] for e in info["extensions"]] == ["PRIMARY", "IMAGE", "FLAGS", "VARIANCE", "ZODI", "EPSF", "WCS-WAVE"]
    assert info["image"]["CTYPE1"] == "RA---TAN-SIP"
    assert info["image"]["CTYPE1W"] == "WAVE-TAB" and info["image"]["PS1_0W"] == "WCS-WAVE"
    assert info["image"]["DATE-AVG"] == "2026-04-29T12:05:47.874"
    assert info["image"]["BUNIT"] == "MJy / sr"
    assert info["flag_bits"]["21"] == "SOURCE" and info["flag_bits"]["12"] == "FULLSAMPLE"


@pytest.mark.parametrize("key", ["2025W17_4B_0077_2_D1"])
def test_real_off_image_frame_has_null_wavelength(ledger, key):
    # Earlier audit defect 1: this Eps Ind B frame does not cover the target but a wavelength was reported.
    rec_l = ledger[key]
    t = TARGETS["epsilon_indi_b"]
    rec = process_frame(Path(ROOT, rec_l["file"]).read_bytes(), FrameInput(
        query_ra_deg=t["query"][0], query_dec_deg=t["query"][1], target=t["target"])).record
    assert rec["quality"]["status"] == "not_covered"
    assert rec["wavelength_um"] is None
    assert rec["quality"]["valid_aperture_pixels"] is None
