"""Perigee frame processor (candidate B).

Turns one SPHEREx Level-2 spectral-image cutout (multi-extension FITS bytes)
into a FrameRecord-shaped dict plus a compact intensity PNG and a categorical
flag-overlay PNG on a fixed north-up / east-left display grid.

Design rules (docs/INTEGRATION_CONTRACT.md and science/INTEGRATION_BOARD.md):

* Pure functions. No web framework, no network, no filesystem, no global state.
  The caller passes bytes and plain metadata (``FrameInput``).
* ``frame_key = <OBSID>_D<DETECTOR>``; time is ``DATE-AVG`` / ``MJD-AVG``.
* The display grid is a gnomonic (TAN) projection tangent at the caller's
  query centre with CDELT1 < 0 (east left) and CDELT2 > 0 (north up). It never
  depends on the frame or the target, so it is identical across frames.
* Every display pixel is inverse-mapped display -> sky -> source pixel through
  the frame's own TAN-SIP celestial WCS.
* Coverage is geometric only. Non-finite pixels inside the image are a quality
  problem, never "not covered".
* Flags are categorical: they are resampled by nearest neighbour (bitwise OR
  over sub-samples when the display pixel is larger than a native pixel). Bit
  values are never interpolated, so no output pixel can carry a bit that is
  absent from the source pixels it was taken from.
* Wavelength comes from the WCS-WAVE lookup table (FITS Paper III -TAB) at the
  checked position. SIP is not applied to the spectral WCS. It is ``None``
  whenever the position is off the image; the table is never extrapolated.
"""

from __future__ import annotations

import base64
import hashlib
import io
import math
import re
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from PIL import Image

PROCESSING_VERSION = "perigee-processor-b/0.1.0"

# SOURCE and FULLSAMPLE are informational (integration board decision 3).
INFORMATIONAL_FLAG_NAMES = frozenset({"SOURCE", "FULLSAMPLE"})

DEFAULT_GRID_SIZE = 256
DEFAULT_FOV_ARCMIN = 6.0
DEFAULT_APERTURE_RADIUS_PX = 2.5
DEFAULT_PERCENTILES = (0.5, 99.5)
# Display stretch: t = clip((v - lo) / (hi - lo), 0, 1); grey = 255 * asinh(t / b) / asinh(1 / b).
ASINH_SOFTENING = 0.1

ACKNOWLEDGMENTS = [
    "This product uses data from SPHEREx, a NASA mission managed by JPL/Caltech, "
    "obtained from the NASA/IPAC Infrared Science Archive (IRSA).",
]

# Overlay colours (RGBA). Categorical: one colour per category, no blending of
# bit values.
_RGBA_NONFINITE = (235, 50, 50, 210)
_RGBA_ADVERSE = (255, 170, 0, 120)


class ProcessingError(Exception):
    """A processing failure with a public error code.

    ``code`` is ``UNSUPPORTED_DATA`` (input is not a usable SPHEREx L2 cutout)
    or ``PROCESSING_FAILED`` (input looked valid but processing broke).
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Inputs and outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TargetAstrometry:
    """Catalog astrometry used only for a ``catalog_prediction`` marker."""

    ra_deg: float
    dec_deg: float
    epoch_jyear: float = 2000.0
    pm_ra_cosdec_masyr: float = 0.0
    pm_dec_masyr: float = 0.0
    parallax_mas: Optional[float] = None
    radial_velocity_kms: Optional[float] = None
    label: Optional[str] = None
    source: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TargetAstrometry":
        return cls(
            ra_deg=float(d["ra_deg"]),
            dec_deg=float(d["dec_deg"]),
            epoch_jyear=float(d.get("epoch_jyear", 2000.0)),
            pm_ra_cosdec_masyr=float(d.get("pm_ra_cosdec_masyr") or 0.0),
            pm_dec_masyr=float(d.get("pm_dec_masyr") or 0.0),
            parallax_mas=_opt_float(d.get("parallax_mas")),
            radial_velocity_kms=_opt_float(d.get("radial_velocity_kms")),
            label=d.get("label"),
            source=d.get("source"),
        )


@dataclass(frozen=True)
class FrameInput:
    """Plain metadata the caller supplies with the FITS bytes."""

    center_ra_deg: float
    center_dec_deg: float
    fov_arcmin: float = DEFAULT_FOV_ARCMIN
    grid_size: int = DEFAULT_GRID_SIZE
    observation_id: Optional[str] = None  # verified against header OBSID
    collection_id: Optional[str] = None
    source_url: Optional[str] = None  # archive file URL
    cutout_url: Optional[str] = None  # URL actually fetched (with cutout params)
    retrieved_at_utc: Optional[str] = None
    target: Optional[TargetAstrometry] = None
    # Shared stretch limits in background-subtracted MJy/sr. None -> per frame.
    display_limits: Optional[Tuple[float, float]] = None
    display_limits_basis: Optional[str] = None
    aperture_radius_px: float = DEFAULT_APERTURE_RADIUS_PX
    preset_id: Optional[str] = None
    embed_data_urls: bool = True

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FrameInput":
        tgt = d.get("target")
        lim = d.get("display_limits")
        return cls(
            center_ra_deg=float(d["center_ra_deg"]),
            center_dec_deg=float(d["center_dec_deg"]),
            fov_arcmin=float(d.get("fov_arcmin", DEFAULT_FOV_ARCMIN)),
            grid_size=int(d.get("grid_size", DEFAULT_GRID_SIZE)),
            observation_id=d.get("observation_id"),
            collection_id=d.get("collection_id"),
            source_url=d.get("source_url"),
            cutout_url=d.get("cutout_url"),
            retrieved_at_utc=d.get("retrieved_at_utc"),
            target=None if tgt is None else (tgt if isinstance(tgt, TargetAstrometry) else TargetAstrometry.from_dict(tgt)),
            display_limits=None if lim is None else (float(lim[0]), float(lim[1])),
            display_limits_basis=d.get("display_limits_basis"),
            aperture_radius_px=float(d.get("aperture_radius_px", DEFAULT_APERTURE_RADIUS_PX)),
            preset_id=d.get("preset_id"),
            embed_data_urls=bool(d.get("embed_data_urls", True)),
        )


@dataclass
class ProcessedFrame:
    record: Dict[str, Any]
    png_bytes: bytes
    flag_png_bytes: Optional[bytes] = None


@dataclass
class ResampledFrame:
    """Intermediate result: display-grid arrays before rendering."""

    values: np.ndarray  # float64 (n, n), background-subtracted, NaN where not displayable
    covered: np.ndarray  # bool (n, n): display pixel centre lies on the source image
    nonfinite: np.ndarray  # bool (n, n): covered but nearest source pixel non-finite
    flags: np.ndarray  # int64 (n, n): resampled bitmask (0 where not covered)
    background_offset: Optional[float]
    # Background-subtracted finite *native* pixels whose centres fall inside the
    # display grid. Stretch percentiles use these, not the upsampled display
    # pixels, so bilinear spreading of bright stars does not inflate "hi".
    native_in_grid: np.ndarray = field(default_factory=lambda: np.zeros(0))


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _opt_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def _round(v: Optional[float], nd: int) -> Optional[float]:
    if v is None:
        return None
    return float(round(float(v), nd))


def _quiet_wcs(header: fits.Header, **kw: Any) -> WCS:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        return WCS(header, **kw)


def data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def frame_key_for(observation_id: str, detector: int) -> str:
    return f"{observation_id}_D{int(detector)}"


def infer_collection_id(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.search(r"/spherex/([a-z]+\d+)/", url)
    return f"spherex_{m.group(1)}" if m else None


# ---------------------------------------------------------------------------
# FITS reading
# ---------------------------------------------------------------------------


@dataclass
class SourceFrame:
    image: np.ndarray  # float64 (ny, nx)
    variance: Optional[np.ndarray]
    flags: Optional[np.ndarray]  # int64 (ny, nx)
    image_header: fits.Header
    flag_names: Dict[int, str]  # bit -> name, from FLAGS header MSKNnnnn
    wave_table: Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]  # X, Y, VALUES(ny_t, nx_t, k)
    celestial: WCS
    sha256: str
    nbytes: int
    primary_version: Optional[str]

    @property
    def shape(self) -> Tuple[int, int]:
        return self.image.shape  # (ny, nx)


def read_source(fits_bytes: bytes) -> SourceFrame:
    if not fits_bytes:
        raise ProcessingError("UNSUPPORTED_DATA", "empty input")
    sha = hashlib.sha256(fits_bytes).hexdigest()
    try:
        hdul = fits.open(io.BytesIO(fits_bytes), memmap=False, lazy_load_hdus=False)
    except Exception as exc:  # astropy raises several types for corrupt input
        raise ProcessingError("UNSUPPORTED_DATA", f"not a readable FITS file: {type(exc).__name__}") from exc
    with hdul:
        names = [h.name for h in hdul]
        if "IMAGE" not in names:
            raise ProcessingError("UNSUPPORTED_DATA", "FITS has no IMAGE extension")
        ih = hdul["IMAGE"].header.copy()
        img = hdul["IMAGE"].data
        if img is None or img.ndim != 2:
            raise ProcessingError("UNSUPPORTED_DATA", "IMAGE extension is not a 2-D array")
        image = np.asarray(img, dtype=np.float64)
        variance = None
        if "VARIANCE" in names and hdul["VARIANCE"].data is not None:
            variance = np.asarray(hdul["VARIANCE"].data, dtype=np.float64)
            if variance.shape != image.shape:
                variance = None
        flags = None
        flag_names: Dict[int, str] = {}
        if "FLAGS" in names and hdul["FLAGS"].data is not None:
            fd = hdul["FLAGS"].data
            if fd.shape == image.shape and np.issubdtype(fd.dtype, np.integer):
                flags = np.asarray(fd, dtype=np.int64)
                fh = hdul["FLAGS"].header
                for key in fh:
                    m = re.fullmatch(r"MSKN(\d{4})", key)
                    if m:
                        flag_names[int(m.group(1))] = str(fh[key]).strip()
        wave_table = None
        if "WCS-WAVE" in names:
            try:
                row = hdul["WCS-WAVE"].data[0]
                xs = np.asarray(row["X"], dtype=np.float64).ravel()
                ys = np.asarray(row["Y"], dtype=np.float64).ravel()
                vals = np.asarray(row["VALUES"], dtype=np.float64)
                if vals.shape[:2] == (ys.size, xs.size) and np.all(np.diff(xs) > 0) and np.all(np.diff(ys) > 0):
                    wave_table = (xs, ys, vals)
            except Exception:
                wave_table = None
        primary_version = hdul[0].header.get("VERSION")
    try:
        cel = _quiet_wcs(ih, naxis=2)
        if not cel.has_celestial:
            raise ValueError("no celestial axes")
        cel = cel.celestial
    except Exception as exc:
        raise ProcessingError("UNSUPPORTED_DATA", f"IMAGE header has no usable celestial WCS: {exc}") from exc
    return SourceFrame(
        image=image,
        variance=variance,
        flags=flags,
        image_header=ih,
        flag_names=flag_names,
        wave_table=wave_table,
        celestial=cel,
        sha256=sha,
        nbytes=len(fits_bytes),
        primary_version=None if primary_version is None else str(primary_version).strip(),
    )


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def display_wcs(center_ra_deg: float, center_dec_deg: float, fov_arcmin: float, n: int) -> WCS:
    """Fixed display grid: TAN at the query centre, north up, east left.

    FITS convention (1-based CRPIX, +y = north). The PNG stores rows top-down,
    so PNG row r corresponds to FITS 0-based row ``n - 1 - r``.
    """
    scale = fov_arcmin / 60.0 / n
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [float(center_ra_deg), float(center_dec_deg)]
    w.wcs.crpix = [(n + 1) / 2.0, (n + 1) / 2.0]
    w.wcs.cdelt = [-scale, scale]  # east left (RA decreases with +x), north up
    w.wcs.cunit = ["deg", "deg"]
    w.wcs.radesys = "ICRS"
    w.pixel_shape = (n, n)
    return w


def native_geometry(cel: WCS, x: float, y: float) -> Dict[str, float]:
    """Local native pixel scale (arcsec), rotation and parity at source pixel (x, y).

    Uses the Jacobian of the full TAN-SIP mapping (finite differences of
    all_pix2world), so SIP's local scale change is included. SPHEREx SIP terms
    change the scale by ~0.5% across a detector; the linear CD-only value
    (scale at CRPIX, near the detector centre) is reported separately.
    """
    h = 0.5
    px = np.array([x - h, x + h, x, x])
    py = np.array([y, y, y - h, y + h])
    ra, dec = cel.all_pix2world(px, py, 0)
    c = math.cos(math.radians(float(np.mean(dec))))
    dra = (ra + 180.0 - ra[0]) % 360.0 - 180.0  # unwrap RA
    # Rows: (east, north) in deg; columns: (d/dx, d/dy).
    j = np.array([[(dra[1] - dra[0]) * c, (dra[3] - dra[2]) * c], [dec[1] - dec[0], dec[3] - dec[2]]])
    det = float(np.linalg.det(j))
    lin = cel.pixel_scale_matrix
    # PA (east of north) of the source +y pixel axis = atan2(east, north).
    pa_y = math.degrees(math.atan2(j[0, 1], j[1, 1])) % 360.0
    return {
        "native_scale_arcsec": math.sqrt(abs(det)) * 3600.0,
        "native_scale_linear_arcsec": math.sqrt(abs(float(np.linalg.det(lin)))) * 3600.0,
        "native_y_axis_pa_deg": pa_y,
        # det<0 is the usual sky parity (east left when north up).
        "native_parity": "sky (east-left when north-up)" if det < 0 else "flipped (east-right when north-up)",
    }


def _world_to_source(cel: WCS, ra: np.ndarray, dec: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x, y = cel.all_world2pix(ra, dec, 0, tolerance=1e-8, maxiter=50, quiet=True)
    return np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)


def _on_image(x: np.ndarray, y: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
    ny, nx = shape
    return np.isfinite(x) & np.isfinite(y) & (x >= -0.5) & (x < nx - 0.5) & (y >= -0.5) & (y < ny - 0.5)


def predict_position(target: TargetAstrometry, mjd: float) -> Tuple[float, float]:
    """Propagate catalog astrometry to ``mjd`` (UTC) with astropy space motion."""
    import astropy.units as u
    from astropy.coordinates import Distance, SkyCoord
    from astropy.time import Time

    if target.parallax_mas and target.parallax_mas > 0:
        dist = Distance(parallax=target.parallax_mas * u.mas)
    else:
        dist = 1e6 * u.pc  # effectively no perspective acceleration
    c = SkyCoord(
        ra=target.ra_deg * u.deg,
        dec=target.dec_deg * u.deg,
        distance=dist,
        pm_ra_cosdec=target.pm_ra_cosdec_masyr * u.mas / u.yr,
        pm_dec=target.pm_dec_masyr * u.mas / u.yr,
        radial_velocity=(target.radial_velocity_kms or 0.0) * u.km / u.s,
        obstime=Time(target.epoch_jyear, format="jyear", scale="tt"),
        frame="icrs",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p = c.apply_space_motion(new_obstime=Time(mjd, format="mjd", scale="utc"))
    return float(p.ra.deg), float(p.dec.deg)


# ---------------------------------------------------------------------------
# Spectral WCS (FITS Paper III -TAB), no SIP, no extrapolation
# ---------------------------------------------------------------------------


def sample_spectral_wcs(header: fits.Header, wave_table, x0: float, y0: float) -> Tuple[Optional[float], Optional[float]]:
    """Wavelength and bandwidth (um) at 0-based source pixel (x0, y0).

    psi_i = CDELTiW * (p_i - CRPIXiW) + CRVALiW with p 1-based (PC is identity
    for key W in these files). psi is located in the index vectors X/Y, and the
    VALUES table is interpolated bilinearly. Returns (None, None) if the table
    is missing or psi falls outside the index vectors (never extrapolate).
    """
    if wave_table is None or not all(k in header for k in ("CRPIX1W", "CRPIX2W")):
        return None, None
    if str(header.get("CTYPE1W", "")).strip() != "WAVE-TAB":
        return None, None
    xs, ys, vals = wave_table
    psi = []
    for i, p in ((1, x0 + 1.0), (2, y0 + 1.0)):
        crpix = float(header[f"CRPIX{i}W"])
        cdelt = float(header.get(f"CDELT{i}W", 1.0))
        crval = float(header.get(f"CRVAL{i}W", 0.0))
        psi.append(cdelt * (p - crpix) + crval)
    px, py = psi
    if not (xs[0] <= px <= xs[-1] and ys[0] <= py <= ys[-1]):
        return None, None
    fx = float(np.interp(px, xs, np.arange(xs.size)))
    fy = float(np.interp(py, ys, np.arange(ys.size)))
    ix = min(int(math.floor(fx)), xs.size - 2)
    iy = min(int(math.floor(fy)), ys.size - 2)
    tx, ty = fx - ix, fy - iy
    v = (
        vals[iy, ix] * (1 - tx) * (1 - ty)
        + vals[iy, ix + 1] * tx * (1 - ty)
        + vals[iy + 1, ix] * (1 - tx) * ty
        + vals[iy + 1, ix + 1] * tx * ty
    )
    k_w = int(header.get("PV1_3W", 1)) - 1
    k_b = int(header.get("PV2_3W", 2)) - 1
    w, b = float(v[k_w]), float(v[k_b])
    return (w if math.isfinite(w) else None), (b if math.isfinite(b) else None)


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------


def resample_flags_nearest(flags: np.ndarray, x: np.ndarray, y: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Nearest-neighbour categorical lookup. Returns 0 where ``valid`` is False."""
    ny, nx = flags.shape
    xi = np.clip(np.floor(x + 0.5).astype(np.int64), 0, nx - 1)
    yi = np.clip(np.floor(y + 0.5).astype(np.int64), 0, ny - 1)
    out = np.where(valid, flags[yi, xi], 0)
    return out.astype(np.int64)


def _bilinear_finite(image: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Bilinear interpolation using only finite neighbours (weights renormalised)."""
    ny, nx = image.shape
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    tx = x - x0
    ty = y - y0
    acc = np.zeros(x.shape, dtype=np.float64)
    wsum = np.zeros(x.shape, dtype=np.float64)
    for dx, dy, w in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)), (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        xi = x0 + dx
        yi = y0 + dy
        inb = (xi >= 0) & (xi < nx) & (yi >= 0) & (yi < ny)
        v = image[np.clip(yi, 0, ny - 1), np.clip(xi, 0, nx - 1)]
        ok = inb & np.isfinite(v)
        acc += np.where(ok, v, 0.0) * np.where(ok, w, 0.0)
        wsum += np.where(ok, w, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(wsum > 0, acc / wsum, np.nan)


def resample(src: SourceFrame, meta: FrameInput) -> ResampledFrame:
    n = int(meta.grid_size)
    dw = display_wcs(meta.center_ra_deg, meta.center_dec_deg, meta.fov_arcmin, n)
    geo = native_geometry(src.celestial, (src.shape[1] - 1) / 2.0, (src.shape[0] - 1) / 2.0)
    disp_scale = meta.fov_arcmin * 60.0 / n
    # Sub-samples per display pixel so that flags are OR-ed over the footprint
    # when display pixels are larger than native pixels. 1 when upsampling.
    k = max(1, int(math.ceil(disp_scale / geo["native_scale_arcsec"])))
    offs = (np.arange(k) + 0.5) / k - 0.5

    jj, ii = np.mgrid[0:n, 0:n].astype(np.float64)  # FITS 0-based, j = row from south
    ra, dec = dw.all_pix2world(ii, jj, 0)
    sx, sy = _world_to_source(src.celestial, ra, dec)
    covered = _on_image(sx, sy, src.shape)

    ny, nx = src.shape
    xi = np.clip(np.floor(sx + 0.5).astype(np.int64), 0, nx - 1)
    yi = np.clip(np.floor(sy + 0.5).astype(np.int64), 0, ny - 1)
    nearest_finite = np.isfinite(src.image[yi, xi])
    nonfinite = covered & ~nearest_finite

    finite_src = src.image[np.isfinite(src.image)]
    bg = float(np.median(finite_src)) if finite_src.size else None
    vals = _bilinear_finite(src.image, sx, sy)
    if bg is not None:
        vals = vals - bg
    vals = np.where(covered & nearest_finite, vals, np.nan)

    # Native pixels whose centres land inside the display grid (for stretch statistics).
    py, px = np.mgrid[0:ny, 0:nx].astype(np.float64)
    nra, ndec = src.celestial.all_pix2world(px, py, 0)
    gi, gj = dw.all_world2pix(nra, ndec, 0)
    in_grid = (gi >= -0.5) & (gi < n - 0.5) & (gj >= -0.5) & (gj < n - 0.5) & np.isfinite(src.image)
    native_in_grid = src.image[in_grid] - (bg if bg is not None else 0.0)

    if src.flags is not None:
        if k == 1:
            fl = resample_flags_nearest(src.flags, sx, sy, covered)
        else:
            fl = np.zeros((n, n), dtype=np.int64)
            for oy in offs:
                for ox in offs:
                    r2, d2 = dw.all_pix2world(ii + ox, jj + oy, 0)
                    x2, y2 = _world_to_source(src.celestial, r2, d2)
                    fl |= resample_flags_nearest(src.flags, x2, y2, _on_image(x2, y2, src.shape))
            fl = np.where(covered, fl, 0)
    else:
        fl = np.zeros((n, n), dtype=np.int64)

    # Flip to top-down rows (PNG order): row 0 = north.
    return ResampledFrame(
        values=vals[::-1].copy(),
        covered=covered[::-1].copy(),
        nonfinite=nonfinite[::-1].copy(),
        flags=fl[::-1].copy(),
        background_offset=bg,
        native_in_grid=native_in_grid,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def per_frame_limits(values: np.ndarray, percentiles: Sequence[float] = DEFAULT_PERCENTILES) -> Optional[Tuple[float, float]]:
    v = values[np.isfinite(values)]
    if v.size == 0:
        return None
    lo, hi = np.percentile(v, percentiles)
    if not hi > lo:
        hi = lo + 1e-6
    return float(lo), float(hi)


def shared_limits(frames: Sequence[ResampledFrame], percentiles: Sequence[float] = DEFAULT_PERCENTILES) -> Optional[Tuple[float, float]]:
    if not frames:
        return None
    v = np.concatenate([f.native_in_grid for f in frames])
    return per_frame_limits(v, percentiles)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_intensity_png(values: np.ndarray, limits: Optional[Tuple[float, float]]) -> bytes:
    """8-bit grey + alpha. Alpha 0 = no displayable value (off-image or non-finite)."""
    n0, n1 = values.shape
    ok = np.isfinite(values)
    grey = np.zeros(values.shape, dtype=np.uint8)
    if limits is not None and ok.any():
        lo, hi = limits
        t = np.clip((values - lo) / (hi - lo), 0.0, 1.0)
        t = np.arcsinh(t / ASINH_SOFTENING) / np.arcsinh(1.0 / ASINH_SOFTENING)
        grey = np.where(ok, np.round(t * 255.0), 0).astype(np.uint8)
    alpha = np.where(ok, 255, 0).astype(np.uint8)
    la = np.dstack([grey, alpha])
    return _png(Image.fromarray(la, mode="LA"))


def render_flag_png(rf: ResampledFrame, adverse_mask: int) -> bytes:
    """Categorical RGBA overlay: non-finite (red), adverse flag (amber), else clear."""
    n0, n1 = rf.flags.shape
    rgba = np.zeros((n0, n1, 4), dtype=np.uint8)
    adverse = rf.covered & ((rf.flags & adverse_mask) != 0)
    rgba[adverse] = _RGBA_ADVERSE
    rgba[rf.nonfinite] = _RGBA_NONFINITE
    return _png(Image.fromarray(rgba, mode="RGBA"))


# ---------------------------------------------------------------------------
# Quality screen
# ---------------------------------------------------------------------------


def _bit_names(bits: int, names: Dict[int, str]) -> List[str]:
    out = []
    b = 0
    while bits >> b:
        if (bits >> b) & 1:
            out.append(names.get(b, f"BIT{b}"))
        b += 1
    return out


def informational_mask(names: Dict[int, str]) -> int:
    m = 0
    for bit, name in names.items():
        if name in INFORMATIONAL_FLAG_NAMES:
            m |= 1 << bit
    return m


def quality_screen(src: SourceFrame, x0: Optional[float], y0: Optional[float], radius: float) -> Dict[str, Any]:
    """Flag screen in a circle of ``radius`` native pixels around (x0, y0)."""
    base = {
        "status": "unknown",
        "covered": None,
        "valid_aperture_pixels": None,
        "adverse_aperture_pixels": None,
        "nonfinite_aperture_pixels": None,
        "aperture_pixels": None,
        "aperture_radius_native_px": radius,
        "flag_names": [],
        "informational_flag_names": [],
        "flag_pixel_counts": {},
        "notes": [],
    }
    if x0 is None or y0 is None or not (math.isfinite(x0) and math.isfinite(y0)):
        base["notes"].append("Position could not be mapped onto this frame.")
        return base
    covered = bool(_on_image(np.array([x0]), np.array([y0]), src.shape)[0])
    base["covered"] = covered
    if not covered:
        base["status"] = "not_covered"
        base["notes"].append("The checked position lies outside this image (geometric coverage test).")
        return base
    ny, nx = src.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    ap = (xx - x0) ** 2 + (yy - y0) ** 2 <= radius ** 2
    n_ap = int(ap.sum())
    nonfin = ~np.isfinite(src.image)
    if src.variance is not None:
        nonfin |= ~np.isfinite(src.variance)
    n_nonfin = int((ap & nonfin).sum())
    base["aperture_pixels"] = n_ap
    base["nonfinite_aperture_pixels"] = n_nonfin
    if n_ap < math.floor(math.pi * radius ** 2):
        base["notes"].append(f"Only {n_ap} native pixels of the screening circle fall on the image (position near an edge).")
    if src.flags is None:
        base["notes"].append("FLAGS extension missing; flag screen not possible.")
        if n_nonfin:
            base["status"] = "flagged"
            base["adverse_aperture_pixels"] = n_nonfin
            base["valid_aperture_pixels"] = None
        return base
    info = informational_mask(src.flag_names)
    fl = src.flags[ap]
    adverse_bits = fl & ~info
    adverse_px = (adverse_bits != 0) | nonfin[ap]
    n_adv = int(adverse_px.sum())
    union_adv = int(np.bitwise_or.reduce(adverse_bits)) if adverse_bits.size else 0
    union_info = int(np.bitwise_or.reduce(fl & info)) if fl.size else 0
    counts: Dict[str, int] = {}
    for b in range(64):
        c = int(((fl >> b) & 1).sum())
        if c:
            counts[src.flag_names.get(b, f"BIT{b}")] = c
    base.update(
        {
            "status": "flagged" if n_adv else "clear",
            "valid_aperture_pixels": n_ap - n_adv,
            "adverse_aperture_pixels": n_adv,
            "flag_names": _bit_names(union_adv, src.flag_names),
            "informational_flag_names": _bit_names(union_info, src.flag_names),
            "flag_pixel_counts": counts,
        }
    )
    if n_nonfin:
        base["notes"].append(f"{n_nonfin} non-finite IMAGE/VARIANCE pixel(s) in the screening circle (e.g. saturation); covered, but flagged.")
    if n_adv == 0:
        base["notes"].append("No adverse flags or non-finite pixels in the screening circle. This is not a detection or a brightness measurement.")
    return base


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def sample_display(fits_bytes: bytes, meta: FrameInput) -> ResampledFrame:
    """First pass for shared stretches: resample without rendering."""
    return resample(read_source(fits_bytes), meta)


def process_frame(fits_bytes: bytes, meta: FrameInput) -> ProcessedFrame:
    if isinstance(meta, dict):
        meta = FrameInput.from_dict(meta)
    src = read_source(fits_bytes)
    h = src.image_header
    obsid = h.get("OBSID")
    det = h.get("DETECTOR")
    if obsid is None or det is None:
        raise ProcessingError("UNSUPPORTED_DATA", "IMAGE header lacks OBSID or DETECTOR")
    obsid = str(obsid).strip()
    det = int(det)
    if meta.observation_id and meta.observation_id != obsid:
        raise ProcessingError(
            "UNSUPPORTED_DATA", f"header OBSID {obsid!r} does not match requested observation {meta.observation_id!r}"
        )
    fkey = frame_key_for(obsid, det)
    date_avg = h.get("DATE-AVG")
    mjd_avg = _opt_float(h.get("MJD-AVG"))
    notes_time = "DATE-AVG / MJD-AVG (mid-exposure) from the IMAGE header"
    if date_avg is None or mjd_avg is None:
        notes_time = "DATE-AVG/MJD-AVG missing from IMAGE header; time left null"
        date_avg, mjd_avg = None, None

    collection_id = meta.collection_id
    limitations: List[str] = []
    if not collection_id:
        collection_id = infer_collection_id(meta.source_url or meta.cutout_url)
        if collection_id:
            limitations.append("collection_id was inferred from the source URL path, not supplied by the archive descriptor.")

    rf = resample(src, meta)
    n = int(meta.grid_size)
    dw = display_wcs(meta.center_ra_deg, meta.center_dec_deg, meta.fov_arcmin, n)
    geo = native_geometry(src.celestial, (src.shape[1] - 1) / 2.0, (src.shape[0] - 1) / 2.0)
    disp_scale = meta.fov_arcmin * 60.0 / n

    # Position used for wavelength + quality: predicted target, else query centre.
    marker = None
    if meta.target is not None and mjd_avg is not None:
        pra, pdec = predict_position(meta.target, mjd_avg)
        label = meta.target.label or "target"
        location_text = f"Catalog-predicted position of {label} at this observation time"
    else:
        pra, pdec = meta.center_ra_deg, meta.center_dec_deg
        location_text = "Query centre of the fixed display grid"
    tx, ty = _world_to_source(src.celestial, np.array([pra]), np.array([pdec]))
    tx0, ty0 = float(tx[0]), float(ty[0])
    q = quality_screen(src, tx0, ty0, meta.aperture_radius_px)
    if q["covered"]:
        wl, bw = sample_spectral_wcs(h, src.wave_table, tx0, ty0)
    else:
        wl, bw = None, None
    if q["covered"] and wl is None:
        limitations.append("Wavelength could not be read from the WCS-WAVE lookup table for this frame.")

    if meta.target is not None and mjd_avg is not None:
        di, dj = dw.all_world2pix([pra], [pdec], 0)
        mx = float(di[0]) + 0.5
        my = n - 0.5 - float(dj[0])
        marker = {
            "kind": "catalog_prediction",
            "x": _round(mx, 3),
            "y": _round(my, 3),
            "inside_grid": bool(0 <= mx <= n and 0 <= my <= n),
            "ra_deg": _round(pra, 8),
            "dec_deg": _round(pdec, 8),
            "epoch_mjd": mjd_avg,
            "epoch_utc": date_avg,
            "label": meta.target.label,
            "source": meta.target.source,
            "explanation": (
                "Catalog position propagated with proper motion"
                + (", parallax distance" if meta.target.parallax_mas else "")
                + (" and radial velocity" if meta.target.radial_velocity_kms else "")
                + " to this frame's mid-exposure time. A finder aid, not a detection. Annual parallax is not modelled."
            ),
        }

    # Display stretch.
    if meta.display_limits is not None:
        limits = (float(meta.display_limits[0]), float(meta.display_limits[1]))
        scale_mode = "shared"
        basis = meta.display_limits_basis or "limits supplied by the caller and shared across a frame set"
    else:
        limits = per_frame_limits(rf.native_in_grid)
        scale_mode = "per_frame"
        basis = f"percentiles {DEFAULT_PERCENTILES[0]}-{DEFAULT_PERCENTILES[1]} of this frame's finite native pixels inside the display grid"
    png = render_intensity_png(rf.values, limits)
    adverse_mask = ~informational_mask(src.flag_names) & ((1 << 63) - 1)
    flag_png = render_flag_png(rf, adverse_mask) if src.flags is not None else None

    image_obj = {
        "src": data_url(png) if meta.embed_data_urls else None,
        "width": n,
        "height": n,
        "media_type": "image/png",
        "encoding": "8-bit grey + alpha; alpha 0 where off-image or non-finite",
    }
    flag_obj = None
    if flag_png is not None:
        flag_obj = {
            "src": data_url(flag_png) if meta.embed_data_urls else None,
            "width": n,
            "height": n,
            "media_type": "image/png",
            "encoding": "RGBA categorical overlay",
            "legend": [
                {"rgba": list(_RGBA_NONFINITE), "meaning": "non-finite source pixel (e.g. saturated), covered"},
                {"rgba": list(_RGBA_ADVERSE), "meaning": "any flag other than SOURCE/FULLSAMPLE"},
                {"rgba": [0, 0, 0, 0], "meaning": "no adverse flag, or off-image"},
            ],
            "adverse_pixel_fraction": _round(float(((rf.flags & adverse_mask) != 0)[rf.covered].mean()) if rf.covered.any() else 0.0, 4),
        }

    cx, cy = _world_to_source(src.celestial, np.array([meta.center_ra_deg]), np.array([meta.center_dec_deg]))
    registration = {
        "center_ra_deg": meta.center_ra_deg,
        "center_dec_deg": meta.center_dec_deg,
        "fov_arcmin": meta.fov_arcmin,
        "width": n,
        "height": n,
        "scale_arcsec_per_pixel": _round(disp_scale, 6),
        "projection": "TAN (gnomonic) tangent at the grid centre, ICRS",
        "orientation": "north_up_east_left",
        "pixel_convention": "x right, y down from the top-left image corner; pixel (i, j) spans [i, i+1) x [j, j+1); the grid centre is (width/2, height/2)",
        "display_wcs": {
            "ctype": ["RA---TAN", "DEC--TAN"],
            "crval": [meta.center_ra_deg, meta.center_dec_deg],
            "crpix_fits_1based": [(n + 1) / 2.0, (n + 1) / 2.0],
            "cdelt_deg": [-disp_scale / 3600.0, disp_scale / 3600.0],
            "note": "FITS convention (+y north). PNG row r is FITS row n-1-r.",
        },
        "method": (
            "Inverse mapping: each display pixel centre -> sky (display TAN) -> source pixel through the frame's "
            "TAN-SIP celestial WCS (astropy all_world2pix). Intensity: bilinear over finite neighbours. "
            "Flags and non-finite mask: nearest neighbour (bitwise OR over sub-samples if downsampling). "
            "Coverage: geometric (source pixel footprint)."
        ),
        "native_scale_arcsec": _round(geo["native_scale_arcsec"], 4),
        "native_scale_basis": "sqrt|det J| of the TAN-SIP mapping at the cutout centre (includes SIP)",
        "native_scale_linear_arcsec": _round(geo["native_scale_linear_arcsec"], 4),
        "native_y_axis_pa_deg": _round(geo["native_y_axis_pa_deg"], 3),
        "native_parity": geo["native_parity"],
        "source_shape": [int(src.shape[0]), int(src.shape[1])],
        "covered_fraction": _round(float(rf.covered.mean()), 4),
        "grid_center_source_pixel": {"x": _round(float(cx[0]), 4), "y": _round(float(cy[0]), 4), "convention": "0-based FITS"},
        "checked_position_source_pixel": {"x": _round(tx0, 4), "y": _round(ty0, 4), "convention": "0-based FITS"},
        "upsampling_factor": _round(geo["native_scale_arcsec"] / disp_scale, 3),
    }

    display_scale = {
        "mode": scale_mode,
        "method": (
            f"asinh: t = clip((v - lo) / (hi - lo), 0, 1); grey = 255 * asinh(t / {ASINH_SOFTENING}) / asinh(1 / {ASINH_SOFTENING})"
            if limits
            else "no finite pixels"
        ),
        "asinh_softening": ASINH_SOFTENING,
        "lo": _round(limits[0], 6) if limits else None,
        "hi": _round(limits[1], 6) if limits else None,
        "units": "MJy/sr after subtracting background_offset",
        "basis": basis,
        "background_offset": _round(rf.background_offset, 6),
        "background_method": "median of this frame's finite IMAGE pixels (single number; no spatial background model)",
        "interpolation": "bilinear (display only)",
    }
    if scale_mode == "per_frame":
        limitations.append("Per-frame contrast: brightness is not directly comparable with other frames.")

    limitations += [
        f"Display pixels ({disp_scale:.2f} arcsec) are resampled from ~{geo['native_scale_arcsec']:.2f} arcsec native pixels; resampling adds no resolution.",
        "Wavelength is the WCS-WAVE lookup-table value at the checked position only; it varies across the image, and the supplement describes this table as an approximation for visualisation.",
        f"Quality screen = flags and non-finite pixels within {meta.aperture_radius_px} native pixels of the checked position. Not a detection, photometry or astrometric validation.",
    ]
    if marker is not None:
        limitations.append("The marker is a catalog prediction, not a measured position.")

    record = {
        "schema_version": 1,
        "frame_id": fkey,
        "frame_key": fkey,
        "observation_id": obsid,
        "detector": det,
        "collection_id": collection_id,
        "preset_id": meta.preset_id,
        "observed_at_utc": date_avg,
        "mjd": mjd_avg,
        "time_basis": notes_time,
        "source_url": meta.source_url,
        "wavelength_um": _round(wl, 6),
        "bandwidth_um": _round(bw, 6),
        "wavelength_location": location_text if q["covered"] else f"{location_text}; the position is not on this image, so no wavelength is reported",
        "wavelength_method": "WCS-WAVE (-TAB) bilinear lookup at the checked source pixel; SIP not applied to the spectral WCS; no extrapolation",
        "image": image_obj,
        "flag_image": flag_obj,
        "registration": registration,
        "quality": q,
        "display_scale": display_scale,
        "marker": marker,
        "provenance": {
            "retrieved_at_utc": meta.retrieved_at_utc,
            "source_url": meta.source_url,
            "cutout_url": meta.cutout_url,
            "sha256": src.sha256,
            "bytes": src.nbytes,
            "processing_version": PROCESSING_VERSION,
            "pipeline_software_version": src.primary_version,
            "l2_dqa": (str(h.get("L2DQAFLG")).strip() if h.get("L2DQAFLG") is not None else None),
            "fine_astrometry_status": h.get("FINAST"),
            "acknowledgments": ACKNOWLEDGMENTS,
        },
        "limitations": limitations,
    }
    return ProcessedFrame(record=record, png_bytes=png, flag_png_bytes=flag_png)
