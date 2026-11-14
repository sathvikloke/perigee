"""Build curated preset frame products for the case frames (candidate B).

Reads original FITS cutouts from the local build_data directory (read-only),
runs backend.data.process.process_frame, and writes small products to
backend/content/presets/<preset_id>/frames/<frame_key>.{json,png,flags.png}
plus backend/content/presets/<preset_id>/frames.json.

It also writes backend/tests/data/artifacts/case_check.json comparing each
frame with the expectations in the case JSON.

Usage:
  .venv/bin/python tools/ingest/build_case_frames.py \
      --targets path/to/targets.json --case path/to/fair_comparison.json \
      --case path/to/moving_neighbor.json
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from common import DEFAULT_BUILD_DATA, REPO, frame_input_dict, load_json, manifest_entry, target_by_id

from backend.data.process import FrameInput, process_frame, sample_display, shared_limits

# Which case frames share one display stretch (from each case's display_requirements).
STRETCH_GROUPS = {
    "fair_comparison": [["A", "B"], ["C"]],  # C is a different wavelength: own stretch, labelled
    "moving_neighbor": [["A", "B", "C"]],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-data", default=DEFAULT_BUILD_DATA)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--case", action="append", required=True)
    ap.add_argument("--out", default=str(REPO / "backend" / "content" / "presets"))
    ap.add_argument("--report", default=str(REPO / "backend" / "tests" / "data" / "artifacts" / "case_check.json"))
    args = ap.parse_args()

    bd = Path(args.build_data)
    manifest = load_json(bd / "manifest.json")
    targets = load_json(args.targets)
    out_root = Path(args.out)
    report: List[Dict[str, Any]] = []
    index: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for case_path in args.case:
        case = load_json(case_path)
        cid = case["case_id"]
        preset = case["target_id"]
        t = target_by_id(targets, preset)
        frames = {f["ref"]: f for f in case["frames"]}
        inputs: Dict[str, Dict[str, Any]] = {}
        for ref, cf in frames.items():
            entry = manifest_entry(manifest, cf["observation_id"], cf["detector"])
            if entry is None:
                raise SystemExit(f"{cid} {ref}: no downloaded cutout for {cf['frame_key']}")
            raw = (bd / entry["file"]).read_bytes()
            inputs[ref] = {"bytes": raw, "meta": frame_input_dict(t, entry, manifest, preset), "case": cf}

        groups = STRETCH_GROUPS.get(cid, [[r] for r in frames])
        for group in groups:
            limits = None
            basis = None
            if len(group) > 1:
                sampled = [sample_display(inputs[r]["bytes"], FrameInput.from_dict(inputs[r]["meta"])) for r in group]
                limits = shared_limits(sampled)
                keys = ", ".join(inputs[r]["case"]["frame_key"] for r in group)
                basis = f"percentiles 0.5-99.5 of the pooled finite native pixels inside the display grid of {keys} (case {cid})"
            for ref in group:
                item = inputs[ref]
                md = dict(item["meta"])
                md["embed_data_urls"] = True
                if limits is not None:
                    md["display_limits"] = limits
                    md["display_limits_basis"] = basis
                t0 = time.perf_counter()
                pf = process_frame(item["bytes"], FrameInput.from_dict(md))
                ms = (time.perf_counter() - t0) * 1000.0
                rec = pf.record
                data_url_len = len(rec["image"]["src"])
                flag_url_len = len(rec["flag_image"]["src"]) if rec["flag_image"] else 0
                key = rec["frame_key"]
                fdir = out_root / preset / "frames"
                fdir.mkdir(parents=True, exist_ok=True)
                rec["image"]["src"] = f"presets/{preset}/frames/{key}.png"
                if rec["flag_image"] is not None:
                    rec["flag_image"]["src"] = f"presets/{preset}/frames/{key}.flags.png"
                rec["provenance"]["retrieved_at_note"] = "Creation time of the local download manifest for this cutout batch."
                (fdir / f"{key}.png").write_bytes(pf.png_bytes)
                if pf.flag_png_bytes is not None:
                    (fdir / f"{key}.flags.png").write_bytes(pf.flag_png_bytes)
                (fdir / f"{key}.json").write_text(json.dumps(rec, indent=1, sort_keys=False) + "\n", encoding="utf-8")

                cf = item["case"]
                idx = index.setdefault(preset, {}).setdefault(
                    key,
                    {
                        "frame_key": key,
                        "observation_id": rec["observation_id"],
                        "detector": rec["detector"],
                        "collection_id": rec["collection_id"],
                        "observed_at_utc": rec["observed_at_utc"],
                        "mjd": rec["mjd"],
                        "wavelength_um": rec["wavelength_um"],
                        "quality_status": rec["quality"]["status"],
                        "display_scale_mode": rec["display_scale"]["mode"],
                        "record": f"presets/{preset}/frames/{key}.json",
                        "image": rec["image"]["src"],
                        "flag_image": rec["flag_image"]["src"] if rec["flag_image"] else None,
                        "cases": [],
                    },
                )
                idx["cases"].append({"case_id": cid, "ref": ref})

                obs_wl = rec["wavelength_um"]
                exp_wl = cf["wavelength_um"]
                report.append(
                    {
                        "case_id": cid,
                        "ref": ref,
                        "frame_key": key,
                        "expected": {
                            "wavelength_um": exp_wl,
                            "bandwidth_um": cf.get("bandwidth_um"),
                            "observed_at_utc": cf["observed_at_utc"],
                            "mjd": cf["mjd"],
                            "quality_status": cf["expected_quality_status"],
                            "sha256": cf["sha256_of_retained_cutout"],
                            "source_url": cf["source_url"],
                        },
                        "observed": {
                            "wavelength_um": obs_wl,
                            "bandwidth_um": rec["bandwidth_um"],
                            "observed_at_utc": rec["observed_at_utc"],
                            "mjd": rec["mjd"],
                            "quality_status": rec["quality"]["status"],
                            "adverse_over_aperture": f"{rec['quality']['adverse_aperture_pixels']}/{rec['quality']['aperture_pixels']}",
                            "flag_names": rec["quality"]["flag_names"],
                            "sha256": rec["provenance"]["sha256"],
                            "source_url": rec["source_url"],
                            "marker_xy": [rec["marker"]["x"], rec["marker"]["y"]] if rec["marker"] else None,
                            "display_scale_mode": rec["display_scale"]["mode"],
                        },
                        "match": {
                            "wavelength_1e-4": obs_wl is not None and abs(round(obs_wl, 4) - exp_wl) < 1e-9,
                            "bandwidth_1e-4": rec["bandwidth_um"] is not None and abs(round(rec["bandwidth_um"], 4) - cf.get("bandwidth_um", -1)) < 1e-9,
                            "date": rec["observed_at_utc"] == cf["observed_at_utc"],
                            "mjd": abs(rec["mjd"] - cf["mjd"]) < 1e-9,
                            "quality_status": rec["quality"]["status"] == cf["expected_quality_status"],
                            "sha256": rec["provenance"]["sha256"] == cf["sha256_of_retained_cutout"],
                            "source_url": rec["source_url"] == cf["source_url"],
                        },
                        "measurements": {
                            "process_ms": round(ms, 1),
                            "png_bytes": len(pf.png_bytes),
                            "flag_png_bytes": len(pf.flag_png_bytes or b""),
                            "png_data_url_chars": data_url_len,
                            "flag_data_url_chars": flag_url_len,
                        },
                    }
                )

    for preset, frames in index.items():
        ordered = sorted(frames.values(), key=lambda f: (f["mjd"], f["frame_key"]))
        doc = {
            "schema_version": 1,
            "preset_id": preset,
            "processing_version": "perigee-processor-b/0.1.0",
            "ordering": "mjd (MJD-AVG), then frame_key",
            "frames": ordered,
        }
        (out_root / preset / "frames.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")

    rp = Path(args.report)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")

    print("| case | ref | frame_key | λ exp | λ obs | bw exp | bw obs | date match | quality exp/obs | sha256 | ms | PNG B | data-URL chars |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in report:
        e, o, m, s = r["expected"], r["observed"], r["match"], r["measurements"]
        print(
            f"| {r['case_id']} | {r['ref']} | {r['frame_key']} | {e['wavelength_um']} | {o['wavelength_um']} | {e['bandwidth_um']} | {o['bandwidth_um']} "
            f"| {m['date']} | {e['quality_status']}/{o['quality_status']} ({o['adverse_over_aperture']}) | {m['sha256']} | {s['process_ms']} | {s['png_bytes']} | {s['png_data_url_chars']} |"
        )
    bad = [r for r in report if not all(r["match"].values())]
    print(f"\n{len(report) - len(bad)}/{len(report)} frames match every expectation")
    for r in bad:
        print("MISMATCH", r["case_id"], r["ref"], {k: v for k, v in r["match"].items() if not v})


if __name__ == "__main__":
    main()
