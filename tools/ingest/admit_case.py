"""Admission check for an authored investigation case (N7).

Validates one case JSON in the existing schema (``backend/content/cases/*.json``)
against the generated frame products the case would be served with, the
shipped preset records and ``targets.json``. It never edits content.

Checks (each reports pass / warn / fail with specific reasons):

``structure``              required fields, ids, refs, step ``check`` paths exist in the records
``frame_references``       every frame resolves to a record in ``<products>/<target>/case-<case_id>/``,
                           identity fields agree, image and flag-overlay assets exist
``provenance``             source URL, collection and SHA-256 agree with the record; https sources
``metadata_agreement``     dates, MJD, wavelength, band width and quality status agree with the records
``quoted_numbers``         wavelengths, dates, "N of M" pixel counts and unit-bearing numbers in the text
                           agree with records, derived pair quantities or the evidence registry
``confounds``              every confound present in the data (time, wavelength, stretch, quality) is
                           named in the learner-facing questions or hints
``display_claims``         shared-grid / shared-stretch / own-stretch claims are true; grey-level
                           examples match the stretch formula; different stretches are acknowledged
``quality_interpretation`` quoted flag names exist; non-finite pixels are explained; no flag is
                           presented as proof of a specific physical cause
``identity_and_prediction`` markers are catalog predictions and never described as detections; the
                           target is not asserted as identified when the evidence says it is not
``answer_key``             supported and unsupported conclusions exist, unsupported ones give a reason,
                           evidence references resolve (per conclusion when an evidence map is given)
``no_new_dependencies``    frames are already-retained data, products are small PNG/JSON only, no
                           secrets or opaque model dependencies
``catalog_integration``    the backend CatalogStore loads the case and serves its frames as ``ready``

Usage (repository root)::

    .venv/bin/python -m tools.ingest.admit_case backend/content/cases/fair_comparison.json
    .venv/bin/python -m tools.ingest.admit_case science/staging/wise_0855_quality_trap/case.json \\
        --products-root science/staging/wise_0855_quality_trap/presets \\
        --evidence-map science/staging/wise_0855_quality_trap/evidence_map.json

Exit status 0 means admitted (no failing check). Warnings are reported but do
not block admission; they name what this tool could not verify.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CONTENT_ROOT = REPO / "backend" / "content"

REQUIRED_KEYS = (
    "schema_version", "case_id", "content_version", "status", "title", "target_id", "opening_question",
    "summary", "frames", "display_requirements", "steps", "claim_prompt", "evidence_requirements",
    "conclusion_guide", "limitations", "sources", "verification",
)
REQUIRED_FRAME_KEYS = (
    "ref", "frame_key", "observation_id", "detector", "collection_id", "observed_at_utc", "mjd",
    "wavelength_um", "bandwidth_um", "expected_quality_status", "source_url", "sha256_of_retained_cutout",
)
ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")
SOURCE_HOSTS = ("https://irsa.ipac.caltech.edu/",)
WAVELENGTH_TOL_UM = 1e-4 + 1e-12   # authored wavelengths are rounded to 4 decimals (ingest.compare_case)
MJD_TOL = 1e-8
MAX_PRODUCT_BYTES = 2_000_000
PRODUCT_SUFFIXES = (".png", ".json")
INFORMATIONAL_FLAGS = {"SOURCE", "FULLSAMPLE"}
MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"])}
NEGATION_RE = re.compile(r"\b(not|no|never|cannot|can't|isn't|aren't|wasn't|doesn't|don't|didn't|rather than|"
                         r"instead of|without|nor)\b|n't\b", re.I)
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|secret|password|passwd|bearer)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+]{8,}", re.I),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"[?&](?:token|sig|signature|key)=[A-Za-z0-9_\-.%]{8,}", re.I),
]
MODEL_DEP_RE = re.compile(
    r"\b(LLM|GPT-?\d*|ChatGPT|OpenAI|Anthropic|Claude|neural network|machine[- ]learning model|"
    r"onnx|pytorch|tensorflow|hugging ?face|inference API)\b", re.I)
CAUSE_RE = re.compile(
    r"\b(?:is|was|are|were)\s+(?:a\s+|an\s+|probably\s+a\s+|likely\s+a\s+)?(?:cosmic[- ]ray|hot pixel|satellite trail)"
    r"|\bcaused by\s+(?:a\s+)?(?:cosmic[- ]ray|hot pixel|satellite)"
    r"|\bflags?\s+(?:prove|proves|show that|shows that|confirm|confirms)\b", re.I)
DETECTION_RE = re.compile(r"\b(detect(?:ed|ion|ions|s)?|measured position|observed position|position measured|found at)\b", re.I)

# Unit classes for quoted numbers. Order matters: longer phrases first.
UNIT_PATTERNS: List[Tuple[str, str]] = [
    ("arcsec/yr", r"(?:arcsec(?:onds?)?|″)\s*(?:per\s+year|/\s*yr)"),
    ("arcmin", r"arcmin(?:utes?)?|′"),
    ("arcsec", r"arcsec(?:onds?)?|″"),
    ("display px", r"display\s+(?:px|pixels?)"),
    ("native px", r"(?:native|SPHEREx)\s+(?:px|pixels?)"),
    ("days", r"days?"),
    ("MJy/sr", r"MJy\s*/\s*sr"),
    ("band widths", r"band\s*widths?"),
    ("light-years", r"light[- ]years?"),
    ("%", r"%"),
]
APPROX_RE = re.compile(r"(about|approximately|roughly|nearly|around|almost|under|over|less than|more than|"
                       r"within|~|≈|up to|at most|at least)\s*$", re.I)
NUM = r"(\d+(?:\.\d+)?)"


@dataclass
class Check:
    name: str
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        return "fail" if self.failures else ("warn" if self.warnings else "pass")

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "status": self.status, "failures": self.failures, "warnings": self.warnings,
                "details": self.details}


@dataclass
class Context:
    case: Dict[str, Any]
    case_path: Optional[Path]
    content_root: Path
    products_root: Path
    targets: Dict[str, Dict[str, Any]]
    records: Dict[str, Dict[str, Any]]           # ref -> record (case set)
    product_dir: Path
    product_index: Optional[Dict[str, Any]]
    evidence_map: Optional[Dict[str, Any]]
    answer_evidence: Optional[Dict[str, Any]]
    manifest: Optional[Dict[str, Any]]


# ---------------------------------------------------------------- helpers
def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def get_path(obj: Any, dotted: str) -> Tuple[bool, Any]:
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9'\"(])", text or "") if s.strip()]


def learner_texts(case: Dict[str, Any], include_not_supported: bool = True) -> List[Tuple[str, str]]:
    """(location, text) pairs a learner or a reviewer reads."""
    out: List[Tuple[str, str]] = []
    for k in ("title", "opening_question", "summary", "claim_prompt"):
        if isinstance(case.get(k), str):
            out.append((k, case[k]))
    bg = case.get("background") or {}
    if isinstance(bg.get("short"), str):
        out.append(("background.short", bg["short"]))
    for i, d in enumerate(bg.get("details") or []):
        out.append((f"background.details[{i}]", d))
    for k, v in (case.get("display_requirements") or {}).items():
        if isinstance(v, str):
            out.append((f"display_requirements.{k}", v))
    for i, st in enumerate(case.get("steps") or []):
        for k in ("prompt", "hint"):
            if isinstance(st.get(k), str):
                out.append((f"steps[{i}].{k}", st[k]))
    cg = case.get("conclusion_guide") or {}
    for i, s in enumerate(cg.get("supported") or []):
        out.append((f"conclusion_guide.supported[{i}]", s))
    if include_not_supported:
        for i, s in enumerate(cg.get("not_supported") or []):
            out.append((f"conclusion_guide.not_supported[{i}]", s))
    if isinstance(cg.get("example_claim"), str):
        out.append(("conclusion_guide.example_claim", cg["example_claim"]))
    for i, s in enumerate(case.get("limitations") or []):
        out.append((f"limitations[{i}]", s))
    return out


def question_texts(case: Dict[str, Any]) -> str:
    parts = [case.get("opening_question") or "", case.get("claim_prompt") or ""]
    for st in case.get("steps") or []:
        parts += [st.get("prompt") or "", st.get("hint") or ""]
    return "\n".join(parts)


def refs_in(sentence: str, refs: Sequence[str]) -> List[str]:
    """Case frame refs named in a sentence. A capital 'A' at the start of a
    sentence is an article unless it is followed by 'and', a comma, '+', ')'
    or 'share'/'has'."""
    found = []
    for r in refs:
        for m in re.finditer(r"(?<![A-Za-z0-9_'’-])" + re.escape(r) + r"(?![A-Za-z0-9_'’-])", sentence):
            if r == "A":
                after = sentence[m.end():m.end() + 8]
                before = sentence[max(0, m.start() - 6):m.start()]
                if not (re.match(r"\s*(?:and\b|or\b|,|\+|\)|/|share|has|is\b|$)", after)
                        or re.search(r"(?:and|or|,|\+|/|\(|in|frames?)\s*$", before)):
                    continue
            found.append(r)
            break
    return found


def round_tol(token: str) -> float:
    """Half a unit of the last quoted digit."""
    if "." in token:
        return 0.5 * 10 ** (-len(token.split(".")[1]))
    return 0.5


def utc(record_value: str) -> datetime:
    return datetime.fromisoformat(record_value.rstrip("Z"))


def grey_level(ds: Dict[str, Any], v: float) -> int:
    soft = float(ds.get("asinh_softening") or 10.0)
    t = min(max((v - ds["low"]) / (ds["high"] - ds["low"]), 0.0), 1.0)
    return round(255 * math.asinh(t * soft) / math.asinh(soft))


def same_scale(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return abs(a["low"] - b["low"]) < 1e-9 and abs(a["high"] - b["high"]) < 1e-9 and a.get("method") == b.get("method")


def repo_paths(text: str) -> List[str]:
    return sorted({m.split("#")[0] for m in re.findall(r"[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-#]+)+\.(?:md|py|json)(?:#[\w-]+)?", text or "")})


# ---------------------------------------------------------------- loading
def build_context(case_path: Path, content_root: Path = DEFAULT_CONTENT_ROOT, products_root: Optional[Path] = None,
                  evidence_map_path: Optional[Path] = None, data_root: Optional[Path] = None,
                  case: Optional[Dict[str, Any]] = None) -> Context:
    case = case if case is not None else load_json(case_path)
    products_root = Path(products_root) if products_root else Path(content_root) / "presets"
    targets_doc = load_json(Path(content_root) / "targets.json")
    targets = {t["id"]: t for t in targets_doc.get("targets", []) if isinstance(t, dict) and "id" in t}
    product_dir = products_root / str(case.get("target_id")) / f"case-{case.get('case_id')}"
    product_index = None
    records: Dict[str, Dict[str, Any]] = {}
    if (product_dir / "frames.json").is_file():
        product_index = load_json(product_dir / "frames.json")
    by_key: Dict[str, Dict[str, Any]] = {}
    if product_dir.is_dir():
        for p in sorted(product_dir.glob("*.json")):
            if p.name == "frames.json":
                continue
            try:
                rec = load_json(p)
            except ValueError:
                continue
            if isinstance(rec, dict) and isinstance(rec.get("frame_key"), str):
                by_key[rec["frame_key"]] = rec
    for f in case.get("frames") or []:
        if isinstance(f, dict) and f.get("frame_key") in by_key:
            records[f.get("ref")] = by_key[f["frame_key"]]
    evidence_map = answer_evidence = None
    if evidence_map_path:
        evidence_map = load_json(evidence_map_path)
        ae = evidence_map.get("answer_evidence")
        if ae:
            ae_path = (Path(evidence_map_path).parent / ae).resolve()
            answer_evidence = load_json(ae_path) if ae_path.is_file() else None
    manifest = None
    if data_root and (Path(data_root) / "manifest.json").is_file():
        manifest = load_json(Path(data_root) / "manifest.json")
    return Context(case, case_path, Path(content_root), products_root, targets, records, product_dir, product_index,
                   evidence_map, answer_evidence, manifest)


# ---------------------------------------------------------------- checks
def check_structure(ctx: Context) -> Check:
    c = Check("structure")
    case = ctx.case
    for k in REQUIRED_KEYS:
        if k not in case:
            c.fail(f"missing top-level field '{k}'")
    try:
        from backend.platform.catalog_models import CaseDocument
        CaseDocument.model_validate(case)
    except Exception as exc:  # pydantic ValidationError or import failure
        c.fail(f"CaseDocument validation failed: {type(exc).__name__}")
    cid = case.get("case_id")
    if not (isinstance(cid, str) and ID_RE.match(cid)):
        c.fail(f"case_id {cid!r} is not a valid content id")
    if ctx.case_path is not None and ctx.case_path.name.endswith(".json") and ctx.case_path.stem not in (cid, "case"):
        c.fail(f"file name '{ctx.case_path.name}' does not match case_id '{cid}'")
    if case.get("target_id") not in ctx.targets:
        c.fail(f"target_id {case.get('target_id')!r} is not in targets.json")
    frames = case.get("frames") or []
    refs = [f.get("ref") for f in frames if isinstance(f, dict)]
    if len(frames) < 2:
        c.fail("a case needs at least two frames")
    if len(set(refs)) != len(refs):
        c.fail(f"duplicate frame refs {refs}")
    keys = [f.get("frame_key") for f in frames if isinstance(f, dict)]
    if len(set(keys)) != len(keys):
        c.fail(f"duplicate frame_keys {keys}")
    for f in frames:
        missing = [k for k in REQUIRED_FRAME_KEYS if k not in f]
        if missing:
            c.fail(f"frame {f.get('ref')}: missing {missing}")
    er = case.get("evidence_requirements") or {}
    for group in er.get("must_include_refs_any_of") or []:
        for r in group:
            if r not in refs:
                c.fail(f"evidence_requirements names ref {r!r} that is not a case frame")
    steps = case.get("steps") or []
    if not steps:
        c.fail("no steps")
    ids = [s.get("id") for s in steps]
    if len(set(ids)) != len(ids):
        c.fail(f"duplicate step ids {ids}")
    for s in steps:
        if not s.get("prompt"):
            c.fail(f"step {s.get('id')}: no prompt")
        for path in s.get("check") or []:
            present = [r for r, rec in ctx.records.items() if get_path(rec, path)[0]]
            if ctx.records and not present:
                c.fail(f"step {s.get('id')}: check field '{path}' does not exist in the frame records")
    c.details = {"refs": refs, "steps": ids, "status_field": case.get("status")}
    if case.get("status") not in ("science_owner_approved",):
        c.warn(f"status is {case.get('status')!r}: not approved for shipping")
    return c


def check_frame_references(ctx: Context) -> Check:
    c = Check("frame_references")
    case = ctx.case
    if not ctx.product_dir.is_dir():
        c.fail(f"product set {ctx.product_dir} does not exist (generate it with tools.ingest.ingest case)")
        return c
    if ctx.product_index is None:
        c.fail(f"{ctx.product_dir}/frames.json is missing")
    assets = (ctx.product_index or {}).get("assets") or {}
    index_keys = {r.get("frame_key") for r in (ctx.product_index or {}).get("frames", [])}
    for f in case.get("frames") or []:
        ref, key = f.get("ref"), f.get("frame_key")
        rec = ctx.records.get(ref)
        if rec is None:
            c.fail(f"frame {ref}: frame_key {key!r} has no record in {ctx.product_dir.name}/")
            continue
        if key not in index_keys:
            c.fail(f"frame {ref}: {key} is not listed in frames.json")
        expect_key = f"{f.get('observation_id')}_D{f.get('detector')}"
        if key != expect_key:
            c.fail(f"frame {ref}: frame_key {key} does not equal <observation_id>_D<detector> = {expect_key}")
        for fld in ("observation_id", "detector"):
            if rec.get(fld) != f.get(fld):
                c.fail(f"frame {ref}: {fld} {f.get(fld)!r} != record {rec.get(fld)!r}")
        if rec.get("case_id") not in (None, case.get("case_id")):
            c.fail(f"frame {ref}: record belongs to case {rec.get('case_id')!r}")
        if rec.get("case_ref") not in (None, ref):
            c.fail(f"frame {ref}: record case_ref is {rec.get('case_ref')!r}")
        if rec.get("preset_id") not in (None, case.get("target_id")):
            c.fail(f"frame {ref}: record preset_id {rec.get('preset_id')!r} != target_id")
        for img in ("image", "flag_image"):
            src = (rec.get(img) or {}).get("src")
            if not src:
                if img == "image":
                    c.fail(f"frame {ref}: record has no image")
                else:
                    c.warn(f"frame {ref}: record has no flag overlay")
                continue
            aid = src.rsplit("/", 1)[-1]
            rel = assets.get(aid)
            if rel is None:
                c.fail(f"frame {ref}: {img} asset {aid} is not in frames.json assets")
                continue
            if not (ctx.products_root / rel).is_file():
                c.fail(f"frame {ref}: {img} file {rel} is missing")
    return c


def check_provenance(ctx: Context) -> Check:
    c = Check("provenance")
    shipped_dir = ctx.content_root / "presets" / str(ctx.case.get("target_id")) / "frames"
    for f in ctx.case.get("frames") or []:
        ref = f.get("ref")
        rec = ctx.records.get(ref)
        url = f.get("source_url") or ""
        if not url.startswith(SOURCE_HOSTS):
            c.fail(f"frame {ref}: source_url is not an https IRSA URL: {url!r}")
        if rec is None:
            continue
        prov = rec.get("provenance") or {}
        if url != rec.get("source_url"):
            c.fail(f"frame {ref}: source_url differs from the record")
        if prov.get("original_url") not in (None, rec.get("source_url")):
            c.fail(f"frame {ref}: record provenance.original_url differs from record source_url")
        if f.get("collection_id") != rec.get("collection_id"):
            c.fail(f"frame {ref}: collection_id {f.get('collection_id')!r} != record {rec.get('collection_id')!r}")
        if f.get("sha256_of_retained_cutout") != prov.get("sha256"):
            c.fail(f"frame {ref}: sha256_of_retained_cutout does not match record provenance.sha256")
        shipped = shipped_dir / f"{f.get('frame_key')}.json"
        if shipped.is_file():
            srec = load_json(shipped)
            if (srec.get("provenance") or {}).get("sha256") != prov.get("sha256"):
                c.fail(f"frame {ref}: SHA-256 differs from the shipped preset record {shipped.name}")
        if ctx.manifest is not None:
            ent = [e for e in ctx.manifest.get("files", []) if e.get("obs_id") == f.get("observation_id")
                   and e.get("detector") == f.get("detector") and e.get("target_id") == ctx.case.get("target_id")]
            if not any(e.get("sha256") == prov.get("sha256") for e in ent):
                c.fail(f"frame {ref}: SHA-256 not found in the download ledger manifest")
    for s in ctx.case.get("sources") or []:
        if not (isinstance(s, dict) and str(s.get("url", "")).startswith("https://") and s.get("label")):
            c.fail(f"source entry {s!r} needs a label and an https url")
    return c


def check_metadata(ctx: Context) -> Check:
    c = Check("metadata_agreement")
    rows = []
    for f in ctx.case.get("frames") or []:
        ref = f.get("ref")
        rec = ctx.records.get(ref)
        if rec is None:
            continue
        row = {"ref": ref}
        try:
            row["date_ok"] = utc(rec["observed_at_utc"]) == utc(f["observed_at_utc"])
        except (KeyError, ValueError, TypeError):
            row["date_ok"] = False
        row["mjd_ok"] = isinstance(rec.get("mjd"), (int, float)) and abs(rec["mjd"] - f.get("mjd", float("nan"))) < MJD_TOL
        for k in ("wavelength_um", "bandwidth_um"):
            ev, ov = f.get(k), rec.get(k)
            row[f"{k}_ok"] = (ev is None and ov is None) or (ev is not None and ov is not None and abs(ev - ov) <= WAVELENGTH_TOL_UM)
        row["quality_ok"] = (rec.get("quality") or {}).get("status") == f.get("expected_quality_status")
        rows.append(row)
        pairs = {
            "date": (f.get("observed_at_utc"), rec.get("observed_at_utc")),
            "mjd": (f.get("mjd"), rec.get("mjd")),
            "wavelength_um": (f.get("wavelength_um"), rec.get("wavelength_um")),
            "bandwidth_um": (f.get("bandwidth_um"), rec.get("bandwidth_um")),
            "quality": (f.get("expected_quality_status"), (rec.get("quality") or {}).get("status")),
        }
        for k, v in row.items():
            if k != "ref" and not v:
                fld = k[:-3]
                case_v, rec_v = pairs[fld]
                c.fail(f"frame {ref}: {fld} disagrees with the record (case {case_v!r}, record {rec_v!r})")
    c.details["rows"] = rows
    return c


def _derived_quantities(ctx: Context) -> List[Dict[str, Any]]:
    """Quantities computed from the records: pair time differences, wavelength
    differences, predicted marker shifts and grid scales."""
    out: List[Dict[str, Any]] = []
    recs = ctx.records
    refs = list(recs)
    for i, a in enumerate(refs):
        ra = recs[a]
        sc = (ra.get("registration") or {}).get("scale_arcsec_per_px")
        nsc = (ra.get("registration") or {}).get("native_scale_arcsec_per_px")
        if sc:
            out.append({"id": f"grid_scale_{a}", "value": sc, "unit": "arcsec", "tolerance": 0.01})
        if nsc:
            out.append({"id": f"native_scale_{a}", "value": nsc, "unit": "arcsec", "tolerance": 0.02})
        q = ra.get("quality") or {}
        if q.get("screen_radius_native_px") is not None:
            out.append({"id": "screen_radius", "value": q["screen_radius_native_px"], "unit": "native px", "tolerance": 0})
        for b in refs[i + 1:]:
            rb = recs[b]
            if isinstance(ra.get("mjd"), (int, float)) and isinstance(rb.get("mjd"), (int, float)):
                out.append({"id": f"days_{a}{b}", "value": abs(rb["mjd"] - ra["mjd"]), "unit": "days", "tolerance": 0.0})
            if ra.get("wavelength_um") is not None and rb.get("wavelength_um") is not None:
                d = abs(rb["wavelength_um"] - ra["wavelength_um"])
                out.append({"id": f"dlambda_{a}{b}", "value": d, "unit": "um", "tolerance": 0.0})
                bw = min(ra.get("bandwidth_um") or 0, rb.get("bandwidth_um") or 0)
                if bw:
                    out.append({"id": f"dlambda_bw_{a}{b}", "value": d / bw, "unit": "band widths", "tolerance": 0.0})
                    out.append({"id": f"dlambda_pct_{a}{b}", "value": 100 * d / bw, "unit": "%", "tolerance": 0.0})
            ma, mb = ra.get("marker") or {}, rb.get("marker") or {}
            if all(isinstance(m.get(k), (int, float)) for m in (ma, mb) for k in ("x", "y")):
                dpx = math.hypot(ma["x"] - mb["x"], ma["y"] - mb["y"])
                out.append({"id": f"marker_px_{a}{b}", "value": dpx, "unit": "display px", "tolerance": 0.0})
                if sc:
                    out.append({"id": f"marker_arcsec_{a}{b}", "value": dpx * sc, "unit": "arcsec", "tolerance": 0.0})
                    if nsc:
                        out.append({"id": f"marker_native_{a}{b}", "value": dpx * sc / nsc, "unit": "native px", "tolerance": 0.0})
    return out


def _matches(value: float, token: str, approx: bool, q: Dict[str, Any]) -> bool:
    tol = max(float(q.get("tolerance") or 0.0), round_tol(token))
    if approx:
        tol = max(tol, 0.25 * abs(q["value"]), round_tol(token) * 2)
    return abs(value - float(q["value"])) <= tol + 1e-9


def check_quoted_numbers(ctx: Context) -> Check:
    c = Check("quoted_numbers")
    case = ctx.case
    frames = [f for f in case.get("frames") or [] if isinstance(f, dict)]
    recs = ctx.records
    registry = list((ctx.answer_evidence or {}).get("quantities") or [])
    strict = bool(registry)
    derived = _derived_quantities(ctx)
    wl_values = [r.get(k) for r in recs.values() for k in ("wavelength_um", "bandwidth_um") if r.get(k) is not None]
    wl_values += [q["value"] for q in derived if q["unit"] == "um"]
    wl_values += [q["value"] for q in registry if q.get("unit") == "um"]
    dates = [utc(r["observed_at_utc"]) for r in recs.values() if r.get("observed_at_utc")]
    verified, unverified = [], []

    for loc, text in learner_texts(case):
        # Wavelengths, including ranges "1.26-1.44 µm" and lists "2.006, 2.012 and 2.028 µm".
        for m in re.finditer(r"((?:\d+(?:\.\d+)?\s*(?:,|and|to|–|-|or)\s*)*\d+(?:\.\d+)?)\s*(?:µm|μm|um|microns?)\b", text):
            for tok in re.findall(r"\d+(?:\.\d+)?", m.group(1)):
                v = float(tok)
                approx = bool(APPROX_RE.search(text[:m.start()][-20:])) or bool(re.search(r"\b(near|around)\s*$", text[:m.start()]))
                tol = round_tol(tok) * (2 if approx else 1)
                if any(abs(v - w) <= tol + 1e-12 for w in wl_values):
                    verified.append(f"{loc}: {tok} µm")
                else:
                    have = ", ".join(f"{r}={recs[r]['wavelength_um']:.4f}" for r in recs
                                     if recs[r].get("wavelength_um") is not None)
                    c.fail(f"{loc}: quoted wavelength {tok} µm matches no frame wavelength, band width or registered "
                           f"difference (frames: {have})")
        # Dates.
        for d in _date_mentions(text):
            ok = any((d["year"] is None or dt.year == d["year"]) and dt.month == d["month"]
                     and (d["day"] is None or dt.day == d["day"]) for dt in dates)
            if ok:
                verified.append(f"{loc}: date {d['text']}")
            else:
                c.fail(f"{loc}: quoted date '{d['text']}' matches no frame observation date "
                       f"({', '.join(sorted({x.strftime('%Y-%m-%d') for x in dates}))})")
        # "N of M screened pixels"
        for m in re.finditer(r"\b(\d+) of (\d+)\b(?=[^.]{0,40}pixels)", text):
            n, tot = int(m.group(1)), int(m.group(2))
            if any((r.get("quality") or {}).get("adverse_aperture_pixels") == n and (r.get("quality") or {}).get("screened_pixels") == tot
                   for r in recs.values()):
                verified.append(f"{loc}: {n} of {tot} pixels")
            else:
                c.fail(f"{loc}: '{n} of {tot}' pixels matches no record's adverse/screened counts")
        # Grey-level examples are checked in display_claims. Other unit-bearing numbers:
        consumed: List[Tuple[int, int]] = []
        for unit, pat in UNIT_PATTERNS:
            # "8 arcsec", and ranges "4.5 to 11.8 arcseconds" / "4.5-11.8 arcsec" (both ends checked)
            for m in re.finditer(r"(?:" + NUM + r"\s*(?:to|–|-)\s*)?" + NUM + r"\s*(?:" + pat + r")(?![A-Za-z])", text):
                if any(a <= m.start() < b for a, b in consumed):
                    continue  # already read with a longer unit (e.g. arcsec per year)
                consumed.append((m.start(), m.end()))
                if unit == "MJy/sr" and re.search(r"grey", text[m.end():m.end() + 30]):
                    continue  # probe values: display_claims checks the grey levels they map to
                approx = bool(APPROX_RE.search(text[:m.start()][-20:]))
                cands = [q for q in registry + derived if q.get("unit") == unit]
                for tok in (t for t in (m.group(1), m.group(2)) if t):
                    if any(_matches(float(tok), tok, approx, q) for q in cands):
                        verified.append(f"{loc}: {tok} {unit}")
                    elif strict:
                        c.fail(f"{loc}: quoted {tok} {unit} (in '{m.group(0).strip()}') matches no record-derived "
                               "quantity or evidence registry entry")
                    else:
                        unverified.append(f"{loc}: {tok} {unit} (in '{m.group(0).strip()}')")
    if unverified:
        c.warn(f"{len(unverified)} unit-bearing numbers are not tied to a record-derived quantity and no evidence "
               "registry was supplied; they are reported, not verified")
    c.details = {"verified": verified, "unverified": unverified, "registry_entries": len(registry),
                 "frames": [f.get("ref") for f in frames]}
    return c


def _date_mentions(text: str) -> List[Dict[str, Any]]:
    out = []
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        out.append({"text": m.group(0), "year": int(m.group(1)), "month": int(m.group(2)), "day": int(m.group(3))})
    month_alt = "|".join(MONTHS)
    pat = re.compile(r"(?:\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:(?:and|to|or)\s+(\d{1,2})(?:st|nd|rd|th)?\s+)?)?"
                     r"\b(" + month_alt + r")\b(?:\s+(\d{1,2})(?:st|nd|rd|th)?(?![\d:]))?(?:,?\s+(\d{4})\b)?", re.I)
    for m in pat.finditer(text):
        month = MONTHS[m.group(3).lower()]
        if month == 5 and m.group(3) == "may" :
            continue  # lowercase "may" is a verb
        year = int(m.group(5)) if m.group(5) else None
        if year is None:
            look = re.match(r"[^.;]{0,40}?\b(\d{4})\b", text[m.end():])
            if look and 1990 < int(look.group(1)) < 2100:
                year = int(look.group(1))
        days = [int(d) for d in (m.group(1), m.group(2), m.group(4)) if d]
        if not days:
            out.append({"text": m.group(0).strip(), "year": year, "month": month, "day": None})
        for d in days:
            out.append({"text": m.group(0).strip(), "year": year, "month": month, "day": d})
    return out


def check_confounds(ctx: Context) -> Check:
    c = Check("confounds")
    recs = ctx.records
    q = question_texts(ctx.case)
    present: Dict[str, str] = {"time": "frames have different observation times"}
    refs = list(recs)
    wl_conf = False
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            ra, rb = recs[a], recs[b]
            if ra.get("wavelength_um") is None or rb.get("wavelength_um") is None:
                continue
            bw = min(ra.get("bandwidth_um") or 1, rb.get("bandwidth_um") or 1)
            if abs(ra["wavelength_um"] - rb["wavelength_um"]) > 0.5 * bw:
                wl_conf = True
    if wl_conf:
        present["wavelength"] = "target wavelengths differ by more than half a band width between some frames"
    scales = [r.get("display_scale") for r in recs.values() if r.get("display_scale")]
    if any(not same_scale(scales[0], s) for s in scales[1:]):
        present["stretch"] = "frames are drawn with different display stretches"
    if any((r.get("quality") or {}).get("status") != "clear" for r in recs.values()):
        present["quality"] = "at least one frame is flagged at the screened position"
    words = {
        "time": r"\b(date|time|apart|month|year|day|\d{4})\w*",
        "wavelength": r"\b(wavelength|colou?r|µm|μm)\b",
        "stretch": r"\b(stretch\w*|contrast|grey levels?|gray levels?)\b",
        "quality": r"\b(quality|flag\w*)\b",
    }
    for k, why in present.items():
        if not re.search(words[k], q, re.I):
            c.fail(f"confound '{k}' is present ({why}) but the opening question, steps and claim prompt never name it")
    if not re.search(r"\bcaus\w*|\bwhy\b|\bwhat (?:else|still)\b|fair", q, re.I):
        c.warn("the questions never ask what causes a difference")
    builds = {str(r.get("provenance", {}).get("pipeline_version")) for r in recs.values()}
    cols = {r.get("collection_id") for r in recs.values()}
    if len(builds) > 1 or len(cols) > 1:
        lim = " ".join(ctx.case.get("limitations") or []) + " " + question_texts(ctx.case)
        if not re.search(r"pipeline|release|build|reprocess", lim, re.I):
            c.fail(f"frames come from different pipeline builds/collections ({sorted(builds)}, {sorted(cols)}) "
                   "but neither the questions nor the limitations say so")
    c.details = {"confounds_present": present}
    return c


SHARED_RE = re.compile(r"shared (?:asinh |contrast |display )?stretch|share (?:one|a|the same)\b[^.]*?stretch|same (?:asinh |contrast |display )?stretch|one shared stretch", re.I)
OWN_RE = re.compile(r"(?:its|their) own (?:asinh |contrast |display )?stretch|per-frame stretch|separate (?:contrast )?stretch", re.I)


def check_display_claims(ctx: Context) -> Check:
    c = Check("display_claims")
    recs = ctx.records
    refs = [f.get("ref") for f in ctx.case.get("frames") or []]
    dr = ctx.case.get("display_requirements") or {}
    grids = {r: (rec.get("registration") or {}).get("grid_id") for r, rec in recs.items()}
    if len(set(grids.values())) > 1:
        if re.search(r"identical|same grid|shared grid|one grid", dr.get("grid", ""), re.I):
            c.fail(f"display_requirements.grid claims one grid but grid_ids differ: {grids}")
        elif not re.search(r"grid", question_texts(ctx.case), re.I):
            c.fail(f"frames are on different grids {grids} and the case does not make that part of the task")
    scales = {r: rec.get("display_scale") for r, rec in recs.items() if rec.get("display_scale")}
    claimed_shared: List[List[str]] = []
    claimed_own: List[str] = []
    grey_checks: List[str] = []
    for loc, text in learner_texts(ctx.case, include_not_supported=False):
        for s in sentences(text):
            if SHARED_RE.search(s) and not NEGATION_RE.search(s.split("stretch")[0][-40:]):
                rs = refs_in(s, refs)
                if re.search(r"\ball (?:three|four|frames)\b|\bacross all\b", s, re.I) and len(rs) < 2:
                    rs = list(refs)
                if len(rs) >= 2:
                    claimed_shared.append(rs)
                    base = scales.get(rs[0])
                    for r in rs[1:]:
                        if base is None or scales.get(r) is None or not same_scale(base, scales[r]):
                            c.fail(f"{loc}: claims {', '.join(rs)} share a stretch, but {rs[0]} and {r} have different "
                                   "display_scale limits in the case products")
            om = OWN_RE.search(s)
            if om:
                for r in refs_in(s[:om.start()], refs):
                    claimed_own.append(r)
                    others = [o for o in scales if o != r]
                    if scales.get(r) is not None and any(same_scale(scales[r], scales[o]) for o in others):
                        c.fail(f"{loc}: claims {r} has its own stretch, but it shares display_scale limits with another frame")
            # grey-level examples: "<v> MJy/sr is grey <g> in A and B but grey <h> in C"
            mv = re.search(NUM + r"\s*MJy\s*/\s*sr", s)
            if mv and "grey" in s.lower():
                v = float(mv.group(1))
                for gm in re.finditer(r"grey (\d+) in ((?:[A-Z](?:,\s*| and | or )?)+)", s):
                    g = int(gm.group(1))
                    for r in refs_in(gm.group(2), refs):
                        if r in scales:
                            exp = grey_level(scales[r], v)
                            grey_checks.append(f"{loc}: {v} MJy/sr in {r}: text {g}, computed {exp}")
                            if abs(exp - g) > 1:
                                c.fail(f"{loc}: says {v} MJy/sr is grey {g} in {r}; the case stretch gives {exp}")
    # Different stretches must be acknowledged (or be part of the task).
    groups: List[List[str]] = []
    for r, s in scales.items():
        for g in groups:
            if same_scale(scales[g[0]], s):
                g.append(r)
                break
        else:
            groups.append([r])
    if len(groups) > 1:
        acknowledged = set(claimed_own) | {r for g in claimed_shared for r in g}
        singletons = [g[0] for g in groups if len(g) == 1]
        if not set(singletons) <= acknowledged and not re.search(r"not directly comparable|per-frame|own stretch",
                                                                 dr.get("stretch", ""), re.I):
            c.fail(f"frames use different stretches {groups} but the case never tells the learner")
    if not dr.get("stretch"):
        c.fail("display_requirements.stretch is missing")
    c.details = {"grid_ids": grids, "stretch_groups": groups, "claimed_shared": claimed_shared, "claimed_own": claimed_own,
                 "grey_level_checks": grey_checks}
    return c


def check_quality(ctx: Context) -> Check:
    c = Check("quality_interpretation")
    vocab = set(INFORMATIONAL_FLAGS)
    for rec_path in (ctx.content_root / "presets").glob("*/*/*.json"):
        try:
            rec = load_json(rec_path)
        except ValueError:
            continue
        if isinstance(rec, dict) and isinstance(rec.get("quality"), dict):
            vocab |= set((rec["quality"].get("flag_counts") or {}).keys())
            vocab |= set(rec["quality"].get("flag_names") or [])
    vocab |= set(((ctx.answer_evidence or {}).get("flag_definitions_from_FITS_header") or {}).keys())
    texts = learner_texts(ctx.case)
    flag_like = re.compile(r"\b(?:[A-Z]{4,}(?:_[A-Z]+)?)\b")
    non_flag_caps = {"SPHEREX", "NASA", "IRSA", "SIMBAD", "WISE", "CATWISE", "GAIA", "IPAC", "HST", "ESA", "DR3",
                     "MJD", "UTC", "PNG", "FITS", "AVG", "DATE", "IMAGE", "FLAGS", "VARIANCE"}
    for loc, text in texts:
        for tok in set(flag_like.findall(text)):
            if tok in non_flag_caps or tok.upper() != tok:
                continue
            if tok not in vocab:
                c.fail(f"{loc}: '{tok}' looks like a flag name but is not in the SPHEREx flag vocabulary seen in records")
    for loc, text in texts:
        if loc.startswith("conclusion_guide.not_supported"):
            continue
        for s in sentences(text):
            if CAUSE_RE.search(s) and not NEGATION_RE.search(s):
                c.fail(f"{loc}: presents a flag or feature as proof of a specific physical cause: '{s}'")
    allq = question_texts(ctx.case) + " " + " ".join(t for _, t in texts)
    for ref, rec in ctx.records.items():
        q = rec.get("quality") or {}
        if (q.get("nonfinite_aperture_pixels") or 0) > 0:
            if not re.search(r"non-finite|saturat|no usable value|transparent", allq, re.I):
                c.fail(f"frame {ref}: {q['nonfinite_aperture_pixels']} non-finite screened pixels but the case never "
                       "explains non-finite or saturated pixels")
        if q.get("status") == "flagged":
            names = [n for n in q.get("flag_names") or []]
            if not (re.search(r"\bflag", allq, re.I) and (not names or any(n in allq for n in names) or "saturat" in allq.lower())):
                c.fail(f"frame {ref}: flagged ({names}) but the case does not name the flags or explain them")
    if not re.search(r"not (?:a|the same as a) detection|is not a detection|not detect|does not (?:prove|mean)|no (?:problem )?flags? (?:were )?found",
                     allq, re.I) and any((r.get("quality") or {}).get("status") == "clear" for r in ctx.records.values()):
        c.warn("a frame passes the quality screen but the case never says that passing is not a detection")
    c.details = {"flag_vocabulary_size": len(vocab)}
    return c


def check_identity(ctx: Context) -> Check:
    c = Check("identity_and_prediction")
    target = ctx.targets.get(ctx.case.get("target_id")) or {}
    for ref, rec in ctx.records.items():
        kind = (rec.get("marker") or {}).get("kind")
        if kind != "catalog_prediction":
            c.fail(f"frame {ref}: marker.kind is {kind!r}, expected 'catalog_prediction'")
    dr_marker = (ctx.case.get("display_requirements") or {}).get("marker", "")
    if not re.search(r"predict", dr_marker, re.I):
        c.fail("display_requirements.marker does not label the marker as a catalog prediction")
    for loc, text in learner_texts(ctx.case, include_not_supported=False):
        is_marker_field = loc == "display_requirements.marker"
        for s in sentences(text):
            if not (is_marker_field or re.search(r"\bmarker|catalog(?:ue)?[- ]predict|\bprediction\b", s, re.I)):
                continue
            if DETECTION_RE.search(s) and not NEGATION_RE.search(s):
                c.fail(f"{loc}: describes the catalog marker as a detection or measurement: '{s}'")
    ti = (ctx.answer_evidence or {}).get("target_identity") or (ctx.evidence_map or {}).get("target_identity")
    names = [n for n in (target.get("display_name"), target.get("simbad_name")) if n]
    if ti and ti.get("status") != "identified":
        name_re = "|".join(re.escape(n) for n in names)
        for loc, text in learner_texts(ctx.case, include_not_supported=False):
            if not (loc.startswith("conclusion_guide") or loc.startswith("steps") or loc == "summary"):
                continue
            for s in sentences(text):
                if s.endswith("?"):
                    continue
                if re.search(r"\b(?:is|are|shows?|detects?|detected|see|seen|visible)\b[^.]{0,30}\b(?:" + name_re + r")\b|\b(?:"
                             + name_re + r")\b\s+(?:is|was)\s+(?:visible|detected|seen|the dot|that dot)", s, re.I) \
                        and not NEGATION_RE.search(s) and not re.search(r"\bwhether\b|\bif\b|\bexpected\b|\bshould\b", s, re.I):
                    c.fail(f"{loc}: asserts the target is identified although the evidence status is "
                           f"{ti.get('status')!r}: '{s}'")
    elif not ti:
        c.details["target_identity"] = "no evidence map; identity assertions checked only for marker-as-detection wording"
    return c


def check_answer_key(ctx: Context) -> Check:
    c = Check("answer_key")
    cg = ctx.case.get("conclusion_guide") or {}
    sup, uns = cg.get("supported"), cg.get("not_supported")
    if not isinstance(sup, list) or not sup:
        c.fail("conclusion_guide.supported is missing or empty")
        sup = []
    if not isinstance(uns, list) or not uns:
        c.fail("conclusion_guide.not_supported is missing or empty")
        uns = []
    for i, s in enumerate(uns):
        if len(sentences(s)) < 2 and not re.search(r"\bbecause\b|;", s):
            c.fail(f"not_supported[{i}] states a claim without a reason: '{s}'")
    if not cg.get("example_claim"):
        c.warn("conclusion_guide.example_claim is missing")
    ver = ctx.case.get("verification") or {}
    paths = repo_paths(" ".join(str(ver.get(k, "")) for k in ("record", "checked_by")))
    resolved = [p for p in paths if (REPO / p).exists()]
    missing = [p for p in paths if p not in resolved]
    if not resolved:
        c.fail(f"verification.record/checked_by name no evidence file that exists in the repository ({paths})")
    if missing:
        c.warn(f"verification references that do not resolve in this tree: {missing}")
    c.details = {"supported": len(sup), "not_supported": len(uns), "evidence_files": resolved}
    em = ctx.evidence_map
    if em is not None:
        if ctx.answer_evidence is None:
            c.fail("evidence map given but its answer_evidence file could not be loaded")
            return c
        answer_ids = {a["id"] for a in ctx.answer_evidence.get("answers", [])}
        for kind, items in (("supported", sup), ("not_supported", uns)):
            mapped = (em.get("conclusions") or {}).get(kind) or []
            texts = [m.get("text") for m in mapped]
            for i, s in enumerate(items):
                if s not in texts:
                    c.fail(f"{kind}[{i}] has no evidence-map entry: '{s[:70]}...'")
            for m in mapped:
                if m.get("text") not in items:
                    c.fail(f"evidence map lists a {kind} conclusion not in the case: '{str(m.get('text'))[:70]}...'")
                ev = m.get("evidence") or []
                if not ev:
                    c.fail(f"{kind} conclusion has no evidence reference: '{str(m.get('text'))[:70]}...'")
                for e in ev:
                    if e not in answer_ids:
                        c.fail(f"{kind} conclusion cites unknown evidence id {e!r}")
        c.details["evidence_map"] = "every conclusion mapped to answer evidence ids"
    return c


def check_no_new_dependencies(ctx: Context) -> Check:
    c = Check("no_new_dependencies")
    shipped_dir = ctx.content_root / "presets" / str(ctx.case.get("target_id")) / "frames"
    for f in ctx.case.get("frames") or []:
        sp = shipped_dir / f"{f.get('frame_key')}.json"
        in_manifest = ctx.manifest is not None and any(
            e.get("sha256") == f.get("sha256_of_retained_cutout") for e in ctx.manifest.get("files", []))
        if sp.is_file():
            if (load_json(sp).get("provenance") or {}).get("sha256") != f.get("sha256_of_retained_cutout"):
                c.fail(f"frame {f.get('ref')}: not the retained cutout shipped in presets/{ctx.case.get('target_id')}/frames")
        elif not in_manifest:
            c.fail(f"frame {f.get('ref')}: {f.get('frame_key')} is not a shipped/retained frame: new raw data would be needed")
    if ctx.product_dir.is_dir():
        for p in ctx.product_dir.rglob("*"):
            if p.is_file():
                if p.suffix.lower() not in PRODUCT_SUFFIXES:
                    c.fail(f"product set contains a non PNG/JSON file: {p.name}")
                elif p.stat().st_size > MAX_PRODUCT_BYTES:
                    c.fail(f"product file {p.name} is {p.stat().st_size} bytes (> {MAX_PRODUCT_BYTES})")
    blobs = [("case", json.dumps(ctx.case, ensure_ascii=False))]
    if ctx.evidence_map is not None:
        blobs.append(("evidence_map", json.dumps(ctx.evidence_map)))
    if ctx.product_index is not None:
        blobs.append(("frames.json", json.dumps(ctx.product_index)))
    for name, blob in blobs:
        for pat in SECRET_PATTERNS:
            m = pat.search(blob)
            if m:
                c.fail(f"{name}: looks like a secret or signed credential: '{m.group(0)[:12]}...'")
    learner = " ".join(t for _, t in learner_texts(ctx.case)) + " " + " ".join(
        str(s.get("label", "")) + " " + str(s.get("url", "")) for s in ctx.case.get("sources") or [] if isinstance(s, dict))
    m = MODEL_DEP_RE.search(learner)
    if m:
        c.fail(f"case text or sources reference an opaque model dependency: '{m.group(0)}'")
    for k in ("model", "model_id", "llm", "prompt_template"):
        if k in ctx.case:
            c.fail(f"case has a model-dependency field '{k}'")
    return c


def check_catalog(ctx: Context) -> Check:
    c = Check("catalog_integration")
    try:
        from backend.platform.catalog import CatalogStore
    except Exception as exc:
        c.fail(f"cannot import CatalogStore: {type(exc).__name__}")
        return c
    cid, tid = ctx.case.get("case_id"), ctx.case.get("target_id")
    shipped_case = ctx.content_root / "cases" / f"{cid}.json"
    in_place = (ctx.products_root.resolve() == (ctx.content_root / "presets").resolve() and shipped_case.is_file()
                and load_json(shipped_case) == ctx.case)
    tmp = None
    try:
        if in_place:
            root = ctx.content_root
        else:
            tmp = Path(tempfile.mkdtemp(prefix="admit_case_"))
            root = tmp / "content"
            (root / "cases").mkdir(parents=True)
            shutil.copy2(ctx.content_root / "targets.json", root / "targets.json")
            (root / "cases" / f"{cid}.json").write_text(json.dumps(ctx.case), encoding="utf-8")
            src_preset = ctx.content_root / "presets" / str(tid)
            dst_preset = root / "presets" / str(tid)
            if src_preset.is_dir():
                shutil.copytree(src_preset, dst_preset, ignore=shutil.ignore_patterns(f"case-{cid}"))
            if ctx.product_dir.is_dir():
                shutil.copytree(ctx.product_dir, dst_preset / f"case-{cid}")
        store = CatalogStore(root)
        issues = [i for i in store.load_issues if cid in i or str(tid) in i]
        for i in issues:
            c.fail(f"catalog load issue: {i}")
        if store.get_case(cid) is None:
            c.fail(f"CatalogStore did not load case {cid}")
            return c
        fr = store.get_frames(tid, cid)
        if fr is None or not fr.frames_available:
            c.fail(f"CatalogStore serves no frames for {tid}/{cid}: {getattr(fr, 'reason', None)}")
            return c
        if fr.status != "ready":
            c.fail(f"case frame listing status is {fr.status!r}: {fr.warnings}")
        keys = {f.get("frame_key") for f in fr.frames}
        want = {f.get("frame_key") for f in ctx.case.get("frames") or []}
        if keys != want:
            c.fail(f"served frames {sorted(keys)} differ from case frames {sorted(want)}")
        for f in fr.frames:
            for img in ("image", "flag_image"):
                aid = (f.get(img) or {}).get("asset_id")
                if img == "image" and not aid:
                    c.fail(f"served frame {f.get('frame_key')} has no resolvable image asset")
                if aid and store.assets.get(aid) is None:
                    c.fail(f"served asset {aid} is not in the asset index")
        c.details = {"served_frames": len(fr.frames), "status": fr.status, "sets": fr.sets,
                     "content_root": "in place" if in_place else "temporary copy (staged products)"}
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    return c


CHECKS = (check_structure, check_frame_references, check_provenance, check_metadata, check_quoted_numbers,
          check_confounds, check_display_claims, check_quality, check_identity, check_answer_key,
          check_no_new_dependencies, check_catalog)


def admit(ctx: Context) -> Dict[str, Any]:
    results = []
    for fn in CHECKS:
        try:
            results.append(fn(ctx))
        except Exception as exc:  # a crashing check is a failing check, never a silent pass
            ch = Check(fn.__name__.replace("check_", ""))
            ch.fail(f"check raised {type(exc).__name__}: {exc}")
            results.append(ch)
    verdict = "admit" if all(r.status != "fail" for r in results) else "reject"
    return {"case_id": ctx.case.get("case_id"), "verdict": verdict,
            "checks": [r.as_dict() for r in results],
            "inputs": {"case": str(ctx.case_path) if ctx.case_path else None,
                       "products": str(ctx.product_dir),
                       "evidence_map": bool(ctx.evidence_map), "manifest": ctx.manifest is not None}}


def admit_path(case_path: Path, **kw: Any) -> Dict[str, Any]:
    return admit(build_context(Path(case_path), **kw))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("case", type=Path)
    ap.add_argument("--content-root", type=Path, default=DEFAULT_CONTENT_ROOT)
    ap.add_argument("--products-root", type=Path, default=None,
                    help="presets root holding <target>/case-<case_id>/ (default: <content-root>/presets)")
    ap.add_argument("--evidence-map", type=Path, default=None)
    ap.add_argument("--data-root", type=Path, default=None, help="optional raw-data root; its manifest.json is checked")
    ap.add_argument("--json", type=Path, default=None, help="write the full report here")
    a = ap.parse_args(argv)
    rep = admit_path(a.case, content_root=a.content_root, products_root=a.products_root,
                     evidence_map_path=a.evidence_map, data_root=a.data_root)
    print(f"{rep['case_id']}: {rep['verdict'].upper()}")
    for ch in rep["checks"]:
        print(f"  [{ch['status']:4}] {ch['name']}")
        for m in ch["failures"]:
            print(f"         FAIL {m}")
        for m in ch["warnings"]:
            print(f"         warn {m}")
    if a.json:
        a.json.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if rep["verdict"] == "admit" else 1


if __name__ == "__main__":
    sys.path.insert(0, str(REPO))
    raise SystemExit(main())
