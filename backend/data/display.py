"""Turn a resampled intensity grid into a small PNG, and flags into an overlay PNG.

Display stretch (recorded in each FrameRecord's `display_scale`):
  1. background offset: subtract the median of the frame's valid display pixels. This only
     shifts the zero point so frames with different sky/zodiacal levels look alike. It is
     not a calibrated background subtraction.
  2. limits: per_frame -> low = -2 sigma, high = 99.9th percentile of that frame, where sigma
                          is the robust noise (1.4826 x median absolute deviation)
             shared    -> limits supplied by the caller (one set for a whole comparison)
  3. asinh stretch between the limits with softening = 4 sigma, clipped to 0..1, 8-bit.
     Tying the softening to the noise keeps faint field stars visible next to a bright,
     saturated target without turning a quiet field into noise.
Pixels with no data are fully transparent (alpha 0) so they can't be mistaken for dark sky.

PNG brightness is for looking, not measuring. Raw MJy/sr values stay in the FITS file.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image

from .records import SharedScale

LOW_SIGMA = 2.0
HIGH_PERCENTILE = 99.9
SOFTENING_SIGMA = 4.0


def background_offset(grid_image: np.ndarray) -> float | None:
    vals = grid_image[np.isfinite(grid_image)]
    return float(np.median(vals)) if vals.size else None


def robust_sigma(values: np.ndarray) -> float | None:
    v = values[np.isfinite(values)]
    if v.size < 16:
        return None
    return float(1.4826 * np.median(np.abs(v - np.median(v))))


def per_frame_limits(values: np.ndarray) -> SharedScale | None:
    v = values[np.isfinite(values)]
    if v.size < 16:
        return None
    sig = robust_sigma(v) or 0.0
    med = float(np.median(v))
    low = med - LOW_SIGMA * sig
    high = float(np.percentile(v, HIGH_PERCENTILE))
    if not high > low:
        high = low + 1e-6
    soft = SOFTENING_SIGMA * sig if sig > 0 else (high - low) * 0.05
    return SharedScale(float(low), float(high), float(soft))


def stretch(values: np.ndarray, scale: SharedScale) -> np.ndarray:
    soft = scale.asinh_softening if scale.asinh_softening > 0 else 1e-6
    span = np.arcsinh((scale.high - scale.low) / soft)
    with np.errstate(invalid="ignore"):
        s = np.arcsinh((values - scale.low) / soft) / span
    return np.clip(s, 0.0, 1.0)


def intensity_png(values: np.ndarray, scale: SharedScale) -> bytes:
    finite = np.isfinite(values)
    g = (stretch(np.where(finite, values, scale.low), scale) * 255.0 + 0.5).astype(np.uint8)
    a = np.where(finite, 255, 0).astype(np.uint8)
    img = Image.fromarray(np.dstack([g, a]))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def flag_overlay_png(adverse: np.ndarray, inside: np.ndarray) -> bytes:
    """Adverse-flag pixels as a hatched magenta overlay (pattern, not color alone)."""
    n0, n1 = adverse.shape
    yy, xx = np.mgrid[0:n0, 0:n1]
    stripe = ((xx + yy) // 3) % 2 == 0
    on = adverse & inside
    rgba = np.zeros((n0, n1, 4), dtype=np.uint8)
    rgba[..., 0] = 230
    rgba[..., 1] = 40
    rgba[..., 2] = 200
    rgba[..., 3] = np.where(on & stripe, 200, np.where(on, 70, 0))
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def scale_record(mode: str, scale: SharedScale | None, offset: float | None) -> dict:
    # Field names follow backend/models/frame.py (API candidate A). low/high are after the offset.
    return {
        "mode": mode,
        "method": "asinh",
        "unit": "MJy/sr",
        "low": None if scale is None else scale.low,
        "high": None if scale is None else scale.high,
        "asinh_softening": None if scale is None else scale.asinh_softening,
        "background_offset": offset,
        "comparable_brightness": False if mode == "per_frame" else None,
        "basis": (
            "Median background offset subtracted for display only; values outside low/high are clipped. "
            + (
                "Each frame has its own contrast, so brightness is NOT comparable between frames."
                if mode == "per_frame"
                else "Frames in this set share one stretch; display brightness still depends on wavelength, PSF and background, so it is not a calibrated brightness comparison."
            )
        ),
    }
