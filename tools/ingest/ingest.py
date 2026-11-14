"""Generate small curated frame products from locally retained original FITS.

Runs the pure processor (backend/data/process.py) over FITS files listed in the
local download ledger (research/build_data/manifest.json) and writes, under
``backend/content/presets/<preset_id>/<set>/``:

* ``<frame_key>.png``        fixed-grid intensity image (grey + alpha)
* ``<frame_key>.flags.png``  optional flag overlay (RGBA)
* ``<frame_key>.json``       FrameRecord with ``image.src`` = asset URL
* ``frames.json``            ordered index (records + asset allowlist)

``<set>`` is ``case-<case_id>`` for a case and ``frames`` for a preset run.
Raw FITS are only read; nothing large is written to the repository.

Examples (from the repository root):

    .venv/bin/python -m tools.ingest.ingest case fair_comparison \
        --data-root "/path/to/research/build_data" \
        --targets backend/content/targets.json \
        --case-file backend/content/cases/fair_comparison.json

    .venv/bin/python -m tools.ingest.ingest preset epsilon_indi_b \
        --data-root "/path/to/research/build_data" --targets backend/content/targets.json \
        --frames 2026W18_1A_0516_1_D3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from backend.data.process import (  # noqa: E402
    FrameInput,
    TargetInput,
    display_limits_from_values,
    frame_key,
    process_frame,
    with_image_sources,
)

ASSET_URL_PREFIX = "/api/v1/assets/"
DEFAULT_OUT = REPO / "backend" / "content" / "presets"


def load_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def target_input(t: Dict[str, Any]) -> TargetInput:
    cp, a = t["catalog_position"], t.get("astrometry") or {}
    return TargetInput(
        ra_deg=cp["ra_deg"],
        dec_deg=cp["dec_deg"],
        epoch_jyear=cp.get("epoch_jyear"),
        pm_ra_cosdec_masyr=a.get("pm_ra_cosdec_masyr"),
        pm_dec_masyr=a.get("pm_dec_masyr"),
        parallax_mas=a.get("parallax_mas"),
        radial_velocity_kms=a.get("radial_velocity_kms"),
        name=t.get("display_name"),
        source=f"{cp.get('source', 'Catalog')} ({cp.get('astrometry_reference', 'astrometry reference not stated')})",
    )


def manifest_index(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = {}
    for rec in manifest["files"]:
        if rec.get("status") != "downloaded":
            continue
        out[frame_key(rec["obs_id"], rec["detector"])] = rec
    return out


def asset_id(preset_id: str, set_name: str, key: str, flags: bool = False) -> str:
    return f"{preset_id}.{set_name}.{key}{'.flags' if flags else ''}.png"


def run(
    preset_id: str,
    set_name: str,
    keys: List[str],
    data_root: Path,
    targets: Dict[str, Any],
    out_root: Path,
    shared_groups: Optional[List[List[str]]] = None,
    expected: Optional[Dict[str, Dict[str, Any]]] = None,
    case_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    manifest = load_json(data_root / "manifest.json")
    idx = manifest_index(manifest)
    tgt = next(t for t in targets["targets"] if t["id"] == preset_id)
    qc = tgt["query_center"]
    fov = float(tgt.get("default_fov_arcmin") or 6)
    tin = target_input(tgt)

    def meta_for(key: str, limits=None, basis=None) -> FrameInput:
        rec = idx[key]
        exp = (expected or {}).get(key, {})
        return FrameInput(
            query_ra_deg=qc["ra_deg"],
            query_dec_deg=qc["dec_deg"],
            fov_arcmin=fov,
            target=tin,
            source_url=rec["archive_url"],
            cutout_url=rec["source_url"],
            observation_id=rec["obs_id"],
            collection_id=rec["collection"],
            detector=rec["detector"],
            retrieved_at_utc=manifest.get("created_utc"),
            retrieved_at_basis="Download-ledger creation time (manifest.json created_utc); per-file retrieval time not recorded.",
            expected_sha256=exp.get("sha256_of_retained_cutout") or rec.get("sha256"),
            display_limits=limits,
            display_limits_basis=basis,
        )

    missing = [k for k in keys if k not in idx]
    if missing:
        raise SystemExit(f"frames not in local download ledger: {missing}")
    raw = {k: (data_root / idx[k]["file"]).read_bytes() for k in keys}

    # First pass (per-frame) gives grid values for shared stretches.
    first = {k: process_frame(raw[k], meta_for(k)) for k in keys}
    limits_for: Dict[str, Any] = {}
    for group in shared_groups or []:
        if len(group) < 2:
            continue
        lim = display_limits_from_values([first[k].grid_values for k in group])
        basis = (
            "Shared asinh stretch: percentiles 1-99.5 of the pooled finite grid pixels of frames "
            + ", ".join(group)
            + ". Grey levels are comparable only within this group; not photometry."
        )
        for k in group:
            limits_for[k] = (lim, basis)

    out_dir = out_root / preset_id / set_name
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    assets = {}
    for k in keys:
        pf = process_frame(raw[k], meta_for(k, *limits_for[k])) if k in limits_for else first[k]
        img_id = asset_id(preset_id, set_name, k)
        (out_dir / f"{k}.png").write_bytes(pf.png_bytes)
        assets[img_id] = f"{preset_id}/{set_name}/{k}.png"
        flag_src = None
        if pf.flag_png_bytes is not None:
            fid = asset_id(preset_id, set_name, k, flags=True)
            (out_dir / f"{k}.flags.png").write_bytes(pf.flag_png_bytes)
            assets[fid] = f"{preset_id}/{set_name}/{k}.flags.png"
            flag_src = ASSET_URL_PREFIX + fid
        rec = with_image_sources(pf.record, ASSET_URL_PREFIX + img_id, flag_src)
        rec["preset_id"] = preset_id
        if case_id:
            rec["case_id"] = case_id
            rec["case_ref"] = (expected or {}).get(k, {}).get("ref")
        (out_dir / f"{k}.json").write_text(json.dumps(rec, indent=1) + "\n")
        records.append(rec)
    records.sort(key=lambda r: (r["mjd"] if r["mjd"] is not None else float("inf"), r["frame_key"]))
    index = {
        "schema_version": 1,
        "preset_id": preset_id,
        "set": set_name,
        "case_id": case_id,
        "generated_by": "tools/ingest/ingest.py",
        "processing_version": records[0]["provenance"]["processing_version"] if records else None,
        "grid_id": records[0]["registration"]["grid_id"] if records else None,
        "assets": assets,
        "frames": records,
    }
    (out_dir / "frames.json").write_text(json.dumps(index, indent=1) + "\n")
    return records


def shared_groups_for_case(case: Dict[str, Any]) -> List[List[str]]:
    """Frames share a stretch when they are on the same detector and their
    case wavelengths differ by less than the smaller bandwidth."""
    frames = case["frames"]
    groups: List[List[str]] = []
    for f in frames:
        placed = False
        for g in groups:
            g0 = next(x for x in frames if x["frame_key"] == g[0])
            if (
                g0["detector"] == f["detector"]
                and g0.get("wavelength_um") is not None
                and f.get("wavelength_um") is not None
                and abs(g0["wavelength_um"] - f["wavelength_um"]) < min(g0["bandwidth_um"], f["bandwidth_um"])
            ):
                g.append(f["frame_key"])
                placed = True
                break
        if not placed:
            groups.append([f["frame_key"]])
    return groups


def compare_case(case: Dict[str, Any], records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by = {r["frame_key"]: r for r in records}
    rows = []
    for f in case["frames"]:
        r = by[f["frame_key"]]
        ew, ow = f.get("wavelength_um"), r["wavelength_um"]
        wl_ok = (ew is None and ow is None) or (ew is not None and ow is not None and abs(ew - ow) <= 1e-4 + 1e-12)
        date_ok = (r["observed_at_utc"] or "").rstrip("Z") == f["observed_at_utc"].rstrip("Z")
        mjd_ok = r["mjd"] is not None and abs(r["mjd"] - f["mjd"]) < 1e-8
        q_ok = r["quality"]["status"] == f["expected_quality_status"]
        sha_ok = r["provenance"]["sha256"] == f["sha256_of_retained_cutout"]
        url_ok = r["source_url"] == f["source_url"]
        coll_ok = r["collection_id"] == f["collection_id"]
        rows.append({
            "ref": f["ref"], "frame_key": f["frame_key"],
            "expected_wavelength_um": ew, "observed_wavelength_um": ow, "wavelength_ok": wl_ok,
            "expected_bandwidth_um": f.get("bandwidth_um"), "observed_bandwidth_um": r["bandwidth_um"],
            "expected_observed_at_utc": f["observed_at_utc"], "observed_at_utc": r["observed_at_utc"],
            "date_ok": date_ok and mjd_ok,
            "expected_quality": f["expected_quality_status"], "observed_quality": r["quality"]["status"],
            "observed_flag_names": r["quality"]["flag_names"],
            "adverse/screened": f"{r['quality']['adverse_aperture_pixels']}/{r['quality']['screened_pixels']}",
            "quality_ok": q_ok, "sha256_ok": sha_ok, "source_url_ok": url_ok, "collection_ok": coll_ok,
            "marker_xy": (r["marker"]["x"], r["marker"]["y"]) if r["marker"] else None,
            "all_ok": wl_ok and date_ok and mjd_ok and q_ok and sha_ok and url_ok and coll_ok,
        })
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("case", "preset"):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--data-root", default=os.environ.get("PERIGEE_DATA_ROOT"),
                       help="research/build_data directory (or env PERIGEE_DATA_ROOT)")
        p.add_argument("--targets", default=str(REPO / "backend" / "content" / "targets.json"))
        p.add_argument("--out", default=str(DEFAULT_OUT))
        if name == "case":
            p.add_argument("--case-file", default=None)
            p.add_argument("--report", default=None, help="write expected-vs-observed JSON here")
        else:
            p.add_argument("--frames", default=None, help="comma-separated frame_keys (default: all retained)")
            p.add_argument("--shared-stretch", action="store_true", help="one shared stretch over all frames")
    a = ap.parse_args(argv)
    if not a.data_root:
        ap.error("--data-root or PERIGEE_DATA_ROOT is required")
    data_root = Path(a.data_root)
    targets = load_json(Path(a.targets))

    if a.cmd == "case":
        case_path = Path(a.case_file or REPO / "backend" / "content" / "cases" / f"{a.id}.json")
        case = load_json(case_path)
        keys = [f["frame_key"] for f in case["frames"]]
        expected = {f["frame_key"]: f for f in case["frames"]}
        groups = shared_groups_for_case(case)
        recs = run(case["target_id"], f"case-{a.id}", keys, data_root, targets, Path(a.out),
                   shared_groups=groups, expected=expected, case_id=a.id)
        rows = compare_case(case, recs)
        print(json.dumps({"case_id": a.id, "shared_groups": groups, "comparison": rows}, indent=1))
        if a.report:
            Path(a.report).write_text(json.dumps({"case_id": a.id, "shared_groups": groups, "comparison": rows}, indent=1) + "\n")
        return 0 if all(r["all_ok"] for r in rows) else 2

    idx = manifest_index(load_json(data_root / "manifest.json"))
    if a.frames:
        keys = [k.strip() for k in a.frames.split(",") if k.strip()]
    else:
        keys = sorted(k for k, r in idx.items() if r["target_id"] == a.id)
    groups = [keys] if a.shared_stretch else None
    recs = run(a.id, "frames", keys, data_root, targets, Path(a.out), shared_groups=groups)
    for r in recs:
        print(r["frame_key"], r["observed_at_utc"], r["wavelength_um"], r["quality"]["status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
