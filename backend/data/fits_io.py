"""Read a SPHEREx Level 2 cutout from bytes and check that it has what we need.

Expected extensions (IRSA SPHEREx Level 2 spectral image, see the Explanatory Supplement):
  IMAGE     float32 surface brightness, MJy/sr, celestial WCS (TAN-SIP)
  FLAGS     int32 bit mask; bit names are in the header as MSKNnnnn / MSKMnnnn
  VARIANCE  float32 (MJy/sr)^2
  WCS-WAVE  lookup table for the per-pixel wavelength WCS (alternate WCS key "W")
ZODI and EPSF are present but not used for display.
"""
from __future__ import annotations

import io
import warnings
from dataclasses import dataclass, field

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from .errors import UnsupportedData


@dataclass
class SpherexCutout:
    image: np.ndarray  # float64, NaN where no data
    flags: np.ndarray | None  # int64 bit mask or None if the extension is missing
    variance: np.ndarray | None
    wcs: WCS  # celestial
    hdul: fits.HDUList  # kept open for the wavelength lookup table
    header: fits.Header  # IMAGE header
    flag_bits: dict[str, int]  # name -> bit value, read from the FLAGS header
    meta: dict = field(default_factory=dict)

    @property
    def shape(self) -> tuple[int, int]:
        return self.image.shape  # (ny, nx)


def open_cutout(data: bytes) -> SpherexCutout:
    if not data.startswith(b"SIMPLE  ="):
        raise UnsupportedData("not a FITS file")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            hdul = fits.open(io.BytesIO(data), memmap=False)
            hdul.verify("exception")
            names = [h.name for h in hdul]
            if "IMAGE" not in names:
                raise UnsupportedData("FITS file has no IMAGE extension")
            img_hdu = hdul["IMAGE"]
            image = img_hdu.data
            header = img_hdu.header
    except UnsupportedData:
        raise
    except Exception as exc:
        raise UnsupportedData("FITS file could not be read (truncated or malformed)") from exc

    if image is None or image.ndim != 2 or min(image.shape) < 2:
        raise UnsupportedData("IMAGE extension is not a 2-D image")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            wcs = WCS(header, naxis=2)
        except Exception as exc:
            raise UnsupportedData("IMAGE extension has no usable sky coordinates") from exc
    if not wcs.has_celestial:
        raise UnsupportedData("IMAGE extension has no usable sky coordinates")

    flags = None
    flag_bits: dict[str, int] = {}
    if "FLAGS" in names and hdul["FLAGS"].data is not None and hdul["FLAGS"].data.shape == image.shape:
        flags = hdul["FLAGS"].data.astype(np.int64)
        flag_bits = read_flag_bits(hdul["FLAGS"].header)

    variance = None
    if "VARIANCE" in names and hdul["VARIANCE"].data is not None and hdul["VARIANCE"].data.shape == image.shape:
        variance = hdul["VARIANCE"].data.astype(np.float64)

    meta = {
        "observation_id": header.get("OBSID"),
        "detector": _int(header.get("DETECTOR")),
        "date_obs": header.get("DATE-OBS"),
        "mjd_obs": _float(header.get("MJD-OBS")),
        "date_avg": header.get("DATE-AVG"),
        "mjd_avg": _float(header.get("MJD-AVG")),
        "bunit": header.get("BUNIT"),
        "psf_fwhm_arcsec": _float(header.get("PSF_FWHM")),
        "pipeline_version": hdul[0].header.get("VERSION"),
        "l2_dqa": header.get("L2DQAFLG"),
        "extensions": names,
        "has_wavelength_table": "WCS-WAVE" in names and "CTYPE1W" in header,
    }
    return SpherexCutout(image.astype(np.float64), flags, variance, wcs, hdul, header, flag_bits, meta)


def read_flag_bits(header: fits.Header) -> dict[str, int]:
    """Map flag names to bit values using the MSKNnnnn / MSKMnnnn header cards."""
    out: dict[str, int] = {}
    for key in header:
        if key.startswith("MSKN"):
            n = key[4:]
            name = str(header[key]).strip()
            value = header.get("MSKM" + n)
            if name and isinstance(value, (int, np.integer)):
                out[name] = int(value)
    return out


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None
