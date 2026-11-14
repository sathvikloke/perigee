"""Check that frames in a comparison set line up on the fixed grid, using field stars.

For each frame after the first, the script resamples the original FITS pixels onto the set's
grid, masks the region around the target, and finds the shift that best aligns the rest of
the field with the first frame (FFT cross-correlation with a parabolic sub-pixel peak).
A well-registered pair gives a field shift near zero; the target's own catalog-predicted
motion is reported next to it for comparison.

Usage:
    python tools/ingest/check_registration.py --raw ../perigee-data/raw
Writes backend/content/presets/<preset>/sets/<set_id>.registration.json and prints a table.
This is a consistency check of our display geometry, not an astrometric measurement.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from data.fits_io import open_cutout  # noqa: E402
from data.grid import GridSpec, resample_bilinear, source_pixel_coords  # noqa: E402

PRESETS = REPO / "backend" / "content" / "presets"
MANIFEST = REPO / "research" / "build_data" / "manifest.json"
MASK_RADIUS_ARCSEC = 50.0


def field_shift(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> tuple[float, float, float]:
    """Shift (dx, dy) in display pixels that moves b onto a, plus peak contrast."""

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=Path)
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    by_key = {f"{f['obs_id']}_D{f['detector']}": f for f in manifest["files"] if f["status"] == "downloaded"}
    index = json.loads((PRESETS / "manifest.json").read_text())
    for preset in index["presets"]:
        for s in preset["comparison_sets"]:
            doc = json.loads((PRESETS / s["path"]).read_text())
            frames = doc["frames"]
            reg = frames[0]["registration"]
            grid = GridSpec(reg["center_ra_deg"], reg["center_dec_deg"], reg["fov_arcmin"], reg["width"])
            scale = grid.scale_arcsec_per_px
            grids = []
            for r in frames:
                e = by_key[r["frame_key"]]
                cut = open_cutout((args.raw / e["target_id"] / Path(e["file"]).name).read_bytes())
                sx, sy = source_pixel_coords(grid, cut.wcs)
                grids.append(resample_bilinear(cut.image, sx, sy))
            n = grid.size
            yy, xx = np.mgrid[0:n, 0:n]
            m0 = frames[0]["marker"]
            cx, cy = (m0["x"] - 0.5, m0["y"] - 0.5) if m0 else (n / 2, n / 2)
            mask = (xx - cx) ** 2 + (yy - cy) ** 2 > (MASK_RADIUS_ARCSEC / scale) ** 2
            rows = []
            shared_refs = set(doc.get("shared_scale", {}).get("refs") or [])
            for r, g in zip(frames[1:], grids[1:]):
                if shared_refs and (r.get("case_ref") not in shared_refs or frames[0].get("case_ref") not in shared_refs):
                    # Different wavelength: stars change brightness, so whole-field correlation can
                    # lock onto the wrong pattern. Not checked here (see Sathvik's control-star check).
                    rows.append({"reference": frames[0]["frame_key"], "compared": r["frame_key"], "field_shift_px": None,
                                 "note": "Different wavelength from the reference; whole-field correlation is not reliable across wavelengths, so it was not used. Checked by eye (target and bright field star line up) and by science/check_registration.py control stars."})
                    print(f"{preset['preset_id']:15s} {s['set_id']:28s} {r['frame_key']:22s} skipped: different wavelength")
                    continue
                dx, dy, contrast = field_shift(grids[0], g, mask)
                mk = r["marker"]
                tdx = None if (mk is None or m0 is None) else mk["x"] - m0["x"]
                tdy = None if (mk is None or m0 is None) else mk["y"] - m0["y"]
                rows.append({
                    "reference": frames[0]["frame_key"],
                    "compared": r["frame_key"],
                    "field_shift_px": [round(dx, 3), round(dy, 3)],
                    "field_shift_arcsec": round(float(np.hypot(dx, dy)) * scale, 3),
                    "correlation_peak_contrast": round(contrast, 1),
                    "catalog_marker_shift_px": None if tdx is None else [round(tdx, 2), round(tdy, 2)],
                    "catalog_marker_shift_arcsec": None if tdx is None else round(float(np.hypot(tdx, tdy)) * scale, 2),
                })
                print(f"{preset['preset_id']:15s} {s['set_id']:28s} {r['frame_key']:22s} field shift {np.hypot(dx, dy) * scale:5.2f}\" "
                      f"(dx {dx:+.2f}, dy {dy:+.2f} px, contrast {contrast:.0f})  catalog marker moved {rows[-1]['catalog_marker_shift_arcsec']}\"")
            out = {
                "set_id": s["set_id"],
                "method": f"FFT cross-correlation of the original pixels resampled onto the set grid, field only (target masked within {MASK_RADIUS_ARCSEC:g} arcsec), parabolic sub-pixel peak",
                "display_scale_arcsec_per_px": scale,
                "native_pixel_arcsec": 6.15,
                "interpretation": "Field shifts well under one native pixel (6.15 arcsec) mean the frames are registered by their WCS. This checks our display geometry only; it is not a proper-motion measurement.",
                "method_check": "Injected grid offsets of 1.5-6 arcsec on these same files were recovered with the right direction and within ~0.4 arcsec (the method slightly underestimates); see backend/tests/data/test_registration.py.",
                "pairs": rows,
            }
            (PRESETS / s["path"]).with_suffix(".registration.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
