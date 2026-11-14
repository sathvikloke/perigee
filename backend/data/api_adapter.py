"""Dict-in / dict-out entry point for the API layer.

API candidate A (backend/routes/_adapters.py) looks for `backend.data.process_frame_for_api`
first. This is that function. It is pure: no network, no globals, no web imports.

    meta (built by the API, JSON-serialisable):
      observation_id, detector, frame_key, collection_id, source_url, cutout_url,
      descriptor_mjd, descriptor_observed_at_utc,
      query {ra_deg, dec_deg, fov_arcmin},
      grid {width, height, center_ra_deg, center_dec_deg, fov_arcmin, orientation},
      marker_target (None for live queries, or a catalog dict),
      retrieved_at_utc, file_sha256, byte_length

    returns {"record": FrameRecord dict (image src left None), "image_png": bytes,
             "flag_png": bytes | None}

Failures raise DataError subclasses (code UNSUPPORTED_DATA / PROCESSING_FAILED). A position
the image does not cover is NOT an error: it is quality.status == "not_covered".
"""
from __future__ import annotations

from typing import Any

from .errors import UnsupportedData
from .process import process_frame
from .records import CatalogTarget, FrameContext, ObservationDescriptor


def _target(d: Any) -> CatalogTarget | None:
    if not d:
        return None
    return CatalogTarget(
        target_id=str(d.get("target_id") or d.get("id") or "target"),
        name=str(d.get("name") or "Target"),
        ra_deg=float(d["ra_deg"]),
        dec_deg=float(d["dec_deg"]),
        epoch_jyear=float(d.get("epoch_jyear") or 2000.0),
        pm_ra_cosdec_masyr=d.get("pm_ra_cosdec_masyr"),
        pm_dec_masyr=d.get("pm_dec_masyr"),
        source=str(d.get("source") or "catalog"),
        parallax_mas=d.get("parallax_mas"),
        radial_velocity_kms=d.get("radial_velocity_kms"),
    )


def process_frame_for_api(fits_bytes: bytes, meta: dict[str, Any]) -> dict[str, Any]:
    try:
        obs = ObservationDescriptor.from_public_dict(
            {
                "observation_id": meta["observation_id"],
                "collection_id": meta["collection_id"],
                "observed_at_utc": meta.get("descriptor_observed_at_utc"),
                "mjd": meta.get("descriptor_mjd"),
                "detector": meta.get("detector"),
                "source_url": meta["source_url"],
            }
        )
        grid = meta.get("grid") or {}
        query = meta.get("query") or {}
        center_ra = float(grid.get("center_ra_deg", query.get("ra_deg")))
        center_dec = float(grid.get("center_dec_deg", query.get("dec_deg")))
        fov = float(grid.get("fov_arcmin", query.get("fov_arcmin", 6.0)))
        size = int(grid.get("width", 256))
    except (KeyError, TypeError, ValueError) as exc:
        raise UnsupportedData("frame metadata is incomplete") from exc
    if meta.get("frame_key") and meta["frame_key"] != obs.frame_key:
        raise UnsupportedData("frame_key does not match observation_id and detector")
    ctx = FrameContext(
        observation=obs,
        center_ra_deg=center_ra,
        center_dec_deg=center_dec,
        fov_arcmin=fov,
        grid_size=size,
        target=_target(meta.get("marker_target")),
        retrieved_at_utc=meta.get("retrieved_at_utc"),
        retrieved_at_basis="Downloaded from the archive cutout service for this request.",
        cutout_url=meta.get("cutout_url"),
    )
    product = process_frame(fits_bytes, ctx)
    record = product.record
    if meta.get("wavelength_location") and record["wavelength_um"] is not None and ctx.target is None:
        record["wavelength_location"] = f"{meta['wavelength_location']} (RA {center_ra:.5f}, Dec {center_dec:.5f})."
    return {"record": record, "image_png": product.image_png, "flag_png": product.flag_png}
