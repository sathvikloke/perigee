"""Numerically compare processor A and B products for the same frames.

Inputs are two directories holding <frame_key>.{json,png,flags.png}. Writes a
JSON report and a small side-by-side PNG (A | B | |A-B|, intensity over
flag overlay) to backend/tests/data/artifacts/.

Usage:
  .venv/bin/python tools/ingest/compare_candidates.py --a DIR_A --b DIR_B --key FRAME_KEY [--key ...]
"""

from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from common import DEFAULT_BUILD_DATA, REPO

from backend.data.process import read_source

ART = REPO / "backend" / "tests" / "data" / "artifacts"


def _load(d: Path, key: str):
    rec = json.loads((d / f"{key}.json").read_text())
    img = np.array(Image.open(d / f"{key}.png").convert("LA"))
    fl = np.array(Image.open(d / f"{key}.flags.png").convert("RGBA")) if (d / f"{key}.flags.png").exists() else None
    return rec, img, fl, (d / f"{key}.png").stat().st_size, ((d / f"{key}.flags.png").stat().st_size if fl is not None else 0)


def _categories(fl: np.ndarray, legend_adverse, legend_nonfinite) -> np.ndarray:
    """0 none, 1 adverse, 2 non-finite."""
    c = np.zeros(fl.shape[:2], dtype=np.int8)
    rgb = fl[..., :3].astype(int)
    c[(fl[..., 3] > 0) & np.all(rgb == np.array(legend_adverse[:3]), axis=-1)] = 1
    c[(fl[..., 3] > 0) & np.all(rgb == np.array(legend_nonfinite[:3]), axis=-1)] = 2
    return c


def _best_shift(a: np.ndarray, b: np.ndarray, ok: np.ndarray, r: int = 3):
    best = None
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            bs = np.roll(np.roll(b, dy, 0), dx, 1)
            oks = ok & np.roll(np.roll(ok, dy, 0), dx, 1)
            oks[:r] = oks[-r:] = False
            oks[:, :r] = oks[:, -r:] = False
            av, bv = a[oks].astype(float), bs[oks].astype(float)
            cc = np.corrcoef(av, bv)[0, 1]
            if best is None or cc > best[0]:
                best = (cc, dx, dy)
    return {"corr": round(best[0], 4), "dx": best[1], "dy": best[2]}


def local_native_scale(fits_path: str, x: float, y: float) -> dict:
    """sqrt|det J| of the full TAN-SIP mapping at (x, y), arcsec; vs linear-only CD."""
    src = read_source(Path(fits_path).read_bytes())
    w = src.celestial
    h = 0.5
    pts = np.array([[x - h, y], [x + h, y], [x, y - h], [x, y + h]])
    ra, dec = w.all_pix2world(pts[:, 0], pts[:, 1], 0)
    c = math.cos(math.radians(dec.mean()))
    j = np.array([[(ra[1] - ra[0]) * c, (ra[3] - ra[2]) * c], [dec[1] - dec[0], dec[3] - dec[2]]]) * 3600.0
    lin = w.pixel_scale_matrix * 3600.0
    return {
        "local_sip_jacobian_arcsec": round(math.sqrt(abs(np.linalg.det(j))), 5),
        "linear_cd_only_arcsec": round(math.sqrt(abs(np.linalg.det(lin))), 5),
        "header_OMEGA_MEDIAN_sqrt_arcsec": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--key", action="append", required=True)
    ap.add_argument("--build-data", default=DEFAULT_BUILD_DATA)
    ap.add_argument("--report", default=str(ART / "compare_a_b.json"))
    ap.add_argument("--image", default=str(ART / "compare_a_b.png"))
    args = ap.parse_args()
    da, db = Path(args.a), Path(args.b)
    rows, tiles = [], []
    for key in args.key:
        ra, ia, fa, sa, sfa = _load(da, key)
        rb, ib, fb, sb, sfb = _load(db, key)
        oka, okb = ia[..., 1] > 0, ib[..., 1] > 0
        both = oka & okb
        cat_a = _categories(fa, ra["flag_image"]["legend"]["adverse_flag"], ra["flag_image"]["legend"]["non_finite"])
        lb = {e["meaning"].split(" ")[0]: e["rgba"] for e in rb["flag_image"]["legend"]}
        cat_b = _categories(fb, lb["any"], lb["non-finite"])
        conf = {f"A{i}_B{j}": int(((cat_a == i) & (cat_b == j)).sum()) for i in range(3) for j in range(3)}
        obs, det = key.rsplit("_D", 1)
        (fits_path,) = glob.glob(str(Path(args.build_data) / "raw" / "*" / f"*_{obs}D{det}_*.fits"))
        p = rb["registration"]["checked_position_source_pixel"]
        hdr_scale = None
        try:
            from astropy.io import fits as _f

            om = _f.getheader(fits_path, "IMAGE").get("OMEGA_MEDIAN")
            hdr_scale = round(math.sqrt(om), 5) if om else None
        except Exception:
            pass
        ns = local_native_scale(fits_path, p["x"], p["y"])
        ns["header_OMEGA_MEDIAN_sqrt_arcsec"] = hdr_scale
        row = {
            "frame_key": key,
            "registration": {
                "center": [ra["registration"]["center_ra_deg"], ra["registration"]["center_dec_deg"], rb["registration"]["center_ra_deg"], rb["registration"]["center_dec_deg"]],
                "scale_arcsec_per_display_px": [ra["registration"].get("scale_arcsec_per_px"), rb["registration"].get("scale_arcsec_per_pixel")],
                "native_scale_arcsec": [ra["registration"].get("native_scale_arcsec_per_px"), rb["registration"].get("native_scale_arcsec")],
                "native_scale_check": ns,
                "orientation": [ra["registration"]["orientation"], rb["registration"]["orientation"]],
                "intensity_method": [ra["registration"]["method"], "bilinear (finite neighbours)"],
                "target_native_px": [[ra["sampled_position"]["native_x"], ra["sampled_position"]["native_y"]], [p["x"], p["y"]]],
                "marker_display_px": [[ra["marker"]["x"], ra["marker"]["y"]], [rb["marker"]["x"], rb["marker"]["y"]]] if ra.get("marker") and rb.get("marker") else None,
                "displayable_mask": {
                    "A_only": int((oka & ~okb).sum()),
                    "B_only": int((okb & ~oka).sum()),
                    "both": int(both.sum()),
                },
                "intensity_best_shift": _best_shift(ia[..., 0], ib[..., 0], both),
            },
            "spectral": {
                "wavelength_um": [ra["wavelength_um"], rb["wavelength_um"]],
                "bandwidth_um": [ra["bandwidth_um"], rb["bandwidth_um"]],
                "abs_diff_wavelength_um": abs(ra["wavelength_um"] - rb["wavelength_um"]) if ra["wavelength_um"] is not None and rb["wavelength_um"] is not None else None,
            },
            "time": [ra["observed_at_utc"], rb["observed_at_utc"]],
            "quality": {
                k: [ra["quality"].get(ka), rb["quality"].get(kb)]
                for k, ka, kb in [
                    ("status", "status", "status"),
                    ("covered", "covered", "covered"),
                    ("aperture_pixels", "screened_pixels", "aperture_pixels"),
                    ("valid", "valid_aperture_pixels", "valid_aperture_pixels"),
                    ("adverse", "adverse_aperture_pixels", "adverse_aperture_pixels"),
                    ("nonfinite", "nonfinite_aperture_pixels", "nonfinite_aperture_pixels"),
                    ("flag_names", "flag_names", "flag_names"),
                    ("flag_counts", "flag_counts", "flag_pixel_counts"),
                ]
            },
            "flag_overlay_confusion_0none_1adverse_2nonfinite": conf,
            "display_scale": {
                "A": {k: ra["display_scale"].get(k) for k in ("mode", "method", "asinh_softening", "low", "high", "background_subtraction")},
                "B": {k: rb["display_scale"].get(k) for k in ("mode", "method", "asinh_softening", "lo", "hi", "background_offset")},
            },
            "size_bytes": {"A_png": sa, "B_png": sb, "A_flags_png": sfa, "B_flags_png": sfb,
                           "A_png_data_url_chars": 22 + 4 * math.ceil(sa / 3), "B_png_data_url_chars": 22 + 4 * math.ceil(sb / 3)},
        }
        rows.append(row)

        # Side-by-side tile: A | B | |A-B| (grey), with flag overlays composited.
        def comp(img, fl):
            base = Image.fromarray(np.dstack([img[..., 0]] * 3 + [np.full(img.shape[:2], 255, np.uint8)]).astype(np.uint8), "RGBA")
            base.putalpha(255)
            bg = Image.new("RGBA", base.size, (40, 60, 90, 255))  # off-image / non-finite shows as blue-grey
            bg.paste(base, mask=Image.fromarray(img[..., 1]))
            return Image.alpha_composite(bg, Image.fromarray(fl, "RGBA"))

        diff = np.where(both, np.abs(ia[..., 0].astype(int) - ib[..., 0].astype(int)), 0).astype(np.uint8)
        tile = Image.new("RGBA", (256 * 3 + 8, 256 + 14), (255, 255, 255, 255))
        tile.paste(comp(ia, fa), (0, 14))
        tile.paste(comp(ib, fb), (260, 14))
        tile.paste(Image.fromarray(diff).convert("RGBA"), (520, 14))
        d = ImageDraw.Draw(tile)
        d.text((2, 1), f"A {key}", fill=(0, 0, 0, 255))
        d.text((262, 1), "B", fill=(0, 0, 0, 255))
        d.text((522, 1), "|A-B| grey (stretches differ)", fill=(0, 0, 0, 255))
        for ox, rec in ((0, ra), (260, rb)):
            if rec.get("marker"):
                mx, my = ox + rec["marker"]["x"], 14 + rec["marker"]["y"]
                d.ellipse([mx - 9, my - 9, mx + 9, my + 9], outline=(0, 220, 255, 255))
        tiles.append(tile)

    sheet = Image.new("RGBA", (tiles[0].width, sum(t.height for t in tiles)), (255, 255, 255, 255))
    y = 0
    for t in tiles:
        sheet.paste(t, (0, y))
        y += t.height
    # The committed inspection sheet is for eyes, not numbers: JPEG keeps it small.
    if args.image.lower().endswith((".jpg", ".jpeg")):
        sheet.convert("RGB").save(args.image, quality=85, optimize=True)
    else:
        sheet.convert("RGB").save(args.image, optimize=True)
    Path(args.report).write_text(json.dumps(rows, indent=1) + "\n")
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
