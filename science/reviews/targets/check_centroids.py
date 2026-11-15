"""Empirical control for the catalog-prediction marker (worker 11).

For every shipped frame of the unsaturated presets, centroid the target in the ORIGINAL
native SPHEREx image near its catalog-predicted position and compare. The header WCS is
corrected per frame by the median native offset of Gaia DR3 field stars (same cached
Gaia lists and the same centroid routine as science/reviews/acceptance, imported, not
copied). Offsets are reported as (east, north) on the sky in display px (1.40625"/px).

This is a coarse consistency check, not astrometry: 6.1" native pixels, a 5x5 first-moment
centroid on an undersampled PSF (pixel-phase bias), blends, and the IR photocentre of
binaries (eps Ind Ba+Bb, RW Aur A+B) all limit it. Use medians over many frames only.

Usage (repository root, astropy venv):
  python science/reviews/targets/check_centroids.py --data-root "/path/to/research/build_data"
Writes science/reviews/targets/centroids.json. Reads FITS read-only.
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import io
import json
import math
import os
import statistics as st

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "acc", os.path.join(ROOT, "science/reviews/acceptance/check_acceptance.py"))
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)
PX = 1.40625


def en_offset(ra, dec, ra0, dec0):
    e = (ra - ra0) * math.cos(math.radians(dec0)) * 3600
    return e, (dec - dec0) * 3600


def mad_sigma(v):
    m = st.median(v)
    return 1.4826 * st.median([abs(x - m) for x in v])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--presets", default="epsilon_indi_b,wise_0855,rw_aurigae,barnards_star,r_draconis")
    a = ap.parse_args()
    out = {}
    for tid in a.presets.split(","):
        rows = []
        for p in sorted(glob.glob(os.path.join(ROOT, f"backend/content/presets/{tid}/frames/*.json"))):
            if p.endswith("frames.json"):
                continue
            r = json.load(open(p))
            if not r["quality"]["covered"]:
                continue
            raw = os.path.join(a.data_root, "raw", tid, os.path.basename(r["provenance"]["original_url"]))
            with open(raw, "rb") as f:
                hdul = fits.open(io.BytesIO(f.read()))
            ih = hdul["IMAGE"].header
            img = hdul["IMAGE"].data.astype(float)
            cel = WCS(ih, fobj=hdul)
            mjd = float(ih["MJD-AVG"])
            sp = r["sampled_position"]
            x, y = (float(v) for v in cel.all_world2pix([[sp["ra_deg"], sp["dec_deg"]]], 0)[0])
            c = acc.native_centroid(img, x, y)
            # Gaia field stars -> per-frame WCS offset (east, north arcsec, centroid minus Gaia)
            g_en = []
            for s in acc.load_gaia(tid):
                gra, gdec = acc.gaia_at(s, mjd)
                if math.hypot(*en_offset(gra, gdec, sp["ra_deg"], sp["dec_deg"])) < 40:
                    continue
                gx, gy = (float(v) for v in cel.all_world2pix([[gra, gdec]], 0)[0])
                nc = acc.native_centroid(img, gx, gy)
                if nc is None or math.hypot(nc[0] - gx, nc[1] - gy) >= 1.0:
                    continue
                cra, cdec = (float(v) for v in cel.all_pix2world([[nc[0], nc[1]]], 0)[0])
                g_en.append(en_offset(cra, cdec, gra, gdec))
            row = {"frame_key": r["frame_key"], "status": r["quality"]["status"],
                   "wavelength_um": r["wavelength_um"], "n_gaia": len(g_en), "target_centroid": c is not None}
            if c is not None and math.hypot(c[0] - x, c[1] - y) < 1.5:
                cra, cdec = (float(v) for v in cel.all_pix2world([[c[0], c[1]]], 0)[0])
                e, n = en_offset(cra, cdec, sp["ra_deg"], sp["dec_deg"])
                row["raw_offset_en_display_px"] = [e / PX, n / PX]
                row["snr_peak_mad"] = c[2]
                if len(g_en) >= 2:
                    ge, gn = st.median([v[0] for v in g_en]), st.median([v[1] for v in g_en])
                    row["gaia_corrected_offset_en_display_px"] = [(e - ge) / PX, (n - gn) / PX]
            rows.append(row)
        corr = [r_["gaia_corrected_offset_en_display_px"] for r_ in rows if "gaia_corrected_offset_en_display_px" in r_]
        rawo = [r_["raw_offset_en_display_px"] for r_ in rows if "raw_offset_en_display_px" in r_]
        summ = {"n_covered": len(rows), "n_target_centroided": len(rawo), "n_gaia_corrected": len(corr)}
        for k, v in (("raw", rawo), ("gaia_corrected", corr)):
            if len(v) >= 3:
                es, ns = [q[0] for q in v], [q[1] for q in v]
                summ[k] = {"median_east_px": st.median(es), "median_north_px": st.median(ns),
                           "median_total_px": math.hypot(st.median(es), st.median(ns)),
                           "scatter_east_px": mad_sigma(es), "scatter_north_px": mad_sigma(ns),
                           "stderr_of_median_total_px": 1.2533 * math.hypot(mad_sigma(es), mad_sigma(ns)) / math.sqrt(len(v))}
        out[tid] = {"summary": summ, "frames": rows}
        print(tid, json.dumps(summ, indent=1))
    json.dump(out, open(os.path.join(HERE, "centroids.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
