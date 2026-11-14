"""Regression (worker 23): the real /frame path with the real processor A.

Reproduces the integration seam defect without network: the API once found no
processor, and expected ``registration.scale_arcsec_per_pixel`` while processor A
writes ``scale_arcsec_per_px``. Here the upstream fetch is scripted to return a
real retained SPHEREx cutout (read only from ``PERIGEE_DATA_ROOT``), the route
runs the real ``backend.data.process`` through ``processor_a_adapter``, and the
response must validate against the public ``FrameResponse`` model.

Skipped when ``PERIGEE_DATA_ROOT`` is not set (no raw data in the repo).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from backend.models.frame import FrameResponse
from backend.routes import _adapters

from .test_frame import make_token, post

FRAME_KEY = "2026W18_1A_0516_1_D3"  # Eps Ind B, fair_comparison A
RAW_REL = "raw/epsilon_indi_b/level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits"
DATA_ROOT = os.environ.get("PERIGEE_DATA_ROOT")

pytestmark = pytest.mark.skipif(
    not DATA_ROOT or not (Path(DATA_ROOT) / RAW_REL).is_file(),
    reason="needs PERIGEE_DATA_ROOT with the retained Eps Ind B cutout",
)


def test_live_frame_path_with_real_processor_validates(client, harness):
    fits_bytes = (Path(DATA_ROOT) / RAW_REL).read_bytes()
    processor, source = _adapters.processor_a_adapter()
    assert processor is not None, "processor A not found by the API seam"
    harness.processor = processor
    harness.settings = replace(harness.settings, frame_fetch_max_bytes=24 * 2**20, frame_budget_s=40.0)
    harness.fetch_handler = lambda req: httpx.Response(
        200, content=fits_bytes, headers={"content-type": "application/fits"}
    )

    # Query at the Eps Ind B preset centre (inside the cutout).
    r = post(client, make_token(ra_deg=331.0966687831005, dec_deg=-56.80064917516836))
    assert r.status_code == 200, r.text[:2000]
    body = r.json()
    FrameResponse.model_validate(body)  # the public contract

    f = body["frame"]
    reg = f["registration"]
    assert isinstance(reg["scale_arcsec_per_px"], float) and reg["scale_arcsec_per_px"] > 0
    assert "scale_arcsec_per_pixel" not in reg
    assert f["frame_key"] == FRAME_KEY
    assert f["provenance"]["data_origin"] == "nasa_archive"
    assert f["provenance"]["sha256"] == hashlib.sha256(fits_bytes).hexdigest()
    assert f["provenance"]["processing_version"].startswith("perigee-processor-a/")
    assert f["quality"]["status"] in ("clear", "flagged")
    # Same exposure as the case frame (2.3232 um at the target); the query centre is
    # a few arcsec away, so the evaluated wavelength agrees closely.
    case = json.loads((Path(__file__).resolve().parents[2] / "content/cases/fair_comparison.json").read_text())
    want = next(x for x in case["frames"] if x["frame_key"] == FRAME_KEY)["wavelength_um"]
    assert f["wavelength_um"] == pytest.approx(want, abs=5e-3)
    assert f["image"]["src"].startswith("data:image/png;base64,")


# PR #35 review: a cutout truncated inside a data unit must reach the client as
# 422 UNSUPPORTED_DATA (contract: corrupt file), not 500 PROCESSING_FAILED.


def _post_truncated(client, harness, data: bytes):
    processor, _ = _adapters.processor_a_adapter()
    assert processor is not None
    harness.processor = processor
    harness.settings = replace(harness.settings, frame_fetch_max_bytes=24 * 2**20, frame_budget_s=40.0)
    harness.fetch_handler = lambda req: httpx.Response(200, content=data, headers={"content-type": "application/fits"})
    return post(client, make_token(ra_deg=331.0966687831005, dec_deg=-56.80064917516836))


def test_truncated_real_cutout_is_422_unsupported_data(client, harness):
    fits_bytes = (Path(DATA_ROOT) / RAW_REL).read_bytes()
    r = _post_truncated(client, harness, fits_bytes[: len(fits_bytes) // 3])
    assert r.status_code == 422, r.text[:500]
    assert r.json()["error"]["code"] == "UNSUPPORTED_DATA"
