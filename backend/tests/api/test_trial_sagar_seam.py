"""Trial 24f: the real /frame path with Sagar's processor (PR #19, ``perigee-data``).

Same shape as ``test_regression_seam.py`` (which is processor-A specific), but the
processor is the one the API would really pick: ``backend.data.process_frame_for_api``
via ``_adapters.PROCESSOR_LOCATIONS``. The upstream fetch is scripted to return a
retained SPHEREx cutout read only from ``PERIGEE_DATA_ROOT``. The second case is the
one retained ``l2b_retry`` archive file (incompatibility I-4 in
coordination/processor-compare/README.md); it is expected to fail with
``UNSUPPORTED_DATA`` while ``archive._SOURCE_URL_RE`` rejects that URL form.

Skipped when ``PERIGEE_DATA_ROOT`` is not set.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from backend.models.frame import FrameResponse
from backend.routes import _adapters

from .test_frame import make_token, post

DATA_ROOT = os.environ.get("PERIGEE_DATA_ROOT")
BASE = "https://irsa.ipac.caltech.edu/ibe/data/spherex"

FRAMES = {
    "eps_ind_b_l2b": dict(
        raw="raw/epsilon_indi_b/level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits",
        source_url=BASE + "/dr1/level2/2026W18_1A/l2b-v27-2026-244/3/level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits",
        observation_id="2026W18_1A_0516_1", detector=3, collection_id="spherex_dr1",
        frame_key="2026W18_1A_0516_1_D3", mjd=61159.5, ra_deg=331.0966687831005, dec_deg=-56.80064917516836,
    ),
    "rw_aur_l2b_retry": dict(
        raw="raw/rw_aurigae/level2_2026W38_1A_0162_1D6_spx_l2b_retry-v27-2026-262.fits",
        source_url=BASE + "/qr3/level2/2026W38_1A/l2b_retry-v27-2026-262/6/level2_2026W38_1A_0162_1D6_spx_l2b_retry-v27-2026-262.fits",
        observation_id="2026W38_1A_0162_1", detector=6, collection_id="spherex_qr3",
        frame_key="2026W38_1A_0162_1_D6", mjd=61297.85, ra_deg=76.95658657511666, dec_deg=30.40129134698889,
    ),
}


def _have(raw: str) -> bool:
    return bool(DATA_ROOT) and (Path(DATA_ROOT) / raw).is_file()


@pytest.mark.parametrize("name", sorted(FRAMES))
def test_live_frame_path_with_sagar_processor(client, harness, name):
    spec = dict(FRAMES[name])
    raw = spec.pop("raw")
    if not _have(raw):
        pytest.skip("needs PERIGEE_DATA_ROOT with " + raw)
    processor, source = _adapters._find(_adapters.PROCESSOR_LOCATIONS)
    assert processor is not None and source == "backend.data.process_frame_for_api"
    fits_bytes = (Path(DATA_ROOT) / raw).read_bytes()
    harness.processor = processor
    harness.settings = replace(harness.settings, frame_fetch_max_bytes=24 * 2**20, frame_budget_s=40.0)
    harness.fetch_handler = lambda req: httpx.Response(
        200, content=fits_bytes, headers={"content-type": "application/fits"}
    )
    r = post(client, make_token(**spec))
    if name == "rw_aur_l2b_retry":
        # Recorded trial result: Sagar's archive URL pattern rejects l2b_retry files.
        if r.status_code != 200:
            assert r.json()["error"]["code"] == "UNSUPPORTED_DATA", r.text[:500]
            pytest.xfail("I-4: l2b_retry source_url rejected by perigee-data _SOURCE_URL_RE")
    assert r.status_code == 200, r.text[:2000]
    body = r.json()
    FrameResponse.model_validate(body)
    f = body["frame"]
    assert f["frame_key"] == spec["frame_key"]
    assert f["provenance"]["data_origin"] == "nasa_archive"
    assert f["provenance"]["sha256"] == hashlib.sha256(fits_bytes).hexdigest()
    assert f["provenance"]["processing_version"].startswith("perigee-data")
    assert f["registration"]["fov_arcmin"] == 6.0  # live grid stays 6'
    assert f["image"]["src"].startswith("data:image/png;base64,")
    assert f["quality"]["status"] in ("clear", "flagged")
