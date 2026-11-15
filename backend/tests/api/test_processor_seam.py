"""The processor-a seam: routes/_adapters.processor_a_adapter wraps
``backend.data.process.process_frame(bytes, FrameInput) -> ProcessedFrame``.

A stand-in module with the same signature is injected via sys.modules, so this test
needs no backend/data code. The stand-in output is FIXTURE data.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any, Optional

import pytest

from backend.routes import _adapters

from .fixtures import tiny_png


@dataclass(frozen=True)
class FrameInput:  # mirrors processor-a fields used by the adapter
    query_ra_deg: float
    query_dec_deg: float
    fov_arcmin: float = 6.0
    grid_size: int = 256
    target: Any = None
    source_url: Optional[str] = None
    observation_id: Optional[str] = None
    collection_id: Optional[str] = None
    detector: Optional[int] = None
    cutout_url: Optional[str] = None
    retrieved_at_utc: Optional[str] = None
    retrieved_at_basis: Optional[str] = None
    expected_sha256: Optional[str] = None
    display_limits: Any = None
    display_limits_basis: Optional[str] = None
    include_flag_image: bool = True


@dataclass
class ProcessedFrame:
    record: dict
    png_bytes: bytes
    flag_png_bytes: Optional[bytes] = None


@pytest.fixture
def standin(monkeypatch):
    seen: list[FrameInput] = []
    mod = types.ModuleType("backend.data.process")

    def process_frame(fits_bytes: bytes, meta: FrameInput) -> ProcessedFrame:
        seen.append(meta)
        return ProcessedFrame(record={"frame_key": "x"}, png_bytes=tiny_png(), flag_png_bytes=None)

    mod.FrameInput = FrameInput
    mod.process_frame = process_frame
    pkg = types.ModuleType("backend.data")
    pkg.__path__ = []  # mark as package
    monkeypatch.setitem(sys.modules, "backend.data", pkg)
    monkeypatch.setitem(sys.modules, "backend.data.process", mod)
    return seen


def test_adapter_maps_meta_and_output(standin):
    adapter, source = _adapters.processor_a_adapter()
    assert adapter is not None and "processor-a" in source
    meta = {
        "query": {"ra_deg": 330.84, "dec_deg": -56.786, "fov_arcmin": 6.0},
        "grid": {"width": 256, "height": 256},
        "source_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/a/b/3/x.fits",
        "observation_id": "o",
        "collection_id": "spherex_dr1",
        "detector": 3,
        "cutout_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/a/b/3/x.fits?center=1,2&size=0.15",
        "retrieved_at_utc": "2026-11-14T00:00:00+00:00",
    }
    out = adapter(b"SIMPLE  =", meta)
    (fi,) = standin
    assert (fi.query_ra_deg, fi.query_dec_deg, fi.fov_arcmin, fi.grid_size) == (330.84, -56.786, 6.0, 256)
    assert fi.target is None and fi.detector == 3 and fi.cutout_url == meta["cutout_url"]
    assert out["image_png"].startswith(b"\x89PNG") and out["flag_png"] is None
    assert out["record"] == {"frame_key": "x"}


def test_absent_backend_data_means_no_processor(monkeypatch):
    monkeypatch.setitem(sys.modules, "backend.data.process", None)  # import raises ImportError
    assert _adapters.processor_a_adapter() == (None, None)


def test_processor_error_codes_map():
    from backend.routes.frames import _processor_error

    class ProcessorError(Exception):
        code = "PROCESSING_FAILED"

    class IntegrityError(ProcessorError):  # processor-a: subclass of UnsupportedDataError
        code = "UNSUPPORTED_DATA"

    assert _processor_error(IntegrityError()).code.value == "UNSUPPORTED_DATA"
    assert _processor_error(ProcessorError()).code.value == "PROCESSING_FAILED"
    assert _processor_error(ValueError()).code.value == "PROCESSING_FAILED"
