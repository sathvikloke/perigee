"""Deliberate registration-offset negative control (N3).

Two layers:

* Synthetic (always runs, no raw data): a star field built from the cached Gaia
  catalog on a known TAN WCS. The image content is then moved by a known amount
  relative to the header. The validator must PASS the unmoved field and FAIL
  (or at worst report UNKNOWN, never PASS) the moved ones, and must recover the
  injected offset.
* Real derived fixtures (skipped without research/build_data): the same on a
  real SPHEREx cutout, plus the unmodified acceptance validator, documenting
  that its Gaia step loses every match at 2 px and then passes silently.

Run:  .venv/bin/python -m pytest science/reviews/registration-audit/tests -q
Raw data location: $PERIGEE_BUILD_DATA or the default research/build_data path.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest
from astropy.wcs import WCS

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
sys.path.insert(0, str(AUDIT))
import regcheck as rc  # noqa: E402

GAIA = AUDIT.parent / "acceptance" / "gaia"
DEFAULT_DATA = Path("/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data")
DATA = Path(os.environ.get("PERIGEE_BUILD_DATA", DEFAULT_DATA))
needs_data = pytest.mark.skipif(not (DATA / "manifest.json").exists(), reason="raw research/build_data not available")

MJD = 61159.5
FAR_TARGET = (0.0, -89.0)  # nothing near the synthetic field


# ------------------------------------------------------------------ synthetic


def synthetic_frame(n_keep=None, seed=7):
    cat = [c for c in rc.read_catalog(GAIA / "wise_0855.csv") if c["full"]]
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [133.75976526566546, -7.242182182223836]
    w.wcs.crpix = [30.5, 30.5]  # FITS 1-based: centre of a 60x60 image
    scale = 6.15 / 3600.0
    w.wcs.cd = [[-scale, 0.0], [0.0, scale]]  # north up, east left
    ny = nx = 60
    yy, xx = np.mgrid[0:ny, 0:nx].astype(float)
    img = np.full((ny, nx), 1.0)
    placed = []
    for c in sorted(cat, key=lambda c: c["G"]):
        ra, dec = rc.acc.gaia_at(c, MJD)
        x, y = (float(v) for v in w.all_world2pix([[ra, dec]], 0)[0])
        if 2 <= x <= nx - 3 and 2 <= y <= ny - 3:
            amp = 10 ** (-0.4 * (c["G"] - 13.0)) * 20.0
            img += amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 0.7 ** 2))
            placed.append(c)
    keep = placed if n_keep is None else placed[:n_keep]
    if n_keep is not None:  # rebuild with only the brightest n_keep stars
        img = np.full((ny, nx), 1.0)
        for c in keep:
            ra, dec = rc.acc.gaia_at(c, MJD)
            x, y = (float(v) for v in w.all_world2pix([[ra, dec]], 0)[0])
            amp = 10 ** (-0.4 * (c["G"] - 13.0)) * 20.0
            img += amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 0.7 ** 2))
    img += np.random.default_rng(seed).normal(0, 0.02, img.shape)
    var = np.full_like(img, 0.02 ** 2)
    flg = np.zeros(img.shape, np.int64)
    return cat, w, img, var, flg


def make_frame(w, img, var, flg):
    return rc.Frame(key="synthetic", img=img.astype(float), var=var.astype(float), flg=flg.astype(np.int64),
                    names={}, wcs=w, mjd=MJD, detector=1, scale_arcsec=6.15)


@pytest.fixture(scope="module")
def synth():
    return synthetic_frame()


def moved(synth, dx=0.0, dy=0.0, rot=0.0):
    cat, w, img, var, flg = synth
    i2, v2, f2 = rc.misregister_arrays(img, var, flg, dx, dy, rot)
    return cat, make_frame(w, i2, v2, f2)


def test_synthetic_identity_passes(synth):
    cat, fr = moved(synth)
    v = rc.registration_verdict(fr, cat, FAR_TARGET)
    assert v["verdict"] == "PASS", v
    assert v["best_offset_abs_px"] < 0.2
    assert v["best_support"] >= 8


@pytest.mark.parametrize("dx,dy", [(1.0, 0.0), (0.0, 2.0), (5.0, 0.0), (-2.0, 3.0)])
def test_synthetic_shift_is_caught_and_measured(synth, dx, dy):
    cat, fr = moved(synth, dx, dy)
    v = rc.registration_verdict(fr, cat, FAR_TARGET)
    assert v["verdict"] == "FAIL", v
    rx, ry = v["best_offset_px"]
    assert math.hypot(rx - dx, ry - dy) < 0.25, (rx, ry)


def test_synthetic_rotation_is_caught(synth):
    cat, fr = moved(synth, rot=3.0)
    v = rc.registration_verdict(fr, cat, FAR_TARGET)
    assert v["verdict"] == "FAIL", v


def test_synthetic_sparse_field_is_unknown_not_pass():
    cat, w, img, var, flg = synthetic_frame(n_keep=2)
    for dx in (0.0, 5.0):
        i2, v2, f2 = rc.misregister_arrays(img, var, flg, dx, 0.0, 0.0)
        v = rc.registration_verdict(make_frame(w, i2, v2, f2), cat, FAR_TARGET)
        assert v["verdict"] == "UNKNOWN", v


def test_legacy_rule_loses_all_matches_at_2px_and_reports_no_failure(synth):
    """Characterises the acceptance validator's blind spot: with the image 2 or 5
    native px off its header, the legacy Gaia step keeps no star (the 1 px
    association cut or the forced-window SNR cut removes them all) and its
    registration flag stays True. If this test starts failing, the acceptance
    validator has changed and README section 'How a wrong registration is
    caught' must be updated."""
    cat, fr0 = moved(synth)
    base = rc.legacy_gaia_rule(fr0, cat, FAR_TARGET)
    assert base["n_within_1px"] >= 8 and base["registration_ok"]
    for dx, dy in ((0.0, 2.0), (5.0, 0.0)):
        cat, fr = moved(synth, dx, dy)
        leg = rc.legacy_gaia_rule(fr, cat, FAR_TARGET)
        assert leg["n_within_1px"] == 0
        assert leg["registration_ok"] is True  # silent pass: no evidence, no failure
        assert rc.registration_verdict(fr, cat, FAR_TARGET)["verdict"] == "FAIL"


def test_forced_measure_matches_legacy_centroid(synth):
    cat, fr = moved(synth)
    n = 0
    for c in cat:
        ra, dec = rc.acc.gaia_at(c, MJD)
        x, y = (float(v) for v in fr.wcs.all_world2pix([[ra, dec]], 0)[0])
        legacy = rc.acc.native_centroid(fr.img, x, y)
        stage, res = rc.forced_measure(fr, x, y)
        assert (legacy is None) == (stage != "ok")
        if legacy is not None:
            n += 1
            assert abs(legacy[0] - res["cx"]) < 1e-12 and abs(legacy[1] - res["cy"]) < 1e-12
    assert n >= 8


def test_fixture_shift_is_exact_for_integer_pixels():
    a = np.arange(30.0).reshape(5, 6)
    i2, _, f2 = rc.misregister_arrays(a, a, a.astype(np.int64), 1.0, 2.0, 0.0)
    assert np.array_equal(i2[2:, 1:], a[:-2, :-1].astype(np.float32))
    assert np.isnan(i2[0, 0]) and np.isnan(i2[4, 0])


# -------------------------------------------------------------- real fixtures


@pytest.fixture(scope="module")
def real():
    m = json.loads((DATA / "manifest.json").read_text())
    return m, {t["id"]: t for t in m["targets"]}, {f"{f['obs_id']}_D{f['detector']}": f for f in m["files"]
                                                   if f.get("status") == "downloaded"}


@needs_data
@pytest.mark.parametrize("preset,key", [("barnards_star", "2025W35_1A_0008_1_D3"),
                                        ("wise_0855", "2026W19_1A_0227_1_D4"),
                                        ("epsilon_indi_b", "2026W18_1A_0516_1_D3")])
def test_real_fixture_offsets_fail(real, preset, key):
    m, targets, mby = real
    cat = rc.read_catalog(GAIA / f"{preset}.csv")
    for dx, dy, expect in ((0.0, 0.0, "PASS"), (1.0, 0.0, "FAIL"), (0.0, 2.0, "FAIL"), (5.0, 0.0, "FAIL")):
        hd = rc.misregistered_hdul(DATA / mby[key]["file"], dx, dy)
        fr = rc.frame_from_hdul(hd, key)
        pra, pdec, _, _ = rc.acc.predict(targets[preset], fr.mjd)
        v = rc.registration_verdict(fr, cat, (pra, pdec))
        assert v["verdict"] == expect, (key, dx, dy, v)
        if expect == "FAIL":
            assert math.hypot(v["best_offset_px"][0] - dx, v["best_offset_px"][1] - dy) < 0.3


@needs_data
def test_real_fixture_unmodified_acceptance_check_passes_2px_offset(real, tmp_path):
    """Runs science/reviews/acceptance/check_acceptance.check_one, unmodified, on a
    derived fixture (pixels moved 2 native px vs the header; PNG re-rendered the
    way processor A would). Its 'registration' column stays True: the PNG agrees
    with the (wrong) header and the Gaia step has no surviving star."""
    from PIL import Image
    m, targets, mby = real
    preset, key = "barnards_star", "2025W35_1A_0008_1_D3"
    rec = json.loads((AUDIT.parents[2] / "backend/content/presets" / preset / "frames" / f"{key}.json").read_text())
    hd = rc.misregistered_hdul(DATA / mby[key]["file"], 0.0, 2.0)
    fr = rc.frame_from_hdul(hd, key)
    gray, alpha = rc.render_png_arrays(fr, rec["registration"], rec["display_scale"])
    fits_p, png_p = tmp_path / "fx.fits", tmp_path / "fx.png"
    hd.writeto(fits_p)
    Image.fromarray(np.stack([gray, alpha], -1).astype(np.uint8), mode="LA").save(png_p)
    out = rc.acc.check_one(rec, str(png_p), None, str(fits_p), mby[key], targets[preset], [rec])
    assert out["evidence"]["png_reconstruction"]["alpha_match_fraction"] > 0.995
    assert out["evidence"]["gaia"]["n_png"] == 0
    assert out["checks"]["registration"] is True
    pra, pdec, _, _ = rc.acc.predict(targets[preset], fr.mjd)
    assert rc.registration_verdict(fr, rc.read_catalog(GAIA / f"{preset}.csv"), (pra, pdec))["verdict"] == "FAIL"


@needs_data
def test_validator_has_no_false_failures_on_real_frames(real):
    m, targets, mby = real
    fails = []
    for key, f in mby.items():
        fr = rc.load_frame(DATA / f["file"], key)
        pra, pdec, _, _ = rc.acc.predict(targets[f["target_id"]], fr.mjd)
        v = rc.registration_verdict(fr, rc.read_catalog(GAIA / f"{f['target_id']}.csv"), (pra, pdec))
        if v["verdict"] == "FAIL":
            fails.append((key, v["reasons"]))
    assert not fails
