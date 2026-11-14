"""Checks ported from candidate processor B (worker 06), adapted to processor A.

All fixtures here are SYNTHETIC (backend/tests/data/synthetic.py), not NASA
observations, except the final block, which reads the retained original
cutouts and is skipped unless PERIGEE_DATA_ROOT is set.

Covered: east-left / north-up orientation over rotations and both parities;
off-image and truncated cutouts -> not_covered with null wavelength; non-finite
pixels -> flagged; nearest-neighbour bitmask resampling never adds bits; the
spectral -TAB lookup (key W) agrees with astropy only after SIP is stripped;
and the SIP-aware native pixel scale (metadata only).
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import synthetic as syn  # noqa: E402
import backend.data.process as proc  # noqa: E402
from backend.data.process import (  # noqa: E402
    FrameInput,
    TargetInput,
    _sample_nearest,
    grid_wcs,
    native_scale_arcsec_at,
    process_frame,
)

RA0, DEC0 = syn.CENTER
N = 256
FOV = 6.0
DISP = FOV * 60.0 / N  # arcsec per display pixel
NATIVE = syn.SCALE_DEG * 3600.0  # arcsec per native pixel
# A display peak sits on the nearest native pixel centre (resampling adds no
# resolution), so allow 0.75 native pixel. An orientation error would be ~85 px.
PEAK_TOL = 0.75 * NATIVE / DISP


def meta(**kw) -> FrameInput:
    base = dict(query_ra_deg=RA0, query_dec_deg=DEC0, fov_arcmin=FOV, grid_size=N)
    base.update(kw)
    return FrameInput(**base)


def offset(east_arcsec: float, north_arcsec: float):
    return RA0 + east_arcsec / 3600.0 / math.cos(math.radians(DEC0)), DEC0 + north_arcsec / 3600.0


def native_xy(ra, dec, **hdr):
    w = WCS(syn.celestial_header(**hdr))
    x, y = w.all_world2pix([[ra, dec]], 0)[0]
    return float(x), float(y)


def rgba(b: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(b)).convert("RGBA"))


def peak_xy(png: bytes):
    """Centre of the brightest block of the PNG (top-left pixel-centre convention)."""
    a = rgba(png)
    g = np.where(a[..., 3] > 0, a[..., 0].astype(int), -1)
    ys, xs = np.nonzero(g == g.max())
    return float(xs.mean()) + 0.5, float(ys.mean()) + 0.5


def grid_to_native(cel: WCS, fov: float):
    """Native pixel coords of every display pixel, as processor A maps them."""
    gw = grid_wcs(RA0, DEC0, fov, N)
    gy, gx = np.mgrid[0:N, 0:N]
    ra, dec = gw.wcs_pix2world(gx.ravel().astype(float), gy.ravel().astype(float), 0)
    x, y = cel.all_world2pix(ra, dec, 0, quiet=True)
    return x.reshape(N, N), y.reshape(N, N)


# --------------------------------------------------------------------------- orientation


@pytest.mark.parametrize("rotation", [0.0, 23.0, -67.0, 180.0])
@pytest.mark.parametrize("flip", [False, True])
def test_known_offset_star_lands_east_left_north_up(rotation, flip):
    """60" east lands left of centre and 60" north lands above, whatever the native WCS."""
    hdr = dict(rot_deg=rotation, flip_parity=flip)
    # Wide fixed limits so the star peak is not clipped into a plateau.
    m = dict(display_limits=(0.0, 200.0))

    star_e = offset(60.0, 0.0)
    fb = syn.make_fits(rot_deg=rotation, flip_parity=flip, sources=((*native_xy(*star_e, **hdr), 100.0),))
    pf = process_frame(fb, meta(target=TargetInput(*star_e, name="east star"), **m))
    x, y = peak_xy(pf.png_bytes)
    assert x == pytest.approx(N / 2 - 60.0 / DISP, abs=PEAK_TOL)  # left of centre = east
    assert y == pytest.approx(N / 2, abs=PEAK_TOL)
    mk = pf.record["marker"]
    assert mk["kind"] == "catalog_prediction"
    assert mk["x"] == pytest.approx(N / 2 - 60.0 / DISP, abs=0.05)
    assert mk["y"] == pytest.approx(N / 2, abs=0.05)

    star_n = offset(0.0, 60.0)
    fb = syn.make_fits(rot_deg=rotation, flip_parity=flip, sources=((*native_xy(*star_n, **hdr), 100.0),))
    pf = process_frame(fb, meta(**m))
    x, y = peak_xy(pf.png_bytes)
    assert x == pytest.approx(N / 2, abs=PEAK_TOL)
    assert y == pytest.approx(N / 2 - 60.0 / DISP, abs=PEAK_TOL)  # above centre = north
    assert pf.record["registration"]["orientation"] == "north_up_east_left"


def test_grid_identical_across_rotation_parity_and_cutout_offset():
    a = process_frame(syn.make_fits(rot_deg=10.0), meta()).record["registration"]
    b = process_frame(syn.make_fits(rot_deg=-40.0, flip_parity=True, crpix_offset=(3.3, -2.1)), meta()).record["registration"]
    for k in ("center_ra_deg", "center_dec_deg", "fov_arcmin", "width", "height", "scale_arcsec_per_px",
              "projection", "orientation", "grid_id"):
        assert a[k] == b[k]


# --------------------------------------------------------------------------- coverage / wavelength


def test_far_off_image_is_not_covered_with_null_wavelength_and_null_counts():
    far = offset(0.0, 20 * 60.0)  # 20 arcmin north of a ~6 arcmin cutout
    r = process_frame(syn.make_fits(), meta(target=TargetInput(*far))).record
    q = r["quality"]
    assert q["status"] == "not_covered" and q["covered"] is False
    assert r["wavelength_um"] is None and r["bandwidth_um"] is None
    for k in ("screened_pixels", "valid_aperture_pixels", "adverse_aperture_pixels", "nonfinite_aperture_pixels"):
        assert q[k] is None  # unknown, never 0


def test_truncated_cutout_is_not_covered_even_though_wcs_extrapolates():
    """Edge cutout with only 25 rows whose WCS still places the centre at y~29."""
    fb = syn.make_fits(shape=(25, syn.NX), crpix_offset=(0.0, -0.5))
    r = process_frame(fb, meta(target=TargetInput(RA0, DEC0))).record
    assert r["sampled_position"]["native_y"] > 24.5
    assert r["quality"]["status"] == "not_covered"
    assert r["wavelength_um"] is None and r["bandwidth_um"] is None
    assert r["quality"]["screened_pixels"] is None


def _strip_sip_independently(h: fits.Header) -> fits.Header:
    """SIP-stripping written separately from the processor's helper."""
    out = h.copy()
    for k in list(out.keys()):
        if re.match(r"^(A|B|AP|BP)_", k):
            del out[k]
    return out


# A quadratic SIP that astropy would (wrongly) also apply to the key-W lookup,
# whose CRPIXnW sits ~800 px away in raw detector coordinates.
SIP = {"A_2_0": 2e-5, "A_0_2": -1e-5, "A_1_1": 1e-5, "B_2_0": 1e-5, "B_0_2": 2e-5, "B_1_1": -1e-5}


@pytest.mark.parametrize("east,north", [(0.0, 0.0), (-80.0, 40.0), (100.0, -120.0)])
def test_spectral_lookup_matches_astropy_with_sip_stripped(east, north):
    fb = syn.make_fits(sip=SIP)
    ra, dec = offset(east, north)
    r = process_frame(fb, meta(target=TargetInput(ra, dec))).record
    x, y = r["sampled_position"]["native_x"], r["sampled_position"]["native_y"]
    assert r["quality"]["covered"] is True
    with fits.open(io.BytesIO(fb)) as hdul, warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ih = hdul["IMAGE"].header
        stripped = WCS(_strip_sip_independently(ih), fobj=hdul, key="W").pixel_to_world_values(x, y)
        with_sip = WCS(ih, fobj=hdul, key="W").pixel_to_world_values(x, y)
    # Matches astropy -TAB with SIP removed, and the analytic table model.
    assert r["wavelength_um"] == pytest.approx(float(stripped[0]), abs=1e-9)
    assert r["bandwidth_um"] == pytest.approx(float(stripped[1]), abs=1e-9)
    assert r["wavelength_um"] == pytest.approx(syn.wavelength_at_native(x), abs=1e-6)
    # Negative control: leaving SIP in would distort the raw-pixel lookup.
    assert abs(float(with_sip[0]) - r["wavelength_um"]) > 1e-3


# --------------------------------------------------------------------------- quality


def _centre_pixel(fb: bytes):
    r = process_frame(fb, meta(target=TargetInput(RA0, DEC0))).record
    return int(round(r["sampled_position"]["native_y"])), int(round(r["sampled_position"]["native_x"]))


def test_nonfinite_image_pixel_is_flagged_not_uncovered_and_drawn_as_nonfinite():
    iy, ix = _centre_pixel(syn.make_fits())
    img = (0.5 * np.ones((syn.NY, syn.NX))).astype(np.float32)
    img[iy, ix] = np.nan
    pf = process_frame(syn.make_fits(image=img), meta(target=TargetInput(RA0, DEC0)))
    r = pf.record
    q = r["quality"]
    assert q["covered"] is True and q["status"] == "flagged"
    assert q["nonfinite_aperture_pixels"] == 1 and q["adverse_aperture_pixels"] >= 1
    assert r["wavelength_um"] is not None
    assert (rgba(pf.png_bytes)[..., 3] == 0).any()  # transparent in the intensity image
    legend = tuple(r["flag_image"]["legend"]["non_finite"])
    assert (rgba(pf.flag_png_bytes).reshape(-1, 4) == legend).all(axis=1).any()  # marked in the overlay


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0.0, -1.0])
def test_bad_variance_at_covered_position_is_flagged(bad):
    iy, ix = _centre_pixel(syn.make_fits())
    var = np.full((syn.NY, syn.NX), 1e-4, dtype=np.float32)
    var[iy, ix] = bad
    q = process_frame(syn.make_fits(variance=var), meta(target=TargetInput(RA0, DEC0))).record["quality"]
    assert q["covered"] is True and q["status"] == "flagged"
    assert q["nonfinite_aperture_pixels"] == 1


# --------------------------------------------------------------------------- bitmask resampling


def test_nearest_lookup_is_exact_at_pixel_centres_and_keeps_integer_bits():
    fl = (np.arange(12, dtype=np.int64).reshape(3, 4) * 7) | (1 << 40)
    x = np.array([0.0, 3.0, 1.49, 1.51, -0.6, 3.6])
    y = np.array([0.0, 2.0, 1.0, 1.0, 0.0, 0.0])
    out, ok = _sample_nearest(fl, x, y, 0)
    assert out.dtype == np.int64
    assert list(out[:4]) == [fl[0, 0], fl[2, 3], fl[1, 1], fl[1, 2]]
    assert list(ok) == [True, True, True, True, False, False] and list(out[4:]) == [0, 0]


@pytest.mark.parametrize("fov", [6.0, 2.0, 30.0])  # nominal, strong upsampling, downsampling
@pytest.mark.parametrize("rotation,flip", [(31.0, False), (-112.0, True)])
def test_bitmask_resampling_never_invents_bits(fov, rotation, flip):
    rng = np.random.default_rng(1)
    palette = np.array([0, 1 << 0, 1 << 1, 1 << 21, (1 << 21) | (1 << 26), 1 << 19], dtype=np.int64)
    fl = palette[rng.integers(0, palette.size, size=(syn.NY, syn.NX))]
    cel = WCS(syn.celestial_header(rotation, flip_parity=flip))
    x, y = grid_to_native(cel, fov)
    out, ok = _sample_nearest(fl, x, y, 0)
    union = int(np.bitwise_or.reduce(fl.ravel()))
    assert np.all((out & ~union) == 0)  # no bit absent from the source
    assert np.all(out[~ok] == 0)  # off-image carries no flags
    # Nearest neighbour copies source values: no new combination (e.g. TRANSIENT|OVERFLOW).
    assert set(np.unique(out[ok])).issubset(set(np.unique(fl)))
    assert not np.any(out == (1 | 2))


def test_flag_overlay_marks_exactly_the_display_pixels_of_an_adverse_native_pixel():
    cel = WCS(syn.celestial_header(23.0))
    iy, ix = 31, 27
    fl = np.full((syn.NY, syn.NX), (1 << 21) | (1 << 12), dtype=np.int32)  # informational only
    fl[iy, ix] |= 1 << 1  # OVERFLOW (adverse) on one native pixel
    pf = process_frame(syn.make_fits(rot_deg=23.0, flags=fl), meta())
    a = np.flipud(rgba(pf.flag_png_bytes))  # back to FITS grid rows (row 0 = south)
    adverse = (a == np.array(pf.record["flag_image"]["legend"]["adverse_flag"])).all(axis=-1)
    x, y = grid_to_native(cel, FOV)
    expect = (np.floor(x + 0.5) == ix) & (np.floor(y + 0.5) == iy)
    assert adverse.sum() > 0
    assert np.array_equal(adverse, expect)

    only_info = np.full((syn.NY, syn.NX), (1 << 21) | (1 << 12), dtype=np.int32)
    pf2 = process_frame(syn.make_fits(rot_deg=23.0, flags=only_info), meta())
    a2 = rgba(pf2.flag_png_bytes)
    assert not (a2 == np.array(pf2.record["flag_image"]["legend"]["adverse_flag"])).all(axis=-1).any()


# --------------------------------------------------------------------------- native scale (SIP-aware)


def test_native_scale_without_sip_equals_linear_scale():
    r = process_frame(syn.make_fits(rot_deg=17.0), meta()).record
    assert r["registration"]["native_scale_arcsec_per_px"] == pytest.approx(NATIVE, abs=1e-4)


@pytest.mark.parametrize("flip", [False, True])
def test_native_scale_includes_sip_at_cutout_centre(flip):
    """x' = u + a u^2, y' = v + b v^2: local scale = s * sqrt((1 + 2aU)(1 + 2bV)) at (U, V)."""
    a, b, off = 5e-5, 4e-5, (-40.0, -35.0)  # CRPIX 40/35 px before the cutout centre, as in real cutouts
    fb = syn.make_fits(sip={"A_2_0": a, "B_0_2": b}, crpix_offset=off, flip_parity=flip)
    r = process_frame(fb, meta()).record
    U, V = -off[0], -off[1]  # pixel offset of the cutout centre from CRPIX
    expect = NATIVE * math.sqrt((1 + 2 * a * U) * (1 + 2 * b * V))
    got = r["registration"]["native_scale_arcsec_per_px"]
    assert got == pytest.approx(expect, abs=2e-4)
    assert abs(got - NATIVE) > 0.02  # the linear-only value would be wrong by ~0.4%


def test_native_scale_is_metadata_only(monkeypatch):
    """Changing the reported scale changes no pixel, marker, mask, wavelength or quality."""
    fb = syn.make_fits(rot_deg=11.0, sip={"A_2_0": 3e-5, "B_0_2": 3e-5}, crpix_offset=(-20.0, 10.0),
                       sources=((25.0, 33.0, 50.0),))
    m = meta(target=TargetInput(*offset(20.0, -15.0), name="t"))
    base = process_frame(fb, m)
    monkeypatch.setattr(proc, "native_scale_arcsec_at", lambda *a, **k: 99.0)
    alt = process_frame(fb, m)
    assert alt.record["registration"]["native_scale_arcsec_per_px"] == 99.0
    assert alt.png_bytes == base.png_bytes
    assert alt.flag_png_bytes == base.flag_png_bytes
    ra, rb = json.loads(json.dumps(base.record)), json.loads(json.dumps(alt.record))
    ra["registration"].pop("native_scale_arcsec_per_px")
    rb["registration"].pop("native_scale_arcsec_per_px")
    assert ra == rb


def test_native_scale_is_pole_safe():
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [12.0, 89.9999]
    w.wcs.crpix = [30.5, 30.5]
    w.wcs.cd = [[-syn.SCALE_DEG, 0.0], [0.0, syn.SCALE_DEG]]
    assert native_scale_arcsec_at(w, 29.5, 29.5) == pytest.approx(NATIVE, abs=1e-4)
    assert native_scale_arcsec_at(w, 29.5, 59.0) == pytest.approx(NATIVE, abs=1e-4)


# --------------------------------------------------------------------------- real cutouts (optional)

ROOT = os.environ.get("PERIGEE_DATA_ROOT")
needs_data = pytest.mark.skipif(not ROOT or not Path(ROOT, "manifest.json").exists(),
                                reason="PERIGEE_DATA_ROOT with retained FITS not available")
CASE_KEYS = ["2026W18_1A_0516_1_D3", "2026W39_2A_0597_4_D3", "2026W18_1A_0516_1_D6",
             "2025W35_1A_0008_1_D3", "2026W12_1A_0610_2_D3", "2026W34_1A_0431_1_D3"]


def _real(key):
    m = json.loads(Path(ROOT, "manifest.json").read_text())
    rec = next(r for r in m["files"] if r.get("status") == "downloaded" and f"{r['obs_id']}_D{r['detector']}" == key)
    return Path(ROOT, rec["file"]).read_bytes()


def _cos_dec_scale(cel, x, y):
    """Candidate B's formula (cos(dec) finite differences), as an independent check."""
    px, py = np.array([x - 0.5, x + 0.5, x, x]), np.array([y, y, y - 0.5, y + 0.5])
    ra, dec = cel.all_pix2world(px, py, 0)
    c = math.cos(math.radians(float(np.mean(dec))))
    dra = (ra + 180.0 - ra[0]) % 360.0 - 180.0
    j = np.array([[(dra[1] - dra[0]) * c, (dra[3] - dra[2]) * c], [dec[1] - dec[0], dec[3] - dec[2]]])
    return math.sqrt(abs(float(np.linalg.det(j)))) * 3600.0


@needs_data
def test_real_native_scale_is_sip_aware():
    fb = _real("2026W18_1A_0516_1_D3")
    r = process_frame(fb, meta(query_ra_deg=331.0966687831005, query_dec_deg=-56.80064917516836)).record
    assert r["registration"]["native_scale_arcsec_per_px"] == pytest.approx(6.1318, abs=1e-4)
    with fits.open(io.BytesIO(fb)) as hdul, warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cel = WCS(hdul["IMAGE"].header, fobj=hdul).celestial
        lin = float(np.mean(proj_plane_pixel_scales(cel)) * 3600.0)
    assert lin == pytest.approx(6.1596, abs=1e-4)  # previous, linear-only value


@needs_data
@pytest.mark.parametrize("key", CASE_KEYS)
def test_real_native_scale_and_spectral_lookup_cross_checks(key):
    fb = _real(key)
    with fits.open(io.BytesIO(fb)) as hdul, warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ih = hdul["IMAGE"].header
        cel = WCS(ih, fobj=hdul).celestial
        ny, nx = hdul["IMAGE"].data.shape
        got = native_scale_arcsec_at(cel, (nx - 1) / 2.0, (ny - 1) / 2.0)
        assert got == pytest.approx(_cos_dec_scale(cel, (nx - 1) / 2.0, (ny - 1) / 2.0), abs=1e-6)
        assert abs(got / float(np.mean(proj_plane_pixel_scales(cel)) * 3600.0) - 1.0) < 0.01
        # Spectral lookup: processor output equals astropy key W with SIP stripped (and not with SIP kept).
        ra, dec = cel.all_pix2world([[(nx - 1) / 2.0 + 3.3, (ny - 1) / 2.0 - 4.1]], 0)[0]
        r = process_frame(fb, meta(query_ra_deg=float(ra), query_dec_deg=float(dec))).record
        x, y = r["sampled_position"]["native_x"], r["sampled_position"]["native_y"]
        assert x == pytest.approx((nx - 1) / 2.0 + 3.3, abs=1e-3)
        stripped = WCS(_strip_sip_independently(ih), fobj=hdul, key="W").pixel_to_world_values(x, y)
        with_sip = WCS(ih, fobj=hdul, key="W").pixel_to_world_values(x, y)
    assert r["registration"]["native_scale_arcsec_per_px"] == pytest.approx(got, abs=1e-4)
    assert r["wavelength_um"] == pytest.approx(float(stripped[0]), abs=1e-9)
    assert r["bandwidth_um"] == pytest.approx(float(stripped[1]), abs=1e-9)
    assert abs(float(with_sip[0]) - r["wavelength_um"]) > 1e-4
