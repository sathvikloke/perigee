"""Wavelength and bandwidth at one sky position in a SPHEREx Level 2 cutout.

SPHEREx uses linear variable filters, so every pixel sees a different wavelength. The
per-pixel value comes from the alternate WCS "W" (CTYPE = WAVE-TAB), a bilinear lookup table
stored in the WCS-WAVE extension and indexed by raw detector pixel position.

Pitfall checked during the build: the IMAGE header also carries SIP distortion keywords for
the sky WCS. If they stay in the header, astropy applies them to the "W" lookup as well and
the wavelength comes out ~0.001 um off. We strip the SIP cards before building the "W" WCS.
The result was checked against a direct bilinear read of the WCS-WAVE table
(`table_lookup` below) and against the original audit values.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from astropy.wcs import WCS

from .fits_io import SpherexCutout

_SIP_PREFIXES = ("A_", "B_", "AP_", "BP_")


@dataclass(frozen=True)
class WavelengthSample:
    wavelength_um: float | None
    bandwidth_um: float | None
    pixel_x: float | None  # 0-based cutout pixel where it was evaluated
    pixel_y: float | None
    note: str | None = None


def spectral_wcs(cut: SpherexCutout) -> WCS | None:
    if not cut.meta.get("has_wavelength_table"):
        return None
    h = cut.header.copy()
    for key in list(h.keys()):
        if key.startswith(_SIP_PREFIXES):
            del h[key]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return WCS(h, fobj=cut.hdul, key="W")
    except Exception:
        return None


def wavelength_at(cut: SpherexCutout, ra_deg: float, dec_deg: float) -> WavelengthSample:
    """Evaluate wavelength/bandwidth where (ra, dec) falls on the cutout. Unknown stays None."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x, y = cut.wcs.world_to_pixel_values(ra_deg, dec_deg)
    x, y = float(x), float(y)
    ny, nx = cut.shape
    if not (np.isfinite(x) and np.isfinite(y)) or not (-0.5 <= x <= nx - 0.5 and -0.5 <= y <= ny - 0.5):
        return WavelengthSample(None, None, None, None, "position is outside this cutout")
    w = spectral_wcs(cut)
    if w is None:
        return WavelengthSample(None, None, x, y, "file has no usable wavelength table")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wl, bw = w.pixel_to_world_values(x, y)
        wl, bw = float(wl), float(bw)
    except Exception:
        return WavelengthSample(None, None, x, y, "wavelength lookup failed")
    if not (np.isfinite(wl) and 0.5 < wl < 5.5):  # SPHEREx covers 0.75-5.0 um
        return WavelengthSample(None, None, x, y, "wavelength lookup gave an implausible value")
    bw_out = bw if np.isfinite(bw) and 0 < bw < 1 else None
    return WavelengthSample(wl, bw_out, x, y)


def table_lookup(cut: SpherexCutout, x: float, y: float) -> tuple[float, float] | None:
    """Independent check: bilinear interpolation straight from the WCS-WAVE table.

    Uses the FITS -TAB convention: table coordinate = (pixel_1based - CRPIXjW) * CDELTjW + CRVALjW.
    Returns None outside the table's control points.
    """
    h = cut.header
    t = cut.hdul["WCS-WAVE"].data
    X = np.asarray(t["X"][0], dtype=float)
    Y = np.asarray(t["Y"][0], dtype=float)
    V = np.asarray(t["VALUES"][0], dtype=float)  # (len(Y), len(X), 2)
    xr = (x + 1 - h["CRPIX1W"]) * h.get("CDELT1W", 1) + h["CRVAL1W"]
    yr = (y + 1 - h["CRPIX2W"]) * h.get("CDELT2W", 1) + h["CRVAL2W"]
    if not (X[0] <= xr <= X[-1] and Y[0] <= yr <= Y[-1]):
        return None
    i = min(max(int(np.searchsorted(X, xr)) - 1, 0), len(X) - 2)
    j = min(max(int(np.searchsorted(Y, yr)) - 1, 0), len(Y) - 2)
    fx = (xr - X[i]) / (X[i + 1] - X[i])
    fy = (yr - Y[j]) / (Y[j + 1] - Y[j])

    def bil(k: int) -> float:
        return float(
            V[j, i, k] * (1 - fx) * (1 - fy)
            + V[j, i + 1, k] * fx * (1 - fy)
            + V[j + 1, i, k] * (1 - fx) * fy
            + V[j + 1, i + 1, k] * fx * fy
        )

    return bil(0), bil(1)
