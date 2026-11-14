"""Unit checks for backend/data/process.py on SYNTHETIC fixtures (not NASA data).

Real-file checks live in test_real_frames.py and are skipped unless the
retained dataset is available (PERIGEE_DATA_ROOT).
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import synthetic as syn  # noqa: E402
from backend.data.process import (  # noqa: E402
    FrameInput,
    IntegrityError,
    InvalidInputError,
    TargetInput,
    UnsupportedDataError,
    grid_wcs,
    inspect_fits,
    png_data_url,
    process_frame,
    sky_to_display_px,
    with_image_sources,
)

RA0, DEC0 = syn.CENTER
PX = syn.SCALE_DEG  # one native pixel in degrees


def meta(**kw) -> FrameInput:
    base = dict(query_ra_deg=RA0, query_dec_deg=DEC0, target=TargetInput(RA0, DEC0, name="Test target"))
    base.update(kw)
    return FrameInput(**base)


def png_rgba(b: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(b)).convert("RGBA"))


# ---------------------------------------------------------------- coverage / wavelength


def test_off_image_position_is_not_covered_with_null_wavelength_and_counts():
    # Target 1 degree away: far off the 60x60 (~6 arcmin) synthetic cutout.
    rec = process_frame(syn.make_fits(), meta(target=TargetInput(RA0 + 1.0, DEC0))).record
    q = rec["quality"]
    assert q["status"] == "not_covered"
    assert q["covered"] is False
    assert rec["wavelength_um"] is None
    assert rec["bandwidth_um"] is None
    assert "not extrapolated" in rec["wavelength_location"]
    # Unknown counts are null, never zero.
    assert q["valid_aperture_pixels"] is None
    assert q["adverse_aperture_pixels"] is None
    assert q["screened_pixels"] is None


def test_position_just_off_the_edge_is_not_covered_even_though_wcs_could_extrapolate():
    # 1.5 native pixels beyond the last pixel center in +x. TAN x increases westward (RA decreasing).
    x_off = syn.NX - 1 + 1.5
    ra = RA0 - (x_off - (syn.NX / 2 - 0.5)) * PX / np.cos(np.radians(DEC0))
    rec = process_frame(syn.make_fits(), meta(target=TargetInput(ra, DEC0))).record
    assert rec["sampled_position"]["native_x"] == pytest.approx(x_off, abs=0.05)
    assert rec["quality"]["status"] == "not_covered"
    assert rec["wavelength_um"] is None


def test_covered_wavelength_matches_lookup_table():
    rec = process_frame(syn.make_fits(), meta()).record
    x = rec["sampled_position"]["native_x"]
    assert rec["quality"]["covered"] is True
    assert rec["wavelength_um"] == pytest.approx(syn.wavelength_at_native(x), abs=1e-6)
    assert rec["bandwidth_um"] == pytest.approx(syn.BW, abs=1e-6)
    assert "catalog-predicted position of Test target" in rec["wavelength_location"]


def test_missing_spectral_table_leaves_wavelength_null_with_note():
    rec = process_frame(syn.make_fits(include_wave=False), meta()).record
    assert rec["wavelength_um"] is None
    assert any("Wavelength unavailable" in n for n in rec["quality"]["notes"])


# ---------------------------------------------------------------- quality screen


def test_nonfinite_pixel_at_covered_position_is_flagged_not_uncovered():
    img = (0.5 * np.ones((syn.NY, syn.NX))).astype(np.float32)
    img[30, 30] = np.nan  # the target maps to native (29.5, 29.5); (30,30) is inside the 2.5 px circle
    rec = process_frame(syn.make_fits(image=img), meta()).record
    q = rec["quality"]
    assert q["covered"] is True
    assert q["status"] == "flagged"
    assert q["nonfinite_aperture_pixels"] == 1
    assert q["adverse_aperture_pixels"] == 1
    assert q["valid_aperture_pixels"] == q["screened_pixels"] - 1
    assert rec["wavelength_um"] is not None  # still covered -> wavelength sampled


def test_saturated_core_is_flagged_not_uncovered():
    # Like R Draconis: many non-finite central pixels must not read as missing coverage.
    img = (0.5 * np.ones((syn.NY, syn.NX))).astype(np.float32)
    img[26:34, 26:34] = np.nan
    rec = process_frame(syn.make_fits(image=img), meta()).record
    assert rec["quality"]["status"] == "flagged"
    assert rec["quality"]["covered"] is True


def test_informational_flags_alone_stay_clear():
    flags = np.zeros((syn.NY, syn.NX), dtype=np.int32)
    flags[25:35, 25:35] = (1 << syn.BIT["SOURCE"]) | (1 << syn.BIT["FULLSAMPLE"])
    rec = process_frame(syn.make_fits(flags=flags), meta()).record
    q = rec["quality"]
    assert q["status"] == "clear"
    assert q["flag_names"] == []
    assert q["flag_counts"]["SOURCE"] == q["screened_pixels"]
    assert q["adverse_aperture_pixels"] == 0  # known zero (flags present), not unknown
    assert any("not a detection" in n for n in q["notes"])


def test_adverse_flag_in_circle_is_flagged_with_names():
    flags = np.zeros((syn.NY, syn.NX), dtype=np.int32)
    flags[29, 30] = (1 << syn.BIT["OVERFLOW"]) | (1 << syn.BIT["SOURCE"])
    flags[5, 5] = 1 << syn.BIT["HOT"]  # outside the circle: ignored
    rec = process_frame(syn.make_fits(flags=flags), meta()).record
    q = rec["quality"]
    assert q["status"] == "flagged"
    assert q["flag_names"] == ["OVERFLOW"]
    assert q["adverse_aperture_pixels"] == 1


def test_unknown_counts_are_null_when_flags_extension_missing():
    rec = process_frame(syn.make_fits(include_flags=False), meta()).record
    q = rec["quality"]
    assert q["status"] == "unknown"
    assert q["valid_aperture_pixels"] is None
    assert q["adverse_aperture_pixels"] is None
    assert any("FLAGS extension missing" in n for n in q["notes"])


def test_missing_flags_but_nonfinite_at_position_is_still_flagged():
    img = (0.5 * np.ones((syn.NY, syn.NX))).astype(np.float32)
    img[30, 30] = np.inf
    rec = process_frame(syn.make_fits(image=img, include_flags=False), meta()).record
    assert rec["quality"]["status"] == "flagged"
    assert rec["quality"]["adverse_aperture_pixels"] is None


def test_missing_variance_with_nothing_wrong_is_unknown_not_clear():
    rec = process_frame(syn.make_fits(include_variance=False), meta()).record
    q = rec["quality"]
    assert q["status"] == "unknown"
    assert q["covered"] is True
    assert any("no usable VARIANCE map" in n for n in q["notes"])
    assert not any("not a detection" in n for n in q["notes"])  # the clear-screen note is absent


def test_missing_variance_does_not_hide_a_known_flag():
    flags = np.zeros((syn.NY, syn.NX), dtype=np.int32)
    flags[29, 30] = 1 << syn.BIT["OVERFLOW"]
    rec = process_frame(syn.make_fits(flags=flags, include_variance=False), meta()).record
    assert rec["quality"]["status"] == "flagged"
    assert rec["quality"]["flag_names"] == ["OVERFLOW"]


def _corner_target() -> TargetInput:
    """Target just inside a corner pixel centre: only about a quarter of the
    2.5 px screen circle falls on the image."""
    x = syn.NX - 1 - 0.2
    y = syn.NY - 1 - 0.2
    ra = RA0 - (x - (syn.NX / 2 - 0.5)) * PX / np.cos(np.radians(DEC0))
    dec = DEC0 + (y - (syn.NY / 2 - 0.5)) * PX
    return TargetInput(ra, dec)


def test_clipped_circle_with_fewer_than_ten_usable_pixels_is_unknown():
    rec = process_frame(syn.make_fits(), meta(target=_corner_target())).record
    q = rec["quality"]
    assert q["covered"] is True
    assert q["valid_aperture_pixels"] < 10
    assert q["status"] == "unknown"
    assert any("screening heuristic, not a NASA" in n for n in q["notes"])


def test_clipped_circle_with_a_flag_stays_flagged():
    flags = np.zeros((syn.NY, syn.NX), dtype=np.int32)
    flags[syn.NY - 1, syn.NX - 1] = 1 << syn.BIT["HOT"]
    rec = process_frame(syn.make_fits(flags=flags), meta(target=_corner_target())).record
    assert rec["quality"]["status"] == "flagged"


def test_undocumented_flag_bit_counts_as_a_problem():
    flags = np.zeros((syn.NY, syn.NX), dtype=np.int32)
    unused = next(b for b in range(31) if b not in syn.BIT.values())
    flags[29, 30] = 1 << unused
    rec = process_frame(syn.make_fits(flags=flags), meta()).record
    q = rec["quality"]
    assert q["status"] == "flagged"
    assert q["flag_names"] == [f"UNDOCUMENTED_BIT_{unused}"]


# ---------------------------------------------------------------- marker and grid


def test_marker_is_catalog_prediction_never_detection():
    rec = process_frame(syn.make_fits(), meta()).record
    m = rec["marker"]
    assert m["kind"] == "catalog_prediction"
    assert "detection" not in m["kind"]
    assert "not a detection" in m["label"]
    assert m["x"] == pytest.approx(128.0, abs=1e-6) and m["y"] == pytest.approx(128.0, abs=1e-6)
    blob = json.dumps(rec)
    assert '"kind": "detection"' not in blob


def test_no_target_means_no_marker_and_query_center_screen():
    rec = process_frame(syn.make_fits(), meta(target=None)).record
    assert rec["marker"] is None
    assert rec["sampled_position"]["kind"] == "query_center"
    assert "query center" in rec["wavelength_location"]


def test_proper_motion_moves_marker_not_grid():
    t = TargetInput(RA0, DEC0, epoch_jyear=2000.0, pm_ra_cosdec_masyr=0.0, pm_dec_masyr=10000.0, parallax_mas=500.0)
    a = process_frame(syn.make_fits(mjd_avg=60000.0), meta(target=t)).record
    b = process_frame(syn.make_fits(mjd_avg=60365.25), meta(target=t)).record
    assert a["registration"] == b["registration"]  # identical fixed grid
    # ~10 arcsec north per year -> marker y decreases (north is up) by ~10/1.406 display px
    dy = a["marker"]["y"] - b["marker"]["y"]
    assert dy == pytest.approx(10.0 / (6 * 60 / 256), rel=0.05)
    assert a["marker"]["x"] == pytest.approx(b["marker"]["x"], abs=0.05)
    assert a["marker"]["propagated"] is True


def test_grid_orientation_north_up_east_left():
    gw = grid_wcs(RA0, DEC0, 6.0, 256)
    x0, y0 = sky_to_display_px(gw, 256, RA0, DEC0)
    xe, _ = sky_to_display_px(gw, 256, RA0 + 0.01, DEC0)  # east
    _, yn = sky_to_display_px(gw, 256, RA0, DEC0 + 0.01)  # north
    assert (x0, y0) == pytest.approx((128.0, 128.0))
    assert xe < x0  # east is left
    assert yn < y0  # north is up


def test_png_pixels_follow_the_sky_not_the_detector():
    # Put a bright source NE of center on a rotated detector; it must appear up-left in the PNG.
    rot = 30.0
    ra_s, dec_s = RA0 + 30 / 3600 / np.cos(np.radians(DEC0)), DEC0 + 30 / 3600
    from astropy.wcs import WCS

    w = WCS(syn.celestial_header(rot))
    sx, sy = w.world_to_pixel_values(ra_s, dec_s)
    pf = process_frame(syn.make_fits(rot_deg=rot, sources=((float(sx), float(sy), 50.0),)), meta())
    rgba = png_rgba(pf.png_bytes)
    assert rgba.shape == (256, 256, 4)
    gray = np.where(rgba[..., 3] > 0, rgba[..., 0].astype(int), -1)
    # Centroid of the brightest display pixels (the stretch saturates the source core).
    ys, xs = np.nonzero(gray == gray.max())
    bx, by = xs.mean() + 0.5, ys.mean() + 0.5
    ex, ey = sky_to_display_px(grid_wcs(RA0, DEC0, 6.0, 256), 256, ra_s, dec_s)
    assert abs(bx - ex) < 4.4 and abs(by - ey) < 4.4  # within one native pixel (~4.4 display px)
    assert bx < 128 and by < 128


def test_off_image_area_is_transparent_and_grid_is_identical_for_different_targets():
    # A 2x field on a ~6 arcmin cutout: the outer area must be transparent, not black data.
    pf = process_frame(syn.make_fits(), meta(fov_arcmin=12.0))
    a = png_rgba(pf.png_bytes)[..., 3]
    assert a[0, 0] == 0 and a[128, 128] == 255
    other = process_frame(syn.make_fits(), meta(fov_arcmin=12.0, target=TargetInput(RA0 + 0.01, DEC0)))
    assert other.record["registration"] == pf.record["registration"]


# ---------------------------------------------------------------- display scale, ids, errors


def test_display_scale_modes():
    per = process_frame(syn.make_fits(), meta()).record["display_scale"]
    assert per["mode"] == "per_frame" and "not directly comparable" in per["basis"]
    sh = process_frame(syn.make_fits(), meta(display_limits=(0.4, 0.6))).record["display_scale"]
    assert sh["mode"] == "shared" and (sh["low"], sh["high"]) == (0.4, 0.6)
    assert sh["background_subtraction"] is None


def test_identity_time_and_provenance_from_header():
    b = syn.make_fits(obsid="2099W01_1A_0001_1", detector=5, date_avg="2025-11-24T12:00:00.000", mjd_avg=61003.5)
    rec = process_frame(b, meta(source_url="https://irsa.ipac.caltech.edu/x/l2b-v27-2026-244/a.fits",
                                collection_id="spherex_qr3")).record
    assert rec["frame_key"] == rec["frame_id"] == "2099W01_1A_0001_1_D5"
    assert rec["observed_at_utc"] == "2025-11-24T12:00:00.000Z"
    assert rec["mjd"] == 61003.5
    assert rec["provenance"]["pipeline_version"] == "l2b-v27-2026-244"
    assert len(rec["provenance"]["sha256"]) == 64
    assert any("Quick-release" in s for s in rec["limitations"])
    json.dumps(rec)  # JSON-serializable


def test_image_sources_helper_and_data_url():
    pf = process_frame(syn.make_fits(), meta())
    assert pf.record["image"]["src"] is None
    url = png_data_url(pf.png_bytes)
    rec = with_image_sources(pf.record, url, None)
    assert rec["image"]["src"].startswith("data:image/png;base64,")
    assert rec["flag_image"] is None
    assert pf.record["image"]["src"] is None  # original untouched


@pytest.mark.parametrize("bad", [b"", b"not a fits file" * 300, b"SIMPLE  =" + b" " * 3000])
def test_garbage_bytes_are_unsupported_data(bad):
    with pytest.raises(UnsupportedDataError):
        process_frame(bad, meta())


def _hdu_layout(b: bytes):
    """(name, header_start, data_start, data_end) for each HDU of a FITS byte string."""
    from astropy.io import fits

    with fits.open(io.BytesIO(b), memmap=False) as h:
        out = []
        for hdu in h:
            info = hdu.fileinfo()
            out.append((hdu.name, info["hdrLoc"], info["datLoc"], info["datLoc"] + info["datSpan"]))
        return out


def test_file_cut_off_inside_a_data_unit_is_unsupported_data_not_a_crash():
    """Headers intact, pixel data short: must raise UnsupportedDataError (API -> 422
    UNSUPPORTED_DATA), not a bare TypeError from astropy's lazy data read (API -> 500)."""
    b = syn.make_fits()
    cuts = []
    for name, _hdr, dat, end in _hdu_layout(b):
        if end - dat >= 2 * 2880:
            cuts.append(dat + 2880)  # one block into this data unit
    assert cuts, "synthetic file should have a data unit at least two blocks long"
    for cut in cuts:
        with pytest.raises(UnsupportedDataError):
            process_frame(b[:cut], meta())


def test_file_cut_at_every_block_never_escapes_untyped_or_reads_clear():
    """Every 2880-byte cut point. A cut inside a data unit must raise
    UnsupportedDataError. A cut exactly between extensions leaves a valid but
    shorter FITS file that the processor cannot tell from one that never had
    those extensions. It may only read "clear" if FLAGS and VARIANCE both survived,
    and the wavelength must be null if WCS-WAVE was cut off."""
    b = syn.make_fits()
    layout = {name: end for name, _h, _d, end in _hdu_layout(b)}
    boundaries = set(layout.values())
    for cut in range(2880, len(b), 2880):
        if cut in boundaries:
            try:
                rec = process_frame(b[:cut], meta()).record
            except UnsupportedDataError:
                continue  # e.g. cut before IMAGE: nothing usable
            if cut < max(layout["FLAGS"], layout["VARIANCE"]):
                assert rec["quality"]["status"] != "clear", cut
            if cut < layout["WCS-WAVE"]:
                assert rec["wavelength_um"] is None, cut
        else:
            with pytest.raises(UnsupportedDataError):
                process_frame(b[:cut], meta())


def test_integrity_checks():
    b = syn.make_fits()
    with pytest.raises(IntegrityError):
        process_frame(b, meta(expected_sha256="0" * 64))
    with pytest.raises(IntegrityError):
        process_frame(b, meta(observation_id="2000W01_1A_0000_0"))
    with pytest.raises(IntegrityError):
        process_frame(b, meta(detector=6))


@pytest.mark.parametrize("kw", [dict(query_ra_deg=float("nan")), dict(query_ra_deg=360.0),
                                dict(query_dec_deg=91.0), dict(fov_arcmin=0.0), dict(grid_size=8),
                                dict(display_limits=(1.0, 1.0))])
def test_invalid_metadata_rejected(kw):
    with pytest.raises(InvalidInputError):
        process_frame(syn.make_fits(), meta(**kw))


# ---------------------------------------------------------------- header inspection


def test_inspect_fits_reports_extensions_and_flag_bits():
    info = inspect_fits(syn.make_fits())
    names = [e["name"] for e in info["extensions"]]
    assert names == ["PRIMARY", "IMAGE", "FLAGS", "VARIANCE", "ZODI", "WCS-WAVE"]
    assert info["image"]["CTYPE1W"] == "WAVE-TAB"
    assert info["flag_bits"]["21"] == "SOURCE"
