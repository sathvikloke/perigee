"""Regression against the six case frames (skipped when the local raw data are absent).

Expected values are copied from backend/content/cases/*.json on the science
branch (science-check-1). Set PERIGEE_BUILD_DATA to the build_data directory.
"""

from __future__ import annotations

import glob
import io
import os
import warnings

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from backend.data.process import FrameInput, process_frame, read_source, sample_spectral_wcs

BUILD = os.environ.get("PERIGEE_BUILD_DATA", "/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data")
pytestmark = pytest.mark.skipif(not os.path.isdir(os.path.join(BUILD, "raw")), reason="original FITS not available")

EPS = dict(center=(331.0966687831005, -56.80064917516836), target=dict(
    ra_deg=331.04414658852124, dec_deg=-56.78284419511611, epoch_jyear=2000.0,
    pm_ra_cosdec_masyr=3981.977, pm_dec_masyr=-2466.832, parallax_mas=270.658, label="Epsilon Indi B"))
BAR = dict(center=(269.4462585584787, 4.768324486236583), target=dict(
    ra_deg=269.4520769586187, dec_deg=4.69336496657667, epoch_jyear=2000.0,
    pm_ra_cosdec_masyr=-801.551, pm_dec_masyr=10362.394, parallax_mas=546.9759, radial_velocity_kms=-110.11, label="Barnard's Star"))

CASES = [
    # preset, obs, det, wavelength, date, status, sha256 prefix
    ("epsilon_indi_b", EPS, "2026W18_1A_0516_1", 3, 2.3232, "2026-04-29T12:05:47.874", "clear", "3781422675f5"),
    ("epsilon_indi_b", EPS, "2026W39_2A_0597_4", 3, 2.3220, "2026-09-27T07:44:24.312", "clear", "378fcf34fb43"),
    ("epsilon_indi_b", EPS, "2026W18_1A_0516_1", 6, 4.9399, "2026-04-29T12:05:47.874", "clear", "74e32a3c1d7f"),
    ("barnards_star", BAR, "2025W35_1A_0008_1", 3, 2.0062, "2025-08-25T00:50:31.845", "flagged", "e7c0a6f7c4c6"),
    ("barnards_star", BAR, "2026W12_1A_0610_2", 3, 2.0123, "2026-03-19T09:06:02.748", "flagged", "9f047b3b75bb"),
    ("barnards_star", BAR, "2026W34_1A_0431_1", 3, 2.0284, "2026-08-19T04:57:42.053", "flagged", "ea3ecdd6d074"),
]


def _bytes(preset, obs, det):
    (path,) = glob.glob(os.path.join(BUILD, "raw", preset, f"*_{obs}D{det}_*.fits"))
    with open(path, "rb") as fh:
        return fh.read()


@pytest.mark.parametrize("preset,cfg,obs,det,wl,date,status,sha", CASES)
def test_case_frame_matches_science_expectations(preset, cfg, obs, det, wl, date, status, sha):
    meta = FrameInput.from_dict(dict(center_ra_deg=cfg["center"][0], center_dec_deg=cfg["center"][1],
                                     observation_id=obs, target=cfg["target"]))
    r = process_frame(_bytes(preset, obs, det), meta).record
    assert r["frame_key"] == f"{obs}_D{det}"
    assert round(r["wavelength_um"], 4) == pytest.approx(wl, abs=1e-9)
    assert r["observed_at_utc"] == date
    assert r["quality"]["status"] == status
    assert r["provenance"]["sha256"].startswith(sha)
    assert r["marker"]["kind"] == "catalog_prediction"


def test_real_spectral_lookup_matches_astropy_tab_with_sip_removed():
    fb = _bytes("epsilon_indi_b", "2026W18_1A_0516_1", 3)
    src = read_source(fb)
    hdul = fits.open(io.BytesIO(fb))
    h = hdul["IMAGE"].header.copy()
    for k in list(h.keys()):
        if k.split("_")[0] in ("A", "B", "AP", "BP") and "_" in k:
            del h[k]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ww = WCS(h, fobj=hdul, key="W")
    for x, y in [(0, 0), (28.58, 28.67), (57, 58), (10.2, 44.9)]:
        wl, bw = sample_spectral_wcs(src.image_header, src.wave_table, x, y)
        awl, abw = ww.pixel_to_world_values(x, y)
        assert wl == pytest.approx(float(awl), abs=1e-7)
        assert bw == pytest.approx(float(abw), abs=1e-7)


def test_real_celestial_sip_matches_manual_polynomial():
    """astropy applies SIP incl. the A_0_0/B_0_0 terms present in SPHEREx headers."""
    fb = _bytes("epsilon_indi_b", "2026W18_1A_0516_1", 3)
    src = read_source(fb)
    h = src.image_header
    x0, y0 = 40.0, 12.0
    u, v = x0 + 1 - h["CRPIX1"], y0 + 1 - h["CRPIX2"]
    f = sum(h.get(f"A_{i}_{j}", 0.0) * u ** i * v ** j for i in range(4) for j in range(4 - i))
    g = sum(h.get(f"B_{i}_{j}", 0.0) * u ** i * v ** j for i in range(4) for j in range(4 - i))
    lin = h.copy()
    for k in list(lin.keys()):
        if k.split("_")[0] in ("A", "B", "AP", "BP") and "_" in k:
            del lin[k]
    lin["CTYPE1"], lin["CTYPE2"] = "RA---TAN", "DEC--TAN"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wl = WCS(lin, naxis=2)
    manual = wl.wcs_pix2world([[x0 + f, y0 + g]], 0)[0]
    auto = src.celestial.all_pix2world([[x0, y0]], 0)[0]
    assert np.allclose(manual, auto, atol=1e-9)
