"""Check that the frames of a case set line up on processor A's fixed grid, using field stars.

Adapted from Sagar Raut's ``tools/ingest/check_registration.py`` (PR #19, branch
``codex/sagar-data``). ``field_shift()`` is his method, kept unchanged; the loader
was rewritten for processor A's products and layout and uses only A's public
helpers (``backend/data/process.py``) plus astropy/numpy. Sagar's package is not
imported.

For each frame after the first in ``<preset>/case-<case_id>/frames.json``, the
original FITS pixels are resampled (bilinear) onto that set's grid, as recorded in
each frame's ``registration`` block. The region around the first frame's
catalog-prediction marker is masked, and the shift that best aligns the rest of
the field with the first frame is found by FFT cross-correlation with a parabolic
sub-pixel peak. A well-registered pair gives a field shift near zero. The same
measurement is also made on the committed display PNGs as served, and the
catalog marker's own motion is reported next to both for comparison.

This checks our display geometry only. It is not an astrometric measurement.
Pairs at very different wavelengths are reported but marked as not reliable:
stars change brightness between bands, so whole-field correlation can lock onto
the wrong pattern (Sagar's version skipped them for the same reason).

Read-only: raw FITS and products are never written. Usage, from the repo root:

    PERIGEE_DATA_ROOT=/path/to/research/build_data \\
        .venv/bin/python -m tools.ingest.check_registration [--json report.json]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from backend.data.process import grid_wcs  # noqa: E402

PRESETS = REPO / "backend" / "content" / "presets"
CASE_SETS = (("epsilon_indi_b", "case-fair_comparison"), ("barnards_star", "case-moving_neighbor"))
MASK_RADIUS_ARCSEC = 50.0  # as in Sagar's version
NATIVE_PIXEL_ARCSEC = 6.15
CROSS_BAND_RATIO = 1.25  # wavelength ratio above which a pair is "cross-band"


def field_shift(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> Tuple[float, float, float]:
    """Shift (dx, dy) in display pixels that moves b onto a, plus peak contrast.

    From Sagar's check_registration.py (PR #19), unchanged. ``mask`` is True
    where pixels are used. Sign: a field star at x_b in ``b`` and x_a in ``a``
    gives dx = x_a - x_b.
    """

    def prep(im):
        v = np.where(np.isfinite(im) & mask, im, np.nan)
        med = np.nanmedian(v)
        hi = np.nanpercentile(v, 99.5)
        v = np.clip(v, None, hi) - med
        v = np.nan_to_num(v, nan=0.0)
        return v * np.hanning(v.shape[0])[:, None] * np.hanning(v.shape[1])[None, :]

    A, B = np.fft.fft2(prep(a)), np.fft.fft2(prep(b))
    r = A * np.conj(B)
    cc = np.fft.fftshift(np.real(np.fft.ifft2(r)))  # plain (not whitened) cross-correlation: stars dominate, mask edges do not
    iy, ix = np.unravel_index(np.argmax(cc), cc.shape)

    def sub(c_m, c_0, c_p):
        d = c_m - 2 * c_0 + c_p
        return 0.0 if d == 0 else 0.5 * (c_m - c_p) / d

    n0, n1 = cc.shape
    dy = iy - n0 // 2 + sub(cc[iy - 1, ix], cc[iy, ix], cc[(iy + 1) % n0, ix])
    dx = ix - n1 // 2 + sub(cc[iy, ix - 1], cc[iy, ix], cc[iy, (ix + 1) % n1])
    contrast = float(cc[iy, ix] / (np.std(cc) + 1e-12))
    return float(dx), float(dy), contrast


def resample_bilinear(image: np.ndarray, sx: np.ndarray, sy: np.ndarray) -> np.ndarray:
    """Bilinear sample of ``image`` at 0-based native pixel coords; NaN off-image.

    A's products use nearest-neighbour; a sub-pixel registration check needs a
    smooth image, so the check resamples bilinearly (as Sagar's did). Display
    pixels whose nearest native pixel is non-finite stay NaN.
    """
    ny, nx = image.shape
    out = np.full(sx.shape, np.nan)
    inside = np.isfinite(sx) & np.isfinite(sy) & (sx >= -0.5) & (sx <= nx - 0.5) & (sy >= -0.5) & (sy <= ny - 0.5)
    if not inside.any():
        return out
    x = np.clip(sx[inside], 0, nx - 1)
    y = np.clip(sy[inside], 0, ny - 1)
    x0 = np.clip(np.floor(x).astype(int), 0, max(nx - 2, 0))
    y0 = np.clip(np.floor(y).astype(int), 0, max(ny - 2, 0))
    fx, fy = x - x0, y - y0
    acc = np.zeros(x.shape)
    wsum = np.zeros(x.shape)
    for ddx, ddy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        v = image[np.minimum(y0 + ddy, ny - 1), np.minimum(x0 + ddx, nx - 1)]
        ok = np.isfinite(v) & (w > 0)
        acc += np.where(ok, v * w, 0.0)
        wsum += np.where(ok, w, 0.0)
    vals = np.full(x.shape, np.nan)
    good = wsum > 1e-6
    vals[good] = acc[good] / wsum[good]
    xn = np.clip(np.round(sx[inside]).astype(int), 0, nx - 1)
    yn = np.clip(np.round(sy[inside]).astype(int), 0, ny - 1)
    vals[~np.isfinite(image[yn, xn])] = np.nan
    out[inside] = vals
    return out


def grid_image(fits_bytes: bytes, registration: Dict[str, Any]) -> np.ndarray:
    """Original IMAGE pixels on A's grid, in display orientation (row 0 = north,
    array index (r, c) is display pixel centre (c + 0.5, r + 0.5))."""
    size = int(registration["width"])
    gw = grid_wcs(registration["center_ra_deg"], registration["center_dec_deg"], registration["fov_arcmin"], size)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        with fits.open(io.BytesIO(fits_bytes), memmap=False) as hdul:
            img = np.asarray(hdul["IMAGE"].data, dtype=np.float64)
            cel = WCS(hdul["IMAGE"].header, fobj=hdul).celestial
            gy, gx = np.mgrid[0:size, 0:size]
            ra, dec = gw.wcs_pix2world(gx.ravel().astype(float), gy.ravel().astype(float), 0)
            sx, sy = cel.all_world2pix(ra, dec, 0, quiet=True)
    return np.flipud(resample_bilinear(img, sx.reshape(size, size), sy.reshape(size, size)))


def product_image(png_path: Path) -> np.ndarray:
    """Committed display PNG as served (grey, NaN where transparent)."""
    arr = np.asarray(Image.open(png_path).convert("LA"), dtype=np.float64)
    return np.where(arr[..., 1] > 0, arr[..., 0], np.nan)


def field_mask(size: int, marker: Optional[Dict[str, Any]], scale_arcsec: float,
               radius_arcsec: float = MASK_RADIUS_ARCSEC) -> np.ndarray:
    """True outside a circle around the marker (grid centre if there is none)."""
    cx, cy = (marker["x"] - 0.5, marker["y"] - 0.5) if marker else (size / 2 - 0.5, size / 2 - 0.5)
    yy, xx = np.mgrid[0:size, 0:size]
    return (xx - cx) ** 2 + (yy - cy) ** 2 > (radius_arcsec / scale_arcsec) ** 2


def _shift_entry(dx: float, dy: float, contrast: float, scale: float) -> Dict[str, Any]:
    return {"px": [round(dx, 3), round(dy, 3)], "arcsec": round(float(np.hypot(dx, dy)) * scale, 3),
            "peak_contrast": round(contrast, 1)}


def check_set(set_dir: Path, data_root: Path, ledger: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    doc = json.loads((set_dir / "frames.json").read_text())
    frames = doc["frames"]
    reg0 = frames[0]["registration"]
    for f in frames[1:]:
        r = f["registration"]
        if any(r[k] != reg0[k] for k in ("center_ra_deg", "center_dec_deg", "fov_arcmin", "width", "height")):
            raise ValueError(f"{set_dir.name}: {f['frame_key']} is not on the reference frame's grid")
    size, scale = int(reg0["width"]), float(reg0["scale_arcsec_per_px"])

    raw, png = [], []
    for f in frames:
        b = Path(data_root, ledger[f["frame_key"]]["file"]).read_bytes()
        if hashlib.sha256(b).hexdigest() != f["provenance"]["sha256"]:
            raise ValueError(f"{f['frame_key']}: raw FITS sha256 does not match the product's provenance")
        raw.append(grid_image(b, f["registration"]))
        png.append(product_image(set_dir / f"{f['frame_key']}.png"))

    m0 = frames[0].get("marker")
    mask = field_mask(size, m0, scale)
    pairs = []
    for f, g, p in zip(frames[1:], raw[1:], png[1:]):
        mk = f.get("marker")
        wl0, wl = frames[0].get("wavelength_um"), f.get("wavelength_um")
        cross = bool(wl0 and wl and max(wl0, wl) / min(wl0, wl) > CROSS_BAND_RATIO)
        row: Dict[str, Any] = {
            "reference": frames[0]["frame_key"],
            "compared": f["frame_key"],
            "wavelength_um": [wl0, wl],
            "cross_band": cross,
            "field_shift_raw": _shift_entry(*field_shift(raw[0], g, mask), scale),
            "field_shift_product_png": _shift_entry(*field_shift(png[0], p, mask), scale),
            "catalog_marker_shift_px": None,
            "catalog_marker_shift_arcsec": None,
        }
        if mk and m0:
            tdx, tdy = mk["x"] - m0["x"], mk["y"] - m0["y"]
            row["catalog_marker_shift_px"] = [round(tdx, 3), round(tdy, 3)]
            row["catalog_marker_shift_arcsec"] = round(float(np.hypot(tdx, tdy)) * scale, 3)
        if cross:
            row["note"] = ("Different wavelength from the reference; whole-field correlation is not reliable "
                           "across bands, so this value is informational only.")
        pairs.append(row)
    return {
        "preset_id": doc["preset_id"],
        "set": doc["set"],
        "grid_id": doc.get("grid_id"),
        "display_scale_arcsec_per_px": scale,
        "native_pixel_arcsec": NATIVE_PIXEL_ARCSEC,
        "method": (f"FFT cross-correlation, field only (target masked within {MASK_RADIUS_ARCSEC:g} arcsec of the "
                   "reference marker), parabolic sub-pixel peak. 'raw': original FITS resampled bilinearly onto the "
                   "set grid. 'product_png': committed nearest-neighbour, per-frame-stretched PNGs."),
        "pairs": pairs,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data-root", default=os.environ.get("PERIGEE_DATA_ROOT"),
                    help="research/build_data directory (or env PERIGEE_DATA_ROOT); read only")
    ap.add_argument("--json", type=Path, help="also write the report here (never into backend/content)")
    args = ap.parse_args(argv)
    if not args.data_root:
        ap.error("--data-root or PERIGEE_DATA_ROOT is required")
    data_root = Path(args.data_root)
    manifest = json.loads((data_root / "manifest.json").read_text())
    ledger = {f"{r['obs_id']}_D{r['detector']}": r for r in manifest["files"] if r.get("status") == "downloaded"}
    reports = []
    for preset, set_name in CASE_SETS:
        rep = check_set(PRESETS / preset / set_name, data_root, ledger)
        reports.append(rep)
        for r in rep["pairs"]:
            fr, fp = r["field_shift_raw"], r["field_shift_product_png"]
            print(f"{preset:15s} {set_name:22s} {r['reference']} -> {r['compared']}: "
                  f"field shift raw {fr['arcsec']:5.2f}\" (dx {fr['px'][0]:+.2f}, dy {fr['px'][1]:+.2f} px, "
                  f"contrast {fr['peak_contrast']:.0f}); png {fp['arcsec']:5.2f}\"; "
                  f"marker moved {r['catalog_marker_shift_arcsec']}\"" + ("  [cross-band]" if r["cross_band"] else ""))
    if args.json:
        if PRESETS in args.json.resolve().parents:
            ap.error("refusing to write into backend/content/presets")
        args.json.write_text(json.dumps({"sets": reports}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
