"""The common display grid every frame is resampled onto.

Grid definition (stored in each FrameRecord's `registration`):
  projection   gnomonic (TAN), ICRS
  center       the query center (or a case's fixed center); NEVER the moving target
  orientation  north up, east left
  size         `size` x `size` display pixels covering `fov_arcmin` on each side
  pixel origin display pixel (0, 0) is the TOP-LEFT corner pixel, x to the right,
               y downward (browser convention); pixel centers are at integer + 0.5 edges

Two frames on grids with the same center, field and size line up pixel for pixel, so any
shift between them comes from the sky (or from the data), not from the display.

Resampling:
  intensity  bilinear between the four nearest source pixels, using only finite neighbours
             (weights renormalised); NaN where the grid falls outside the cutout AND wherever
             the nearest source pixel has no value (no-data pixels are never filled in)
  flags      nearest source pixel (bit masks are categories, never averaged)
Display pixels are ~4x smaller than SPHEREx's 6.15" pixels at the default 6' / 256 px.
That is interpolation, not extra telescope resolution.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from astropy.wcs import WCS

NATIVE_PIXEL_ARCSEC = 6.15


@dataclass(frozen=True)
class GridSpec:
    center_ra_deg: float
    center_dec_deg: float
    fov_arcmin: float
    size: int = 256

    @property
    def scale_arcsec_per_px(self) -> float:
        return self.fov_arcmin * 60.0 / self.size

    def wcs(self) -> WCS:
        """FITS-style WCS for the grid (y up). Use `to_display_xy` for browser pixel coords."""
        w = WCS(naxis=2)
        w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        w.wcs.crval = [self.center_ra_deg, self.center_dec_deg]
        w.wcs.crpix = [(self.size + 1) / 2.0, (self.size + 1) / 2.0]
        d = self.fov_arcmin / 60.0 / self.size
        w.wcs.cdelt = [-d, d]  # east left, north up
        w.wcs.radesys = "ICRS"
        return w

    def to_display_xy(self, ra_deg: float, dec_deg: float) -> tuple[float, float]:
        """Sky position -> display pixel coordinates (origin top-left, continuous, 0..size)."""
        x, y = self.wcs().world_to_pixel_values(ra_deg, dec_deg)  # 0-based, y up
        return float(x) + 0.5, float(self.size - 0.5 - y)

    @property
    def grid_id(self) -> str:
        """Equal grid_id <=> identical display grid (same center, field and size)."""
        import hashlib

        key = f"{self.center_ra_deg:.8f}|{self.center_dec_deg:.8f}|{self.fov_arcmin:g}|{self.size}|TAN|NUEL"
        return "grid_" + hashlib.sha256(key.encode()).hexdigest()[:12]

    def registration(self) -> dict:
        # Field names follow backend/models/frame.py (API candidate A).
        return {
            "grid_id": self.grid_id,
            "center_ra_deg": self.center_ra_deg,
            "center_dec_deg": self.center_dec_deg,
            "fov_arcmin": self.fov_arcmin,
            "width": self.size,
            "height": self.size,
            "scale_arcsec_per_px": round(self.scale_arcsec_per_px, 6),
            "native_scale_arcsec_per_px": NATIVE_PIXEL_ARCSEC,
            "projection": "TAN",
            "frame": "ICRS",
            "orientation": "north_up_east_left",
            "pixel_origin": "top-left pixel corner; x right, y down",
            "method": "bilinear resample of intensity (finite neighbours only; source pixels without a value stay empty); nearest-pixel resample of flags",
        }


def source_pixel_coords(grid: GridSpec, src_wcs: WCS) -> tuple[np.ndarray, np.ndarray]:
    """For every display pixel (row 0 = top), the 0-based source pixel position it samples."""
    n = grid.size
    gy, gx = np.mgrid[0:n, 0:n].astype(float)
    fits_y = (n - 1) - gy  # display row 0 is the top (north)
    ra, dec = grid.wcs().pixel_to_world_values(gx, fits_y)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sx, sy = src_wcs.world_to_pixel_values(ra, dec)
    return np.asarray(sx, float), np.asarray(sy, float)


def resample_bilinear(image: np.ndarray, sx: np.ndarray, sy: np.ndarray) -> np.ndarray:
    ny, nx = image.shape
    out = np.full(sx.shape, np.nan)
    inside = np.isfinite(sx) & np.isfinite(sy) & (sx >= -0.5) & (sx <= nx - 0.5) & (sy >= -0.5) & (sy <= ny - 0.5)
    if not inside.any():
        return out
    x = np.clip(sx[inside], 0, nx - 1)
    y = np.clip(sy[inside], 0, ny - 1)
    x0 = np.clip(np.floor(x).astype(int), 0, max(nx - 2, 0))
    y0 = np.clip(np.floor(y).astype(int), 0, max(ny - 2, 0))
    fx = x - x0
    fy = y - y0
    acc = np.zeros(x.shape)
    wsum = np.zeros(x.shape)
    for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xi = np.minimum(x0 + dx, nx - 1)
        yi = np.minimum(y0 + dy, ny - 1)
        v = image[yi, xi]
        ok = np.isfinite(v) & (w > 0)
        acc += np.where(ok, v * w, 0.0)
        wsum += np.where(ok, w, 0.0)
    vals = np.full(x.shape, np.nan)
    good = wsum > 1e-6
    vals[good] = acc[good] / wsum[good]
    # Never fill a source pixel that has no value: if the nearest source pixel is non-finite
    # (e.g. a saturated star core), the display pixel stays empty instead of being
    # interpolated from its neighbours.
    xn = np.clip(np.round(sx[inside]).astype(int), 0, nx - 1)
    yn = np.clip(np.round(sy[inside]).astype(int), 0, ny - 1)
    vals[~np.isfinite(image[yn, xn])] = np.nan
    out[inside] = vals
    return out


def resample_nearest(arr: np.ndarray, sx: np.ndarray, sy: np.ndarray, fill: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Nearest-pixel resample. Returns (values, inside_mask)."""
    ny, nx = arr.shape
    xi = np.round(sx)
    yi = np.round(sy)
    inside = np.isfinite(xi) & np.isfinite(yi) & (xi >= 0) & (xi <= nx - 1) & (yi >= 0) & (yi <= ny - 1)
    out = np.full(sx.shape, fill, dtype=arr.dtype)
    out[inside] = arr[yi[inside].astype(int), xi[inside].astype(int)]
    return out, inside
