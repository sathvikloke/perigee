"""Independent scientific check of the retained SPHEREx cutouts.

Owner: Sathvik (science/**). This is a verification tool, not the app's
processing pipeline (that is Sagar's backend/data/**). It re-derives, from the
original FITS bytes and SIMBAD astrometry, the facts the investigations rely on:

* observation time (MJD-AVG / DATE-AVG from the IMAGE header),
* the catalog-propagated target position at that time (astropy space motion,
  no annual parallax),
* the sampled wavelength/bandwidth at that position (spectral WCS key "W"),
* coverage and a conservative flag screen in a small aperture.

It then compares its results with the earlier audit values in
research/build_data/manifest.json so disagreements are visible.

The flag screen is a screening check only. Passing it is NOT a detection,
calibrated photometry or astrometric validation.

Usage (from the repository root):
    .research-venv/bin/python science/check_frames.py
Writes science/audit/frames.json (small, no image data).
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS, FITSFixedWarning

warnings.simplefilter("ignore", FITSFixedWarning)
warnings.simplefilter("ignore", AstropyWarning)
from astropy import log as _astropy_log  # noqa: E402

_astropy_log.setLevel("WARNING")  # silence the INFO note about SIP on the spectral WCS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research" / "build_data"
OUT = Path(__file__).resolve().parent / "audit" / "frames.json"

APERTURE_RADIUS_PX = 2.5  # ~15 arcsec at ~6.15"/px
# Bits treated as informational rather than adverse.
INFORMATIONAL = {"SOURCE", "FULLSAMPLE"}
CHECK_VERSION = "science-check-1"


def target_coord(t: dict) -> SkyCoord:
    return SkyCoord(
        ra=t["ra_j2000_deg"] * u.deg,
        dec=t["dec_j2000_deg"] * u.deg,
        pm_ra_cosdec=(t["pm_ra_cosdec_masyr"] or 0.0) * u.mas / u.yr,
        pm_dec=(t["pm_dec_masyr"] or 0.0) * u.mas / u.yr,
        distance=(1000.0 / t["parallax_mas"]) * u.pc if t.get("parallax_mas") else None,
        radial_velocity=(t.get("radial_velocity_kms") or 0.0) * u.km / u.s,
        obstime=Time(t["reference_epoch_jyear"], format="jyear"),
        frame="icrs",
    )


def flag_names(header: fits.Header) -> dict[int, str]:
    out = {}
    for key in header:
        if key.startswith("MSKN"):
            out[int(key[4:])] = header[key]
    return out


def check_file(rec: dict, tcoord: SkyCoord) -> dict:
    path = DATA / rec["file"]
    with fits.open(path) as h:
        ih = h["IMAGE"].header
        img = h["IMAGE"].data.astype(float)
        var = h["VARIANCE"].data.astype(float)
        flg = h["FLAGS"].data.astype(np.int64)
        names = flag_names(h["FLAGS"].header)
        mjd_avg = float(ih["MJD-AVG"])
        mjd_obs = float(ih["MJD-OBS"])
        date_avg = ih["DATE-AVG"]
        obsid = ih.get("OBSID")
        detector = ih.get("DETECTOR")
        cel = WCS(ih)
        pos = tcoord.apply_space_motion(new_obstime=Time(mjd_avg, format="mjd"))
        x, y = cel.world_to_pixel(SkyCoord(pos.ra, pos.dec, frame="icrs"))
        x, y = float(x), float(y)
        ny, nx = img.shape
        inside = (0 <= x <= nx - 1) and (0 <= y <= ny - 1)
        wl = bw = None
        if inside:
            try:
                sw = WCS(header=ih, fobj=h, key="W")
                sw.sip = None
                w = sw.pixel_to_world_values(x, y)
                wl, bw = float(w[0]), float(w[1])
            except Exception as exc:  # keep unknown, never invent
                wl = bw = None
                rec.setdefault("_notes", []).append(f"wavelength unavailable: {exc}")
        yy, xx = np.mgrid[0:ny, 0:nx]
        ap = (xx - x) ** 2 + (yy - y) ** 2 <= APERTURE_RADIUS_PX**2
        n_ap = int(ap.sum())
        finite = np.isfinite(img) & np.isfinite(var) & (var > 0)
        n_finite = int((ap & finite).sum())
        bits_in_ap: dict[str, int] = {}
        adverse = np.zeros_like(ap)
        for bit, name in names.items():
            hit = ap & ((flg >> bit) & 1).astype(bool)
            c = int(hit.sum())
            if c:
                bits_in_ap[name] = c
            if name not in INFORMATIONAL:
                adverse |= hit
        n_adverse = int((adverse | (ap & ~finite)).sum())
        # Coverage is geometric: is the predicted position on this cutout?
        # Non-finite pixels at a covered position (e.g. saturated bright stars)
        # are a quality problem, not missing coverage.
        if not inside or n_ap == 0:
            status = "not_covered"
        elif n_adverse > 0:
            status = "flagged"
        else:
            status = "clear"
        # pixel scale from celestial WCS
        scales = cel.celestial.proj_plane_pixel_scales()
        scale = float(np.mean([u.Quantity(s, u.deg).to_value(u.arcsec) for s in scales]))
    return {
        "target_id": rec["target_id"],
        "file": rec["file"],
        "collection": rec["collection"],
        "observation_id": obsid,
        "detector": detector,
        "observed_at_utc": date_avg,
        "mjd_avg": mjd_avg,
        "mjd_obs": mjd_obs,
        "source_url": rec.get("archive_url"),
        "cutout_url": rec.get("source_url"),
        "sha256": rec.get("sha256"),
        "pred_ra_deg": float(pos.ra.deg),
        "pred_dec_deg": float(pos.dec.deg),
        "x": x,
        "y": y,
        "inside": inside,
        "pixel_scale_arcsec": scale,
        "wavelength_um": wl,
        "bandwidth_um": bw,
        "aperture_pixels": n_ap,
        "finite_aperture_pixels": n_finite,
        "adverse_aperture_pixels": n_adverse,
        "flags_in_aperture": bits_in_ap,
        "status": status,
        "audit": {
            "wavelength_um": rec.get("wavelength_um"),
            "x": rec.get("x"),
            "y": rec.get("y"),
            "flagged_or_invalid_aperture_pixels": rec.get("flagged_or_invalid_aperture_pixels"),
            "aperture_pixels": rec.get("aperture_pixels"),
        },
    }


def main() -> int:
    manifest = json.loads((DATA / "manifest.json").read_text())
    targets = {t["id"]: t for t in manifest["targets"]}
    coords = {k: target_coord(t) for k, t in targets.items()}
    rows, problems = [], []
    for rec in manifest["files"]:
        if rec.get("status") != "downloaded":
            continue
        try:
            rows.append(check_file(rec, coords[rec["target_id"]]))
        except Exception as exc:
            problems.append({"file": rec["file"], "error": repr(exc)})
    rows.sort(key=lambda r: (r["target_id"], r["mjd_avg"], r["observation_id"] or "", r["detector"] or 0))

    # comparison with the earlier audit
    wl_diff = [abs(r["wavelength_um"] - r["audit"]["wavelength_um"]) for r in rows
               if r["wavelength_um"] is not None and r["audit"]["wavelength_um"] is not None]
    pos_diff = [np.hypot(r["x"] - r["audit"]["x"], r["y"] - r["audit"]["y"]) for r in rows
                if r["audit"]["x"] is not None]
    summary = {}
    for tid in targets:
        rs = [r for r in rows if r["target_id"] == tid]
        summary[tid] = {
            "frames": len(rs),
            "clear": sum(r["status"] == "clear" for r in rs),
            "flagged": sum(r["status"] == "flagged" for r in rs),
            "not_covered": sum(r["status"] == "not_covered" for r in rs),
            "first_utc": rs[0]["observed_at_utc"] if rs else None,
            "last_utc": rs[-1]["observed_at_utc"] if rs else None,
        }
    out = {
        "check_version": CHECK_VERSION,
        "aperture_radius_px": APERTURE_RADIUS_PX,
        "informational_bits": sorted(INFORMATIONAL),
        "method": "Target propagated from SIMBAD J2000 with astropy apply_space_motion to MJD-AVG "
                  "(no annual parallax, no binary orbit). Wavelength from spectral WCS key W at that pixel. "
                  "Status: not_covered if the predicted position is outside the cutout; flagged if any "
                  "non-informational flag bit or non-finite pixel lies in the aperture; else clear.",
        "limitations": [
            "A clear status is a screening result, not a detection, calibrated flux or astrometric validation.",
            "Annual parallax is not applied; for Barnard's Star, Eps Ind B and WISE 0855 it shifts the "
            "apparent position by up to ~0.55, 0.27 and 0.44 arcsec (<0.1 px).",
            "Eps Ind B is a binary brown dwarf (Ba/Bb) unresolved at ~6 arcsec pixels; orbital motion is ignored.",
        ],
        "comparison_with_earlier_audit": {
            "frames_compared": len(wl_diff),
            "max_wavelength_diff_um": max(wl_diff) if wl_diff else None,
            "max_position_diff_px": max(pos_diff) if pos_diff else None,
        },
        "summary": summary,
        "problems": problems,
        "frames": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("comparison_with_earlier_audit", "summary", "problems")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
