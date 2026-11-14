"""Fixed-grid registration check for a curated case (independent of the app).

Reprojects the case frames from the original FITS files onto ONE north-up,
east-left TAN grid centered on the preset query_center, then:

* measures how much surrounding (control) stars shift between frames, and
* reports where the catalog-predicted marker falls on that grid per frame.

If controls are stable to a small fraction of a pixel, an apparent shift of
the target on the grid is not a rendering artifact. This is a verification of
the display geometry, NOT a proper-motion measurement (the bright targets used
here are saturated at their centers).

Usage (from the repository root):
    .research-venv/bin/python science/check_registration.py moving_neighbor
Writes science/audit/registration_<case_id>.json and a PNG next to it for
human inspection.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
from astropy import log
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates, maximum_filter

warnings.simplefilter("ignore")
log.setLevel("ERROR")

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research" / "build_data"
AUDIT = Path(__file__).resolve().parent / "audit"
GRID_PX = 72
GRID_SCALE_ARCSEC = 5.0  # 6 arcmin field


def grid_wcs(ra: float, dec: float) -> WCS:
    g = WCS(naxis=2)
    g.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    g.wcs.crval = [ra, dec]
    g.wcs.crpix = [(GRID_PX + 1) / 2, (GRID_PX + 1) / 2]
    s = GRID_SCALE_ARCSEC / 3600
    g.wcs.cdelt = [-s, s]  # east left, north up
    return g


def centroid(img: np.ndarray, x: float, y: float, r: int = 3) -> tuple[float, float]:
    ys, xs = np.mgrid[int(y) - r:int(y) + r + 1, int(x) - r:int(x) + r + 1]
    v = img[ys, xs] - np.nanmedian(img)
    v = np.nan_to_num(v)
    v[v < 0] = 0
    return float((xs * v).sum() / v.sum()), float((ys * v).sum() / v.sum())


def main(case_id: str) -> int:
    case = json.loads((ROOT / "backend/content/cases" / f"{case_id}.json").read_text())
    targets = {t["id"]: t for t in json.loads((ROOT / "backend/content/targets.json").read_text())["targets"]}
    frames_audit = json.loads((AUDIT / "frames.json").read_text())["frames"]
    t = targets[case["target_id"]]
    g = grid_wcs(t["query_center"]["ra_deg"], t["query_center"]["dec_deg"])
    yy, xx = np.mgrid[:GRID_PX, :GRID_PX]
    world = g.pixel_to_world(xx, yy)

    reps = []
    for f in case["frames"]:
        a = next(r for r in frames_audit if r["observation_id"] == f["observation_id"]
                 and r["detector"] == f["detector"] and r["target_id"] == case["target_id"])
        with fits.open(DATA / a["file"]) as h:
            img = h["IMAGE"].data.astype(float) - h["ZODI"].data
            w = WCS(h["IMAGE"].header)
        px, py = w.world_to_pixel(world)
        rep = map_coordinates(img, [py, px], order=1, cval=np.nan, mode="constant")
        mx, my = g.world_to_pixel_values(a["pred_ra_deg"], a["pred_dec_deg"])
        reps.append((f, a, rep, float(mx), float(my)))

    f0 = reps[0][2]
    bg = np.nanmedian(f0)
    mad = 1.4826 * np.nanmedian(np.abs(f0 - bg))
    peaks = (f0 == maximum_filter(np.nan_to_num(f0, nan=-1e9), size=7)) & (f0 > bg + 25 * mad)
    mx0, my0 = reps[0][3], reps[0][4]
    controls = [(float(x), float(y)) for y, x in zip(*np.nonzero(peaks))
                if np.hypot(x - mx0, y - my0) > 10 and 5 < x < GRID_PX - 5 and 5 < y < GRID_PX - 5]
    ref = [centroid(f0, x, y) for x, y in controls]

    rows = []
    for f, a, rep, mx, my in reps:
        shifts = np.array([np.subtract(centroid(rep, *c), c) for c in ref])
        rows.append({
            "ref": f["ref"],
            "frame_key": f["frame_key"],
            "observed_at_utc": a["observed_at_utc"],
            "wavelength_um": a["wavelength_um"],
            "control_median_shift_px": [round(float(v), 3) for v in np.median(shifts, 0)],
            "control_shift_std_px": [round(float(v), 3) for v in np.std(shifts, 0)],
            "marker_grid_px": [round(mx, 3), round(my, 3)],
            "marker_offset_from_first_arcsec": [round((mx - mx0) * GRID_SCALE_ARCSEC, 2),
                                                round((my - my0) * GRID_SCALE_ARCSEC, 2)],
            "nonfinite_pixels_within_2px_of_marker": int(np.isnan(rep[int(my) - 2:int(my) + 3, int(mx) - 2:int(mx) + 3]).sum()),
        })
    out = {
        "case_id": case_id,
        "grid": {"size_px": GRID_PX, "scale_arcsec": GRID_SCALE_ARCSEC, "orientation": "north up, east left",
                 "center": [t["query_center"]["ra_deg"], t["query_center"]["dec_deg"]],
                 "resampling": "bilinear on IMAGE minus ZODI (inspection only)"},
        "n_control_stars": len(controls),
        "frames": rows,
        "interpretation_limit": "Checks display geometry only. Not a proper-motion measurement.",
    }
    AUDIT.mkdir(exist_ok=True)
    (AUDIT / f"registration_{case_id}.json").write_text(json.dumps(out, indent=1))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, len(reps), figsize=(4 * len(reps), 4.4))
        for axi, (f, a, rep, mx, my) in zip(np.atleast_1d(ax), reps):
            axi.imshow(rep, origin="lower", cmap="gray", vmin=bg - 2 * mad, vmax=bg + 40 * mad)
            axi.plot(mx, my, "+", color="r", ms=10)
            axi.axhline(my0, color="c", lw=0.6)
            axi.set_title(f"{f['ref']} {a['observed_at_utc'][:10]} {a['wavelength_um']:.3f} um", fontsize=9)
        plt.tight_layout()
        plt.savefig(AUDIT / f"registration_{case_id}.png", dpi=80)
    except ImportError:
        pass
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "moving_neighbor"))
