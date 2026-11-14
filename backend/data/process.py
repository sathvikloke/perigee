"""Pure SPHEREx Level-2 cutout processor: one original FITS -> one browser frame.

Owner: data/processor workstream (``backend/data/**``).

``process_frame(fits_bytes, meta)`` takes the original FITS bytes plus plain
metadata and returns a :class:`ProcessedFrame` holding a JSON-serializable
FrameRecord dict and PNG bytes. It performs no network access, imports no web
framework and keeps no global request state, so the API layer can wrap it and
unit tests can run it on small local fixtures.

Binding science decisions implemented here (science/INTEGRATION_BOARD.md):

1. ``frame_key = <observation_id>_D<detector>``; ``frame_id`` carries the same value.
2. ``observed_at_utc`` = IMAGE ``DATE-AVG``; ``mjd`` = IMAGE ``MJD-AVG`` (mid-exposure).
3. Quality: ``not_covered`` is geometric only (screen position off the cutout);
   non-finite pixels at a covered position mean ``flagged``; pixel counts are
   ``None`` when unknown, never 0; ``SOURCE`` and ``FULLSAMPLE`` are informational.
4. Wavelength is ``None`` when the position is off the cutout; the spectral WCS
   is never extrapolated.
5. Fixed display grid: TAN projection, north up, east left, centered on the
   caller's query center, identical for every frame processed with the same
   (center, fov, size). The grid never recenters on the target.

A ``clear`` quality status means the stated flag checks passed near the
screened position. It is not a detection, calibrated photometry or an
astrometric validation. The marker is always ``kind: catalog_prediction``.
"""

from __future__ import annotations

import hashlib
import io
import logging
import math
import re
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS, FITSFixedWarning
from astropy.wcs.utils import proj_plane_pixel_scales
from PIL import Image

PROCESSING_VERSION = "perigee-processor-a/0.1.2"

#: Radius of the quality-screen circle in native SPHEREx pixels (~15 arcsec).
#: Matches the science screen used to verify the authored cases.
APERTURE_RADIUS_PX = 2.5
# Perigee screening heuristic (not a NASA/SPHEREx standard): a screen with no
# problems found is only "clear" if at least this many usable pixels back it.
MIN_CLEAR_PIXELS = 10

#: Flag bits that describe the scene rather than a data problem.
INFORMATIONAL_FLAGS = frozenset({"SOURCE", "FULLSAMPLE"})

DEFAULT_GRID_SIZE = 256
DEFAULT_FOV_ARCMIN = 6.0
MIN_FOV_ARCMIN = 0.5
MAX_FOV_ARCMIN = 30.0
MIN_GRID_SIZE = 16
MAX_GRID_SIZE = 1024

#: Default display stretch: asinh between these percentiles of finite grid pixels.
DEFAULT_PERCENTILES = (1.0, 99.5)
ASINH_SOFTENING = 10.0

ACKNOWLEDGMENTS = [
    "This product uses data from SPHEREx, a NASA mission managed by the Jet Propulsion "
    "Laboratory, California Institute of Technology, obtained from the NASA/IPAC Infrared "
    "Science Archive (IRSA), operated by the California Institute of Technology under "
    "contract with NASA.",
]

_log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- errors


class ProcessorError(Exception):
    """Base class. ``code`` maps onto the public error envelope."""

    code = "PROCESSING_FAILED"


class UnsupportedDataError(ProcessorError):
    """The bytes are not a SPHEREx L2 image this processor understands (UNSUPPORTED_DATA)."""

    code = "UNSUPPORTED_DATA"


class IntegrityError(UnsupportedDataError):
    """The bytes or header do not match the descriptor the caller supplied."""


class InvalidInputError(ProcessorError, ValueError):
    """The metadata passed to the processor is out of range."""

    code = "PROCESSING_FAILED"


# --------------------------------------------------------------------------- inputs


@dataclass(frozen=True)
class TargetInput:
    """Catalog position of the object to screen and mark.

    ``epoch_jyear`` and the astrometry are optional. With proper motion and an
    epoch, the position is propagated to each frame's mid-exposure time
    (no annual parallax). The result is a catalog prediction, never a detection.
    """

    ra_deg: float
    dec_deg: float
    epoch_jyear: Optional[float] = None
    pm_ra_cosdec_masyr: Optional[float] = None
    pm_dec_masyr: Optional[float] = None
    parallax_mas: Optional[float] = None
    radial_velocity_kms: Optional[float] = None
    name: Optional[str] = None
    source: Optional[str] = None  # e.g. "SIMBAD via CDS Sesame; Gaia EDR3 astrometry"


@dataclass(frozen=True)
class FrameInput:
    """Plain metadata accompanying one FITS file.

    ``source_url`` is the archive URL of the original image; ``cutout_url`` the
    exact service request (if a cutout). ``display_limits`` switches the stretch
    to ``shared`` mode with the given (low, high) values in the image unit.
    """

    query_ra_deg: float
    query_dec_deg: float
    fov_arcmin: float = DEFAULT_FOV_ARCMIN
    grid_size: int = DEFAULT_GRID_SIZE
    target: Optional[TargetInput] = None
    source_url: Optional[str] = None
    observation_id: Optional[str] = None
    collection_id: Optional[str] = None
    detector: Optional[int] = None
    cutout_url: Optional[str] = None
    retrieved_at_utc: Optional[str] = None
    retrieved_at_basis: Optional[str] = None
    expected_sha256: Optional[str] = None
    display_limits: Optional[Tuple[float, float]] = None
    display_limits_basis: Optional[str] = None
    include_flag_image: bool = True


@dataclass
class ProcessedFrame:
    """Processor output. ``record`` is JSON-serializable; image sources are left
    for the caller to fill (data URL for live frames, asset URL for curated)."""

    record: Dict[str, Any]
    png_bytes: bytes
    flag_png_bytes: Optional[bytes] = None
    #: Finite resampled grid values (image unit); used to derive shared stretches.
    grid_values: Optional[np.ndarray] = field(default=None, repr=False)


# --------------------------------------------------------------------------- helpers


def _finite_float(name: str, value: Any) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(f"{name} must be a number") from exc
    if not math.isfinite(f):
        raise InvalidInputError(f"{name} must be finite")
    return f


def _validate(meta: FrameInput) -> None:
    ra = _finite_float("query_ra_deg", meta.query_ra_deg)
    dec = _finite_float("query_dec_deg", meta.query_dec_deg)
    fov = _finite_float("fov_arcmin", meta.fov_arcmin)
    if not 0.0 <= ra < 360.0:
        raise InvalidInputError("query_ra_deg must be in [0, 360)")
    if not -90.0 <= dec <= 90.0:
        raise InvalidInputError("query_dec_deg must be in [-90, 90]")
    if not MIN_FOV_ARCMIN <= fov <= MAX_FOV_ARCMIN:
        raise InvalidInputError(f"fov_arcmin must be in [{MIN_FOV_ARCMIN}, {MAX_FOV_ARCMIN}]")
    if not isinstance(meta.grid_size, int) or not MIN_GRID_SIZE <= meta.grid_size <= MAX_GRID_SIZE:
        raise InvalidInputError(f"grid_size must be an int in [{MIN_GRID_SIZE}, {MAX_GRID_SIZE}]")
    if meta.target is not None:
        _finite_float("target.ra_deg", meta.target.ra_deg)
        _finite_float("target.dec_deg", meta.target.dec_deg)
    if meta.display_limits is not None:
        lo = _finite_float("display_limits[0]", meta.display_limits[0])
        hi = _finite_float("display_limits[1]", meta.display_limits[1])
        if not hi > lo:
            raise InvalidInputError("display_limits must satisfy high > low")


def _iso_utc(date_str: Optional[str], timesys: Optional[str]) -> Optional[str]:
    """Return an explicit-UTC ISO string ('...Z'), keeping header precision."""
    if not date_str:
        return None
    s = str(date_str).strip()
    if (timesys or "UTC").strip().upper() == "UTC":
        return s if s.endswith("Z") else s + "Z"
    t = Time(s, format="isot", scale=(timesys or "utc").strip().lower())
    return t.utc.isot + "Z"


def frame_key(observation_id: str, detector: int) -> str:
    """Stable per-image identity (INTEGRATION_BOARD decision 1)."""
    return f"{observation_id}_D{int(detector)}"


def grid_wcs(center_ra_deg: float, center_dec_deg: float, fov_arcmin: float, size: int) -> WCS:
    """Fixed north-up / east-left TAN grid. FITS pixel (0,0) is the south-east
    corner; the PNG is written with row 0 = north."""
    w = WCS(naxis=2)
    scale_deg = fov_arcmin / 60.0 / size
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [center_ra_deg, center_dec_deg]
    w.wcs.crpix = [(size + 1) / 2.0, (size + 1) / 2.0]  # 1-based: center of the array
    w.wcs.cdelt = [-scale_deg, scale_deg]
    w.wcs.cunit = ["deg", "deg"]
    w.wcs.radesys = "ICRS"
    return w


def sky_to_display_px(gw: WCS, size: int, ra_deg: float, dec_deg: float) -> Tuple[float, float]:
    """Sky -> display pixel coordinates (origin top-left corner of the PNG,
    x right, y down; the top-left pixel spans [0,1) x [0,1))."""
    fx, fy = gw.world_to_pixel_values(ra_deg, dec_deg)  # 0-based, pixel centers at integers
    return float(fx) + 0.5, float(size) - (float(fy) + 0.5)


def predict_position(target: TargetInput, mjd: Optional[float]) -> Tuple[float, float, bool]:
    """Catalog position propagated to ``mjd``. Returns (ra, dec, propagated)."""
    has_pm = (
        target.epoch_jyear is not None
        and mjd is not None
        and (target.pm_ra_cosdec_masyr or target.pm_dec_masyr)
    )
    if not has_pm:
        return float(target.ra_deg), float(target.dec_deg), False
    dist = (1000.0 / target.parallax_mas) * u.pc if target.parallax_mas and target.parallax_mas > 0 else None
    kwargs = dict(
        ra=target.ra_deg * u.deg,
        dec=target.dec_deg * u.deg,
        pm_ra_cosdec=(target.pm_ra_cosdec_masyr or 0.0) * u.mas / u.yr,
        pm_dec=(target.pm_dec_masyr or 0.0) * u.mas / u.yr,
        obstime=Time(target.epoch_jyear, format="jyear"),
        frame="icrs",
    )
    if dist is not None:
        kwargs["distance"] = dist
        kwargs["radial_velocity"] = (target.radial_velocity_kms or 0.0) * u.km / u.s
    c = SkyCoord(**kwargs)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # ErfaWarning for "dubious year" / no-distance
        p = c.apply_space_motion(new_obstime=Time(mjd, format="mjd"))
    return float(p.ra.deg), float(p.dec.deg), True


def flag_bit_names(header: fits.Header) -> Dict[int, str]:
    """Bit index -> name from the FLAGS header ``MSKNnnnn`` keywords."""
    out: Dict[int, str] = {}
    for key in header.keys():
        m = re.fullmatch(r"MSKN(\d{4})", key)
        if m:
            out[int(m.group(1))] = str(header[key]).strip()
    return out


_SIP_KEY = re.compile(r"^(A|B|AP|BP)_(ORDER|\d+_\d+)$")


def _without_sip(header: fits.Header) -> fits.Header:
    """Copy of ``header`` without SIP keywords. SIP describes the celestial
    distortion only; the spectral lookup table (key W, WAVE-TAB) is indexed by
    raw detector pixel and must not be distorted (as in the IRSA tutorial)."""
    h = header.copy()
    for k in [k for k in h.keys() if _SIP_KEY.match(k)]:
        del h[k]
    return h


def native_scale_arcsec_at(cel: WCS, x: float, y: float, h: float = 0.5) -> float:
    """Local native pixel scale (arcsec per pixel) at 0-based native pixel (x, y).

    ``sqrt(|det J|)`` of the full celestial mapping (TAN plus SIP, via
    ``all_pix2world``), with ``J`` taken by central differences of +/-``h`` pixels
    and expressed in a gnomonic plane tangent at (x, y), so it is pole-safe.
    SPHEREx cutouts sit far from CRPIX, where SIP changes the scale by up to
    ~0.5% relative to the linear CD matrix. Metadata only: never used to
    resample, screen or mark.
    """
    px = np.array([x, x - h, x + h, x, x], dtype=float)
    py = np.array([y, y, y, y - h, y + h], dtype=float)
    ra, dec = cel.all_pix2world(px, py, 0)
    a, d = np.radians(ra), np.radians(dec)
    a0, d0 = a[0], d[0]
    cosc = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(a - a0)
    xi = np.cos(d) * np.sin(a - a0) / cosc
    eta = (np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(a - a0)) / cosc
    j = np.array([[xi[2] - xi[1], xi[4] - xi[3]], [eta[2] - eta[1], eta[4] - eta[3]]]) / (2.0 * h)
    return float(math.degrees(math.sqrt(abs(float(np.linalg.det(j))))) * 3600.0)


def _open(fits_bytes: bytes) -> fits.HDUList:
    if not isinstance(fits_bytes, (bytes, bytearray, memoryview)) or len(fits_bytes) < 2880:
        raise UnsupportedDataError("input is not a FITS file (too short)")
    if not bytes(fits_bytes[:9]) == b"SIMPLE  =":
        raise UnsupportedDataError("input is not a FITS file (missing SIMPLE card)")
    try:
        hdul = fits.open(io.BytesIO(bytes(fits_bytes)), memmap=False, lazy_load_hdus=False)
    except Exception as exc:  # astropy raises OSError/ValueError variants
        raise UnsupportedDataError(f"FITS parse failed: {type(exc).__name__}") from exc
    return hdul


def _ext(hdul: fits.HDUList, name: str):
    try:
        return hdul[name]
    except KeyError:
        return None


def _sample_nearest(arr: np.ndarray, x: np.ndarray, y: np.ndarray, fill):
    """Nearest-neighbour sample of ``arr`` at 0-based native pixel coords."""
    ny, nx = arr.shape
    ix = np.floor(x + 0.5).astype(np.int64)
    iy = np.floor(y + 0.5).astype(np.int64)
    ok = np.isfinite(x) & np.isfinite(y) & (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    out = np.full(x.shape, fill, dtype=arr.dtype if fill is not np.nan else np.float64)
    out[ok] = arr[iy[ok], ix[ok]]
    return out, ok


def _stretch(values: np.ndarray, lo: float, hi: float) -> np.ndarray:
    t = np.clip((values - lo) / (hi - lo), 0.0, 1.0)
    return np.arcsinh(t * ASINH_SOFTENING) / np.arcsinh(ASINH_SOFTENING)


def display_limits_from_values(
    values: Sequence[np.ndarray], percentiles: Tuple[float, float] = DEFAULT_PERCENTILES
) -> Optional[Tuple[float, float]]:
    """Shared (low, high) from the finite grid values of one or more frames."""
    arrs = [np.asarray(v, dtype=float).ravel() for v in values if v is not None]
    if not arrs:
        return None
    allv = np.concatenate(arrs)
    allv = allv[np.isfinite(allv)]
    if allv.size == 0:
        return None
    lo, hi = np.percentile(allv, percentiles)
    if not hi > lo:
        hi = lo + 1e-6
    return float(lo), float(hi)


def _png(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# Overlay colours (RGBA) for the optional flag image.
_ADVERSE_RGBA = (255, 64, 64, 150)
_NONFINITE_RGBA = (255, 200, 0, 200)


# --------------------------------------------------------------------------- main


def process_frame(fits_bytes: bytes, meta: FrameInput) -> ProcessedFrame:
    """Convert one original SPHEREx L2 FITS (full image or IRSA cutout) to a
    fixed-grid PNG plus a FrameRecord dict. Raises :class:`ProcessorError`
    subclasses for invalid input, unsupported data or integrity mismatches."""
    _validate(meta)
    sha256 = hashlib.sha256(bytes(fits_bytes)).hexdigest()
    if meta.expected_sha256 and meta.expected_sha256.lower() != sha256:
        raise IntegrityError("sha256 of FITS bytes does not match the expected value")

    notes: List[str] = []
    limitations: List[str] = []

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        warnings.simplefilter("ignore", AstropyWarning)
        hdul = _open(fits_bytes)
        try:
            return _process(hdul, meta, sha256, notes, limitations)
        finally:
            hdul.close()


def _process(hdul, meta: FrameInput, sha256: str, notes: List[str], limitations: List[str]) -> ProcessedFrame:
    image_hdu = _ext(hdul, "IMAGE")
    if image_hdu is None or image_hdu.data is None or image_hdu.data.ndim != 2:
        raise UnsupportedDataError("no 2-D IMAGE extension (expected a SPHEREx L2 spectral image)")
    ih = image_hdu.header
    img = np.asarray(image_hdu.data, dtype=np.float64)
    ny, nx = img.shape

    flags_hdu = _ext(hdul, "FLAGS")
    var_hdu = _ext(hdul, "VARIANCE")
    flg = None
    bit_names: Dict[int, str] = {}
    if flags_hdu is not None and flags_hdu.data is not None and flags_hdu.data.shape == img.shape:
        flg = np.asarray(flags_hdu.data).astype(np.int64)
        bit_names = flag_bit_names(flags_hdu.header)
        if not bit_names:
            notes.append("FLAGS extension has no MSKN bit names; flag screen unavailable.")
            flg = None
    else:
        notes.append("FLAGS extension missing or mismatched; flag screen unavailable.")
    var = None
    if var_hdu is not None and var_hdu.data is not None and var_hdu.data.shape == img.shape:
        var = np.asarray(var_hdu.data, dtype=np.float64)
    else:
        notes.append("VARIANCE extension missing or mismatched; validity uses IMAGE only.")

    # ---- identity and time (header is authoritative; descriptor must agree)
    obsid = str(ih.get("OBSID")).strip() if ih.get("OBSID") is not None else None
    detector = int(ih["DETECTOR"]) if ih.get("DETECTOR") is not None else None
    if obsid is None or detector is None:
        raise UnsupportedDataError("IMAGE header lacks OBSID or DETECTOR")
    if meta.observation_id and meta.observation_id != obsid:
        raise IntegrityError(f"header OBSID {obsid!r} != descriptor observation_id {meta.observation_id!r}")
    if meta.detector is not None and int(meta.detector) != detector:
        raise IntegrityError(f"header DETECTOR {detector} != descriptor detector {meta.detector}")
    key = frame_key(obsid, detector)
    timesys = ih.get("TIMESYS")
    observed_at = _iso_utc(ih.get("DATE-AVG"), timesys)
    mjd = float(ih["MJD-AVG"]) if ih.get("MJD-AVG") is not None else None
    if observed_at is None or mjd is None:
        notes.append("DATE-AVG/MJD-AVG missing; observation time left null (not substituted).")

    # ---- celestial WCS of the native image (TAN-SIP)
    try:
        cel = WCS(ih, fobj=hdul).celestial
        if not cel.has_celestial:
            raise ValueError("no celestial axes")
    except Exception as exc:
        raise UnsupportedDataError(f"IMAGE celestial WCS unusable: {type(exc).__name__}") from exc
    # Reported scale: local TAN-SIP scale at the native image centre (metadata only).
    native_scale_arcsec = round(native_scale_arcsec_at(cel, (nx - 1) / 2.0, (ny - 1) / 2.0), 4)
    # Nominal scale from the linear CD/PC matrix only, quoted (to 0.01") in the
    # human-readable limitation text. Kept on its previous basis so that adopting
    # the SIP-aware field above changes no other product text.
    nominal_scale_arcsec = float(np.mean(proj_plane_pixel_scales(cel)) * 3600.0)

    # ---- screened position: catalog prediction if a target is given, else query center
    t = meta.target
    if t is not None:
        pos_ra, pos_dec, propagated = predict_position(t, mjd)
        pos_kind = "catalog_prediction"
    else:
        pos_ra, pos_dec, propagated = meta.query_ra_deg, meta.query_dec_deg, False
        pos_kind = "query_center"
    px, py = cel.all_world2pix(np.array([[pos_ra, pos_dec]]), 0, quiet=True)[0]
    px, py = float(px), float(py)
    covered = bool(np.isfinite(px) and np.isfinite(py) and 0.0 <= px <= nx - 1 and 0.0 <= py <= ny - 1)

    # ---- wavelength at that position (never extrapolated)
    wl = bw = None
    target_label = (t.name if t is not None and t.name else "the target") if t is not None else None
    if covered:
        try:
            if _ext(hdul, "WCS-WAVE") is None:
                raise ValueError("no WCS-WAVE extension")
            sw = WCS(header=_without_sip(ih), fobj=hdul, key="W")
            vals = sw.pixel_to_world_values(px, py)
            wl_v, bw_v = float(vals[0]), float(vals[1])
            if math.isfinite(wl_v) and wl_v > 0:
                wl = wl_v
                bw = bw_v if math.isfinite(bw_v) and bw_v > 0 else None
            else:
                notes.append("Spectral WCS returned a non-finite wavelength; left null.")
        except Exception as exc:
            notes.append(f"Wavelength unavailable: spectral WCS (key W) could not be evaluated ({type(exc).__name__}).")
        if pos_kind == "catalog_prediction":
            wavelength_location = (
                f"Spectral WCS (key W) sampled at the catalog-predicted position of {target_label} "
                f"at this frame's mid-exposure time (native pixel x={px:.2f}, y={py:.2f}). "
                "Other pixels in the image record other wavelengths."
            )
        else:
            wavelength_location = (
                f"Spectral WCS (key W) sampled at the query center (native pixel x={px:.2f}, y={py:.2f}). "
                "Other pixels in the image record other wavelengths."
            )
    else:
        wavelength_location = (
            "Not sampled: the "
            + ("catalog-predicted target position" if pos_kind == "catalog_prediction" else "query center")
            + " lies outside this image, and the spectral WCS is not extrapolated."
        )

    # ---- quality screen in a circle around the screened position
    finite = np.isfinite(img)
    if var is not None:
        finite &= np.isfinite(var) & (var > 0)
    flag_counts: Dict[str, int] = {}
    adverse_names: List[str] = []
    valid_n = adverse_n = nonfinite_n = aperture_n = None
    if not covered:
        status = "not_covered"
        notes.append("The screened position is outside this image (geometric coverage check).")
    else:
        yy, xx = np.mgrid[0:ny, 0:nx]
        ap = (xx - px) ** 2 + (yy - py) ** 2 <= APERTURE_RADIUS_PX**2
        aperture_n = int(ap.sum())
        nonfinite_mask = ap & ~finite
        nonfinite_n = int(nonfinite_mask.sum())
        full_circle = math.pi * APERTURE_RADIUS_PX**2
        if aperture_n < 0.8 * full_circle:
            notes.append(f"Screen circle is clipped by the image edge ({aperture_n} pixels screened).")
        if flg is not None:
            adverse = np.zeros_like(ap)
            for bit, name in sorted(bit_names.items()):
                hit = ap & (((flg >> bit) & 1) == 1)
                c = int(hit.sum())
                if c:
                    flag_counts[name] = c
                    if name not in INFORMATIONAL_FLAGS:
                        adverse_names.append(name)
                        adverse |= hit
            # Bits the header does not name are treated as problems (we cannot
            # tell they are harmless). None occur in the 183 retained frames.
            named_mask = 0
            for bit in bit_names:
                named_mask |= 1 << bit
            unnamed = flg & ~named_mask & 0x7FFFFFFF
            for bit in range(31):
                hit = ap & (((unnamed >> bit) & 1) == 1)
                c = int(hit.sum())
                if c:
                    label = f"UNDOCUMENTED_BIT_{bit}"
                    flag_counts[label] = c
                    adverse_names.append(label)
                    adverse |= hit
            bad = adverse | nonfinite_mask
            adverse_n = int(bad.sum())
            valid_n = int((ap & ~bad).sum())
            # Known problems always win: any adverse or non-finite pixel -> flagged.
            # Only a screen with nothing wrong found can be "unknown" instead of
            # "clear", when the evidence behind it is too thin.
            if adverse_n > 0:
                status = "flagged"
            elif var is None:
                status = "unknown"
                notes.append(
                    "This file has no usable VARIANCE map, so pixel validity could not be fully "
                    "checked; the screen is reported as unknown rather than clear."
                )
            elif valid_n < MIN_CLEAR_PIXELS:
                status = "unknown"
                notes.append(
                    f"Only {valid_n} usable pixels in the screen circle. Perigee asks for at least "
                    f"{MIN_CLEAR_PIXELS} before calling a screen clear; this is our screening "
                    "heuristic, not a NASA or SPHEREx standard."
                )
            else:
                status = "clear"
        else:
            # Without flags we only know about non-finite pixels.
            if nonfinite_n > 0:
                status = "flagged"
            else:
                status = "unknown"
            adverse_n = None
            valid_n = None
        if nonfinite_n:
            notes.append(
                f"{nonfinite_n} of {aperture_n} screened pixels are non-finite (no usable value); "
                "the position is covered, so this is a quality problem, not missing coverage."
            )
        if status == "clear":
            notes.append(
                "No adverse flags or non-finite pixels within the screen circle. "
                "This is a screening result, not a detection or a brightness measurement."
            )
    informational_present = sorted(n for n in flag_counts if n in INFORMATIONAL_FLAGS)
    if informational_present:
        notes.append("Informational flags present (not treated as problems): " + ", ".join(informational_present) + ".")

    # ---- resample onto the fixed grid (nearest native pixel; no new resolution)
    size = meta.grid_size
    gw = grid_wcs(meta.query_ra_deg, meta.query_dec_deg, meta.fov_arcmin, size)
    gy, gx = np.mgrid[0:size, 0:size]
    ra_g, dec_g = gw.wcs_pix2world(gx.ravel().astype(float), gy.ravel().astype(float), 0)
    nxp, nyp = cel.all_world2pix(ra_g, dec_g, 0, quiet=True)
    nxp = nxp.reshape(size, size)
    nyp = nyp.reshape(size, size)
    vals, on_image = _sample_nearest(img, nxp, nyp, np.nan)
    fin_s, _ = _sample_nearest(finite.astype(np.uint8), nxp, nyp, 0)
    good = on_image & (fin_s == 1)
    grid_values = vals[good]

    if meta.display_limits is not None:
        lo, hi = float(meta.display_limits[0]), float(meta.display_limits[1])
        scale_mode = "shared"
        basis = meta.display_limits_basis or "Limits supplied by the caller and shared across the compared frames."
    else:
        lim = display_limits_from_values([grid_values])
        lo, hi = lim if lim is not None else (0.0, 1.0)
        scale_mode = "per_frame"
        basis = (
            f"Percentiles {DEFAULT_PERCENTILES[0]}-{DEFAULT_PERCENTILES[1]} of this frame's finite grid pixels. "
            "Brightness is not directly comparable between frames."
        )
    gray = np.zeros((size, size), dtype=np.uint8)
    gray[good] = np.round(_stretch(vals[good], lo, hi) * 255.0).astype(np.uint8)
    alpha = np.where(good, 255, 0).astype(np.uint8)
    # FITS grid row 0 is south; PNG row 0 must be north.
    png = _png(np.flipud(np.dstack([gray, alpha])))

    flag_png = None
    if meta.include_flag_image and (flg is not None or (~finite).any()):
        rgba = np.zeros((size, size, 4), dtype=np.uint8)
        if flg is not None:
            adverse_bits = 0
            for bit, name in bit_names.items():
                if name not in INFORMATIONAL_FLAGS:
                    adverse_bits |= 1 << bit
            fs, _ = _sample_nearest(flg, nxp, nyp, 0)
            rgba[on_image & ((fs & adverse_bits) != 0)] = _ADVERSE_RGBA
        rgba[on_image & (fin_s == 0)] = _NONFINITE_RGBA
        flag_png = _png(np.flipud(rgba))

    # ---- marker (catalog prediction only)
    marker = None
    if t is not None:
        mx, my = sky_to_display_px(gw, size, pos_ra, pos_dec)
        on_grid = bool(0.0 <= mx <= size and 0.0 <= my <= size)
        epoch_utc = Time(mjd, format="mjd").utc.isot + "Z" if mjd is not None else None
        marker = {
            "kind": "catalog_prediction",
            "label": "Catalog prediction (not a detection)",
            "x": round(mx, 3),
            "y": round(my, 3),
            "on_grid": on_grid,
            "ra_deg": pos_ra,
            "dec_deg": pos_dec,
            "epoch_mjd": mjd,
            "epoch_utc": epoch_utc,
            "propagated": propagated,
            "source": (
                (t.source or "Catalog position")
                + (
                    f", propagated from epoch J{t.epoch_jyear} with catalog proper motion"
                    + (" and parallax distance" if t.parallax_mas else "")
                    + " to this frame's mid-exposure time (annual parallax and binary orbits not modeled)."
                    if propagated
                    else " (no proper motion applied)."
                )
            ),
        }

    # ---- limitations attached to this result
    limitations.append(
        f"Display image is nearest-neighbour resampled from ~{nominal_scale_arcsec:.2f} arcsec native pixels onto a "
        f"{size}x{size} grid of {meta.fov_arcmin * 60.0 / size:.3f} arcsec display pixels; it adds no resolution."
    )
    limitations.append("Pixels are contrast-stretched for viewing only; no background subtraction; not photometry.")
    if scale_mode == "per_frame":
        limitations.append("Per-frame stretch: brightness is not directly comparable with other frames.")
    limitations.append(
        "The quality screen checks flags in a small circle around one position. A clear result is not a detection."
    )
    if marker is not None:
        limitations.append("The marker is a catalog prediction, not a position measured in this image.")
    if meta.collection_id and "qr" in meta.collection_id.lower():
        limitations.append("Quick-release (QR) products may be reprocessed in a later data release.")

    pipeline_version = None
    m = re.search(r"(l2b-v\d+-\d{4}-\d+)", meta.source_url or "")
    if m:
        pipeline_version = m.group(1)
    primary_version = hdul[0].header.get("VERSION")

    record: Dict[str, Any] = {
        "schema_version": 1,
        "frame_id": key,
        "frame_key": key,
        "observation_id": obsid,
        "detector": detector,
        "collection_id": meta.collection_id,
        "observed_at_utc": observed_at,
        "mjd": mjd,
        "time_basis": "DATE-AVG / MJD-AVG (mid-exposure) from the IMAGE header",
        "source_url": meta.source_url,
        "wavelength_um": wl,
        "bandwidth_um": bw,
        "wavelength_location": wavelength_location,
        "sampled_position": {
            "kind": pos_kind,
            "ra_deg": pos_ra,
            "dec_deg": pos_dec,
            "native_x": px if math.isfinite(px) else None,
            "native_y": py if math.isfinite(py) else None,
            "native_pixel_convention": "0-based FITS pixel centers of the IMAGE extension",
        },
        "image": {"src": None, "width": size, "height": size, "media_type": "image/png"},
        "flag_image": (
            {"src": None, "width": size, "height": size, "media_type": "image/png",
             "legend": {"adverse_flag": list(_ADVERSE_RGBA), "non_finite": list(_NONFINITE_RGBA)}}
            if flag_png is not None else None
        ),
        "registration": {
            "center_ra_deg": meta.query_ra_deg,
            "center_dec_deg": meta.query_dec_deg,
            "fov_arcmin": meta.fov_arcmin,
            "width": size,
            "height": size,
            "scale_arcsec_per_px": meta.fov_arcmin * 60.0 / size,
            "native_scale_arcsec_per_px": native_scale_arcsec,
            "projection": "TAN",
            "orientation": "north_up_east_left",
            "method": "nearest_neighbour",
            "method_detail": "Each display pixel takes the value of the native pixel containing its sky position, "
                             "via the IMAGE TAN-SIP WCS. Pixels outside the image or non-finite are transparent.",
            "pixel_convention": "origin at the top-left corner of the PNG, x right, y down, display pixels",
            "grid_id": grid_id(meta.query_ra_deg, meta.query_dec_deg, meta.fov_arcmin, size),
        },
        "quality": {
            "status": status,
            "covered": covered,
            "screen_radius_native_px": APERTURE_RADIUS_PX,
            "screened_pixels": aperture_n,
            "valid_aperture_pixels": valid_n,
            "adverse_aperture_pixels": adverse_n,
            "nonfinite_aperture_pixels": nonfinite_n,
            "flag_names": sorted(adverse_names),
            "flag_counts": flag_counts,
            "informational_flags": sorted(INFORMATIONAL_FLAGS),
            "notes": notes,
        },
        "display_scale": {
            "mode": scale_mode,
            "method": "asinh",
            "asinh_softening": ASINH_SOFTENING,
            "low": lo,
            "high": hi,
            "unit": str(ih.get("BUNIT", "")).strip() or None,
            "basis": basis,
            "background_subtraction": None,
            "clipping": "values below low map to black, above high to white",
        },
        "marker": marker,
        "provenance": {
            "retrieved_at": meta.retrieved_at_utc,
            "retrieved_at_basis": meta.retrieved_at_basis,
            "original_url": meta.source_url,
            "cutout_url": meta.cutout_url,
            "sha256": sha256,
            "processing_version": PROCESSING_VERSION,
            "pipeline_version": pipeline_version,
            "ssdc_software_version": str(primary_version).strip() if primary_version else None,
            "l2_dqa": str(ih.get("L2DQAFLG")).strip() if ih.get("L2DQAFLG") is not None else None,
            "native_shape": [ny, nx],
            "acknowledgments": list(ACKNOWLEDGMENTS),
        },
        "limitations": limitations,
    }
    return ProcessedFrame(record=record, png_bytes=png, flag_png_bytes=flag_png, grid_values=grid_values)


def grid_id(center_ra_deg: float, center_dec_deg: float, fov_arcmin: float, size: int) -> str:
    """Short stable identifier: frames with equal grid_id share the display grid."""
    s = f"TAN|{center_ra_deg:.9f}|{center_dec_deg:.9f}|{fov_arcmin:.6f}|{size}|NUEL"
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def png_data_url(png_bytes: bytes) -> str:
    import base64

    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def with_image_sources(record: Dict[str, Any], image_src: str, flag_src: Optional[str]) -> Dict[str, Any]:
    """Return a copy of ``record`` with ``image.src`` / ``flag_image.src`` filled."""
    import copy

    out = copy.deepcopy(record)
    out["image"]["src"] = image_src
    if out.get("flag_image") is not None:
        if flag_src is None:
            out["flag_image"] = None
        else:
            out["flag_image"]["src"] = flag_src
    return out


def inspect_fits(fits_bytes: bytes) -> Dict[str, Any]:
    """Small header/extension summary for diagnostics and tests (no pixels)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        hdul = _open(fits_bytes)
        try:
            exts = []
            for h in hdul:
                shape = list(h.data.shape) if getattr(h, "data", None) is not None and hasattr(h.data, "shape") else None
                exts.append({"name": h.name, "type": type(h).__name__, "shape": shape})
            ih = hdul["IMAGE"].header if "IMAGE" in hdul else fits.Header()
            fh = hdul["FLAGS"].header if "FLAGS" in hdul else fits.Header()
            return {
                "extensions": exts,
                "image": {k: (ih.get(k) if ih.get(k) is None else str(ih.get(k)).strip() if isinstance(ih.get(k), str) else ih.get(k))
                          for k in ("OBSID", "DETECTOR", "BUNIT", "DATE-OBS", "DATE-AVG", "MJD-OBS", "MJD-AVG",
                                    "TIMESYS", "CTYPE1", "CTYPE2", "CTYPE1W", "CTYPE2W", "PS1_0W", "L2DQAFLG")},
                "flag_bits": {str(b): n for b, n in sorted(flag_bit_names(fh).items())},
            }
        finally:
            hdul.close()
