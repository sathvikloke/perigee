"""Frame processing on real (trimmed) SPHEREx files, checked against the original audit."""
import io

import numpy as np
import pytest
from conftest import (
    BARNARD_CENTER,
    BARNARD_OBS,
    BARNARD_URL,
    EPSINDB_AUDIT,
    EPSINDB_CENTER,
    EPSINDB_OBS,
    EPSINDB_URL,
    drop_extension,
)
from PIL import Image

from data import FrameContext, ObservationDescriptor, SharedScale, UnsupportedData, process_frame
from data.fits_io import open_cutout
from data.wavelength import table_lookup, wavelength_at


def eps_ctx(target=None, **kw):
    o = ObservationDescriptor(EPSINDB_OBS, "spherex_dr1", None, 61159.503360127, 3, EPSINDB_URL)
    return FrameContext(o, *EPSINDB_CENTER, fov_arcmin=kw.pop("fov", 4.0), target=target, **kw)


def barnard_ctx(target=None):
    o = ObservationDescriptor(BARNARD_OBS, "spherex_dr1", None, None, 2, BARNARD_URL)
    return FrameContext(o, *BARNARD_CENTER, fov_arcmin=4.0, target=target)


def png_size(b):
    im = Image.open(io.BytesIO(b))
    return im.size, im.mode


def test_wavelength_matches_audit_and_independent_table_read(epsindb_bytes, epsindb_target):
    rec = process_frame(epsindb_bytes, eps_ctx(epsindb_target)).record
    assert rec["wavelength_um"] == pytest.approx(EPSINDB_AUDIT["wavelength_um"], abs=1e-6)
    assert rec["bandwidth_um"] == pytest.approx(EPSINDB_AUDIT["bandwidth_um"], abs=1e-6)
    cut = open_cutout(epsindb_bytes)
    wl, bw = table_lookup(cut, EPSINDB_AUDIT["x"], EPSINDB_AUDIT["y"])
    assert wl == pytest.approx(EPSINDB_AUDIT["wavelength_um"], abs=1e-6)
    assert "predicted target position" in rec["wavelength_location"]


def test_wavelength_differs_across_the_same_detector(epsindb_bytes):
    """Same file, two positions 2 arcmin apart: the LVF gives different wavelengths."""
    cut = open_cutout(epsindb_bytes)
    ra, dec = EPSINDB_CENTER
    a = wavelength_at(cut, ra, dec).wavelength_um
    b = wavelength_at(cut, ra, dec + 2 / 60).wavelength_um
    assert a and b and abs(a - b) > 0.005


def test_clear_screen_matches_audit(epsindb_bytes, epsindb_target):
    q = process_frame(epsindb_bytes, eps_ctx(epsindb_target)).record["quality"]
    assert q["status"] == "clear" and q["covered"] is True
    assert q["valid_aperture_pixels"] == EPSINDB_AUDIT["aperture_pixels"] and q["adverse_aperture_pixels"] == 0
    assert any("not show that a source was detected" in n for n in q["notes"])


def test_bright_flagged_target_stays_flagged(barnard_bytes, barnard_target):
    q = process_frame(barnard_bytes, barnard_ctx(barnard_target)).record["quality"]
    assert q["status"] == "flagged" and q["valid_aperture_pixels"] == 0 and q["adverse_aperture_pixels"] > 0
    assert q["covered"] is True  # saturated, not uncovered (board decision 3)
    assert "OVERFLOW" in q["flag_names"] and "SOURCE" not in q["flag_names"]


def test_nonfinite_pixels_alone_make_a_frame_flagged(epsindb_bytes):
    """Blank out the target's pixels (synthetic edit of the real file) with no flag set."""
    from astropy.io import fits
    import io as _io

    with fits.open(_io.BytesIO(epsindb_bytes)) as hdul:
        img = hdul["IMAGE"].data.copy()
        img[27:31, 27:31] = np.nan
        hdul["IMAGE"].data = img
        buf = _io.BytesIO()
        hdul.writeto(buf)
    rec = process_frame(buf.getvalue(), eps_ctx()).record
    assert rec["quality"]["status"] == "flagged" and rec["quality"]["covered"] is True
    assert any("no usable value" in n for n in rec["quality"]["notes"])


def test_position_off_the_image_is_not_covered_never_clear(epsindb_bytes):
    o = ObservationDescriptor(EPSINDB_OBS, "spherex_dr1", None, None, 3, EPSINDB_URL)
    from data import CatalogTarget

    far = CatalogTarget("x", "far", EPSINDB_CENTER[0], EPSINDB_CENTER[1] + 0.2, 2026.3, 0.0, 0.0, "test")
    rec = process_frame(epsindb_bytes, FrameContext(o, *EPSINDB_CENTER, 4.0, target=far)).record
    assert rec["quality"]["status"] == "not_covered" and rec["quality"]["covered"] is False
    assert rec["quality"]["valid_aperture_pixels"] is None  # not measured, not "zero bad pixels"
    assert rec["wavelength_um"] is None and rec["marker"] is None
    assert any("outside the displayed field" in L for L in rec["limitations"])


def test_missing_flags_means_unknown(epsindb_bytes):
    rec = process_frame(drop_extension(epsindb_bytes, "FLAGS"), eps_ctx()).record
    assert rec["quality"]["status"] == "unknown" and rec["quality"]["adverse_aperture_pixels"] is None
    assert rec["flag_image"] is None


def test_missing_variance_means_unknown_not_invented(epsindb_bytes):
    rec = process_frame(drop_extension(epsindb_bytes, "VARIANCE"), eps_ctx()).record
    assert rec["quality"]["status"] == "unknown"


def test_missing_wavelength_table_stays_null(epsindb_bytes):
    rec = process_frame(drop_extension(epsindb_bytes, "WCS-WAVE"), eps_ctx()).record
    assert rec["wavelength_um"] is None and rec["bandwidth_um"] is None
    assert any("Wavelength unknown" in L for L in rec["limitations"])


def test_wrong_file_for_the_observation_is_rejected(epsindb_bytes):
    o = ObservationDescriptor("2025W34_2B_0557_4", "spherex_dr1", None, None, 2, BARNARD_URL)
    with pytest.raises(UnsupportedData):
        process_frame(epsindb_bytes, FrameContext(o, *EPSINDB_CENTER, 4.0))
    wrong_det = ObservationDescriptor(EPSINDB_OBS, "spherex_dr1", None, None, 6, EPSINDB_URL.replace("/3/", "/6/").replace("1D3", "1D6"))
    with pytest.raises(UnsupportedData):
        process_frame(epsindb_bytes, FrameContext(wrong_det, *EPSINDB_CENTER, 4.0))


@pytest.mark.parametrize("bad", [b"", b"<html>oops</html>", b"SIMPLE  =" + b" " * 100])
def test_corrupt_bytes_fail_with_unsupported_data(bad):
    with pytest.raises(UnsupportedData):
        process_frame(bad, eps_ctx())


def test_truncated_real_file(epsindb_bytes):
    with pytest.raises(UnsupportedData):
        process_frame(epsindb_bytes[: len(epsindb_bytes) // 3], eps_ctx())


def test_output_geometry_and_pngs(epsindb_bytes, epsindb_target):
    p = process_frame(epsindb_bytes, eps_ctx(epsindb_target))
    r = p.record
    assert png_size(p.image_png) == ((256, 256), "LA")
    assert png_size(p.flag_png)[0] == (256, 256)
    reg = r["registration"]
    assert reg["center_ra_deg"] == EPSINDB_CENTER[0] and reg["orientation"] == "north_up_east_left"
    assert reg["scale_arcsec_per_px"] == pytest.approx(4 * 60 / 256)
    assert r["marker"]["kind"] == "catalog_prediction" and "Not a measured position" in r["marker"]["source"]
    assert 0 <= r["marker"]["x"] <= 256 and 0 <= r["marker"]["y"] <= 256
    assert r["provenance"]["original_url"] == EPSINDB_URL and len(r["provenance"]["sha256"]) == 64
    assert r["display_scale"]["mode"] == "per_frame"
    assert r["observed_at_utc"] == "2026-04-29T12:05:47.874Z"  # DATE-AVG, mid-exposure (board decision 2)
    assert r["mjd"] == pytest.approx(61159.504026317) and r["frame_key"] == "2026W18_1A_0516_1_D3"
    assert r["image"]["src"] is None
    assert p.with_data_urls()["image"]["src"].startswith("data:image/png;base64,")


def test_grid_is_fixed_on_the_sky_not_on_the_target(epsindb_bytes, epsindb_target):
    """Registration never depends on the target; only the marker moves."""
    a = process_frame(epsindb_bytes, eps_ctx(epsindb_target)).record
    b = process_frame(epsindb_bytes, eps_ctx(None)).record
    assert a["registration"] == b["registration"] and a["frame_id"] == b["frame_id"]


def test_marker_follows_catalog_proper_motion(epsindb_target):
    from data.process import predicted_position

    ra0, dec0, _ = predicted_position(epsindb_target, 61159.5)
    ra1, dec1, _ = predicted_position(epsindb_target, 61159.5 + 5 * 365.25)
    shift_arcsec = np.hypot((ra1 - ra0) * np.cos(np.radians(dec0)), dec1 - dec0) * 3600
    assert shift_arcsec == pytest.approx(5 * np.hypot(3.981977, 2.466832), rel=1e-3)


def test_shared_scale_is_recorded(epsindb_bytes):
    r = process_frame(epsindb_bytes, eps_ctx(shared_scale=SharedScale(-0.1, 3.0, 0.2))).record["display_scale"]
    assert r["mode"] == "shared" and r["high"] == 3.0
    assert "not a calibrated brightness comparison" in r["basis"]


def test_live_frame_json_stays_small(epsindb_bytes):
    import json

    p = process_frame(epsindb_bytes, eps_ctx(fov=6.0))
    assert len(json.dumps(p.with_data_urls())) < 200_000


def test_no_data_pixels_are_never_filled_in(barnard_bytes):
    """Barnard's saturated core has non-finite pixels; the display must leave them empty."""
    from data.grid import GridSpec, resample_bilinear, source_pixel_coords

    cut = open_cutout(barnard_bytes)
    g = GridSpec(*BARNARD_CENTER, 6.0, 256)
    sx, sy = source_pixel_coords(g, cut.wcs)
    out = resample_bilinear(cut.image, sx, sy)
    xn, yn = np.round(sx).astype(int), np.round(sy).astype(int)
    on = (xn >= 0) & (yn >= 0) & (xn < cut.shape[1]) & (yn < cut.shape[0])
    nearest_nan = np.zeros_like(on)
    nearest_nan[on] = ~np.isfinite(cut.image[yn[on], xn[on]])
    assert nearest_nan.sum() > 0
    assert np.isnan(out[nearest_nan]).all()
