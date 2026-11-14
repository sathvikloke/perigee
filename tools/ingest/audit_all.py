"""Regression gate: run processor A over every retained cutout and check it.

Adapted from candidate processor B's ``tools/ingest/audit_all.py`` (worker 06)
for processor A (``backend/data/process.py``) and A's field names. Reads the
local download ledger and original FITS (read only), writes nothing unless
``--out`` is given, and exits non-zero on any failure.

Checks:

1. every ``downloaded`` ledger entry processes without error;
2. per preset, the clear / flagged / not_covered (and total) counts equal
   ``retained_frames`` in ``backend/content/targets.json``; no ``unknown``;
3. every ``not_covered`` frame has a null wavelength and bandwidth, and every
   covered frame has a wavelength;
4. each case frame in ``backend/content/cases/*.json`` matches: wavelength to
   1e-4 um, observation time compared as parsed UTC instants (A writes a
   trailing ``Z``; the case files do not), quality status and sha256;
5. unless ``--skip-products``: each committed preset record
   (``backend/content/presets/<preset>/frames/<frame_key>.json``) agrees with
   the fresh run on status, wavelength, sha256, native scale and
   processing_version, i.e. the committed products are not stale.

    .venv/bin/python -m tools.ingest.audit_all --data-root "$PERIGEE_DATA_ROOT"
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.data.process import PROCESSING_VERSION, FrameInput, process_frame  # noqa: E402
from tools.ingest.ingest import load_json, manifest_index, target_input  # noqa: E402

CONTENT = REPO / "backend" / "content"
WL_TOL_UM = 1e-4
STATUSES = ("clear", "flagged", "not_covered")


def parse_utc(s: Optional[str]) -> Optional[datetime]:
    """ISO-8601 time with or without a trailing Z, as an aware UTC datetime."""
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    d = datetime.fromisoformat(s)
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


def frame_input(rec: Dict[str, Any], manifest: Dict[str, Any], tgt: Dict[str, Any]) -> FrameInput:
    """The same per-frame inputs tools/ingest/ingest.py uses (per-frame stretch)."""
    qc = tgt["query_center"]
    return FrameInput(
        query_ra_deg=qc["ra_deg"],
        query_dec_deg=qc["dec_deg"],
        fov_arcmin=float(tgt.get("default_fov_arcmin") or 6),
        target=target_input(tgt),
        source_url=rec["archive_url"],
        cutout_url=rec["source_url"],
        observation_id=rec["obs_id"],
        collection_id=rec["collection"],
        detector=rec["detector"],
        retrieved_at_utc=manifest.get("created_utc"),
        retrieved_at_basis="Download-ledger creation time (manifest.json created_utc); per-file retrieval time not recorded.",
        expected_sha256=rec.get("sha256"),
    )


# Wavelengths are compared with a tolerance, not ==: the same code and pinned
# numpy/astropy give results that differ in the last bits between macOS arm64
# (where the products were built) and Linux x86-64 (CI, Vercel), up to ~3e-15
# relative. 1e-9 um is far above that noise and far below any real change
# (the case check uses 1e-4 um). (Sagar, PR #35.)
WAVELENGTH_TOL_UM = 1e-9


def _as_wavelength(v: Any) -> Optional[float]:
    """A finite float, or None when ``v`` is not a usable wavelength (bool,
    non-number, NaN, +/-inf). JSON null is handled by the caller."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def wavelength_differs(committed: Any, rebuilt: Any, tol: float = WAVELENGTH_TOL_UM) -> bool:
    """True when the committed and freshly rebuilt wavelengths disagree.

    Both null: equal (off-image, no wavelength). One null: differs. Any value
    that is not a finite number (NaN, inf, strings, booleans) counts as a
    difference, so it can never pass as equal (abs(nan - x) > tol is False).
    Otherwise they differ when |a - b| > tol.
    """
    if committed is None and rebuilt is None:
        return False
    if committed is None or rebuilt is None:
        return True
    a, b = _as_wavelength(committed), _as_wavelength(rebuilt)
    if a is None or b is None:
        return True
    return not abs(a - b) <= tol


def audit(data_root: Path, targets_path: Path, cases_dir: Path, presets_dir: Optional[Path]) -> Dict[str, Any]:
    manifest = load_json(data_root / "manifest.json")
    idx = manifest_index(manifest)
    targets = load_json(targets_path)
    tby = {t["id"]: t for t in targets["targets"]}
    failures: List[Dict[str, Any]] = []
    counts: Dict[str, Counter] = defaultdict(Counter)
    records: Dict[str, Dict[str, Any]] = {}
    times: List[float] = []
    png_sizes: List[int] = []
    flag_sizes: List[int] = []

    for key, rec in sorted(idx.items()):
        tid = rec["target_id"]
        raw = (data_root / rec["file"]).read_bytes()
        t0 = time.perf_counter()
        try:
            pf = process_frame(raw, frame_input(rec, manifest, tby[tid]))
        except Exception as exc:  # report and keep going
            failures.append({"check": "process", "frame_key": key, "error": f"{type(exc).__name__}: {exc}"})
            continue
        times.append((time.perf_counter() - t0) * 1000.0)
        png_sizes.append(len(pf.png_bytes))
        flag_sizes.append(len(pf.flag_png_bytes or b""))
        r = pf.record
        records[key] = r
        st = r["quality"]["status"]
        counts[tid][st] += 1
        if st == "not_covered":
            if r["wavelength_um"] is not None or r["bandwidth_um"] is not None:
                failures.append({"check": "null_wavelength", "frame_key": key, "wavelength_um": r["wavelength_um"]})
        elif r["wavelength_um"] is None:
            failures.append({"check": "covered_has_wavelength", "frame_key": key})

    # ---- per-preset counts vs targets.json
    per_preset = {}
    for tid, t in tby.items():
        exp = t.get("retained_frames") or {}
        got = counts.get(tid, Counter())
        obs = {"total": sum(got.values()), **{s: got[s] for s in STATUSES}, "unknown": got["unknown"]}
        ok = all(obs[k] == exp.get(k) for k in ("total",) + STATUSES) and obs["unknown"] == 0
        per_preset[tid] = {"expected": {k: exp.get(k) for k in ("total",) + STATUSES}, "observed": obs, "match": ok}
        if not ok:
            failures.append({"check": "preset_counts", "preset_id": tid, "expected": exp, "observed": obs})

    # ---- case frames vs case JSON
    case_rows = []
    for cp in sorted(cases_dir.glob("*.json")):
        case = load_json(cp)
        for f in case["frames"]:
            key = f["frame_key"]
            r = records.get(key)
            if r is None:
                failures.append({"check": "case_frame_missing", "case_id": case["case_id"], "frame_key": key})
                continue
            ew, ow = f.get("wavelength_um"), r["wavelength_um"]
            row = {
                "case_id": case["case_id"], "ref": f.get("ref"), "frame_key": key,
                "wavelength_um": [ew, ow],
                "wavelength_ok": (ew is None and ow is None)
                or (ew is not None and ow is not None and abs(ew - ow) <= WL_TOL_UM + 1e-12),
                "observed_at_utc": [f.get("observed_at_utc"), r["observed_at_utc"]],
                "time_ok": parse_utc(f.get("observed_at_utc")) is not None
                and parse_utc(f.get("observed_at_utc")) == parse_utc(r["observed_at_utc"]),
                "quality": [f.get("expected_quality_status"), r["quality"]["status"]],
                "quality_ok": f.get("expected_quality_status") == r["quality"]["status"],
                "sha256_ok": f.get("sha256_of_retained_cutout") == r["provenance"]["sha256"],
            }
            row["ok"] = all(row[k] for k in ("wavelength_ok", "time_ok", "quality_ok", "sha256_ok"))
            case_rows.append(row)
            if not row["ok"]:
                failures.append({"check": "case_frame", **row})

    # ---- committed products are not stale
    product_check = None
    if presets_dir is not None:
        stale, missing = [], []
        for key, r in records.items():
            p = presets_dir / idx[key]["target_id"] / "frames" / f"{key}.json"
            if not p.exists():
                missing.append(key)
                continue
            c = load_json(p)
            diffs = {}
            if c["quality"]["status"] != r["quality"]["status"]:
                diffs["status"] = [c["quality"]["status"], r["quality"]["status"]]
            if wavelength_differs(c["wavelength_um"], r["wavelength_um"]):
                diffs["wavelength_um"] = [c["wavelength_um"], r["wavelength_um"]]
            if c["provenance"]["sha256"] != r["provenance"]["sha256"]:
                diffs["sha256"] = True
            if c["registration"]["native_scale_arcsec_per_px"] != r["registration"]["native_scale_arcsec_per_px"]:
                diffs["native_scale_arcsec_per_px"] = [c["registration"]["native_scale_arcsec_per_px"],
                                                       r["registration"]["native_scale_arcsec_per_px"]]
            if c["provenance"]["processing_version"] != PROCESSING_VERSION:
                diffs["processing_version"] = c["provenance"]["processing_version"]
            if diffs:
                stale.append({"frame_key": key, **diffs})
        product_check = {"checked": len(records) - len(missing), "missing": missing, "stale": stale[:20],
                         "stale_count": len(stale), "ok": not missing and not stale}
        if not product_check["ok"]:
            failures.append({"check": "committed_products", "missing": len(missing), "stale": len(stale)})

    return {
        "processor": PROCESSING_VERSION,
        "frames_in_ledger": len(idx),
        "frames_processed": len(records),
        "per_preset": per_preset,
        "case_frames": case_rows,
        "committed_products": product_check,
        "not_covered_frames": sorted(k for k, r in records.items() if r["quality"]["status"] == "not_covered"),
        "runtime_ms": {
            "median": round(statistics.median(times), 1) if times else None,
            "max": round(max(times), 1) if times else None,
            "note": "process_frame wall time (FITS parse, resample, PNG encode); single process",
        },
        "size_bytes": {
            "png_median": int(statistics.median(png_sizes)) if png_sizes else None,
            "png_max": max(png_sizes) if png_sizes else None,
            "flag_png_median": int(statistics.median(flag_sizes)) if flag_sizes else None,
            "flag_png_max": max(flag_sizes) if flag_sizes else None,
        },
        "failures": failures,
        "ok": not failures,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data-root", default=os.environ.get("PERIGEE_DATA_ROOT"),
                    help="research/build_data directory (or env PERIGEE_DATA_ROOT)")
    ap.add_argument("--targets", default=str(CONTENT / "targets.json"))
    ap.add_argument("--cases", default=str(CONTENT / "cases"), help="directory of case JSON files")
    ap.add_argument("--presets", default=str(CONTENT / "presets"), help="committed product tree to check")
    ap.add_argument("--skip-products", action="store_true", help="do not compare with committed products")
    ap.add_argument("--out", default=None, help="write the full JSON summary here")
    a = ap.parse_args(argv)
    if not a.data_root:
        ap.error("--data-root or PERIGEE_DATA_ROOT is required")
    rep = audit(Path(a.data_root), Path(a.targets), Path(a.cases), None if a.skip_products else Path(a.presets))
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
    short = {k: rep[k] for k in ("processor", "frames_in_ledger", "frames_processed", "not_covered_frames",
                                 "runtime_ms", "size_bytes", "failures", "ok")}
    short["per_preset"] = {k: {**v["observed"], "match": v["match"]} for k, v in rep["per_preset"].items()}
    short["case_frames"] = [{k: row[k] for k in ("case_id", "frame_key", "wavelength_um", "quality", "ok")}
                            for row in rep["case_frames"]]
    if rep["committed_products"] is not None:
        short["committed_products"] = {k: rep["committed_products"][k] for k in ("checked", "stale_count", "ok")}
    print(json.dumps(short, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
