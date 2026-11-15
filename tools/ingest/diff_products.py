"""Prove that two curated product trees differ only in allowed JSON fields.

Compares ``--old`` (e.g. the committed ``backend/content/presets``) with
``--new`` (a regeneration into a scratch directory):

* the two trees hold exactly the same file paths;
* every non-JSON file (PNG intensity and flag images) is byte-identical;
* every JSON file is equal after ignoring the allowed leaf fields, compared
  by structure (key order and float formatting cannot hide a change).

Default allowed fields: ``registration.native_scale_arcsec_per_px`` and
``provenance.processing_version`` in each FrameRecord (top level or inside a
``frames.json`` index), plus the index-level ``processing_version``.

Exit status 0 only when no disallowed difference exists.

    .venv/bin/python -m tools.ingest.diff_products --old backend/content/presets --new /tmp/regen
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_ALLOWED = (
    "registration.native_scale_arcsec_per_px",
    "provenance.processing_version",
    "processing_version",
)


def _walk(a: Any, b: Any, path: Tuple[str, ...], out: List[Tuple[str, Any, Any]]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((".".join(path + (k,)), a.get(k, "<missing>"), b.get(k, "<missing>")))
            else:
                _walk(a[k], b[k], path + (k,), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((".".join(path) + "[len]", len(a), len(b)))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            _walk(x, y, path + (f"[{i}]",), out)
    elif type(a) is not type(b) or a != b:
        out.append((".".join(path), a, b))


def _allowed(path: str, allowed: Tuple[str, ...]) -> bool:
    # Strip a leading "frames.[i]." so index entries share the per-record rules.
    parts = path.split(".")
    if len(parts) > 2 and parts[0] == "frames" and parts[1].startswith("["):
        parts = parts[2:]
    return ".".join(parts) in allowed


def compare(old: Path, new: Path, allowed: Tuple[str, ...]) -> Dict[str, Any]:
    of = {p.relative_to(old).as_posix() for p in old.rglob("*") if p.is_file()}
    nf = {p.relative_to(new).as_posix() for p in new.rglob("*") if p.is_file()}
    report: Dict[str, Any] = {
        "only_in_old": sorted(of - nf),
        "only_in_new": sorted(nf - of),
        "files_compared": 0,
        "binary_identical": 0,
        "binary_different": [],
        "json_identical": 0,
        "json_allowed_only": 0,
        "json_disallowed": {},
        "allowed_field_changes": {k: 0 for k in allowed},
        "native_scale_max_abs_delta": 0.0,
    }
    for rel in sorted(of & nf):
        report["files_compared"] += 1
        a, b = (old / rel).read_bytes(), (new / rel).read_bytes()
        if not rel.endswith(".json"):
            if a == b:
                report["binary_identical"] += 1
            else:
                report["binary_different"].append(rel)
            continue
        diffs: List[Tuple[str, Any, Any]] = []
        _walk(json.loads(a), json.loads(b), (), diffs)
        bad = [d for d in diffs if not _allowed(d[0], allowed)]
        if bad:
            report["json_disallowed"][rel] = [{"path": p, "old": x, "new": y} for p, x, y in bad[:20]]
        elif diffs:
            report["json_allowed_only"] += 1
        else:
            report["json_identical"] += 1
        for p, x, y in diffs:
            if _allowed(p, allowed):
                key = next(k for k in allowed if p.endswith(k))
                report["allowed_field_changes"][key] += 1
                if key.endswith("native_scale_arcsec_per_px") and isinstance(x, float) and isinstance(y, float):
                    report["native_scale_max_abs_delta"] = max(report["native_scale_max_abs_delta"], abs(x - y))
    report["ok"] = not (
        report["only_in_old"] or report["only_in_new"] or report["binary_different"] or report["json_disallowed"]
    )
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--allow", action="append", default=None,
                    help="allowed dotted field path (repeatable); default: native scale + processing_version")
    a = ap.parse_args(argv)
    allowed = tuple(a.allow) if a.allow else DEFAULT_ALLOWED
    rep = compare(Path(a.old), Path(a.new), allowed)
    print(json.dumps(rep, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
