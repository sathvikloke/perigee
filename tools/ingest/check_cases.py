"""Compare the packaged case frames with the authored case JSON (integration board decision 6).

    python tools/ingest/check_cases.py [--cases backend/content/cases]

For every frame in each case file: the packaged record must exist and match on collection,
source URL, date (mid-exposure), wavelength (to 1e-4 um) and quality status. Exits 1 on any
mismatch. Read-only: never edits case content.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRESETS = REPO / "backend" / "content" / "presets"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, default=REPO / "backend" / "content" / "cases")
    args = ap.parse_args()
    index = json.loads((PRESETS / "manifest.json").read_text())
    sets = {s["for_case"]: s for p in index["presets"] for s in p["comparison_sets"]}
    problems, checked = [], 0
    for case_path in sorted(args.cases.glob("*.json")):
        case = json.loads(case_path.read_text())
        cid = case["case_id"]
        if cid not in sets:
            problems.append(f"{cid}: no packaged set")
            continue
        doc = json.loads((PRESETS / sets[cid]["path"]).read_text())
        recs = {r["frame_key"]: r for r in doc["frames"]}
        for f in case["frames"]:
            checked += 1
            r = recs.get(f["frame_key"])
            tag = f"{cid} {f.get('ref')} {f['frame_key']}"
            if r is None:
                problems.append(f"{tag}: missing from package")
                continue
            checks = {
                "collection": r["collection_id"] == f["collection_id"],
                "source_url": r["source_url"] == f["source_url"],
                "date": r["observed_at_utc"].rstrip("Z") == f["observed_at_utc"].rstrip("Z"),
                "wavelength": r["wavelength_um"] is not None and abs(r["wavelength_um"] - f["wavelength_um"]) <= 1e-4,
                "quality": r["quality"]["status"] == f["expected_quality_status"],
                "ref": r.get("case_ref") == f.get("ref"),
            }
            bad = [k for k, ok in checks.items() if not ok]
            line = f"{tag}: wl {r['wavelength_um']:.5f} vs {f['wavelength_um']}, {r['observed_at_utc']} , {r['quality']['status']}"
            print(("MISMATCH " + ",".join(bad) + " | " if bad else "ok  ") + line)
            if bad:
                problems.append(f"{tag}: {bad}")
    print(f"{checked} case frames checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
