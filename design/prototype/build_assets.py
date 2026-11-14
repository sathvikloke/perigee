"""Render real retained FITS samples for the UI reference; not the app processor.

Run with the science checkout as argv[1]. Uses the independently checked fixed
grid from science/check_registration.py. Never edits or downloads source data.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates
from PIL import Image

root = Path(sys.argv[1])
out = Path(__file__).parent / "assets"
out.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("registration", root / "science/check_registration.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
case = json.loads((root / "backend/content/cases/fair_comparison.json").read_text())
audit = json.loads((root / "science/audit/frames.json").read_text())["frames"]
target = next(t for t in json.loads((root / "backend/content/targets.json").read_text())["targets"] if t["id"] == case["target_id"])
grid = module.grid_wcs(target["query_center"]["ra_deg"], target["query_center"]["dec_deg"])
yy, xx = np.mgrid[:module.GRID_PX, :module.GRID_PX]
world = grid.pixel_to_world(xx, yy)
arrays = []
for frame in case["frames"]:
    a = next(r for r in audit if r["observation_id"] == frame["observation_id"] and r["detector"] == frame["detector"] and r["target_id"] == case["target_id"])
    path = root / "research/build_data" / a["file"]
    with fits.open(path) as hdul:
        data = hdul["IMAGE"].data.astype(float) - hdul["ZODI"].data
        wcs = WCS(hdul["IMAGE"].header)
    px, py = wcs.world_to_pixel(world)
    arrays.append(map_coordinates(data, [py, px], order=1, cval=np.nan, mode="constant"))
    mx, my = grid.world_to_pixel_values(a["pred_ra_deg"], a["pred_dec_deg"])
    frame["marker_percent"] = [(float(mx) + .5) / 72 * 100, (71.5 - float(my)) / 72 * 100]
    frame["retained_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    frame["preview_asset"] = f"assets/frame-{frame['ref'].lower()}.png"

bg = float(np.nanmedian(arrays[0]))
mad = float(1.4826 * np.nanmedian(np.abs(arrays[0] - bg)))
lo, hi = bg - 2 * mad, bg + 40 * mad
for frame, data in zip(case["frames"], arrays):
    gray = (np.clip(np.nan_to_num((data - lo) / (hi - lo), nan=0), 0, 1) * 255).astype(np.uint8)
    rgba = np.dstack([gray, gray, gray, np.isfinite(data).astype(np.uint8) * 255])
    Image.fromarray(np.flipud(rgba)).save(out / f"frame-{frame['ref'].lower()}.png")
manifest = {"case_id": case["case_id"], "target": target["query_center"], "frames": case["frames"], "processing": {"method": "Bilinear resampling of IMAGE minus ZODI; inspection only", "grid_px": 72, "scale_arcsec_per_pixel": 5, "orientation": "North up, east left", "stretch": "Shared linear stretch across A, B and C", "lower": lo, "upper": hi, "transparent_pixels": "Outside retained cutout coverage; not zero signal", "marker": "Catalog prediction; not a measured detection"}}
(out / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Rendered {len(arrays)} real FITS previews and provenance in {out}")
