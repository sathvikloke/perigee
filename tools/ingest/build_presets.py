"""Build the curated preset assets from the retained original SPHEREx cutouts.

Usage (from the repo root):
    python tools/ingest/fetch_manifest.py --out ../perigee-data/raw        # once, verifies hashes
    python tools/ingest/build_presets.py --raw ../perigee-data/raw

Writes backend/content/presets/:
    manifest.json                 index of presets, case sets and every asset (id -> file, sha256, bytes)
    <preset_id>/frames.json       ordered FrameRecords for the preset's full sequence (per-frame contrast)
    <preset_id>/sets/<case_id>.json  the case's frames (A/B/C) with the stretch the case asks for
    <preset_id>/img/*.png         intensity and flag-overlay PNGs

Every record is built with backend/data/process.py, the same code the live API uses.
Image `src` values are same-origin asset URLs: /api/v1/assets/<asset_id>.
Case frames come from Sathvik's case files (science/CASE_SELECTION.md, integration board
decision 6). They are copied below so this script runs without his branch checked out;
`tools/ingest/check_cases.py` compares the output with the case JSON itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from data import CatalogTarget, FrameContext, ObservationDescriptor, SharedScale, process_frame  # noqa: E402
from data.process import PROCESSING_VERSION  # noqa: E402

MANIFEST = REPO / "research" / "build_data" / "manifest.json"
OUT = REPO / "backend" / "content" / "presets"
SCHEMA_VERSION = 1
ASSET_VERSION = "v1"

PRESET_NAMES = {
    "barnards_star": "Barnard's Star",
    "epsilon_indi_b": "Epsilon Indi B",
    "wise_0855": "WISE 0855",
    "rw_aurigae": "RW Aurigae",
    "r_draconis": "R Draconis",
}
# 4 arcmin keeps the north-up grid inside every audit cutout (6' squares at any angle: a 4'
# square's diagonal is 5.7'), so curated frames have no empty corners.
PRESET_FOV_ARCMIN = 4.0
GRID_SIZE = 256

# Case frames as chosen by Sathvik (case JSON `frames[].frame_key`). `shared` lists the refs that
# get one common stretch (case `display_requirements.stretch`); the others keep their own.
CASE_SETS = {
    "epsilon_indi_b": [
        {
            "set_id": "fair_comparison",
            "for_case": "fair_comparison",
            "frames": {"A": "2026W18_1A_0516_1_D3", "B": "2026W39_2A_0597_4_D3", "C": "2026W18_1A_0516_1_D6"},
            "shared": ["A", "B"],
            "why": "Sathvik's selection: A/B same detector, ~151 days apart, wavelength differs by 0.0012 um, both clear; C is A's moment at 4.94 um (the unfair comparison).",
        }
    ],
    "barnards_star": [
        {
            "set_id": "moving_neighbor",
            "for_case": "moving_neighbor",
            "frames": {"A": "2025W35_1A_0008_1_D3", "B": "2026W12_1A_0610_2_D3", "C": "2026W34_1A_0431_1_D3"},
            "shared": ["A", "B", "C"],
            "why": "Sathvik's selection: same detector, three epochs over ~1 year, wavelengths within 0.022 um. All flagged at the saturated star.",
        }
    ],
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def descriptor(e: dict) -> ObservationDescriptor:
    det = int(e["detector"])
    return ObservationDescriptor(
        observation_id=e["obs_id"],
        collection_id=e["collection"],
        observed_at_utc=e["date_utc"] + "Z",
        mjd=float(e["mjd"]),
        detector=det,
        source_url=e["archive_url"],
    )


def catalog_target(t: dict) -> CatalogTarget:
    return CatalogTarget(
        target_id=t["id"],
        name=PRESET_NAMES.get(t["id"], t["name"]),
        ra_deg=t["ra_j2000_deg"],
        dec_deg=t["dec_j2000_deg"],
        epoch_jyear=t["reference_epoch_jyear"],
        pm_ra_cosdec_masyr=t.get("pm_ra_cosdec_masyr"),
        pm_dec_masyr=t.get("pm_dec_masyr"),
        source=t["position_source"],
        parallax_mas=t.get("parallax_mas"),
        radial_velocity_kms=t.get("radial_velocity_kms"),
    )


class AssetWriter:
    def __init__(self, out: Path):
        self.out = out
        self.index: dict[str, dict] = {}

    def put(self, preset_id: str, name: str, png: bytes) -> str:
        asset_id = f"{preset_id}.{name}.{ASSET_VERSION}"
        rel = Path(preset_id) / "img" / f"{name}.{ASSET_VERSION}.png"
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)
        self.index[asset_id] = {"path": rel.as_posix(), "media_type": "image/png", "bytes": len(png), "sha256": sha256_bytes(png)}
        return asset_id


def build_record(raw: Path, e: dict, t: dict, created_utc: str, shared: SharedScale | None):
    data = (raw / e["target_id"] / Path(e["file"]).name).read_bytes()
    if sha256_bytes(data) != e["sha256"]:
        raise SystemExit(f"hash mismatch for {e['file']}: re-run fetch_manifest.py")
    ctx = FrameContext(
        observation=descriptor(e),
        center_ra_deg=t["query_ra_deg"],
        center_dec_deg=t["query_dec_deg"],
        fov_arcmin=PRESET_FOV_ARCMIN,
        grid_size=GRID_SIZE,
        target=catalog_target(t),
        shared_scale=shared,
        retrieved_at_utc=created_utc,
        retrieved_at_basis=(
            "When the original audit ledger was written. The bytes were re-downloaded from cutout_url "
            "and matched the ledger's SHA-256 before processing."
        ),
        cutout_url=e["source_url"],
    )
    return process_frame(data, ctx)


def attach(product, writer: AssetWriter, preset_id: str, stem: str) -> dict:
    rec = product.record
    img_id = writer.put(preset_id, f"{stem}.image", product.image_png)
    rec["image"]["src"] = f"/api/v1/assets/{img_id}"
    rec["image"]["asset_id"] = img_id
    if rec.get("flag_image") is not None and product.flag_png is not None:
        flag_id = writer.put(preset_id, f"{stem}.flags", product.flag_png)
        rec["flag_image"]["src"] = f"/api/v1/assets/{flag_id}"
        rec["flag_image"]["asset_id"] = flag_id
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=Path, help="directory with <target_id>/<file>.fits")
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    created_utc = manifest["created_utc"]
    targets = {t["id"]: t for t in manifest["targets"]}
    files = [f for f in manifest["files"] if f["status"] == "downloaded"]
    writer = AssetWriter(OUT)
    presets_index = []

    for preset_id in PRESET_NAMES:
        t = targets[preset_id]
        entries = [f for f in files if f["target_id"] == preset_id]
        frames, skipped = [], []
        by_key = {}
        for e in entries:
            key = f"{e['obs_id']}_D{e['detector']}"
            by_key[key] = e
            try:
                prod = build_record(args.raw, e, t, created_utc, None)
            except Exception as exc:  # keep going; record why
                skipped.append({"frame_key": key, "reason": getattr(exc, "code", type(exc).__name__)})
                continue
            frames.append(attach(prod, writer, preset_id, f"{key}.seq"))
        frames.sort(key=lambda r: (r["mjd"], r["frame_key"]))  # mid-exposure time, then frame_key
        grid = frames[0]["registration"] if frames else None
        preset_dir = OUT / preset_id
        preset_dir.mkdir(parents=True, exist_ok=True)
        status_counts: dict[str, int] = {}
        for r in frames:
            status_counts[r["quality"]["status"]] = status_counts.get(r["quality"]["status"], 0) + 1
        (preset_dir / "frames.json").write_text(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "preset_id": preset_id,
            "name": PRESET_NAMES[preset_id],
            "delivery": "curated",
            "delivery_note": "Pre-processed from retained original archive files; not a live archive query.",
            "processing_version": PROCESSING_VERSION,
            "registration": grid,
            "ordering": "mjd (mid-exposure) ascending, then frame_key",
            "frames": frames,
            "skipped": skipped,
        }, indent=1) + "\n")

        sets_out = []
        for spec in CASE_SETS.get(preset_id, []):
            refs = spec["frames"]
            per = {ref: build_record(args.raw, by_key[k], t, created_utc, None) for ref, k in refs.items()}
            group = [per[r] for r in spec["shared"]]
            low = median(p.stats["auto_scale"]["low"] for p in group)
            high = median(p.stats["auto_scale"]["high"] for p in group)
            soft = median(p.stats["auto_scale"]["asinh_softening"] for p in group)
            shared = SharedScale(low, high, soft)
            recs = []
            for ref, k in refs.items():
                prod = build_record(args.raw, by_key[k], t, created_utc, shared if ref in spec["shared"] else None)
                rec = attach(prod, writer, preset_id, f"{k}.{spec['set_id']}")
                rec["case_ref"] = ref
                recs.append(rec)
            wl = [r["wavelength_um"] for r in recs if r["case_ref"] in spec["shared"]]
            set_doc = {
                "schema_version": SCHEMA_VERSION,
                "set_id": spec["set_id"],
                "preset_id": preset_id,
                "for_case": spec["for_case"],
                "status": "frames chosen by Sathvik; check_cases.py compares them with the case JSON",
                "why_selected": spec["why"],
                "delivery": "curated",
                "processing_version": PROCESSING_VERSION,
                "shared_scale": {"refs": spec["shared"], "low": low, "high": high, "asinh_softening": soft, "unit": "MJy/sr", "rule": "median of the shared frames' own per-frame limits and softening"},
                "summary": [
                    {
                        "case_ref": r["case_ref"],
                        "frame_key": r["frame_key"],
                        "observed_at_utc": r["observed_at_utc"],
                        "detector": r["detector"],
                        "wavelength_um": r["wavelength_um"],
                        "bandwidth_um": r["bandwidth_um"],
                        "quality_status": r["quality"]["status"],
                        "valid_aperture_pixels": r["quality"]["valid_aperture_pixels"],
                        "adverse_aperture_pixels": r["quality"]["adverse_aperture_pixels"],
                        "marker_xy": None if r["marker"] is None else [r["marker"]["x"], r["marker"]["y"]],
                    }
                    for r in recs
                ],
                "max_wavelength_difference_um_shared_frames": (max(wl) - min(wl)) if wl and all(w is not None for w in wl) else None,
                "frames": recs,
            }
            (preset_dir / "sets").mkdir(exist_ok=True)
            (preset_dir / "sets" / f"{spec['set_id']}.json").write_text(json.dumps(set_doc, indent=1) + "\n")
            sets_out.append({"set_id": spec["set_id"], "for_case": spec["for_case"], "path": f"{preset_id}/sets/{spec['set_id']}.json", "frame_keys": refs})

        presets_index.append({
            "preset_id": preset_id,
            "name": PRESET_NAMES[preset_id],
            "frames_path": f"{preset_id}/frames.json",
            "frame_count": len(frames),
            "skipped_count": len(skipped),
            "quality_counts": status_counts,
            "registration": grid,
            "catalog_target": {
                "ra_j2000_deg": t["ra_j2000_deg"], "dec_j2000_deg": t["dec_j2000_deg"],
                "pm_ra_cosdec_masyr": t.get("pm_ra_cosdec_masyr"), "pm_dec_masyr": t.get("pm_dec_masyr"),
                "source": t["position_source"], "note": t.get("position_note"),
            },
            "comparison_sets": sets_out,
        })
        print(preset_id, len(frames), "frames", status_counts, "skipped", skipped)

    total = sum(a["bytes"] for a in writer.index.values())
    (OUT / "manifest.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "processing_version": PROCESSING_VERSION,
        "generated_by": "tools/ingest/build_presets.py",
        "source_ledger": "research/build_data/manifest.json",
        "grid": {"fov_arcmin": PRESET_FOV_ARCMIN, "size": GRID_SIZE, "center": "each preset's audit query position (catalog position moved to 2026.0)"},
        "presets": presets_index,
        "assets": writer.index,
        "asset_total_bytes": total,
    }, indent=1) + "\n")
    print("assets", len(writer.index), "bytes", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
