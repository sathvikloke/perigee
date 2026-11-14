"""PR #35 review, no raw data needed: a synthetic SPHEREx-like cutout cut off
inside a data unit goes through the real processor A seam and the API answers
422 UNSUPPORTED_DATA, while the intact file still processes (200)."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import httpx

from backend.routes import _adapters

from .test_frame import make_token, post

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
import synthetic as syn  # noqa: E402

BLOCK = 2880


def _run(client, harness, data: bytes):
    processor, _ = _adapters.processor_a_adapter()
    assert processor is not None
    harness.processor = processor
    harness.settings = replace(harness.settings, frame_fetch_max_bytes=24 * 2**20, frame_budget_s=40.0)
    harness.fetch_handler = lambda req: httpx.Response(200, content=data, headers={"content-type": "application/fits"})
    ra, dec = syn.CENTER
    # Identity must match the synthetic header, or the processor's integrity
    # check (a different 422) would fire instead of the truncation path.
    return post(client, make_token(ra_deg=ra, dec_deg=dec, observation_id="2099W01_1A_0001_1", detector=3,
                                   frame_key="2099W01_1A_0001_1_D3", mjd=61000.5))


def test_intact_synthetic_cutout_processes(client, harness):
    r = _run(client, harness, syn.make_fits())
    assert r.status_code == 200, r.text[:500]


def test_cut_inside_a_data_unit_is_422_unsupported_data(client, harness):
    full = syn.make_fits()
    # Cut half a block past the first header block: inside the IMAGE data unit.
    r = _run(client, harness, full[: 3 * BLOCK + BLOCK // 2])
    assert r.status_code == 422, r.text[:500]
    body = r.json()
    assert body["error"]["code"] == "UNSUPPORTED_DATA"
    assert body["error"]["retryable"] is False
    assert body["error"]["details"].get("error_type") == "UnsupportedDataError"
