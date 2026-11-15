"""Case admission validator (tools/ingest/admit_case.py).

Uses only committed content: the two shipped cases with their shipped
products, and the staged WISE 0855 candidate with its staged products and
evidence map. No raw FITS is needed. Each "broken" test edits an in-memory
copy of a real case and asserts that the *right* check fails with a specific
reason, so a check that silently passes everything would fail these tests.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.ingest.admit_case import admit, build_context  # noqa: E402

CASES = REPO / "backend" / "content" / "cases"
STAGE = REPO / "science" / "staging" / "wise_0855_quality_trap"
STAGE_KW = {"products_root": STAGE / "presets", "evidence_map_path": STAGE / "evidence_map.json"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(case_path: Path, case: dict = None, **kw) -> dict:
    return admit(build_context(case_path, case=case, **kw))


def check(report: dict, name: str) -> dict:
    return next(c for c in report["checks"] if c["name"] == name)


def failures(report: dict, name: str) -> str:
    return "\n".join(check(report, name)["failures"])


def failing(report: dict) -> set:
    return {c["name"] for c in report["checks"] if c["status"] == "fail"}


# ------------------------------------------------------------ accepted cases
@pytest.mark.parametrize("case_id", ["fair_comparison", "moving_neighbor"])
def test_shipped_cases_are_admitted(case_id):
    rep = run(CASES / f"{case_id}.json")
    assert rep["verdict"] == "admit", {c["name"]: c["failures"] for c in rep["checks"] if c["failures"]}
    # The checks did real work on these cases, not a vacuous pass.
    assert check(rep, "metadata_agreement")["details"]["rows"]
    assert len(check(rep, "quoted_numbers")["details"]["verified"]) >= 10
    assert check(rep, "catalog_integration")["details"]["served_frames"] == 3


def test_staged_candidate_is_admitted_with_strict_number_registry():
    rep = run(STAGE / "case.json", **STAGE_KW)
    assert rep["verdict"] == "admit", {c["name"]: c["failures"] for c in rep["checks"] if c["failures"]}
    qn = check(rep, "quoted_numbers")["details"]
    assert qn["registry_entries"] > 0 and qn["unverified"] == []
    dc = check(rep, "display_claims")["details"]
    assert dc["stretch_groups"] == [["A", "B"], ["C"]]
    assert len(dc["grey_level_checks"]) == 3
    # Staged, not approved: the validator says so instead of hiding it.
    assert any("staged_candidate" in w for w in check(rep, "structure")["warnings"])


# ------------------------------------------------------------ broken copies
def test_wrong_frame_key_fails_frame_references():
    case = load(CASES / "fair_comparison.json")
    case["frames"][1]["frame_key"] = "2026W39_2A_0597_4_D4"
    rep = run(CASES / "fair_comparison.json", case)
    assert rep["verdict"] == "reject"
    assert "2026W39_2A_0597_4_D4" in failures(rep, "frame_references")
    assert "no record" in failures(rep, "frame_references")


def test_wrong_quoted_wavelength_fails_quoted_numbers():
    case = load(CASES / "fair_comparison.json")
    case["steps"][0]["hint"] = case["steps"][0]["hint"].replace("2.322 µm", "2.522 µm")
    rep = run(CASES / "fair_comparison.json", case)
    assert failing(rep) == {"quoted_numbers"}
    assert "2.522 µm" in failures(rep, "quoted_numbers")


def test_wrong_quoted_date_fails_quoted_numbers():
    case = load(CASES / "moving_neighbor.json")
    case["summary"] = case["summary"].replace("March 2026", "April 2026")
    rep = run(CASES / "moving_neighbor.json", case)
    assert failing(rep) == {"quoted_numbers"}
    assert "April 2026" in failures(rep, "quoted_numbers")


def test_wrong_day_in_staged_question_fails():
    case = load(STAGE / "case.json")
    case["opening_question"] = case["opening_question"].replace("7 and 10 November 2025", "7 and 12 November 2025")
    rep = run(STAGE / "case.json", case, **STAGE_KW)
    assert failing(rep) == {"quoted_numbers"}
    assert "12 November 2025" in failures(rep, "quoted_numbers")


def test_frame_metadata_mismatch_fails_metadata_agreement():
    case = load(CASES / "fair_comparison.json")
    case["frames"][2]["wavelength_um"] = 4.8
    rep = run(CASES / "fair_comparison.json", case)
    assert "metadata_agreement" in failing(rep)
    assert "wavelength_um" in failures(rep, "metadata_agreement")


def test_false_shared_stretch_claim_fails_display_claims():
    case = load(CASES / "fair_comparison.json")
    case["display_requirements"]["stretch"] = "A, B and C share one asinh stretch (case-fair_comparison products)."
    rep = run(CASES / "fair_comparison.json", case)
    assert failing(rep) == {"display_claims"}
    assert "share a stretch" in failures(rep, "display_claims")


def test_wrong_grey_level_example_fails_display_claims():
    case = load(STAGE / "case.json")
    st = next(s for s in case["steps"] if s["id"] == "stretch")
    st["hint"] = st["hint"].replace("grey 177 in C", "grey 159 in C")
    rep = run(STAGE / "case.json", case, **STAGE_KW)
    assert failing(rep) == {"display_claims"}
    assert "grey 159 in C" in failures(rep, "display_claims")


def test_missing_unsupported_conclusions_fails_answer_key():
    case = load(CASES / "moving_neighbor.json")
    del case["conclusion_guide"]["not_supported"]
    rep = run(CASES / "moving_neighbor.json", case)
    assert failing(rep) == {"answer_key"}
    assert "not_supported is missing" in failures(rep, "answer_key")


def test_unsupported_conclusion_without_reason_fails_answer_key():
    case = load(CASES / "moving_neighbor.json")
    case["conclusion_guide"]["not_supported"][0] = "I measured Barnard's Star's proper motion."
    rep = run(CASES / "moving_neighbor.json", case)
    assert "without a reason" in failures(rep, "answer_key")


def test_staged_conclusion_without_evidence_mapping_fails_answer_key():
    case = load(STAGE / "case.json")
    case["conclusion_guide"]["supported"].append("WISE 0855 did not change between A and C.")
    rep = run(STAGE / "case.json", case, **STAGE_KW)
    assert "answer_key" in failing(rep)
    assert "no evidence-map entry" in failures(rep, "answer_key")


def test_detection_wording_for_catalog_marker_fails_identity():
    case = load(CASES / "moving_neighbor.json")
    st = next(s for s in case["steps"] if s["id"] == "marker")
    st["hint"] = "The marker shows where Barnard's Star was detected on each date."
    rep = run(CASES / "moving_neighbor.json", case)
    assert failing(rep) == {"identity_and_prediction"}
    assert "detection" in failures(rep, "identity_and_prediction")


def test_marker_display_requirement_called_detection_fails_identity():
    case = load(CASES / "fair_comparison.json")
    case["display_requirements"]["marker"] = "Detected position of Epsilon Indi B in each frame."
    rep = run(CASES / "fair_comparison.json", case)
    msgs = failures(rep, "identity_and_prediction")
    assert "does not label the marker as a catalog prediction" in msgs
    assert "describes the catalog marker as a detection" in msgs


def test_detection_wording_is_allowed_in_unsupported_list():
    # moving_neighbor already says "The marker shows where the star was detected" as a NOT supported claim.
    case = load(CASES / "moving_neighbor.json")
    assert any("detected" in s for s in case["conclusion_guide"]["not_supported"])
    assert check(run(CASES / "moving_neighbor.json"), "identity_and_prediction")["status"] == "pass"


def test_asserting_unidentified_target_fails_identity():
    case = load(STAGE / "case.json")
    case["conclusion_guide"]["supported"][4] = "The dot near the marker is WISE 0855."
    em = load(STAGE / "evidence_map.json")
    em["conclusions"]["supported"][4]["text"] = case["conclusion_guide"]["supported"][4]
    tmp_map = STAGE / "evidence_map.json"
    ctx = build_context(STAGE / "case.json", case=case, products_root=STAGE / "presets", evidence_map_path=tmp_map)
    ctx.evidence_map = em  # in memory only; the committed map is unchanged
    rep = admit(ctx)
    assert "asserts the target is identified" in failures(rep, "identity_and_prediction")


def test_flag_presented_as_proof_of_cause_fails_quality():
    case = load(STAGE / "case.json")
    st = next(s for s in case["steps"] if s["id"] == "jumping_dot")
    st["hint"] += " It was a cosmic ray."
    rep = run(STAGE / "case.json", case, **STAGE_KW)
    assert failing(rep) == {"quality_interpretation"}
    assert "specific physical cause" in failures(rep, "quality_interpretation")


def test_unknown_flag_name_fails_quality():
    case = load(CASES / "fair_comparison.json")
    st = case["steps"][1]
    st["hint"] = st["hint"].replace("TRANSIENT and NONFUNC", "TRANSIENT and GHOSTLY")
    rep = run(CASES / "fair_comparison.json", case)
    assert "GHOSTLY" in failures(rep, "quality_interpretation")


def test_unstated_quality_confound_fails_confounds():
    case = load(CASES / "moving_neighbor.json")

    def scrub(t: str) -> str:
        return re.sub(r"(?i)\b(quality|flag\w*)\b", "detail", t)

    case["opening_question"] = scrub(case["opening_question"])
    case["claim_prompt"] = scrub(case["claim_prompt"])
    for st in case["steps"]:
        st["prompt"], st["hint"] = scrub(st["prompt"]), scrub(st["hint"])
    rep = run(CASES / "moving_neighbor.json", case)
    assert "confound 'quality'" in failures(rep, "confounds")


def test_secret_in_case_fails_no_new_dependencies():
    case = load(CASES / "fair_comparison.json")
    case["sources"].append({"label": "signed link", "url": "https://example.org/x?token=abcdef0123456789"})
    rep = run(CASES / "fair_comparison.json", case)
    assert "secret" in failures(rep, "no_new_dependencies")


def test_unretained_frame_fails_no_new_dependencies():
    case = copy.deepcopy(load(CASES / "fair_comparison.json"))
    case["frames"][0]["sha256_of_retained_cutout"] = "0" * 64
    rep = run(CASES / "fair_comparison.json", case)
    assert "not the retained cutout" in failures(rep, "no_new_dependencies")
    assert "sha256" in failures(rep, "provenance").lower()


def test_missing_product_set_fails_frame_references_and_catalog(tmp_path):
    rep = run(STAGE / "case.json", products_root=tmp_path, evidence_map_path=STAGE / "evidence_map.json")
    assert "does not exist" in failures(rep, "frame_references")
    assert "catalog_integration" in failing(rep)
