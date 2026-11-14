"""Tiny synthetic SPHEREx-like L2 FITS builder for unit tests.

SYNTHETIC TEST FIXTURE, NOT A NASA OBSERVATION. It mimics the extension layout
found in real IRSA SPHEREx L2b cutouts (PRIMARY, IMAGE, FLAGS, VARIANCE, ZODI,
EPSF, WCS-WAVE) closely enough to exercise the processor: a TAN celestial WCS,
MSKNnnnn flag-bit names, DATE-AVG/MJD-AVG, and a WAVE-TAB spectral WCS (key W)
whose lookup table makes wavelength linear in raw detector x.
"""

from __future__ import annotations

import io
from typing import Dict, Optional, Tuple

import numpy as np
from astropy.io import fits

CENTER = (150.0, 20.0)  # RA, Dec of native pixel (NX/2-0.5, NY/2-0.5)
NX = NY = 60
SCALE_DEG = 6.15 / 3600.0
CRPIX_RAW = (-760.0, -197.0)  # cutout offset into raw detector coords, as in real files

FLAG_BITS: Dict[int, str] = {
    0: "TRANSIENT", 1: "OVERFLOW", 2: "SUR_ERROR", 6: "NONFUNC", 7: "DICHROIC", 9: "MISSING_DATA",
    10: "HOT", 11: "COLD", 12: "FULLSAMPLE", 14: "PHANMISS", 15: "NONLINEAR", 17: "PERSIST",
    19: "OUTLIER", 20: "CROSSTALK", 21: "SOURCE", 22: "GHOST", 23: "GHOST_FPA", 24: "GHOST_EXT",
    25: "STREAK", 26: "BLOOM", 27: "SNOWBALL", 28: "HALO",
}
BIT = {v: k for k, v in FLAG_BITS.items()}

# Wavelength model: lambda(raw_x) = WL0 + WL_SLOPE * (raw_x - 1), bandwidth constant.
WL0, WL_SLOPE, BW = 1.0, 0.001, 0.05


def wavelength_at_native(x0: float) -> float:
    """Expected wavelength at 0-based native cutout pixel x0 under the table model."""
    raw_index_coord = 1.0 + ((x0 + 1.0) - CRPIX_RAW[0])  # CRVAL1W=1, CDELT1W=1, 1-based pixel
    return WL0 + WL_SLOPE * (raw_index_coord - 1.0)


def celestial_header(rot_deg: float = 0.0) -> fits.Header:
    h = fits.Header()
    h["WCSAXES"] = 2
    h["CTYPE1"], h["CTYPE2"] = "RA---TAN", "DEC--TAN"
    h["CRVAL1"], h["CRVAL2"] = CENTER
    h["CRPIX1"], h["CRPIX2"] = NX / 2.0 + 0.5, NY / 2.0 + 0.5
    c, s = np.cos(np.radians(rot_deg)), np.sin(np.radians(rot_deg))
    h["PC1_1"], h["PC1_2"], h["PC2_1"], h["PC2_2"] = -SCALE_DEG * c, SCALE_DEG * s, SCALE_DEG * s, SCALE_DEG * c
    h["CDELT1"], h["CDELT2"] = 1.0, 1.0
    h["CUNIT1"], h["CUNIT2"] = "deg", "deg"
    h["RADESYS"] = "ICRS"
    return h


def spectral_keys(h: fits.Header) -> None:
    h["WCSAXESW"] = 2
    h["CRPIX1W"], h["CRPIX2W"] = CRPIX_RAW
    h["CDELT1W"], h["CDELT2W"] = 1, 1
    h["CUNIT1W"], h["CUNIT2W"] = "um", "um"
    h["CTYPE1W"], h["CTYPE2W"] = "WAVE-TAB", "WAVE-TAB"
    h["CRVAL1W"], h["CRVAL2W"] = 1, 1
    h["PV1_3W"], h["PV2_3W"] = 1, 2
    h["PS1_0W"], h["PS2_0W"] = "WCS-WAVE", "WCS-WAVE"
    h["PS1_1W"], h["PS2_1W"] = "VALUES", "VALUES"
    h["PS1_2W"], h["PS2_2W"] = "X", "Y"


def wave_table() -> fits.BinTableHDU:
    xs = np.array([1, 2049], dtype=np.int32)
    ys = np.array([1, 2049], dtype=np.int32)
    vals = np.zeros((2, 2, 2), dtype=np.float32)  # numpy order (y, x, k) == FITS TDIM (k, x, y)
    for iy in range(2):
        for ix in range(2):
            vals[iy, ix, 0] = WL0 + WL_SLOPE * (xs[ix] - 1)
            vals[iy, ix, 1] = BW
    cols = [
        fits.Column(name="X", format="2J", array=xs[None, :]),
        fits.Column(name="Y", format="2J", array=ys[None, :]),
        fits.Column(name="VALUES", format="8E", dim="(2,2,2)", array=vals[None, ...]),
    ]
    return fits.BinTableHDU.from_columns(cols, name="WCS-WAVE")


def make_fits(
    *,
    image: Optional[np.ndarray] = None,
    flags: Optional[np.ndarray] = None,
    include_flags: bool = True,
    include_variance: bool = True,
    include_wave: bool = True,
    obsid: str = "2099W01_1A_0001_1",
    detector: int = 3,
    mjd_avg: float = 61000.5,
    date_avg: str = "2025-11-24T12:00:00.000",
    rot_deg: float = 0.0,
    sources: Tuple[Tuple[float, float, float], ...] = (),
) -> bytes:
    """Return FITS bytes. ``sources`` are (x, y, amplitude) native-pixel Gaussians."""
    rng = np.random.default_rng(1)
    img = image if image is not None else (0.5 + 0.01 * rng.standard_normal((NY, NX))).astype(np.float32)
    yy, xx = np.mgrid[0:NY, 0:NX]
    for sx, sy, amp in sources:
        img = img + (amp * np.exp(-((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * 0.8**2))).astype(np.float32)
    ih = celestial_header(rot_deg)
    ih["EXTNAME"] = "IMAGE"
    ih["BUNIT"] = "MJy / sr"
    ih["DETECTOR"] = detector
    ih["OBSID"] = obsid
    ih["TIMESYS"] = "UTC"
    ih["DATE-OBS"] = date_avg
    ih["MJD-OBS"] = mjd_avg - 0.0007
    ih["DATE-AVG"] = date_avg
    ih["MJD-AVG"] = mjd_avg
    ih["L2DQAFLG"] = "Pass"
    spectral_keys(ih)
    hdus = [fits.PrimaryHDU(), fits.ImageHDU(np.asarray(img, dtype=np.float32), header=ih, name="IMAGE")]
    if include_flags:
        fh = celestial_header(rot_deg)
        for bit, name in FLAG_BITS.items():
            fh[f"MSKN{bit:04d}"] = name
            fh[f"MSKM{bit:04d}"] = 1 << bit
        f = flags if flags is not None else np.zeros((NY, NX), dtype=np.int32)
        hdus.append(fits.ImageHDU(f.astype(np.int32), header=fh, name="FLAGS"))
    if include_variance:
        hdus.append(fits.ImageHDU(np.full((NY, NX), 1e-4, dtype=np.float32), header=celestial_header(rot_deg), name="VARIANCE"))
    hdus.append(fits.ImageHDU(np.zeros((NY, NX), dtype=np.float32), name="ZODI"))
    if include_wave:
        hdus.append(wave_table())
    buf = io.BytesIO()
    fits.HDUList(hdus).writeto(buf)
    return buf.getvalue()
