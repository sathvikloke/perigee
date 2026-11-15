"""Draft transfer exercise (B5): derive every number from shipped records and raw FITS.

Computational review, not a shipped case. Nothing under backend/ is written.

Frames (all shipped in backend/content/presets/wise_0855/frames/, all on the
same fixed grid as the WISE 0855 preset):

  P = 2025W45_2A_0278_1_D2   2025-11-07, D2
  Q = 2025W46_1A_0108_1_D2   2025-11-10, D2
  R = 2026W20_1A_0214_1_D2   2026-05-11, D2

What it does, per frame:
  * reads the shipped FrameRecord (dates, wavelength at the marker, bandwidth,
    quality, per-frame display_scale, marker, provenance);
  * finds the raw cutout in research/build_data/manifest.json by obs_id +
    detector, hashes the raw file, and checks record sha256 == manifest sha256 ==
    sha256(file);
  * re-runs processor A (backend/data/process.py) on the raw FITS with the same
    inputs tools/ingest uses, and checks that the record fields and the PNG bytes
    reproduce;
  * re-runs it again with one shared stretch for P+Q (only to show what the
    per-frame stretch does; not proposed as a product);
  * a census of bright compact spots (native local maxima drawn white by each
    frame's own stretch): adverse FLAGS names, detector pixel (WCS key A),
    single-pixel test, nearest cached Gaia DR3 star (G < 17,
    science/reviews/acceptance/gaia/wise_0855.csv) and whether the other frames
    show something at the same sky position;
  * the grey level each frame's stretch gives the same sky value;
  * the WISE 0855 catalog-predicted shift between frames, and where the cached
    Gaia DR3 neighbour 5756956644387831296 falls relative to the marker.

None of this is photometry, a detection test or a measured proper motion.
Raw values are a reviewer check (single flagged pixel vs star-shaped source),
not learner-facing brightness numbers.

Usage (repository root):
    .venv/bin/python science/reviews/transfer-exercise/check_transfer.py \
        --data-root "/path/to/research/build_data"

Writes results.json, answer_evidence.json (per-answer evidence for the N1 answer key) and
contact_sheet.png to --out (default: next to this file).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image, ImageDraw

warnings.simplefilter("ignore")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from backend.data.process import (  # noqa: E402
    FrameInput,
    display_limits_from_values,
    flag_bit_names,
    grid_wcs,
    process_frame,
    sky_to_display_px,
)
from tools.ingest.ingest import target_input  # noqa: E402

PRESET = "wise_0855"
FRAMES = [("P", "2025W45_2A_0278_1_D2"), ("Q", "2025W46_1A_0108_1_D2"), ("R", "2026W20_1A_0214_1_D2")]
NEIGHBOUR = "5756956644387831296"  # Gaia DR3, G = 16.3 (science/reviews/targets row 8)
INFORMATIONAL = {"SOURCE", "FULLSAMPLE"}

REC_DIR = REPO / "backend/content/presets" / PRESET / "frames"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gaia_at(row, jyear):
    dt = jyear - float(row["ref_epoch"])
    pmra, pmdec = float(row["pmra"] or 0.0), float(row["pmdec"] or 0.0)  # 2-parameter Gaia rows: no PM
    dec = float(row["dec"]) + pmdec * dt / 3.6e6
    ra = float(row["ra"]) + pmra * dt / 3.6e6 / math.cos(math.radians(float(row["dec"])))
    return ra, dec


def mjd_to_jyear(mjd: float) -> float:
    return 2000.0 + (mjd - 51544.5) / 365.25


def native_flags_at(hdul, ra, dec):
    """Adverse FLAGS names at the native pixel containing (ra, dec)."""
    ih = hdul["IMAGE"].header
    cel = WCS(ih, fobj=hdul).celestial
    x, y = cel.all_world2pix([[ra, dec]], 0)[0]
    ix, iy = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
    fl = np.asarray(hdul["FLAGS"].data).astype(np.int64)
    names = flag_bit_names(hdul["FLAGS"].header)
    ny, nx = fl.shape
    if not (0 <= ix < nx and 0 <= iy < ny):
        return None
    v = int(fl[iy, ix])
    return sorted(n for b, n in names.items() if v >> b & 1 and n not in INFORMATIONAL)


def full_grid(hdul, gw, size):
    """Display-oriented (row 0 = north) grid of native values, NaN where the
    processor would leave the pixel transparent; same sampling as process.py."""
    ih = hdul["IMAGE"].header
    cel = WCS(ih, fobj=hdul).celestial
    img = np.asarray(hdul["IMAGE"].data, dtype=np.float64)
    var = np.asarray(hdul["VARIANCE"].data, dtype=np.float64)
    finite = np.isfinite(img) & np.isfinite(var) & (var > 0)
    gy, gx = np.mgrid[0:size, 0:size]
    ra_g, dec_g = gw.wcs_pix2world(gx.ravel().astype(float), gy.ravel().astype(float), 0)
    nxp, nyp = cel.all_world2pix(ra_g, dec_g, 0, quiet=True)
    ix = np.floor(nxp + 0.5).astype(np.int64).reshape(size, size)
    iy = np.floor(nyp + 0.5).astype(np.int64).reshape(size, size)
    ny, nx = img.shape
    ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    vals = np.full((size, size), np.nan)
    vals[ok] = np.where(finite[iy[ok], ix[ok]], img[iy[ok], ix[ok]], np.nan)
    return np.flipud(vals)


CASE_REF = {"P": "A", "Q": "B", "R": "C"}  # exercise ref -> staged case ref

EXTERNAL_SOURCES = {
    "faherty2014": {"label": "Faherty et al. 2014, ApJL 793, L16 (arXiv:1408.4671)",
                    "url": "https://arxiv.org/abs/1408.4671",
                    "fact": "WISE 0855 J3 = 24.8 (+0.33/-0.53) mag at 2.6 sigma, equivalently J3 > 23.8 mag at 5 sigma (Vega)."},
    "schneider2016": {"label": "Schneider et al. 2016 (arXiv:1605.05618)",
                      "url": "https://arxiv.org/abs/1605.05618",
                      "fact": "HST F125W = 26.41 +/- 0.27 mag (Vega), a marginal (S/N ~4) detection."},
    "dore2014": {"label": "Dore et al. 2014, SPHEREx cosmology design paper (arXiv:1412.4872)",
                 "url": "https://arxiv.org/abs/1412.4872",
                 "fact": "All-sky point-source requirement of about 18.5 AB mag (5 sigma) per spectral element after the "
                         "full survey; a single exposure is shallower."},
    "targets_review": {"label": "science/reviews/targets/README.md row 8",
                       "url": "science/reviews/targets/README.md",
                       "fact": "Gaia DR3 5756956644387831296 (G 16.3, nearly static) lies 4.5-11.8 arcsec from the WISE 0855 "
                               "marker in the 34 shipped frames."},
}


N2 = "origin/claude/n2-controls@45ee56b science/reviews/overnight-controls/results/"
N2_CROSSCHECK = {
    "source": N2,
    "read_not_rederived": "Values below were read from the N2 control outputs on 2026-11-15 and are cited, not recomputed here.",
    "stretch_probe": {"file": N2 + "A_stretch_probes.csv",
                      "fact": "1.0 MJy/sr -> grey 156 (P) / 174 (Q) per-frame, 159 / 159 shared; observed PNG grey ranges agree."},
    "background_order_reverses": {"file": N2 + "results.json",
                                  "fact": "Shipped per-frame PNG median grey Q 20 vs P 16; shared stretch P 19 vs Q 16; "
                                          "physical median Q/P = 0.971."},
    "jump_pointing": {"file": N2 + "B_features.csv; " + N2 + "B_field_sources.csv",
                      "fact": "Detector pixel (1709,1364): sky jump 5.36 arcsec, 3.81 display px. Three strict-quality Gaia "
                              "field stars agree between P and Q to median 0.40 arcsec (max 0.76); their detector shift "
                              "(about -0.83, -0.28 native px) predicts 5.38 arcsec for a detector-fixed pixel. R's cutout does "
                              "not contain detector pixel (1709,1364)."},
    "p_only_dot": {"file": N2 + "B_features.csv",
                   "fact": "Detector pixel (1689,1364), two pixels 12.55 and 8.38 MJy/sr; same detector pixel in Q = 0.27 "
                           "MJy/sr, unflagged; R's cutout does not contain that detector pixel."},
    "pairs": {"file": N2 + "C_pairs.csv",
              "fact": "P-Q: delta lambda 0.0018 band widths (smaller band width), same detector, release, software and "
                      "rotation; differ in pipeline build, stretch, quality screen, pointing (0.87 native px). P-R: 184.8 d, "
                      "6.22 band widths, field rotated about 180 deg."},
}


def build_evidence(out):
    """Machine-readable evidence per answer. Every number is copied from `out`
    (results.json); the conclusion and limit strings are the authored
    interpretation, reviewed in README.md section 'Second review pass'."""
    fr = out["frames"]
    pq, pr = out["pairs"]["P-Q"], out["pairs"]["P-R"]
    det = out["detector_pixel_1709_1364"]
    nm = out["near_marker"]
    feats = out["flagged_features"]
    fdesc = out["flag_descriptions_from_FITS_header"]
    jump = [f for f in feats if f["detector_xy"] == [1709, 1364]]
    ponly = next(f for f in feats if f["frame"] == "P" and "HALO" in f["adverse_flags"])
    redge = next(f for f in feats if f["frame"] == "R" and f["adverse_flags"])
    steady = [f for f in feats if not f["adverse_flags"]]
    bg = out["frame_background"]
    sp, csp = out["stretch_probe"], out["case_stretch_probe"]
    i1 = sp["values_MJy_sr"].index(1.0)

    def frame_meta(r):
        f = fr[r]
        return {"ref": r, "case_ref": CASE_REF[r], "frame_key": f["frame_key"], "observation_id": f["observation_id"],
                "detector": f["detector"], "collection_id": f["collection_id"], "observed_at_utc": f["observed_at_utc"],
                "mjd": f["mjd"], "wavelength_um": f["wavelength_um"], "bandwidth_um": f["bandwidth_um"],
                "quality_status": f["quality_status"], "quality_flag_names": f["quality_flag_names"],
                "adverse_screened": [f["adverse_aperture_pixels"], f["screened_pixels"]],
                "display_scale_preset_frames": f["display_scale"], "pipeline_build": out["pipeline_builds"][r],
                "grid_id": f["grid_id"], "sha256": f["sha256"]["file"], "source_url": f["source_url"],
                "record": f"backend/content/presets/wise_0855/frames/{f['frame_key']}.json",
                "image": f"backend/content/presets/wise_0855/frames/{f['frame_key']}.png",
                "flag_image": f"backend/content/presets/wise_0855/frames/{f['frame_key']}.flags.png",
                "reproduced_by_processor_a": all(f["reproduced"].values()) and f["sha256"]["all_equal"]}

    def q(id_, value, unit, tol, path, note=""):
        return {"id": id_, "value": value, "unit": unit, "tolerance": tol, "results_path": path, "note": note}

    sep_lo = min(nm[r]["first_moment_sep_from_gaia_neighbour_arcsec"] for r in nm)
    sep_hi = max(nm[r]["first_moment_sep_from_gaia_neighbour_arcsec"] for r in nm)
    quantities = [
        q("days_PQ", pq["days_apart"], "days", 0.05, "pairs.P-Q.days_apart"),
        q("days_PR", pr["days_apart"], "days", 0.5, "pairs.P-R.days_apart"),
        q("dlambda_PQ", pq["delta_wavelength_um"], "um", 1e-5, "pairs.P-Q.delta_wavelength_um"),
        q("dlambda_PR", pr["delta_wavelength_um"], "um", 5e-4, "pairs.P-R.delta_wavelength_um"),
        q("dlambda_over_bw_PQ_percent", round(100 * pq["delta_wavelength_over_bandwidth"], 2), "%", 0.1,
          "pairs.P-Q.delta_wavelength_over_bandwidth x 100"),
        q("dlambda_over_bw_PR", pr["delta_wavelength_over_bandwidth"], "band widths", 0.3,
          "pairs.P-R.delta_wavelength_over_bandwidth"),
        q("marker_shift_PQ_px", pq["predicted_marker_shift_display_px"], "display px", 0.02, "pairs.P-Q.predicted_marker_shift_display_px",
          "catalog prediction, not measured"),
        q("marker_shift_PQ_arcsec", pq["predicted_marker_shift_arcsec"], "arcsec", 0.02, "pairs.P-Q.predicted_marker_shift_arcsec",
          "catalog prediction, not measured"),
        q("marker_shift_PR_px", pr["predicted_marker_shift_display_px"], "display px", 0.1, "pairs.P-R.predicted_marker_shift_display_px",
          "catalog prediction, not measured"),
        q("marker_shift_PR_arcsec", pr["predicted_marker_shift_arcsec"], "arcsec", 0.1, "pairs.P-R.predicted_marker_shift_arcsec",
          "catalog prediction, not measured"),
        q("pointing_shift_detector_pixel_arcsec", det["sky_separation_of_pixel_centre_P_to_Q_arcsec"], "arcsec", 0.5,
          "detector_pixel_1709_1364.sky_separation_of_pixel_centre_P_to_Q_arcsec"),
        q("jump_display_shift_px", det["display_shift_px"], "display px", 0.3, "detector_pixel_1709_1364.display_shift_px"),
        q("near_spot_to_gaia_arcsec_max", sep_hi, "arcsec", 0.5, "near_marker.*.first_moment_sep_from_gaia_neighbour_arcsec (max)",
          f"range {sep_lo}-{sep_hi}; quoted as 'within about 1 arcsec'"),
        q("near_spot_to_marker_P_arcsec", nm["P"]["first_moment_sep_from_marker_arcsec"], "arcsec", 1.0,
          "near_marker.P.first_moment_sep_from_marker_arcsec"),
        q("near_spot_to_marker_Q_arcsec", nm["Q"]["first_moment_sep_from_marker_arcsec"], "arcsec", 1.0,
          "near_marker.Q.first_moment_sep_from_marker_arcsec"),
        q("near_spot_to_marker_R_arcsec", nm["R"]["first_moment_sep_from_marker_arcsec"], "arcsec", 0.5,
          "near_marker.R.first_moment_sep_from_marker_arcsec"),
        q("gaia_star_to_marker_range_low_arcsec", 4.5, "arcsec", 0.05, "external: targets_review", "over the 34 shipped frames"),
        q("gaia_star_to_marker_range_high_arcsec", 11.8, "arcsec", 0.05, "external: targets_review", "over the 34 shipped frames"),
        q("probe_value", 1.0, "MJy/sr", 1e-9, "case_stretch_probe.values_MJy_sr[1]"),
        q("grey_case_AB_at_1", csp["grey_level"]["P"][i1], "grey", 0, "case_stretch_probe.grey_level.P[1]"),
        q("grey_case_C_at_1", csp["grey_level"]["R"][i1], "grey", 0, "case_stretch_probe.grey_level.R[1]"),
        q("grey_preset_P_at_1", sp["grey_level"]["P"][i1], "grey", 0, "stretch_probe.grey_level.P[1]"),
        q("grey_preset_Q_at_1", sp["grey_level"]["Q"][i1], "grey", 0, "stretch_probe.grey_level.Q[1]"),
        q("jump_peak_over_neighbour_min", min(f["peak_over_brightest_neighbour"] for f in out["bright_spots"]
                                              if f["detector_xy"] == [1709, 1364]), "x", 50,
          "bright_spots[detector_xy=1709,1364].peak_over_brightest_neighbour (min)", "quoted as 'hundreds of times'"),
        q("screen_radius_native_px", 2.5, "native px", 0, "frames.*.quality screen_radius_native_px (record)"),
        q("persist_pixels_Q", fr["Q"]["adverse_aperture_pixels"], "pixels", 0, "frames.Q.adverse_aperture_pixels"),
        q("screened_pixels_Q", fr["Q"]["screened_pixels"], "pixels", 0, "frames.Q.screened_pixels"),
        q("wise0855_pm_arcsec_per_yr", 8.1, "arcsec/yr", 0.06, "external: backend/content/targets.json wise_0855.one_line"),
        q("wise0855_distance_ly", 7.4, "light-years", 0.05, "external: backend/content/targets.json wise_0855.one_line"),
    ]

    answers = [
        {
            "id": "A1_matched_pair",
            "defect_fixed": 1,
            "question": "Which pair has closely matched target wavelength for investigating a temporal difference, and what still differs?",
            "frames": ["P", "Q", "R"],
            "observations": {
                "P-Q": {k: pq[k] for k in ("days_apart", "delta_wavelength_um", "delta_wavelength_over_bandwidth", "same_detector",
                                           "same_grid", "stretch_high_ratio")},
                "P-R": {k: pr[k] for k in ("days_apart", "delta_wavelength_um", "delta_wavelength_over_bandwidth", "same_detector",
                                           "same_grid")},
                "quality": {r: [fr[r]["quality_status"], fr[r]["quality_flag_names"]] for r in fr},
                "pipeline_builds": out["pipeline_builds"],
                "pointing_shift_at_detector_pixel_arcsec": det["sky_separation_of_pixel_centre_P_to_Q_arcsec"],
            },
            "calculation": "pairs.* in results.json: |delta MJD|, |delta wavelength at marker|, divided by the smaller band width.",
            "image_reference": "contact_sheet.png, top row tiles 1-3 (labels and dates are in results.json frames.*)",
            "supported_conclusion": f"P/Q is the better pair for looking at change over time: {pq['days_apart']} days apart "
                                    f"with target wavelengths {pq['delta_wavelength_um']:.5f} um apart "
                                    f"({100 * pq['delta_wavelength_over_bandwidth']:.1f}% of the band width), on the same "
                                    "detector and grid.",
            "remaining_controls": [f"Q is flagged {', '.join(fr['Q']['quality_flag_names'])} at the marker "
                                   f"({fr['Q']['adverse_aperture_pixels']} of {fr['Q']['screened_pixels']} screened pixels); "
                                   f"P is {fr['P']['quality_status']}.",
                                   f"Pointing differs by {det['sky_separation_of_pixel_centre_P_to_Q_arcsec']} arcsec at "
                                   "detector pixel (1709, 1364).",
                                   "Different pipeline builds (l2b-v27-2026-247 vs -206).",
                                   "Per-frame display stretch in the preset products (shared only in the staged case products)."],
            "same_for_P_Q": "detector, release (spherex_dr1), field rotation (N2 C_pairs.csv)",
            "n2_crosscheck": N2_CROSSCHECK["pairs"],
            "limit": "Matched wavelength makes P/Q the better pair, not a pair that differs only in time.",
        },
        {
            "id": "A2_jumping_dot",
            "defect_fixed": [2, 3],
            "question": "What is the dot that jumps between P and Q while the stars stay still?",
            "frames": ["P", "Q", "R"],
            "features": jump,
            "flag_meanings_from_FITS_header": {k: fdesc[k] for k in ("NONFUNC", "TRANSIENT", "SUR_ERROR")},
            "observations": {"same_detector_pixel": jump[0]["detector_xy"] == jump[1]["detector_xy"],
                             "detector_xy": jump[0]["detector_xy"],
                             "morphology": "one native pixel above 5x the frame median in its 3x3 neighbourhood in both frames",
                             "peak_over_brightest_neighbour": [s["peak_over_brightest_neighbour"] for s in out["bright_spots"]
                                                               if s["detector_xy"] == [1709, 1364]],
                             "pointing": det,
                             "R_at_same_sky_position_MJy_sr": jump[0]["brightest_within_9arcsec_in_other_frames"]["R"]},
            "calculation": "WCS (key A) detector coordinates of the native local maximum; WCS celestial position of the same "
                           "pixel centre in P and Q; separation in arcsec.",
            "image_reference": "contact_sheet.png, yellow boxes at display (114.9, 82.9) in P and (117.9, 80.6) in Q; bottom "
                               "row shows the shipped flag overlay (red) covering it",
            "supported_conclusion": "The jumping dot is one flagged native pixel (NONFUNC, TRANSIENT, SUR_ERROR) at the same "
                                    "detector pixel in P and Q. It shifts on the sky grid because the pointing differs. The "
                                    "flags and single-pixel morphology do not justify treating it as a moving or new source.",
            "n2_crosscheck": N2_CROSSCHECK["jump_pointing"],
            "limit": "The flags say the pixel is unusable and that a transient was detected during onboard processing; they "
                     "do not establish a physical cause (no cosmic-ray, hot-pixel or other mechanism is claimed). R's "
                     "cutout does not contain this detector pixel, so R's background at that sky position is only a "
                     "statement about the sky there, not evidence about the detector pixel.",
        },
        {
            "id": "A3_P_only_dot",
            "defect_fixed": [2, 3],
            "question": "What is the dot present only in P?",
            "frames": ["P", "Q", "R"],
            "features": [ponly],
            "flag_meanings_from_FITS_header": {k: fdesc[k] for k in ("TRANSIENT", "OUTLIER", "HALO", "SUR_ERROR")},
            "observations": {"native_pixels_in_3x3_above_5x_frame_median": ponly["native_pixels_in_3x3_above_5x_frame_median"],
                             "other_frames_at_same_sky_position_MJy_sr": ponly["brightest_within_9arcsec_in_other_frames"]},
            "calculation": "native 3x3 values and FLAGS bits at the local maximum; brightest value within 1.5 native px of the "
                           "same sky position in Q and R.",
            "image_reference": "contact_sheet.png, yellow box at display (32.4, 111.8) in P",
            "supported_conclusion": "The P-only dot covers two adjacent native pixels flagged TRANSIENT, OUTLIER, HALO and "
                                    "SUR_ERROR, and Q and R show background at that sky position. It gives no support for "
                                    "a new astronomical source.",
            "n2_crosscheck": N2_CROSSCHECK["p_only_dot"],
            "limit": "Physical cause not established. Absence from Q and R is a statement about these three frames only.",
        },
        {
            "id": "A4_other_unmatched_spots",
            "defect_fixed": 2,
            "question": "Are there other bright spots without a Gaia counterpart?",
            "frames": ["P", "Q", "R"],
            "features": [redge] + steady,
            "observations": {"bright_spots_total": len(out["bright_spots"]),
                             "matched_to_gaia_within_9arcsec": len(out["bright_spots"]) - len(out["bright_spots_without_gaia_match_within_9arcsec"])},
            "calculation": "census in results.json bright_spots (native local maxima >= the frame's display high).",
            "image_reference": "contact_sheet.png yellow boxes",
            "supported_conclusion": "One more flagged single pixel sits at R's edge (NONFUNC, TRANSIENT, SUR_ERROR). One "
                                    "unflagged, star-like spot near display (128, 31) is present in all three frames with "
                                    "similar values; it is a steady source not in the G < 17 Gaia cache and is not identified.",
            "limit": "The census only covers spots drawn white by each frame's own stretch; fainter changes were not searched for.",
        },
        {
            "id": "A5_brightness",
            "defect_fixed": 6,
            "question": "Q looks brighter overall than P in the preset view (and C differs from A/B in the case view). Is that the sky?",
            "frames": ["P", "Q", "R"],
            "observations": {"stretch_probe_preset_per_frame": sp, "stretch_probe_staged_case": csp, "frame_background": bg},
            "calculation": "grey = 255 asinh(10 t)/asinh(10), t = clip((v - low)/(high - low)); low/high from each record's "
                           "display_scale (or the shared P+Q limits); background = median of display-grid values.",
            "image_reference": "contact_sheet.png: top row tiles 1-2 (per-frame) vs tiles 4-5 (shared P+Q stretch)",
            "supported_conclusion": "The same input radiance gets a different grey level under each frame's own stretch "
                                    f"(1.0 MJy/sr: grey {sp['grey_level']['P'][i1]} in P, {sp['grey_level']['Q'][i1]} in Q), so "
                                    "the per-frame stretch changes grey levels between frames. Under one shared stretch the "
                                    f"same value gets the same grey ({csp['grey_level']['P'][i1]} in both). Q's grid median is "
                                    f"{bg['median_ratio_Q_over_P']} of P's, yet the per-frame stretch draws Q lighter; under the "
                                    "shared stretch the order reverses.",
            "n2_crosscheck": [N2_CROSSCHECK["stretch_probe"], N2_CROSSCHECK["background_order_reverses"]],
            "limit": "This proves a display effect exists; it does not prove every frame-wide brightness difference has only "
                     "that cause, and the small physical difference in median (Q 0.971 of P) has no established cause. The "
                     "medians are descriptive, uncalibrated and carry no uncertainty; no brightness change or constancy is "
                     "measured. For R (C in the case), wavelength also differs.",
        },
        {
            "id": "A6_marker_and_nearby_dot",
            "defect_fixed": [5, 7],
            "question": "Is the dot near the marker WISE 0855?",
            "frames": ["P", "Q", "R"],
            "observations": {"near_marker": nm, "gaia_neighbour_catalog": out["neighbour"],
                             "marker_kind": "catalog_prediction"},
            "calculation": "brightest native local maximum within 3 native px of the marker; 3x3 first moment above the frame "
                           "median; separations from the marker and from the cached Gaia DR3 position at each epoch.",
            "image_reference": "contact_sheet.png magenta circles (catalog prediction)",
            "external_sources": [EXTERNAL_SOURCES[k] for k in ("targets_review", "faherty2014", "schneider2016", "dore2014")],
            "supported_conclusion": "The marker is a catalog prediction, not an image detection. The dot nearest it lies "
                                    f"{sep_lo}-{sep_hi} arcsec from the catalogued Gaia DR3 star 5756956644387831296 and "
                                    f"{nm['R']['first_moment_sep_from_marker_arcsec']}-{nm['P']['first_moment_sep_from_marker_arcsec']} "
                                    "arcsec from the marker: a positional association with that star, so it is not evidence "
                                    "of WISE 0855.",
            "limit": "A positional association is not an identification; the first moment is crude (3x3, undersampled PSF). "
                     "That WISE 0855 is far below SPHEREx sensitivity at 1.26-1.44 um is a sourced expectation (published "
                     "J-band brightness vs SPHEREx design depth), not a measured non-detection or an upper limit. In Q two "
                     "PERSIST-flagged pixels sit inside the screen circle next to this dot.",
        },
        {
            "id": "A7_motion_test",
            "defect_fixed": 4,
            "question": "Can P and R show whether WISE 0855 moved?",
            "frames": ["P", "R"],
            "observations": {"P-R": pr, "near_marker_R": nm["R"]},
            "calculation": "pairs.P-R; predicted shift from the catalog markers only.",
            "n2_crosscheck": N2_CROSSCHECK["pairs"],
            "image_reference": "contact_sheet.png tiles 1 and 3",
            "supported_conclusion": "P/R does not establish WISE 0855 motion here: the target is not securely detected or "
                                    "identified in these frames, and no astrometric fit was made. The pair also mixes "
                                    f"{round(pr['days_apart'])} days with a {pr['delta_wavelength_um']} um wavelength change "
                                    f"({pr['delta_wavelength_over_bandwidth']} band widths).",
            "limit": "No universal rule is implied: positions can be compared across wavelengths, and shifts below one native "
                     "pixel can be measured with a detected source, adequate signal, PSF knowledge and a proper fit. "
                     "Wavelength, PSF, sensitivity, sampling and quality all have to be considered; here the first "
                     "requirement (a detected, identified target) already fails.",
        },
    ]
    return {
        "schema": "perigee-answer-evidence/1",
        "exercise": "science/reviews/transfer-exercise/README.md",
        "staged_case": "science/staging/wise_0855_quality_trap/case.json",
        "generated_by": "science/reviews/transfer-exercise/check_transfer.py",
        "results": "results.json (same output directory)",
        "status": "computational review; not a learner outcome or human validation",
        "frames": {r: frame_meta(r) for r in ("P", "Q", "R")},
        "flag_definitions_from_FITS_header": fdesc,
        "external_sources": EXTERNAL_SOURCES,
        "n2_controls_crosscheck": N2_CROSSCHECK,
        "target_identity": {
            "target": "WISE 0855",
            "status": "not_identified",
            "marker": "catalog prediction (not a detection)",
            "nearest_feature": "positionally associated with Gaia DR3 5756956644387831296",
            "expectation": "far below SPHEREx sensitivity at 1.26-1.44 um (sourced expectation, not a measured limit)",
        },
        "quantities": quantities,
        "answers": answers,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=HERE,
                    help="output directory for results.json, answer_evidence.json, contact_sheet.png (default: this folder)")
    a = ap.parse_args()
    OUT = a.out
    OUT.mkdir(parents=True, exist_ok=True)
    root = a.data_root
    manifest = json.loads((root / "manifest.json").read_text())
    targets = json.loads((REPO / "backend/content/targets.json").read_text())
    tgt = next(t for t in targets["targets"] if t["id"] == PRESET)
    qc = tgt["query_center"]
    with open(REPO / "science/reviews/acceptance/gaia/wise_0855.csv") as f:
        gaia = list(csv.DictReader(f))

    out = {"preset": PRESET, "targets_content_version": targets["content_version"],
           "manifest_created_utc": manifest["created_utc"], "frames": {}}
    recs, raw, products = {}, {}, {}
    for ref, key in FRAMES:
        rec = json.loads((REC_DIR / f"{key}.json").read_text())
        recs[ref] = rec
        obs, det = rec["observation_id"], rec["detector"]
        ent = [e for e in manifest["files"] if e.get("obs_id") == obs and e.get("detector") == det
               and e.get("target_id") == PRESET and e.get("status") == "downloaded"]
        assert len(ent) == 1, (key, len(ent))
        ent = ent[0]
        path = root / ent["file"]
        file_sha = sha256_file(path)
        data = path.read_bytes()
        hdul = fits.open(path, memmap=False)
        raw[ref] = hdul
        ih = hdul["IMAGE"].header
        meta = FrameInput(
            query_ra_deg=qc["ra_deg"], query_dec_deg=qc["dec_deg"],
            fov_arcmin=float(tgt.get("default_fov_arcmin") or 6), target=target_input(tgt),
            source_url=ent["archive_url"], cutout_url=ent["source_url"], observation_id=obs,
            collection_id=ent["collection"], detector=det, retrieved_at_utc=manifest.get("created_utc"),
            retrieved_at_basis="Download-ledger creation time (manifest.json created_utc); per-file retrieval time not recorded.",
            expected_sha256=ent["sha256"])
        pf = process_frame(data, meta)
        products[ref] = (meta, data, pf)
        r2 = pf.record
        shipped_png = (REC_DIR / f"{key}.png").read_bytes()
        q = rec["quality"]
        out["frames"][ref] = {
            "frame_key": key,
            "observation_id": obs,
            "detector": det,
            "collection_id": rec["collection_id"],
            "header": {"OBSID": str(ih.get("OBSID")).strip(), "DETECTOR": int(ih["DETECTOR"]),
                       "DATE-AVG": ih.get("DATE-AVG"), "MJD-AVG": float(ih["MJD-AVG"])},
            "observed_at_utc": rec["observed_at_utc"],
            "mjd": rec["mjd"],
            "wavelength_um": rec["wavelength_um"],
            "bandwidth_um": rec["bandwidth_um"],
            "quality_status": q["status"],
            "quality_flag_names": q["flag_names"],
            "adverse_aperture_pixels": q["adverse_aperture_pixels"],
            "screened_pixels": q["screened_pixels"],
            "display_scale": {k: rec["display_scale"][k] for k in ("mode", "method", "low", "high", "unit")},
            "marker_xy": [rec["marker"]["x"], rec["marker"]["y"]],
            "grid_id": rec["registration"]["grid_id"],
            "source_url": rec["source_url"],
            "sha256": {"record": rec["provenance"]["sha256"], "manifest": ent["sha256"], "file": file_sha,
                       "all_equal": rec["provenance"]["sha256"] == ent["sha256"] == file_sha},
            "manifest_wavelength_um": ent.get("wavelength_um"),
            "reproduced": {
                "wavelength_um_equal_1e-9": abs(r2["wavelength_um"] - rec["wavelength_um"]) < 1e-9,
                "quality_equal": r2["quality"] == rec["quality"],
                "display_scale_equal": r2["display_scale"] == rec["display_scale"],
                "marker_equal": r2["marker"] == rec["marker"],
                "png_bytes_equal": pf.png_bytes == shipped_png,
            },
        }

    # Pairs: time, wavelength, stretch
    def pair(x, y):
        fx, fy = recs[x], recs[y]
        dlam = abs(fx["wavelength_um"] - fy["wavelength_um"])
        bw = min(fx["bandwidth_um"], fy["bandwidth_um"])
        mx, my = fx["marker"], fy["marker"]
        dpx = math.hypot(mx["x"] - my["x"], mx["y"] - my["y"])
        scale = fx["registration"]["scale_arcsec_per_px"]
        return {
            "days_apart": round(abs(fy["mjd"] - fx["mjd"]), 3),
            "delta_wavelength_um": round(dlam, 5),
            "delta_wavelength_over_bandwidth": round(dlam / bw, 3),
            "same_detector": fx["detector"] == fy["detector"],
            "stretch_high_ratio": round(fy["display_scale"]["high"] / fx["display_scale"]["high"], 3),
            "stretch_low_ratio": round(fy["display_scale"]["low"] / fx["display_scale"]["low"], 3),
            "predicted_marker_shift_display_px": round(dpx, 2),
            "predicted_marker_shift_arcsec": round(dpx * scale, 2),
            "same_grid": fx["registration"]["grid_id"] == fy["registration"]["grid_id"],
        }
    out["pairs"] = {"P-Q": pair("P", "Q"), "P-R": pair("P", "R"), "Q-R": pair("Q", "R")}

    # Shared stretch for P+Q (illustration only) and physical grid values
    vals = {r: products[r][2].grid_values for r in ("P", "Q", "R")}
    lo, hi = display_limits_from_values([vals["P"], vals["Q"]])
    shared = {}
    for r in ("P", "Q"):
        meta, data, _ = products[r]
        m2 = FrameInput(**{**meta.__dict__, "display_limits": (lo, hi), "display_limits_basis": "review only"})
        shared[r] = process_frame(data, m2)
    out["shared_stretch_P_Q"] = {"low": lo, "high": hi, "unit": "MJy / sr",
                                 "note": "Review illustration only; percentiles 1-99.5 of pooled P+Q grid values."}

    size = recs["P"]["registration"]["width"]
    gw = grid_wcs(qc["ra_deg"], qc["dec_deg"], recs["P"]["registration"]["fov_arcmin"], size)
    gp, gq = full_grid(raw["P"], gw, size), full_grid(raw["Q"], gw, size)
    for r, g in (("P", gp), ("Q", gq)):  # same pixels as the processor's grid_values
        assert np.isclose(np.sort(g[np.isfinite(g)]), np.sort(np.asarray(vals[r], float))).all(), r

    # Per-frame stretch: the grey level the shipped stretch gives to the same
    # physical value in each frame (exact; same formula as process._stretch).
    def grey_for(ref, v):
        ds = recs[ref]["display_scale"]
        t = min(max((v - ds["low"]) / (ds["high"] - ds["low"]), 0.0), 1.0)
        return round(255 * math.asinh(t * ds["asinh_softening"]) / math.asinh(ds["asinh_softening"]))
    probe = [0.5, 1.0, 2.0, 2.5]
    out["stretch_probe"] = {
        "values_MJy_sr": probe,
        "grey_level": {r: [grey_for(r, v) for v in probe] for r in ("P", "Q", "R")},
        "note": "Same sky value, different displayed grey: each shipped frame has its own stretch "
                "(display_scale.mode = per_frame). Rounding to 8-bit is approximate.",
    }

    # Census of bright compact spots (what a blinking learner notices), per frame.
    # A spot = native local maximum at or above that frame's display "high"
    # (i.e. drawn pure white by the shipped per-frame stretch) on the display grid.
    # For each: adverse native flags at the peak, detector pixel (WCS key A),
    # single-pixel test (peak vs brightest of its 8 neighbours), nearest cached
    # Gaia DR3 star at the frame epoch, and whether the other frames show
    # something bright within 1.5 native px (~9") of the same sky position.
    natives = {}
    for ref in ("P", "Q", "R"):
        h = raw[ref]
        ih = h["IMAGE"].header
        natives[ref] = {
            "img": np.asarray(h["IMAGE"].data, dtype=np.float64),
            "flg": np.asarray(h["FLAGS"].data).astype(np.int64),
            "names": flag_bit_names(h["FLAGS"].header),
            "cel": WCS(ih, fobj=h).celestial,
            "det": WCS(ih, key="A"),
        }

    def brightest_near(ref, ra, dec, rad=1.5):
        n = natives[ref]
        x, y = n["cel"].all_world2pix([[ra, dec]], 0)[0]
        ny, nx = n["img"].shape
        best = None
        for yy in range(int(math.floor(y - rad)), int(math.ceil(y + rad)) + 1):
            for xx in range(int(math.floor(x - rad)), int(math.ceil(x + rad)) + 1):
                if 0 <= xx < nx and 0 <= yy < ny and math.hypot(xx - x, yy - y) <= rad and np.isfinite(n["img"][yy, xx]):
                    v = float(n["img"][yy, xx])
                    best = v if best is None else max(best, v)
        return best

    overlays = {r: np.array(Image.open(REC_DIR / f"{recs[r]['frame_key']}.flags.png").convert("RGBA")) for r in ("P", "Q", "R")}
    spots = []
    for ref in ("P", "Q", "R"):
        n = natives[ref]
        img, ny, nx = n["img"], *n["img"].shape
        jyr = mjd_to_jyear(recs[ref]["mjd"])
        padded = np.pad(img, 1, constant_values=np.nan)
        for yy in range(ny):
            for xx in range(nx):
                v = img[yy, xx]
                if not (np.isfinite(v) and v >= recs[ref]["display_scale"]["high"]):
                    continue
                nb8 = np.delete(padded[yy:yy + 3, xx:xx + 3].ravel(), 4)  # edge pixels: missing neighbours = NaN
                if np.nanmax(nb8) >= v:
                    continue
                ra, dec = n["cel"].all_pix2world([[xx, yy]], 0)[0]
                dx, dy = sky_to_display_px(gw, size, ra, dec)
                if not (0 <= dx < size and 0 <= dy < size):
                    continue
                fv = int(n["flg"][yy, xx])
                adverse = sorted(nm for b, nm in n["names"].items() if fv >> b & 1 and nm not in INFORMATIONAL)
                dpx = n["det"].wcs_pix2world([[xx, yy]], 0)[0]
                gsep, gid, gmag = min(
                    (math.hypot((gaia_at(g, jyr)[0] - ra) * math.cos(math.radians(dec)), gaia_at(g, jyr)[1] - dec) * 3600,
                     g["source_id"], float(g["phot_g_mean_mag"])) for g in gaia)
                spots.append({
                    "frame": ref, "display_xy": [round(dx, 1), round(dy, 1)], "native_xy": [xx, yy],
                    "detector_xy": [int(round(dpx[0])), int(round(dpx[1]))],
                    "peak_MJy_sr": round(float(v), 2),
                    "peak_over_brightest_neighbour": round(float(v / np.nanmax(nb8)), 1) if np.nanmax(nb8) > 0 else None,
                    "adverse_flags_at_peak": adverse,
                    "shipped_flag_overlay_rgba": [int(c) for c in overlays[ref][int(dy), int(dx)]],
                    "nearest_gaia_dr3": {"id": gid, "G": round(gmag, 2), "sep_arcsec": round(gsep, 1)},
                    "brightest_within_9arcsec": {o: (round(b, 2) if (b := brightest_near(o, ra, dec)) is not None else None)
                                                 for o in ("P", "Q", "R") if o != ref},
                })
    used = sorted({f for sp in spots for f in sp["adverse_flags_at_peak"]} | set(recs["Q"]["quality"]["flag_names"]) | {"SOURCE"})
    fh = raw["Q"]["FLAGS"].header
    out["flag_descriptions_from_FITS_header"] = {
        str(fh[k]).strip(): str(fh.get("MSKD" + k[4:], "")).strip()
        for k in fh.keys() if k.startswith("MSKN") and str(fh[k]).strip() in used}
    out["spot_threshold"] = "native local maximum >= the frame's display_scale.high (drawn white)"
    out["bright_spots"] = spots
    unmatched = [s for s in spots if s["nearest_gaia_dr3"]["sep_arcsec"] > 9.0]
    out["bright_spots_without_gaia_match_within_9arcsec"] = unmatched

    # Marker neighbourhood: the Gaia neighbour, per frame
    nb = next(g for g in gaia if g["source_id"] == NEIGHBOUR)
    out["neighbour"] = {}
    for ref, key in FRAMES:
        rec = recs[ref]
        ra, dec = gaia_at(nb, mjd_to_jyear(rec["mjd"]))
        x, y = sky_to_display_px(gw, size, ra, dec)
        sep = math.hypot(x - rec["marker"]["x"], y - rec["marker"]["y"]) * rec["registration"]["scale_arcsec_per_px"]
        out["neighbour"][ref] = {"gaia_dr3": NEIGHBOUR, "G": float(nb["phot_g_mean_mag"]),
                                 "display_xy": [round(x, 2), round(y, 2)],
                                 "sep_from_marker_arcsec": round(sep, 2),
                                 "adverse_native_flags_at_neighbour": native_flags_at(raw[ref], ra, dec)}

    # ---- N1 additions: evidence for each answer (2026-11-15 overnight pass) ----
    def sep_arcsec(ra1, dec1, ra2, dec2):
        return math.hypot((ra1 - ra2) * math.cos(math.radians(0.5 * (dec1 + dec2))), dec1 - dec2) * 3600

    def bits_at(ref, xx, yy):
        n = natives[ref]
        v = int(n["flg"][yy, xx])
        return v, sorted(nm for b, nm in n["names"].items() if v >> b & 1)

    # (a) Flagged features: raw FLAGS integer, every bit set, 3x3 native values
    #     and a morphology count (native pixels in the 3x3 more than 10x the
    #     frame's median above it). Morphology is descriptive, not a cause.
    features = []
    for sp in unmatched:
        ref = sp["frame"]
        n = natives[ref]
        xx, yy = sp["native_xy"]
        med = float(np.nanmedian(n["img"]))
        win = np.pad(n["img"], 1, constant_values=np.nan)[yy:yy + 3, xx:xx + 3]
        v, allbits = bits_at(ref, xx, yy)
        ra, dec = n["cel"].all_pix2world([[xx, yy]], 0)[0]
        features.append({
            "frame": ref, "frame_key": recs[ref]["frame_key"],
            "native_xy_0based": [xx, yy], "detector_xy": sp["detector_xy"],
            "display_xy": sp["display_xy"], "ra_deg": round(float(ra), 6), "dec_deg": round(float(dec), 6),
            "flags_value": v, "flag_bit_indices": [b for b in range(v.bit_length()) if v >> b & 1],
            "flag_bits_set": allbits, "adverse_flags": sp["adverse_flags_at_peak"],
            "peak_MJy_sr": sp["peak_MJy_sr"], "frame_median_MJy_sr": round(med, 3),
            "native_3x3_MJy_sr": [[None if not np.isfinite(c) else round(float(c), 2) for c in row] for row in win],
            "native_pixels_in_3x3_above_5x_frame_median": int(np.nansum(win > 5 * med)),
            "brightest_within_9arcsec_in_other_frames": sp["brightest_within_9arcsec"],
        })
    out["flagged_features"] = features

    # (b) The P/Q "jumping dot": the same detector pixel. Where does its centre
    #     fall on the sky in each frame (pointing difference), versus the fixed
    #     catalog positions of field stars?
    track = {}
    for ref in ("P", "Q"):
        f = next(x for x in features if x["frame"] == ref and x["detector_xy"] == [1709, 1364])
        track[ref] = f
    pq_sep = sep_arcsec(track["P"]["ra_deg"], track["P"]["dec_deg"], track["Q"]["ra_deg"], track["Q"]["dec_deg"])
    # Unrounded display positions of the two pixel centres (the census rounds to 0.1 px).
    dxy = {r: sky_to_display_px(gw, size, track[r]["ra_deg"], track[r]["dec_deg"]) for r in ("P", "Q")}
    dpx = math.hypot(dxy["P"][0] - dxy["Q"][0], dxy["P"][1] - dxy["Q"][1])
    star_seps = {r: [s["nearest_gaia_dr3"]["sep_arcsec"] for s in spots if s["frame"] == r and s["nearest_gaia_dr3"]["sep_arcsec"] <= 9.0]
                 for r in ("P", "Q", "R")}
    out["detector_pixel_1709_1364"] = {
        "native_xy_0based": {"P": track["P"]["native_xy_0based"], "Q": track["Q"]["native_xy_0based"]},
        "sky_separation_of_pixel_centre_P_to_Q_arcsec": round(pq_sep, 2),
        "display_shift_px": round(dpx, 2),
        "display_shift_arcsec": round(dpx * recs["P"]["registration"]["scale_arcsec_per_px"], 2),
        "native_scale_arcsec_per_px": recs["P"]["registration"]["native_scale_arcsec_per_px"],
        "field_star_peaks_sep_from_gaia_arcsec_max": {r: max(v) if v else None for r, v in star_seps.items()},
        "field_star_peak_count": {r: len(v) for r, v in star_seps.items()},
        "note": "The same detector pixel maps to sky positions this far apart because the two pointings differ. "
                "Field-star peaks (native local maxima, quantized to ~6.2 arcsec native pixels) stay within the "
                "listed distance of their fixed Gaia positions in each frame.",
    }

    # (c) What lies nearest the marker: the brightest native local maximum
    #     within 3 native px of the predicted position, a 3x3 background-
    #     subtracted first moment (crude; undersampled PSF), and its distance
    #     from the marker and from the cached Gaia DR3 neighbour. Descriptive
    #     only: not a detection test, a centroid fit or photometry.
    near = {}
    for ref, key in FRAMES:
        n = natives[ref]
        rec = recs[ref]
        m = rec["marker"]
        mx, my = n["cel"].all_world2pix([[m["ra_deg"], m["dec_deg"]]], 0)[0]
        img = n["img"]
        med = float(np.nanmedian(img))
        mad = float(np.nanmedian(np.abs(img - med)) * 1.4826)
        best = None
        for yy in range(int(math.floor(my - 3)), int(math.ceil(my + 3)) + 1):
            for xx in range(int(math.floor(mx - 3)), int(math.ceil(mx + 3)) + 1):
                if not (1 <= xx < img.shape[1] - 1 and 1 <= yy < img.shape[0] - 1):
                    continue
                if math.hypot(xx - mx, yy - my) > 3:
                    continue
                w = img[yy - 1:yy + 2, xx - 1:xx + 2]
                if not np.isfinite(w).all() or img[yy, xx] < np.delete(w.ravel(), 4).max():
                    continue
                if best is None or img[yy, xx] > img[best[1], best[0]]:
                    best = (xx, yy)
        xx, yy = best
        w = np.clip(img[yy - 1:yy + 2, xx - 1:xx + 2] - med, 0, None)
        gy, gx = np.mgrid[yy - 1:yy + 2, xx - 1:xx + 2]
        cx, cy = float((w * gx).sum() / w.sum()), float((w * gy).sum() / w.sum())
        cra, cdec = n["cel"].all_pix2world([[cx, cy]], 0)[0]
        nra, ndec = gaia_at(nb, mjd_to_jyear(rec["mjd"]))
        dxy = sky_to_display_px(gw, size, cra, cdec)
        screened_adverse = []
        for sy in range(img.shape[0]):
            for sx in range(img.shape[1]):
                if math.hypot(sx - mx, sy - my) <= recs[ref]["quality"]["screen_radius_native_px"]:
                    v, allbits = bits_at(ref, sx, sy)
                    adv = [b for b in allbits if b not in INFORMATIONAL]
                    if adv:
                        screened_adverse.append({"native_xy_0based": [sx, sy], "flags_value": v, "adverse_flags": adv,
                                                 "value_MJy_sr": round(float(img[sy, sx]), 3)})
        near[ref] = {
            "marker_native_xy_0based": [round(float(mx), 2), round(float(my), 2)],
            "local_max_native_xy_0based": [xx, yy],
            "local_max_MJy_sr": round(float(img[yy, xx]), 3),
            "frame_median_MJy_sr": round(med, 3),
            "frame_robust_scatter_MJy_sr": round(mad, 3),
            "peak_excess_over_robust_scatter": round((float(img[yy, xx]) - med) / mad, 1),
            "first_moment_display_xy": [round(dxy[0], 1), round(dxy[1], 1)],
            "first_moment_sep_from_marker_arcsec": round(sep_arcsec(cra, cdec, m["ra_deg"], m["dec_deg"]), 1),
            "first_moment_sep_from_gaia_neighbour_arcsec": round(sep_arcsec(cra, cdec, nra, ndec), 1),
            "local_max_adverse_flags": [b for b in bits_at(ref, xx, yy)[1] if b not in INFORMATIONAL],
            "screened_adverse_pixels": screened_adverse,
            "method": "brightest native local maximum within 3 native px of the marker; 3x3 first moment above the frame median",
        }
    out["near_marker"] = near

    # (d) Frame-wide background in physical units, and the grey level that the
    #     shipped per-frame stretch gives it (what "Q looks brighter" rests on).
    def grey_ds(ds, v):
        t = min(max((v - ds["low"]) / (ds["high"] - ds["low"]), 0.0), 1.0)
        return round(255 * math.asinh(t * ds["asinh_softening"]) / math.asinh(ds["asinh_softening"]))
    bgd = {}
    for r in ("P", "Q", "R"):
        g = np.asarray(vals[r], float)
        g = g[np.isfinite(g)]
        p16, p50, p84 = (float(x) for x in np.percentile(g, [16, 50, 84]))
        bgd[r] = {"grid_median_MJy_sr": round(p50, 4), "grid_p16_MJy_sr": round(p16, 4), "grid_p84_MJy_sr": round(p84, 4),
                  "grey_of_median_shipped_per_frame": grey_ds(recs[r]["display_scale"], p50)}
    shared_ds = {"low": lo, "high": hi, "asinh_softening": recs["P"]["display_scale"]["asinh_softening"]}
    for r in ("P", "Q"):
        bgd[r]["grey_of_median_shared_P_Q"] = grey_ds(shared_ds, bgd[r]["grid_median_MJy_sr"])
    out["frame_background"] = {
        "frames": bgd,
        "median_ratio_Q_over_P": round(bgd["Q"]["grid_median_MJy_sr"] / bgd["P"]["grid_median_MJy_sr"], 3),
        "note": "Medians of the display-grid pixel values in the record unit (MJy / sr). Descriptive only: no background "
                "model, calibration check or uncertainty; not photometry.",
    }
    out["case_stretch_probe"] = {
        "values_MJy_sr": probe,
        "grey_level": {"P": [grey_ds(shared_ds, v) for v in probe], "Q": [grey_ds(shared_ds, v) for v in probe],
                       "R": [grey_ds(recs["R"]["display_scale"], v) for v in probe]},
        "note": "Staged case products: P and Q on one shared stretch (ingest shared_groups_for_case), R on its own.",
    }
    out["pipeline_builds"] = {r: recs[r]["source_url"].split("/")[-3] for r in ("P", "Q", "R")}
    (OUT / "results.json").write_text(json.dumps(out, indent=1) + "\n")
    (OUT / "answer_evidence.json").write_text(json.dumps(build_evidence(out), indent=1) + "\n")

    # Contact sheet: shipped P, Q, R (per-frame stretch); P, Q shared stretch; flags overlays for P, Q
    tiles = []
    for ref in ("P", "Q", "R"):
        tiles.append((f"{ref} shipped (own stretch)", Image.open(REC_DIR / f"{recs[ref]['frame_key']}.png").convert("RGBA"),
                      Image.open(REC_DIR / f"{recs[ref]['frame_key']}.flags.png").convert("RGBA")))
    for ref in ("P", "Q"):
        tiles.append((f"{ref} shared P+Q stretch (review)", Image.open(io.BytesIO(shared[ref].png_bytes)).convert("RGBA"), None))
    z = 2
    W = size * z
    sheet = Image.new("RGB", (W * len(tiles) + 10 * (len(tiles) - 1), W * 2 + 40), (40, 40, 40))
    for i, (label, im, fl) in enumerate(tiles):
        base = Image.new("RGBA", im.size, (0, 0, 80, 255))
        base.alpha_composite(im)
        top = base.resize((W, W), Image.NEAREST).convert("RGB")
        x0 = i * (W + 10)
        sheet.paste(top, (x0, 20))
        if fl is not None:
            ov = base.copy()
            ov.alpha_composite(fl)
            sheet.paste(ov.resize((W, W), Image.NEAREST).convert("RGB"), (x0, W + 40))
        dr = ImageDraw.Draw(sheet)
        dr.text((x0 + 2, 4), label, fill=(255, 255, 255))
        ref = label[0]
        if fl is not None:
            for sp in unmatched:
                if sp["frame"] == ref:
                    sx, sy = sp["display_xy"][0] * z, sp["display_xy"][1] * z
                    dr.rectangle([x0 + sx - 10, 20 + sy - 10, x0 + sx + 10, 20 + sy + 10], outline=(255, 220, 0))
        mx, my = recs[ref]["marker"]["x"] * z, recs[ref]["marker"]["y"] * z
        for yoff in (20, W + 40) if fl is not None else (20,):
            dr.ellipse([x0 + mx - 12, yoff + my - 12, x0 + mx + 12, yoff + my + 12], outline=(255, 0, 255))
    ImageDraw.Draw(sheet).text((2, W + 24), "bottom: shipped image + shipped flag overlay (red = adverse flag, yellow = non-finite); magenta circle = catalog prediction; yellow box = bright spot with no Gaia DR3 star within 9 arcsec", fill=(220, 220, 220))
    sheet.save(OUT / "contact_sheet.png", optimize=True)
    print(json.dumps({k: out[k] for k in ("pairs", "bright_spots_without_gaia_match_within_9arcsec", "neighbour")}, indent=1))
    for ref in out["frames"]:
        f = out["frames"][ref]
        print(ref, f["frame_key"], f["sha256"]["all_equal"], f["reproduced"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
