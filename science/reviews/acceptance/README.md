# Independent scientific acceptance: processor A (with a short processor B column)

Reviewer: parallel worker 15, 2026-11-14 ~12:10 CST. Review only: no processor code or products were changed.

| Subject | Branch @ commit | `processing_version` | Products checked |
|---|---|---|---|
| **Processor A** (primary) | `codex/parallel-05-processor-a` @ `9c9049a` (draft PR #11) | `perigee-processor-a/0.1.0` | 6 case frames (`presets/*/case-*/`) + 7 representative frames below. An automated sweep also covered all 189 records (183 retained frames + 6 case copies). |
| Processor B | `codex/parallel-06-processor-b` @ `86710e0` | `perigee-processor-b/0.1.0` | Only its 6 case frames (all it has pushed) |
| Truth inputs | original cutouts + `manifest.json` in `research/build_data/` (read only); case JSON from `origin/codex/sathvik-science`; Gaia DR3 (`gaia/*.csv`) | | |

## Matrix

PASS means every check in that column agreed with an independent re-derivation from the original bytes (criteria below). There are no FAIL results. The single UNKNOWN is noted after the table.

| frame_key | Why chosen | Status | 1 Sky reg. | 2 Wavelength | 3 Time | 4 Flags | 5 Coverage | 6 Stretch | 7 Provenance | Case JSON | **B** (1–7, case) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `2026W18_1A_0516_1_D3` | fair_comparison A | clear | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `2026W39_2A_0597_4_D3` | fair_comparison B | clear | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `2026W18_1A_0516_1_D6` | fair_comparison C, MWIR | clear | PASS¹ | PASS | PASS | PASS | PASS | PASS (per_frame, labeled) | PASS | PASS | PASS¹ |
| `2025W35_1A_0008_1_D3` | moving_neighbor A | flagged | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `2026W12_1A_0610_2_D3` | moving_neighbor B | flagged | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `2026W34_1A_0431_1_D3` | moving_neighbor C | flagged | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `2025W17_4B_0077_2_D1` | Eps Ind B not_covered | not_covered | PASS | PASS (null) | PASS | PASS (null counts) | PASS | PASS | PASS | – | – |
| `2025W27_2A_0331_1_D4` | R Dra not_covered, MWIR, defect-1 frame | not_covered | PASS | PASS (null) | PASS | PASS (null counts) | PASS | PASS | PASS | – | – |
| `2025W37_1A_0069_1_D2` | RW Aur not_covered, defect-1 frame | not_covered | PASS | PASS (null) | PASS | PASS (null counts) | PASS | PASS | PASS | – | – |
| `2026W01_2A_0426_1_D3` | R Dra saturated (21/21 non-finite) | flagged | PASS | PASS | PASS | PASS | PASS | PASS | PASS | – | – |
| `2025W29_2A_0288_1_D4` | R Dra saturated, MWIR | flagged | PASS | PASS | PASS | PASS | PASS | PASS | PASS | – | – |
| `2026W19_1A_0227_1_D1` | WISE 0855, SWIR | clear | PASS | PASS | PASS | PASS | PASS | PASS | PASS | – | – |
| `2026W19_1A_0227_1_D4` | WISE 0855, MWIR, same exposure | clear | PASS | PASS | PASS | PASS | PASS | PASS | PASS | – | – |

¹ For fair_comparison C (D6), no Gaia star passed the signal-to-noise cut, so the absolute star check is **UNKNOWN** for this frame alone. The PNG still matches a reconstruction from the header WCS byte for byte, and Eps Ind B sits at the marker. For an MWIR frame with a Gaia check, see `…_D4` (WISE 0855).

**Sweep over all 189 processor-A records:** 189/189 PASS on columns 1–7, with 0 failures. The marker matches the independent prediction to within 0.0007 display px. The PNG reconstruction is exact for 100% of pixels in every frame. Gaia stars land in the PNG with a median offset of 0.45 display px; the worst frame is 2.0 px (161 frames). Wavelength agrees with the independent value to within 3.3e-10 µm (185 covered frames). The flag overlay reconstruction is 100%. Coverage is exactly 4 frames not_covered (all off the image geometrically), and 0 images contain undocumented flag bits.

> **Correction (2026-11-15, overnight N3):** column 1, `registration`, is **internal consistency with each file's header WCS** (marker, grid identity, PNG reconstruction), plus a Gaia comparison that runs only when some star survives a 1-native-px association. N3's negative control showed that a frame whose pixels are shifted 2 or 5 native px against an unchanged header still reads `registration: True`, because every Gaia star drops out of the association. So the 189/189 above is **not** an independent astrometric validation of 189 frames.
>
> The script now also reports an independent **`astrometry`** column (N3's WCS-free `regcheck.registration_verdict`: blind detections voted against Gaia DR3). On the current products it is **PASS 133, UNKNOWN 56, FAIL 0** of the 189 records; over the 183 unique cutouts that is 128 PASS and 55 UNKNOWN, since the 6 case copies repeat their frames. UNKNOWN means too few usable stars, not a pass; it includes fair_comparison C, one WISE 0855 frame and 25 R Draconis frames. On the derived misregistration fixtures it FAILs every 1, 2 and 5 px shift. `qa/regression/run.sh` fails on any `False` cell, so an astrometry FAIL now breaks the gate. Details: `science/reviews/registration-audit/README.md`.

## What each check did (independent of `backend/data`, `tools/ingest`)

1. **Sky registration.**
   - **Marker:** the target is propagated from the manifest J2000 astrometry to `MJD-AVG` with astropy `apply_space_motion`. A crude linear-proper-motion control agrees to within 0.3 display px. It is then projected with a hand-written gnomonic transform (north up, east left, origin at the top-left corner) and compared with `marker.x/y`.
   - **Image:** every display pixel center is mapped to the sky with the inverse gnomonic transform, then to a native pixel through the raw IMAGE header TAN-SIP WCS (astropy `all_world2pix`). The native value is sampled, the record's stated stretch is applied, and the result is compared with the PNG gray and alpha bytes. A left-right mirrored reconstruction is the negative control: it matches only 1–20% of pixels in non-saturated fields.
   - **Absolute check:** Gaia DR3 field stars are propagated to `MJD-AVG` and centroided in the native image (spikes removed). Only stars within 1 native px of Gaia are kept, then centroided in the PNG.
   - **Grid identity:** the registration block and `grid_id` are equal for every record in a set (decision 5).
   - **MWIR orientation:** all 183 cutout headers have det(PC) < 0 (normal sky parity) on detectors D1–D6, and the D3 and D6 matrices of the same exposure agree. No mirrored WCS exists at Level 2. The processor relies on the WCS rather than on any assumed flip, and the MWIR frames pass the image and Gaia checks.
2. **Wavelength.** Two independent evaluations at the predicted native pixel: (a) astropy key `W` with `sip=None`, as in the IRSA tutorial; (b) a hand-written bilinear lookup of the `WCS-WAVE` table (FITS Paper III -TAB). The two agree to 9e-16 µm, and the record matches them to within 1e-6 µm. Off-image positions must give `null`. The values that extrapolation would have produced (0.739, 3.820, 1.662 and 1.096 µm) do not appear in the records, so defect 1 in `CASE_SELECTION.md` is not reproduced.
3. **Time.** `observed_at_utc` equals `DATE-AVG` (plus `Z`) and `mjd` equals `MJD-AVG`. `DATE-AVG` and `MJD-AVG` agree with each other to within 0.01 s, and `TIMESYS` is UTC.
4. **Flags.** Bits are decoded from `MSKNnnnn`, and each `MSKMnnnn == 1<<n` was checked. The aperture is r = 2.5 native px. Adverse means any bit except SOURCE or FULLSAMPLE, or a non-finite IMAGE/VARIANCE pixel (or VARIANCE ≤ 0). Screened, adverse, valid and non-finite counts, per-flag counts, flag names and status all match. Counts are `null` for not_covered frames. R Dra frames with 21/21 non-finite pixels are `flagged` and `covered: true`, so defect 2 is not reproduced.
5. **Absent coverage.** `not_covered` occurs if and only if the predicted native position is outside the pixel-center bounds. The four such frames are 1.9–5.7 px off the image (edge-clipped cutouts).
6. **Display stretch.** The PNG equals asinh(10·t) applied to the stated `low`/`high`, byte for byte. Shared limits were recomputed as the pooled 1–99.5 percentiles of the stated group, and the basis text names exactly that group. Per-frame frames say "not directly comparable" in both `basis` and `limitations`. No record text claims flux, magnitude, brightening or detection; every occurrence of those words is a negation.
7. **Provenance.**
   - The sha256 of the raw file equals the record hash and the manifest hash (and the case JSON hash).
   - `source_url` and `original_url` equal the manifest `archive_url`; `cutout_url` equals the manifest `source_url`.
   - `frame_key` equals `OBSID_D{DETECTOR}` from the header.
   - `marker.kind` is always `catalog_prediction`, labeled "(not a detection)".
   - The limitations state concretely: no added resolution, not photometry, not a detection, and catalog prediction.
   - `retrieved_at` is the manifest time, and the record says so.

**Case JSON (decision 6), A and B:**
- Wavelength differs from the case JSON by at most 4.7e-5 µm (tolerance 1e-4).
- Status, MJD, sha256 and URL are identical.
- Dates are identical apart from processor A's added `Z` (see escalation 5).

## Escalations (scientific meaning first)

1. **`moving_neighbor` display requirement gives the wrong expected motion (content, Sathvik).**
   - The case JSON says the marker "should move north by about 2 display pixels at 5 arcsec/pixel". The shipped grid is 6′/256 = **1.406″ per display px**.
   - Independently, the marker moves **4.19 px (5.9″)** from A to B and **7.29 px (10.25″)** from A to C, almost due north (dx = +0.3 and +0.6 px, i.e. slightly west, which is consistent with the negative pmRA).
   - The PNG glow, centroided iteratively in a 14 px window with saturated holes counted as white, shifts 3.2 px north from A to B and 6.6 px from A to C. The visible motion is real and matches the prediction to within about 1 px.
   - Suggested wording: "about 7 display pixels (about 10″, under two SPHEREx pixels)". As written, QA would read a correct 7 px shift as a bug. The worker's flag is **confirmed**.
2. **The gate-2 coordinate 330.84, −56.786 is Eps Ind A's J2000 position (confirmed).**
   - It is 0.46″ from Gaia DR3 6412595290592307840 propagated to J2000.
   - Gaia DR3 puts the star **122.7″ (2.05′) away at 2026.0**, at RA 330.8925, Dec −56.8043, and 127″ away at 2026.9.
   - **What still holds:** the SIA reach test is unaffected, because the images are degrees wide.
   - **What breaks:**
     - A display centered on this coordinate shows the star about 2′ off center: inside a 6′ field, but outside any field narrower than about 3.5′.
     - Any text, marker or "target" annotation that treats the coordinate as the star's position is wrong by about 20 SPHEREx pixels.
   - **Fix:** label the coordinate "J2000 catalog position", or use the 2026.0 propagated position for the live test.
3. **Saturated cores render as transparent holes (A and B).** Non-finite pixels have alpha 0 in the main PNG. On a dark page they look like a black hole in the brightest star: about 40–60 display px for Barnard's Star and up to about 400 for R Dra. That invites the reading "the star is dark in the middle" or "the hole shrank, so it dimmed". The overlay marks them, but the frontend should either show the flag overlay or legend by default for flagged frames, or the processor should paint non-finite covered pixels distinctly. This is display semantics, not a data error.
4. **R Dra `2025W27_2A_0331_1_D4`:** the target is 1.9 native px beyond the image edge, and the star's halo is visible at that edge. `not_covered` with a null wavelength is correct (decisions 3 and 4), but the user-facing copy should say "just outside this image", not imply absence.
5. Cosmetic and integration issues:
   - **Time string format:** A writes `observed_at_utc` as `…845Z`, while the case JSON and processor B write `…845`. Pick one in the contract, or a verbatim comparison (QA step 2) will mismatch.
   - **Schema differences between A and B:** the fields that differ include:

     | A | B |
     |---|---|
     | `display_scale.low/high` | `lo/hi` |
     | `scale_arcsec_per_px` | `scale_arcsec_per_pixel` |
     | `screened_pixels` | `aperture_pixels` |
     | `flag_counts` | `flag_pixel_counts` |
   - **Opposite overlay colors:** A uses red = adverse and yellow = non-finite; B uses red = non-finite and orange = adverse. The frontend must read `flag_image.legend`, not hard-code the colors.
   - **Duplicate frame keys:** A also writes the six case keys under `presets/*/frames/` with a *per-frame* stretch. Cases must load `case-*/`.
   - **B rounds wavelength** to 1e-6 µm. That is fine.
   - **B also subtracts a single median background offset.** This is documented in B's record.
6. Performance: none found.

## Reproduce

```bash
git fetch origin && git checkout codex/parallel-15-science-review   # contains A's products at 9c9049a
~/Library/Python/3.9/bin/uv venv -p /Users/sathvikloke/.local/bin/python3.12 .venv
~/Library/Python/3.9/bin/uv pip install -p .venv/bin/python astropy numpy pillow certifi
DATA="/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data"
.venv/bin/python science/reviews/acceptance/check_acceptance.py --data-root "$DATA"            # 13 frames -> results.json
.venv/bin/python science/reviews/acceptance/check_acceptance.py --data-root "$DATA" --all --out /tmp/results_all.json  # 189 records
.venv/bin/python science/reviews/acceptance/check_processor_b.py --data-root "$DATA"           # B, 6 frames -> results_processor_b.json
```

The Gaia controls are cached in `gaia/*.csv`. They came from the ESA Gaia TAP service (`gaiadr3.gaia_source`, radius 0.075° around each preset `query_center`), with G < 15 for Barnard's Star and RW Aur and G < 17 for the others. VizieR and IRSA TAP were unavailable at the time.

## Limitations of this review

- **Shared trust in the header WCS.** The native celestial WCS is evaluated with astropy (WCSLIB), as in the processor. The independence is in the code paths, not the library. Gaia is the only control independent of both, and it is limited to stars that centroid cleanly (161 of 189 frames, none in fair_comparison C). The independent `astrometry` column (added 2026-11-15) is PASS for 133 of 189 records and UNKNOWN for the rest.
- **Shared astrometry.** Target astrometry comes from the same SIMBAD values the processor uses, so a catalog error would go unnoticed. Annual parallax is not modeled (< 0.6″).
- **Approximate wavelength table.** Wavelength checks rely on the header `WCS-WAVE` table. The SPHEREx supplement calls it an approximation for visualization.
- **Flags not validated physically.** Flag meanings were taken from the `MSKD` descriptions and not checked against the physical data.
- **Not tested:** the live `/api/v1/frame` path, frontend rendering, and processor B beyond its six case frames. B's stretch formula was confirmed against its stated limits (100% within 1 DN), but the way it derives those limits was not recomputed.
