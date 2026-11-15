"""Registration check (tools/ingest/check_registration.py) on SYNTHETIC data.

The check and its injected-offset test are adapted from Sagar Raut's
check_registration.py and test_data_registration.py (PR #19), ported to
processor A's grid and layout. All FITS here come from synthetic.py: they are
labelled test fixtures, not NASA observations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import synthetic as syn  # noqa: E402
from backend.data.process import FrameInput, TargetInput, process_frame  # noqa: E402
from tools.ingest.check_registration import check_set, field_mask, field_shift, grid_image  # noqa: E402

FOV, SIZE = 6.0, 256  # processor A's default grid
SCALE = FOV * 60.0 / SIZE  # 1.40625 arcsec per display pixel
# Field stars (native x, y, amplitude), all well outside the 50" (~8 native px) target mask.
FIELD = ((8, 10, 4.0), (50, 12, 3.0), (15, 48, 5.0), (46, 44, 3.5), (30, 6, 2.5),
         (6, 30, 3.0), (54, 30, 4.0), (28, 54, 3.0), (20, 20, 2.0), (40, 38, 2.5))
TARGET_NATIVE = (29.5, 29.5)


def _reg(ra: float, dec: float) -> dict:
    return {"center_ra_deg": ra, "center_dec_deg": dec, "fov_arcmin": FOV, "width": SIZE, "height": SIZE}


def _centre_mask() -> np.ndarray:
    return field_mask(SIZE, {"x": SIZE / 2, "y": SIZE / 2}, SCALE)


def _err_arcsec(dx: float, dy: float, expected_arcsec: tuple) -> float:
    return float(np.hypot(dx * SCALE - expected_arcsec[0], dy * SCALE - expected_arcsec[1]))


@pytest.mark.parametrize("dra_arcsec,ddec_arcsec", [(0, 6), (4, -3), (1.5, 0), (-2.5, -2.5)])
def test_injected_grid_offset_is_recovered(dra_arcsec, ddec_arcsec):
    """Moving the grid centre east/north by a known amount moves every field star
    west/south on the display (right/down). field_shift must report the shift
    that undoes it, within 0.5", and must not match a wrong answer."""
    b = syn.make_fits(sources=FIELD + (TARGET_NATIVE + (20.0,),))
    ra, dec = syn.CENTER
    a_img = grid_image(b, _reg(ra, dec))
    b_img = grid_image(b, _reg(ra + dra_arcsec / 3600 / np.cos(np.radians(dec)), dec + ddec_arcsec / 3600))
    dx, dy, contrast = field_shift(a_img, b_img, _centre_mask())

    expected = (-dra_arcsec, -ddec_arcsec)  # display arcsec: +x is west, +y is south
    assert _err_arcsec(dx, dy, expected) < 0.5
    assert contrast > 5
    # The same measurement must fail the wrong expectations: opposite sign, or off by 2".
    for wrong in ((dra_arcsec, ddec_arcsec), (expected[0] + 2.0, expected[1]), (expected[0], expected[1] - 2.0)):
        if wrong != expected:
            assert _err_arcsec(dx, dy, wrong) > 1.0


def test_zero_offset_gives_zero_shift():
    b = syn.make_fits(sources=FIELD)
    img = grid_image(b, _reg(*syn.CENTER))
    dx, dy, _ = field_shift(img, img, _centre_mask())
    assert abs(dx) < 1e-6 and abs(dy) < 1e-6


def test_moving_target_inside_mask_does_not_register_as_field_shift():
    """A bright target that moves ~9" between frames (inside the mask) while the
    field stays put must give a field shift near zero."""
    still = syn.make_fits(sources=FIELD + ((29.5, 29.5, 40.0),))
    moved = syn.make_fits(sources=FIELD + ((31.0, 29.5, 40.0),))
    reg = _reg(*syn.CENTER)
    a_img, b_img = grid_image(still, reg), grid_image(moved, reg)
    dx, dy, _ = field_shift(a_img, b_img, _centre_mask())
    assert np.hypot(dx, dy) * SCALE < 0.3
    # Without the mask the bright target dominates and the "field" shift is wrong.
    ux, _, _ = field_shift(a_img, b_img, np.ones((SIZE, SIZE), dtype=bool))
    assert abs(ux) * SCALE > 3.0


def _write_case_set(tmp_path: Path, wcs_error_native_px: float):
    """A two-frame synthetic set in processor A's layout, built by process_frame.
    The second frame's WCS is wrong by ``wcs_error_native_px`` native pixels in x."""
    set_dir = tmp_path / "presets" / "synthetic" / "case-test"
    raw = tmp_path / "raw"
    set_dir.mkdir(parents=True)
    raw.mkdir()
    ledger, records = {}, []
    target = TargetInput(*syn.CENTER, name="Synthetic target")
    for i, off in enumerate((0.0, wcs_error_native_px)):
        obsid = f"2099W01_1A_000{i + 1}_1"
        b = syn.make_fits(sources=FIELD + (TARGET_NATIVE + (20.0,),), obsid=obsid, crpix_offset=(off, 0.0))
        pf = process_frame(b, FrameInput(query_ra_deg=syn.CENTER[0], query_dec_deg=syn.CENTER[1], target=target))
        key = pf.record["frame_key"]
        (raw / f"{key}.fits").write_bytes(b)
        (set_dir / f"{key}.png").write_bytes(pf.png_bytes)
        ledger[key] = {"file": f"raw/{key}.fits"}
        records.append(pf.record)
    (set_dir / "frames.json").write_text(json.dumps(
        {"preset_id": "synthetic", "set": "case-test", "grid_id": records[0]["registration"]["grid_id"],
         "frames": records}))
    return set_dir, ledger


def test_check_set_on_processor_a_layout_registered(tmp_path):
    set_dir, ledger = _write_case_set(tmp_path, 0.0)
    rep = check_set(set_dir, tmp_path, ledger)
    (pair,) = rep["pairs"]
    assert rep["display_scale_arcsec_per_px"] == pytest.approx(SCALE)
    assert pair["field_shift_raw"]["arcsec"] < 0.1
    assert pair["field_shift_product_png"]["arcsec"] < 0.1
    assert pair["catalog_marker_shift_arcsec"] == pytest.approx(0.0, abs=1e-6)
    assert pair["cross_band"] is False


def test_check_set_detects_injected_wcs_error(tmp_path):
    """Half a native pixel (3.075") of WCS error in frame 2: the field appears
    3.075" east (display left), so the shift that undoes it is +x."""
    set_dir, ledger = _write_case_set(tmp_path, 0.5)
    (pair,) = check_set(set_dir, tmp_path, ledger)["pairs"]
    dx, dy = pair["field_shift_raw"]["px"]
    assert dx * SCALE == pytest.approx(0.5 * 6.15, abs=0.5)
    assert abs(dy) * SCALE < 0.5
    assert pair["field_shift_product_png"]["arcsec"] == pytest.approx(0.5 * 6.15, abs=1.0)
    assert pair["field_shift_raw"]["arcsec"] > 2.0  # a registered-looking answer would be wrong


def test_check_set_rejects_raw_file_that_does_not_match_provenance(tmp_path):
    set_dir, ledger = _write_case_set(tmp_path, 0.0)
    key = next(iter(ledger))
    (tmp_path / ledger[key]["file"]).write_bytes(syn.make_fits(sources=FIELD[:3], obsid="2099W01_1A_0001_1"))
    with pytest.raises(ValueError, match="sha256"):
        check_set(set_dir, tmp_path, ledger)
