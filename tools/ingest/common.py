"""Shared helpers for the local ingest tools (filesystem only; no network)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_BUILD_DATA = os.environ.get(
    "PERIGEE_BUILD_DATA", "/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data"
)


def load_json(path: Path | str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def target_by_id(targets_doc: Dict[str, Any], target_id: str) -> Dict[str, Any]:
    for t in targets_doc["targets"]:
        if t["id"] == target_id:
            return t
    raise KeyError(target_id)


def target_astrometry(t: Dict[str, Any]) -> Dict[str, Any]:
    cp, am = t["catalog_position"], t["astrometry"]
    return {
        "ra_deg": cp["ra_deg"],
        "dec_deg": cp["dec_deg"],
        "epoch_jyear": cp.get("epoch_jyear", 2000.0),
        "pm_ra_cosdec_masyr": am.get("pm_ra_cosdec_masyr"),
        "pm_dec_masyr": am.get("pm_dec_masyr"),
        "parallax_mas": am.get("parallax_mas"),
        "radial_velocity_kms": am.get("radial_velocity_kms"),
        "label": t["display_name"],
        "source": cp.get("source"),
    }


def manifest_entry(manifest: Dict[str, Any], observation_id: str, detector: int) -> Optional[Dict[str, Any]]:
    for f in manifest["files"]:
        if f.get("status") == "downloaded" and f.get("obs_id") == observation_id and int(f.get("detector", -1)) == int(detector):
            return f
    return None


def frame_input_dict(t: Dict[str, Any], entry: Dict[str, Any], manifest: Dict[str, Any], preset_id: str) -> Dict[str, Any]:
    return {
        "center_ra_deg": t["query_center"]["ra_deg"],
        "center_dec_deg": t["query_center"]["dec_deg"],
        "fov_arcmin": t.get("default_fov_arcmin", 6),
        "grid_size": 256,
        "observation_id": entry["obs_id"],
        "collection_id": entry["collection"],
        "source_url": entry["archive_url"],
        "cutout_url": entry["source_url"],
        "retrieved_at_utc": manifest.get("created_utc"),
        "target": target_astrometry(t),
        "preset_id": preset_id,
    }
