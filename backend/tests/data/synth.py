"""Tiny synthetic SPHEREx-like L2 cutouts for unit tests (labelled synthetic; not sky data)."""

from __future__ import annotations

import io
import math
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

FLAG_BITS: Dict[int, str] = {
    0: "TRANSIENT",
    1: "OVERFLOW",
    2: "SUR_ERROR",
    6: "NONFUNC",
    12: "FULLSAMPLE",
    19: "OUTLIER",
    21: "SOURCE",
    26: "BLOOM",
}

CENTER = (331.0966687831005, -56.80064917516836)
NATIVE_ARCSEC = 6.15


def celestial_header(
    center: Tuple[float, float] = CENTER,
    shape: Tuple[int, int] = (60, 60),
    rotation_deg: float = 0.0,
    flip_parity: bool = False,
    crpix_offset: Tuple[float, float] = (0.0, 0.0),
) -> fits.Header:
    ny, nx = shape
    s = NATIVE_ARCSEC / 3600.0
    t = math.radians(rotation_deg)
    cd = s * np.array([[-math.cos(t), math.sin(t)], [math.sin(t), math.cos(t)]])
    if flip_parity:
        cd[:, 0] *= -1.0
    h = fits.Header()
    h["CTYPE1"] = "RA---TAN"
    h["CTYPE2"] = "DEC--TAN"
    h["CRVAL1"] = center[0]
    h["CRVAL2"] = center[1]
    h["CRPIX1"] = (nx + 1) / 2.0 + crpix_offset[0]
    h["CRPIX2"] = (ny + 1) / 2.0 + crpix_offset[1]
    h["CD1_1"], h["CD1_2"], h["CD2_1"], h["CD2_2"] = cd[0, 0], cd[0, 1], cd[1, 0], cd[1, 1]
    h["CUNIT1"] = "deg"
    h["CUNIT2"] = "deg"
    h["RADESYS"] = "ICRS"
    return h


def make_cutout(
    *,
    shape: Tuple[int, int] = (60, 60),
    rotation_deg: float = 0.0,
    flip_parity: bool = False,
    stars: Iterable[Tuple[float, float, float]] = (),
    flags: Optional[np.ndarray] = None,
    nan_at: Iterable[Tuple[int, int]] = (),
    obsid: str = "2099W01_1A_0001_1",
    detector: int = 3,
    crpix_offset: Tuple[float, float] = (0.0, 0.0),
    background: float = 1.0,
) -> bytes:
    """Return FITS bytes with PRIMARY, IMAGE, FLAGS, VARIANCE, WCS-WAVE.

    ``stars`` are (ra_deg, dec_deg, amplitude) Gaussians (sigma 0.8 native px).
    ``nan_at`` are (y, x) source pixels set to NaN in IMAGE.
    """
    ny, nx = shape
    ch = celestial_header(shape=shape, rotation_deg=rotation_deg, flip_parity=flip_parity, crpix_offset=crpix_offset)
    w = WCS(ch)
    yy, xx = np.mgrid[0:ny, 0:nx].astype(np.float64)
    img = np.full(shape, background, dtype=np.float64)
    for ra, dec, amp in stars:
        x0, y0 = w.all_world2pix([[ra, dec]], 0)[0]
        img += amp * np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / (2 * 0.8 ** 2))
    for (y, x) in nan_at:
        img[y, x] = np.nan
    img = img.astype(np.float32)

    ih = ch.copy()
    ih["EXTNAME"] = "IMAGE"
    ih["OBSID"] = obsid
    ih["DETECTOR"] = detector
    ih["DATE-AVG"] = "2099-01-01T00:00:00.000"
    ih["MJD-AVG"] = 87158.0
    # Spectral -TAB WCS like SPHEREx: raw detector coordinates via CRPIXnW.
    ih["WCSAXESW"] = 2
    for i, crpix in ((1, -760.0), (2, -197.0)):
        ih[f"CRPIX{i}W"] = crpix
        ih[f"CDELT{i}W"] = 1
        ih[f"CRVAL{i}W"] = 1
        ih[f"CTYPE{i}W"] = "WAVE-TAB"
        ih[f"CUNIT{i}W"] = "um"
        ih[f"PS{i}_0W"] = "WCS-WAVE"
        ih[f"PS{i}_1W"] = "VALUES"
    ih["PS1_2W"] = "X"
    ih["PS2_2W"] = "Y"
    ih["PV1_3W"] = 1
    ih["PV2_3W"] = 2

    if flags is None:
        flags = np.zeros(shape, dtype=np.int32)
    fh = ch.copy()
    fh["EXTNAME"] = "FLAGS"
    for bit, name in FLAG_BITS.items():
        fh[f"MSKN{bit:04d}"] = name
        fh[f"MSKM{bit:04d}"] = 1 << bit

    vh = ch.copy()
    vh["EXTNAME"] = "VARIANCE"

    xs = np.array([1, 1021, 2040], dtype=np.int32)
    ys = np.array([1, 2040], dtype=np.int32)
    vals = np.zeros((ys.size, xs.size, 2), dtype=np.float32)
    for j, yv in enumerate(ys):
        for i, xv in enumerate(xs):
            vals[j, i, 0] = 2.0 + 0.0001 * (xv - 1) + 0.00002 * (yv - 1)  # wavelength
            vals[j, i, 1] = 0.05 + 0.00001 * (xv - 1)  # bandwidth
    cols = fits.ColDefs(
        [
            fits.Column(name="X", format=f"{xs.size}J", dim=f"({xs.size})", array=xs[None, :]),
            fits.Column(name="Y", format=f"{ys.size}J", dim=f"({ys.size})", array=ys[None, :]),
            fits.Column(name="VALUES", format=f"{vals.size}E", dim=f"(2,{xs.size},{ys.size})", array=vals[None, ...]),
        ]
    )
    wave = fits.BinTableHDU.from_columns(cols, name="WCS-WAVE")

    hdul = fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.ImageHDU(img, header=ih, name="IMAGE"),
            fits.ImageHDU(flags.astype(np.int32), header=fh, name="FLAGS"),
            fits.ImageHDU(np.ones(shape, dtype=np.float32), header=vh, name="VARIANCE"),
            wave,
        ]
    )
    buf = io.BytesIO()
    hdul.writeto(buf)
    return buf.getvalue()


def expected_wavelength(x0: float, y0: float) -> float:
    """Analytic wavelength of the synthetic table at 0-based cutout pixel (x0, y0)."""
    psi_x = (x0 + 1) + 760 + 1
    psi_y = (y0 + 1) + 197 + 1
    return 2.0 + 0.0001 * (psi_x - 1) + 0.00002 * (psi_y - 1)
