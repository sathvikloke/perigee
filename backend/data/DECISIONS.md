# Data pipeline decisions log (Sagar, 2026-11-14)

In the order they were made. ⚠ marks the ones Sathvik or the team should look at.

1. **Raw data rebuilt from IRSA instead of waiting for a transfer.** `tools/ingest/fetch_manifest.py`
   re-downloads every cutout in `research/build_data/manifest.json` and checks it against the
   audit's SHA-256. All 183 matched byte for byte. Anyone can now rebuild the dataset in
   ~10 minutes without Sathvik's laptop.
2. **Search uses SIA v2, not TAP.** Both were tried. TAP returned 502s and 60 s timeouts. SIA
   returned 502s about half the time but answered fast, so retries work.
3. **Wavelength: SIP keywords stripped before building the "W" WCS.** With them left in,
   astropy applies the sky distortion to the wavelength lookup and is ~0.0014 µm off.
   Checked against a direct bilinear read of the WCS-WAVE table.
4. **Flag classes read from each file's header** (`MSKN`/`MSKM` cards), not hard-coded. Bits
   the header doesn't name count as adverse.
5. **Display stretch tied to noise.** Limits are −2σ and the 99.9th percentile, with asinh
   softening of 4σ (σ = 1.4826 × MAD). A fixed percentile stretch either hid Barnard's field
   stars behind the bright star or turned Epsilon Indi B's field into noise.
6. **Bilinear display resampling, flags nearest-pixel.** ⚠ Processor-a uses nearest-pixel for
   both, which looks blocky but shows the true 6.15″ pixels; this branch looks smoother. The
   science values are identical (see the comparison below). This is a look-and-feel choice for
   whoever picks the base.
7. **No-data pixels are never filled in.** A bug found while comparing with processor-a: the
   first bilinear version filled single NaN pixels from their neighbours, which painted a value
   into Barnard's saturated core. Fixed and tested.
8. **Aligned with the integration board** after it appeared mid-session: `frame_key`,
   mid-exposure time, `not_covered` = off-image only, non-finite pixels = `flagged`, null
   wavelength off-image, Sathvik's six case frames. The first version had joined the detector
   into `observation_id` and used exposure-start time.
9. **Catalog propagation uses parallax distance and radial velocity** (astropy space motion).
   For Barnard's Star the RV term moves the predicted marker ~0.4″ over 26 years. Times are
   built in TDB from Julian years, so no leap-second table is needed.
10. ⚠ **Stricter "unknown"** than the board in two edge cases: a file with no VARIANCE extension,
    and a clipped edge circle with under 10 usable pixels. The board's rule would call these
    "clear"; the contract (scenarios 14–15) asks for a screen with enough evidence behind it.
    None of the 183 retained frames hits either case.
11. **Curated presets use a 4′ field** (contract range 2–10′). The audit cutouts are 6′ squares at
    any angle, so a 6′ north-up grid has empty corners (88.6% coverage on average) while 4′ is
    always fully covered. The live default stays 6′, and those cutouts are requested 1.5× larger,
    so live frames have no empty corners.
12. **Asset IDs** are `<preset>.<frame_key>.<set>.<image|flags>.v1` and are listed in
    `backend/content/presets/manifest.json` with SHA-256 and size. PR #10 (catalog) was written
    against processor-a's folder layout, so serving this package needs a small loader change
    there, or the comparison task picks processor-a's layout.
13. ⚠ **Registration check limited to same-wavelength frames.** Whole-field cross-correlation
    reported a false 55″ shift between Epsilon Indi B A (2.3 µm) and C (4.9 µm), because stars
    change brightness between those wavelengths. A↔C was checked instead by the target's own
    light center: within 0.5–0.65″ of the marker in A, B and C.
