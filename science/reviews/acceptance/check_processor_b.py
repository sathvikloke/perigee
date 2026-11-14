"""Short independent check of processor B's six case frames (read from its git branch).

Same controls as check_acceptance.py, adapted to B's record schema and its
bilinear resampling + background offset. Reads B's products with `git show`
so no checkout of the B branch is needed.

Usage (repository root):
    .venv/bin/python science/reviews/acceptance/check_processor_b.py \
        --data-root "/path/to/research/build_data" --ref origin/codex/parallel-06-processor-b
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_acceptance as ca  # noqa: E402

warnings.simplefilter("ignore")

CASES = {
    "epsilon_indi_b": ["2026W18_1A_0516_1_D3", "2026W39_2A_0597_4_D3", "2026W18_1A_0516_1_D6"],
    "barnards_star": ["2025W35_1A_0008_1_D3", "2026W12_1A_0610_2_D3", "2026W34_1A_0431_1_D3"],
}


def show(ref, path, binary=False):
    out = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, check=True).stdout
    return out if binary else out.decode()


def bilinear_finite(img, good, x, y):
    ny, nx = img.shape
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    tx, ty = x - x0, y - y0
    acc = np.zeros(x.shape)
    wsum = np.zeros(x.shape)
    for dx, dy, w in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)), (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        xi, yi = x0 + dx, y0 + dy
        ok = (xi >= 0) & (xi < nx) & (yi >= 0) & (yi < ny)
        xi_c, yi_c = np.clip(xi, 0, nx - 1), np.clip(yi, 0, ny - 1)
        ok &= good[yi_c, xi_c]
        acc += np.where(ok, w * np.nan_to_num(img[yi_c, xi_c]), 0)
        wsum += np.where(ok, w, 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return acc / wsum, wsum > 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--ref", default="origin/codex/parallel-06-processor-b")
    ap.add_argument("--science-ref", default="origin/codex/sathvik-science")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results_processor_b.json"))
    a = ap.parse_args(argv)
    data = Path(a.data_root)
    manifest = json.loads((data / "manifest.json").read_text())
    targets = {t["id"]: t for t in manifest["targets"]}
    mby = {f"{r['obs_id']}_D{r['detector']}": r for r in manifest["files"] if r.get("status") == "downloaded"}
    sha_commit = subprocess.run(["git", "rev-parse", a.ref], capture_output=True, text=True).stdout.strip()
    cases = {c: json.loads(ca.git_show(a.science_ref, f"backend/content/cases/{c}.json")) for c in ("fair_comparison", "moving_neighbor")}
    case_frames = {f["frame_key"]: f for c in cases.values() for f in c["frames"]}
    rows = []
    for preset, keys in CASES.items():
        recs = {k: json.loads(show(a.ref, f"backend/content/presets/{preset}/frames/{k}.json")) for k in keys}
        regs = [json.dumps({kk: r["registration"][kk] for kk in ("center_ra_deg", "center_dec_deg", "fov_arcmin", "width", "height", "orientation", "display_wcs")}, sort_keys=True) for r in recs.values()]
        grid_same = len(set(regs)) == 1
        for k in keys:
            rec = recs[k]
            mrec = mby[k]
            raw = (data / mrec["file"]).read_bytes()
            h = fits.open(io.BytesIO(raw))
            ih = h["IMAGE"].header
            img = h["IMAGE"].data.astype(float)
            var = h["VARIANCE"].data.astype(float)
            flg = h["FLAGS"].data.astype(np.int64)
            ny, nx = img.shape
            cel = WCS(ih, fobj=h)
            reg = rec["registration"]
            ra0, dec0, fov, size = reg["center_ra_deg"], reg["center_dec_deg"], reg["fov_arcmin"], reg["width"]
            mjd = float(ih["MJD-AVG"])
            pra, pdec, _, _ = ca.predict(targets[preset], mjd)
            x, y = (float(v) for v in cel.all_world2pix([[pra, pdec]], 0)[0])
            mx, my = ca.sky_to_display(pra, pdec, ra0, dec0, fov, size)
            wa, ba = ca.wave_astropy(ih, h, x, y)
            good = np.isfinite(img) & np.isfinite(var) & (var > 0)
            yy, xx = np.mgrid[0:ny, 0:nx]
            ap_ = (xx - x) ** 2 + (yy - y) ** 2 <= ca.APERTURE_R ** 2
            names = {int(kk[4:]): h["FLAGS"].header[kk].strip() for kk in h["FLAGS"].header if kk.startswith("MSKN")}
            adv_bits = sum(1 << b for b, n in names.items() if n not in ca.INFORMATIONAL)
            adverse = ap_ & (((flg & adv_bits) != 0) | ~good)
            st = "flagged" if adverse.sum() else "clear"
            q = rec["quality"]
            # PNG reconstruction with B's stated method (bilinear over finite neighbours, minus offset)
            png = np.asarray(Image.open(io.BytesIO(show(a.ref, f"backend/content/presets/{preset}/frames/{k}.png", binary=True))))
            gray, alpha = png[..., 0].astype(int), png[..., 1].astype(int)
            sra, sdec = ca.display_centers_to_sky(ra0, dec0, fov, size)
            px, py = cel.all_world2pix(sra.ravel(), sdec.ravel(), 0, quiet=True)
            v, ok = bilinear_finite(img, good, px.reshape(size, size), py.reshape(size, size))
            ds = rec["display_scale"]
            exp = np.zeros((size, size), int)
            exp[ok] = ca.stretch(v[ok] - ds["background_offset"], ds["lo"], ds["hi"], 1.0 / ds["asinh_softening"])
            both = (alpha == 255) & ok
            d = np.abs(gray - exp)[both]
            # Gaia stars in the PNG
            offs = []
            for s in ca.load_gaia(preset):
                gra, gdec = ca.gaia_at(s, mjd)
                if math.hypot((gra - pra) * math.cos(math.radians(pdec)), gdec - pdec) * 3600 < 40:
                    continue
                gx, gy = (float(t) for t in cel.all_world2pix([[gra, gdec]], 0)[0])
                nc = ca.native_centroid(img, gx, gy)
                if nc is None or math.hypot(nc[0] - gx, nc[1] - gy) > 1:
                    continue
                dxp, dyp = ca.sky_to_display(gra, gdec, ra0, dec0, fov, size)
                pc = ca.png_centroid(gray, alpha, dxp, dyp)
                if pc:
                    offs.append(math.hypot(pc[0] - dxp, pc[1] - dyp))
            cf = case_frames[k]
            row = {
                "frame_key": k,
                "registration": (abs(rec["marker"]["x"] - mx) < 0.05 and abs(rec["marker"]["y"] - my) < 0.05 and grid_same
                                 and (not offs or float(np.median(offs)) < 2.5)),
                "marker_minus_independent_px": math.hypot(rec["marker"]["x"] - mx, rec["marker"]["y"] - my),
                "gaia_png_median_offset_display_px": float(np.median(offs)) if offs else None, "gaia_n": len(offs),
                "grid_identical": grid_same,
                "wavelength": abs(rec["wavelength_um"] - wa) < 1e-6 and abs(rec["bandwidth_um"] - ba) < 1e-5,
                "wavelength_record_minus_independent": rec["wavelength_um"] - wa,
                "time": rec["observed_at_utc"] == ih["DATE-AVG"] and rec["mjd"] == mjd,
                "flags": (q["status"] == st and q["adverse_aperture_pixels"] == int(adverse.sum())
                          and q["valid_aperture_pixels"] == int((ap_ & ~adverse).sum())
                          and q["nonfinite_aperture_pixels"] == int((ap_ & ~good).sum())),
                "coverage": q["covered"] is True and 0 <= x <= nx - 1 and 0 <= y <= ny - 1,
                "stretch_recon_within_1_fraction": float((d <= 1).mean()) if d.size else None,
                "stretch_recon_within_2_fraction": float((d <= 2).mean()) if d.size else None,
                "alpha_match_fraction": float((alpha == np.where(ok, 255, 0)).mean()),
                "stretch_mode": ds["mode"],
                "provenance": (hashlib.sha256(raw).hexdigest() == rec["provenance"]["sha256"] == mrec["sha256"]
                               and rec["source_url"] == mrec["archive_url"] and rec["provenance"]["cutout_url"] == mrec["source_url"]
                               and rec["marker"]["kind"] == "catalog_prediction"),
                "case_match": (abs(rec["wavelength_um"] - cf["wavelength_um"]) <= 1e-4 and rec["observed_at_utc"] == cf["observed_at_utc"]
                               and rec["mjd"] == cf["mjd"] and q["status"] == cf["expected_quality_status"]
                               and rec["provenance"]["sha256"] == cf["sha256_of_retained_cutout"]),
            }
            row["stretch"] = bool(row["stretch_recon_within_2_fraction"] and row["stretch_recon_within_2_fraction"] > 0.99)
            rows.append(row)
    out = {"processor_b_commit": sha_commit, "rows": rows}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
