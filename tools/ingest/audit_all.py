"""Run the candidate-B processor over every retained cutout (no products written).

Checks per-target quality counts against targets.json ``retained_frames``,
confirms that uncovered positions get ``wavelength_um: null``, and measures
runtime and output sizes. Writes a small JSON summary.

Usage:
  .venv/bin/python tools/ingest/audit_all.py --targets path/to/targets.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

from common import DEFAULT_BUILD_DATA, REPO, frame_input_dict, load_json, target_by_id

from backend.data.process import FrameInput, process_frame


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-data", default=DEFAULT_BUILD_DATA)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", default=str(REPO / "backend" / "tests" / "data" / "artifacts" / "audit_all.json"))
    args = ap.parse_args()

    bd = Path(args.build_data)
    manifest = load_json(bd / "manifest.json")
    targets = load_json(args.targets)
    counts = defaultdict(Counter)
    times, png_sizes, flag_sizes, url_sizes = [], [], [], []
    not_covered, wl_old_diffs, failures = [], [], []
    for entry in manifest["files"]:
        if entry.get("status") != "downloaded":
            continue
        tid = entry["target_id"]
        t = target_by_id(targets, tid)
        raw = (bd / entry["file"]).read_bytes()
        meta = FrameInput.from_dict(frame_input_dict(t, entry, manifest, tid))
        t0 = time.perf_counter()
        try:
            pf = process_frame(raw, meta)
        except Exception as exc:  # report, keep going
            failures.append({"file": entry["file"], "error": repr(exc)})
            continue
        times.append((time.perf_counter() - t0) * 1000.0)
        rec = pf.record
        png_sizes.append(len(pf.png_bytes))
        flag_sizes.append(len(pf.flag_png_bytes or b""))
        url_sizes.append(len(rec["image"]["src"]) + (len(rec["flag_image"]["src"]) if rec["flag_image"] else 0))
        st = rec["quality"]["status"]
        counts[tid][st] += 1
        if st == "not_covered":
            not_covered.append(
                {
                    "frame_key": rec["frame_key"],
                    "observed_at_utc": rec["observed_at_utc"],
                    "wavelength_um": rec["wavelength_um"],
                    "old_audit_wavelength_um": entry.get("wavelength_um"),
                    "source_pixel": rec["registration"]["checked_position_source_pixel"],
                }
            )
        elif entry.get("wavelength_um") is not None and rec["wavelength_um"] is not None:
            wl_old_diffs.append(abs(rec["wavelength_um"] - entry["wavelength_um"]))

    per_target = {}
    for t in targets["targets"]:
        exp = t["retained_frames"]
        got = counts[t["id"]]
        obs = {"total": sum(got.values()), "clear": got["clear"], "flagged": got["flagged"], "not_covered": got["not_covered"], "unknown": got["unknown"]}
        per_target[t["id"]] = {"expected": exp, "observed": obs, "match": all(obs[k] == exp[k] for k in ("total", "clear", "flagged", "not_covered"))}

    summary = {
        "processor": "perigee-processor-b/0.1.0",
        "frames_processed": len(times),
        "failures": failures,
        "per_target": per_target,
        "not_covered_frames": not_covered,
        "max_abs_wavelength_diff_vs_old_manifest_um": max(wl_old_diffs) if wl_old_diffs else None,
        "runtime_ms": {
            "median": round(statistics.median(times), 1),
            "p95": round(sorted(times)[int(0.95 * (len(times) - 1))], 1),
            "max": round(max(times), 1),
            "note": "process_frame wall time incl. FITS parse, resample, PNG encode, base64; single process, Apple laptop",
        },
        "size_bytes": {
            "png_median": int(statistics.median(png_sizes)),
            "png_max": max(png_sizes),
            "flag_png_median": int(statistics.median(flag_sizes)),
            "flag_png_max": max(flag_sizes),
            "both_data_urls_chars_median": int(statistics.median(url_sizes)),
            "both_data_urls_chars_max": max(url_sizes),
        },
    }
    Path(args.out).write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("frames_processed", "per_target", "runtime_ms", "size_bytes", "max_abs_wavelength_diff_vs_old_manifest_um")}, indent=1))
    print("not covered:", json.dumps(not_covered, indent=1))
    print("failures:", failures)


if __name__ == "__main__":
    main()
