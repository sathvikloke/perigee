"""FIXTURES ONLY -- synthetic stand-ins for the archive and the processor.

Nothing produced here is a NASA observation. The fixture processor marks every
record ``provenance.data_origin = "fixture"`` and its image is a flat synthetic
gradient. The fixture FITS bytes are a minimal header-only file, not SPHEREx data.
"""

from __future__ import annotations

import struct
import zlib
from typing import Any

from backend.routes._archive import CollectionResult

FIXTURE_LIMITATION = "FIXTURE: synthetic test image and metadata; not a NASA observation."


def tiny_png(width: int = 8, height: int = 8, value: int = 128) -> bytes:
    """Encode a small 8-bit grayscale PNG (pure Python; test use only)."""
    raw = b"".join(b"\x00" + bytes([(value + x + y) % 256 for x in range(width)]) for y in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def fixture_fits_bytes() -> bytes:
    cards = ["SIMPLE  =                    T", "BITPIX  =                    8", "NAXIS   =                    0", "END"]
    header = "".join(c.ljust(80) for c in cards)
    return header.ljust(2880).encode("ascii")


def fixture_descriptor(
    obs: str, det: int, mjd: float | None, collection: str = "spherex_dr1", week: str = "2026W18_1A"
) -> dict:
    url = (
        f"https://irsa.ipac.caltech.edu/ibe/data/spherex/{collection.split('_')[1]}/level2/"
        f"{week}/l2b-v27-2026-244/{det}/level2_{obs}D{det}_spx_l2b-v27-2026-244.fits"
    )
    return {
        "observation_id": obs,
        "detector": det,
        "frame_key": f"{obs}_D{det}",
        "collection_id": collection,
        "observed_at_utc": None,
        "mjd": mjd,
        "time_basis": "sia_t_min",
        "band_name": f"SPHEREx-D{det}",
        "detector_wavelength_range_um": None,
        "source_url": url,
    }


class FakeSearch:
    """Per-collection scripted archive. Values: list of descriptors or an exception."""

    def __init__(self, script: dict[str, Any]):
        self.script = script
        self.calls: list[dict] = []

    async def __call__(self, client, **kwargs) -> CollectionResult:
        self.calls.append(kwargs)
        outcome = self.script.get(kwargs["collection_id"], [])
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, CollectionResult):
            return outcome
        return CollectionResult(kwargs["collection_id"], list(outcome))


def fixture_processor(fits_bytes: bytes, meta: dict) -> dict:
    """Stand-in for backend.data.process_frame. Returns a FrameRecord-shaped dict."""
    assert fits_bytes.startswith(b"SIMPLE")
    q = meta["query"]
    return {
        "record": {
            "observed_at_utc": meta["descriptor_observed_at_utc"],
            "mjd": meta["descriptor_mjd"],
            "time_basis": "fixture",
            "wavelength_um": None,
            "bandwidth_um": None,
            "wavelength_location": meta["wavelength_location"],
            "image": {"width": 8, "height": 8},
            "flag_image": None,
            "registration": {
                "center_ra_deg": q["ra_deg"],
                "center_dec_deg": q["dec_deg"],
                "fov_arcmin": q["fov_arcmin"],
                "scale_arcsec_per_px": q["fov_arcmin"] * 60 / 8,
                "orientation": "north_up_east_left",
                "projection": "TAN",
                "method": "fixture (no resampling)",
                "width": 8,
                "height": 8,
            },
            "quality": {
                "status": "unknown",
                "covered": None,
                "valid_aperture_pixels": None,
                "adverse_aperture_pixels": None,
                "flag_names": [],
                "notes": [FIXTURE_LIMITATION],
            },
            "display_scale": {"mode": "per_frame", "method": "fixture", "comparable_brightness": False},
            "marker": None,
            "provenance": {
                "data_origin": "fixture",
                "retrieved_at": meta["retrieved_at_utc"],
                "original_url": meta["source_url"],
                "processing_version": "fixture-0",
                "acknowledgments": [],
            },
            "limitations": [FIXTURE_LIMITATION],
        },
        "image_png": tiny_png(),
        "flag_png": None,
    }
