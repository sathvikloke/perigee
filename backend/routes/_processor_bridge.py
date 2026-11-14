"""Integration bridge: API A's processor seam -> processor A's typed function.

routes/_adapters.py calls ``process_frame(fits_bytes, meta: dict) -> dict`` with
``{"record", "image_png", "flag_png"}``. backend/data/process.py (worker 05) exposes
``process_frame(fits_bytes, FrameInput) -> ProcessedFrame``. This module translates
between the two without changing either side. Processor exceptions propagate
unchanged so the API's error mapping (UNSUPPORTED_DATA vs PROCESSING_FAILED) holds.
"""

from __future__ import annotations

from typing import Any

from backend.data.process import FrameInput, TargetInput
from backend.data.process import process_frame as _process


def _target(meta: dict[str, Any]) -> TargetInput | None:
    t = meta.get("marker_target")
    if not t:
        return None
    return TargetInput(
        ra_deg=t["ra_deg"],
        dec_deg=t["dec_deg"],
        epoch_jyear=t.get("epoch_jyear"),
        pm_ra_cosdec_masyr=t.get("pm_ra_cosdec_masyr"),
        pm_dec_masyr=t.get("pm_dec_masyr"),
        parallax_mas=t.get("parallax_mas"),
        name=t.get("name"),
        source=t.get("source"),
    )


def process_frame(fits_bytes: bytes, meta: dict[str, Any]) -> dict[str, Any]:
    grid = meta.get("grid") or {}
    query = meta.get("query") or {}
    frame_input = FrameInput(
        # The fixed display grid is centred on the query, never on a target.
        query_ra_deg=grid.get("center_ra_deg", query.get("ra_deg")),
        query_dec_deg=grid.get("center_dec_deg", query.get("dec_deg")),
        fov_arcmin=grid.get("fov_arcmin", query.get("fov_arcmin", 6.0)),
        grid_size=int(grid.get("width", 256)),
        target=_target(meta),
        source_url=meta.get("source_url"),
        observation_id=meta.get("observation_id"),
        collection_id=meta.get("collection_id"),
        detector=meta.get("detector"),
        cutout_url=meta.get("cutout_url"),
        retrieved_at_utc=meta.get("retrieved_at_utc"),
        retrieved_at_basis="API fetch time of this cutout",
        expected_sha256=meta.get("file_sha256"),
    )
    result = _process(fits_bytes, frame_input)
    return {
        "record": result.record,
        "image_png": result.png_bytes,
        "flag_png": result.flag_png_bytes,
    }
