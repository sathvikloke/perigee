"""Unit tests for the candidate-B processor (synthetic fixtures; no network)."""

from __future__ import annotations

import io
import math

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from backend.data.process import (
    FrameInput,
    ProcessingError,
    display_wcs,
    process_frame,
    read_source,
    resample,
    resample_flags_nearest,
    sample_spectral_wcs,
)
from backend.tests.data import synth

RA0, DEC0 = synth.CENTER
N = 256
SCALE = 6.0 * 60.0 / N  # arcsec per display pixel
# The display peak sits near the nearest native pixel centre (resampling adds no
# resolution), so allow 0.75 native pixel. An orientation/sign error would be ~85 px.
PEAK_TOL = 0.75 * synth.NATIVE_ARCSEC / SCALE


def _meta(**kw):
    d = dict(center_ra_deg=RA0, center_dec_deg=DEC0, fov_arcmin=6.0, grid_size=N, collection_id="spherex_test")
    d.update(kw)
    return FrameInput.from_dict(d)


def _offset(east_arcsec: float, north_arcsec: float):
    return RA0 + east_arcsec / 3600.0 / math.cos(math.radians(DEC0)), DEC0 + north_arcsec / 3600.0


def _brightest(fits_bytes: bytes, meta: FrameInput):
    """Peak of the resampled (unclipped) display values, in top-left pixel-centre convention."""
    v = resample(read_source(fits_bytes), meta).values  # rows already top-down (north first)
    y, x = np.unravel_index(np.nanargmax(v), v.shape)
    return x + 0.5, y + 0.5


# --------------------------------------------------------------------------- orientation


@pytest.mark.parametrize("rotation", [0.0, 23.0, -67.0, 180.0])
@pytest.mark.parametrize("flip", [False, True])
def test_known_offset_star_lands_east_left_north_up(rotation, flip):
    """A star 60" east of centre lands left of centre; 60" north lands above, whatever the native WCS."""
    star_e = _offset(60.0, 0.0)
    fb = synth.make_cutout(rotation_deg=rotation, flip_parity=flip, stars=[(*star_e, 100.0)])
    meta = _meta(target={"ra_deg": star_e[0], "dec_deg": star_e[1], "epoch_jyear": 2099.0})
    pf = process_frame(fb, meta)
    x, y = _brightest(fb, meta)
    assert x == pytest.approx(N / 2 - 60.0 / SCALE, abs=PEAK_TOL)  # left of centre = east
    assert y == pytest.approx(N / 2, abs=PEAK_TOL)
    # The catalog marker agrees with where the pixels put the star.
    assert pf.record["marker"]["kind"] == "catalog_prediction"
    assert pf.record["marker"]["x"] == pytest.approx(N / 2 - 60.0 / SCALE, abs=0.05)

    star_n = _offset(0.0, 60.0)
    fb = synth.make_cutout(rotation_deg=rotation, flip_parity=flip, stars=[(*star_n, 100.0)])
    pf = process_frame(fb, _meta())
    x, y = _brightest(fb, _meta())
    assert x == pytest.approx(N / 2, abs=PEAK_TOL)
    assert y == pytest.approx(N / 2 - 60.0 / SCALE, abs=PEAK_TOL)  # above centre = north
    assert pf.record["registration"]["orientation"] == "north_up_east_left"


def test_display_wcs_axes_signs():
    w = display_wcs(RA0, DEC0, 6.0, N)
    (ra_r, dec_r), (ra_l, _), (_, dec_up) = w.all_pix2world([[200, 128.5 - 1], [50, 128.5 - 1], [127.5, 200]], 0)
    assert ra_l > ra_r  # east (larger RA) is on the left
    assert dec_up > DEC0  # larger FITS row (top of PNG after flip) is north


def test_grid_is_identical_across_frames():
    a = process_frame(synth.make_cutout(rotation_deg=10), _meta()).record["registration"]
    b = process_frame(synth.make_cutout(rotation_deg=-40, crpix_offset=(3.3, -2.1)), _meta()).record["registration"]
    for k in ("center_ra_deg", "center_dec_deg", "fov_arcmin", "width", "height", "scale_arcsec_per_pixel", "display_wcs"):
        assert a[k] == b[k]


# --------------------------------------------------------------------------- coverage / wavelength


def test_off_image_is_not_covered_with_null_wavelength():
    far = _offset(0.0, 20 * 60.0)  # 20 arcmin north: off a 6-arcmin cutout
    pf = process_frame(synth.make_cutout(), _meta(target={"ra_deg": far[0], "dec_deg": far[1], "epoch_jyear": 2099.0}))
    r = pf.record
    assert r["quality"]["status"] == "not_covered"
    assert r["quality"]["covered"] is False
    assert r["wavelength_um"] is None and r["bandwidth_um"] is None
    for k in ("valid_aperture_pixels", "adverse_aperture_pixels", "nonfinite_aperture_pixels"):
        assert r["quality"][k] is None  # unknown, never 0


def test_truncated_cutout_centre_position_not_covered():
    """Edge cutout (25 rows) whose WCS still places the target at y~29: geometric test says off-image."""
    fb = synth.make_cutout(shape=(25, 60), crpix_offset=(0.0, 17.5))
    pf = process_frame(fb, _meta())
    src_y = pf.record["registration"]["checked_position_source_pixel"]["y"]
    assert src_y > 24.5
    assert pf.record["quality"]["status"] == "not_covered"
    assert pf.record["wavelength_um"] is None


def test_wavelength_matches_analytic_table_and_astropy_without_sip():
    fb = synth.make_cutout(rotation_deg=17.0)
    pf = process_frame(fb, _meta())
    p = pf.record["registration"]["checked_position_source_pixel"]
    assert pf.record["wavelength_um"] == pytest.approx(synth.expected_wavelength(p["x"], p["y"]), abs=2e-6)
    # Independent check with astropy's -TAB implementation.
    hdul = fits.open(io.BytesIO(fb))
    ww = WCS(hdul["IMAGE"].header, fobj=hdul, key="W")
    wl, bw = ww.pixel_to_world_values(p["x"], p["y"])
    assert pf.record["wavelength_um"] == pytest.approx(float(wl), abs=2e-6)
    assert pf.record["bandwidth_um"] == pytest.approx(float(bw), abs=2e-6)


def test_spectral_lookup_never_extrapolates():
    src = read_source(synth.make_cutout())
    assert sample_spectral_wcs(src.image_header, src.wave_table, -5000.0, 10.0) == (None, None)


# --------------------------------------------------------------------------- quality


def test_nonfinite_at_covered_position_is_flagged_not_uncovered():
    fb0 = synth.make_cutout()
    p = process_frame(fb0, _meta()).record["registration"]["checked_position_source_pixel"]
    yx = (int(round(p["y"])), int(round(p["x"])))
    pf = process_frame(synth.make_cutout(nan_at=[yx]), _meta())
    q = pf.record["quality"]
    assert q["covered"] is True
    assert q["status"] == "flagged"
    assert q["nonfinite_aperture_pixels"] == 1
    assert q["adverse_aperture_pixels"] >= 1
    assert pf.record["wavelength_um"] is not None
    # The display marks it as non-finite (transparent intensity, red overlay), not as off-image.
    a = np.array(Image.open(io.BytesIO(pf.png_bytes)))
    f = np.array(Image.open(io.BytesIO(pf.flag_png_bytes)))
    assert (a[..., 1] == 0).any()
    assert (f[..., 0] == 235).any()


def test_informational_flags_do_not_flag():
    fl = np.full((60, 60), (1 << 21) | (1 << 12), dtype=np.int32)  # SOURCE | FULLSAMPLE everywhere
    q = process_frame(synth.make_cutout(flags=fl), _meta()).record["quality"]
    assert q["status"] == "clear"
    assert q["adverse_aperture_pixels"] == 0
    assert set(q["informational_flag_names"]) == {"SOURCE", "FULLSAMPLE"}


def test_adverse_flag_in_aperture_flags_frame():
    fl = np.zeros((60, 60), dtype=np.int32)
    fl[29:31, 29:31] = 1 << 1  # OVERFLOW
    q = process_frame(synth.make_cutout(flags=fl), _meta()).record["quality"]
    assert q["status"] == "flagged"
    assert q["flag_names"] == ["OVERFLOW"]


# --------------------------------------------------------------------------- categorical resampling


def _bits_subset(out: np.ndarray, allowed_union: int) -> bool:
    return bool(np.all((out & ~allowed_union) == 0))


@pytest.mark.parametrize("fov", [6.0, 2.0, 40.0])  # upsample, strong upsample, downsample (OR path)
def test_bitmask_resampling_never_invents_bits(fov):
    rng = np.random.default_rng(1)
    palette = np.array([0, 1 << 0, 1 << 1, 1 << 21, (1 << 21) | (1 << 26), 1 << 19], dtype=np.int64)
    fl = palette[rng.integers(0, palette.size, size=(60, 60))]
    src = read_source(synth.make_cutout(flags=fl.astype(np.int32), rotation_deg=31.0))
    rf = resample(src, _meta(fov_arcmin=fov))
    union = int(np.bitwise_or.reduce(fl.ravel()))
    assert _bits_subset(rf.flags, union)
    assert np.all(rf.flags[~rf.covered] == 0)
    if fov <= 6.0:
        # Nearest neighbour: every output value is a value present in the source.
        assert set(np.unique(rf.flags[rf.covered])).issubset(set(np.unique(fl)))
        # A bit pattern absent from the source (e.g. TRANSIENT|OVERFLOW) never appears.
        assert not np.any(rf.flags == (1 | 2))


def test_nearest_flag_lookup_is_exact_at_pixel_centres():
    fl = np.arange(12, dtype=np.int64).reshape(3, 4) * 7
    x = np.array([0.0, 3.0, 1.49, 1.51])
    y = np.array([0.0, 2.0, 1.0, 1.0])
    out = resample_flags_nearest(fl, x, y, np.ones(4, dtype=bool))
    assert list(out) == [fl[0, 0], fl[2, 3], fl[1, 1], fl[1, 2]]


# --------------------------------------------------------------------------- identity / errors


def test_identity_time_and_marker_kind():
    r = process_frame(synth.make_cutout(), _meta(observation_id="2099W01_1A_0001_1")).record
    assert r["frame_key"] == "2099W01_1A_0001_1_D3"
    assert r["observed_at_utc"] == "2099-01-01T00:00:00.000"
    assert r["mjd"] == 87158.0
    assert r["marker"] is None  # no target supplied -> no marker
    assert r["wavelength_location"].startswith("Query centre")


def test_observation_mismatch_and_garbage_are_unsupported():
    with pytest.raises(ProcessingError) as e:
        process_frame(synth.make_cutout(), _meta(observation_id="OTHER"))
    assert e.value.code == "UNSUPPORTED_DATA"
    with pytest.raises(ProcessingError) as e:
        process_frame(b"not a fits file at all" * 200, _meta())
    assert e.value.code == "UNSUPPORTED_DATA"
