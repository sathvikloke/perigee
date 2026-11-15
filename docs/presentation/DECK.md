# Seven-slide presentation

**Historical deck:** this PDF predates the final usability release and third-case integration. Use the [current video script and submission plan](SUBMISSION_VIDEO.md). If this deck is selected instead of the video, refresh its captures and claims first; in particular, quality flags establish unreliable evidence, not the cause of an artifact, and the processing sweep is distinct from independent astrometric coverage.

The completed deck uses the released app and real processed NASA SPHEREx images. It includes the team and challenge, a learner story, the actual interface, the data sources, and the product limits.

- [Public presentation PDF](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf)
- [Repository copy](../../frontend/public/demo/perigee-demo.pdf)
- [Live investigation](https://perigee.lokesathvik.workers.dev/?preset=epsilon_indi_b)
- [Longer demo script and rehearsal](README.md)

The PDF has seven 16:9 pages. An editable presentation is saved in Sathvik's connected Spaces account as **Perigee — NASA Space Apps demo**. The public PDF preserves the historical reviewed slide renders; use the editable deck for changes, then replace this public copy. A successful submission has not been confirmed.

## Presenter notes and sources

### 1. Perigee: investigate the infrared sky

Perigee is a public web app for comparing real NASA SPHEREx observations and writing a conclusion with traceable evidence. Audience hypotheses: learners, educators and astronomy clubs. No user impact study is claimed. Image is a real processed SPHEREx observation, not generated imagery. Source: NASA/IPAC IRSA, frame 2026W18_1A_0516_1_D3; https://irsa.ipac.caltech.edu/Missions/spherex.html. Challenge: https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/. Team names follow docs/TEAM.md and the published team page.

### 2. Did this brown dwarf change?

Illustrative learner scenario, not an interviewed user. Open the Epsilon Indi B investigation and blink A+B. Dates differ by 150.8 days and predicted-position wavelengths by about 0.0012 micrometers. Both pass the local flag screen. These are initial comparison checks, not a quantitative variability measurement. No visible change does not prove no change: the display stretch clips the core to white. Screenshot from the rehearsed, released app. Sources: backend/content/cases/fair_comparison.json; science/reviews/epsilon/README.md; NASA/IPAC IRSA SPHEREx DR1 and QR3, https://irsa.ipac.caltech.edu/Missions/spherex.html.

### 3. Same moment, different infrared color

Switch A+C in the live app. Both frames were taken on 29 April 2026 at 12:05:47.874 UTC by different detectors. At 4.94 micrometers Epsilon Indi B stands out relative to field stars. Wavelength and each image’s display stretch differ. Do not claim every pixel difference is caused only by wavelength, or read a flux ratio from display greys. Sources: fair_comparison case JSON and science/reviews/epsilon/README.md; original NASA/IPAC IRSA frame 2026W18_1A_0516_1, detectors 3 and 6. Screenshot is real app capture.

### 4. A convincing change can be a bad pixel

Point to the red dot just below and right of the ring. The original FITS pixel is flagged NONFUNC, TRANSIENT, SUR_ERROR and SOURCE. It is outside the small central quality-screen aperture, so the target can pass that screen while this neighboring artifact is still present. This is an actual reviewed example, not a simulated discovery. The screenshot is cropped to observation A for legibility; the data and colors are unchanged. Source: science/reviews/epsilon/README.md finding 4 and the original NASA/IPAC SPHEREx FITS frame 2026W18_1A_0516_1_D3.

### 5. A conclusion someone else can check

The screenshot shows a rehearsal example, not a measured student result. The product is intended for learners, teachers and astronomy clubs; those audiences and learning benefits are hypotheses. Demonstrated behavior: autosave, Reopen, JSON download and a readable 3-page PDF. Export carries frame IDs, UTC dates, wavelengths at the predicted position, quality, original archive URLs, raw file SHA-256, processing version, case limitations and learner notes. Notes stay in the browser unless exported. Sources: docs/presentation/rehearsal/evidence-card-fair_comparison.json and corresponding PDF; qa/public-release/README.md; qa/production-journey/README.md.

### 6. Any sky position, real NASA observations

This is a general coordinate viewer, not only a preset gallery. A logged-out production smoke search outside the presets returned 377 archive matches and processed a real frame. Results remain in observation-time order; partial archive failures stay visible and can be retried. All 189 bundled records (183 frames plus 6 case copies) passed independent code re-derivation from original FITS; this does not establish scientific discoveries or user learning. NASA/IPAC IRSA provides SPHEREx L2 DR1/QR3 imagery; SIMBAD provides target context; ESA Gaia DR3 supports field registration. Sources: https://irsa.ipac.caltech.edu/Missions/spherex.html; https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/; https://simbad.cfa.harvard.edu/; https://www.cosmos.esa.int/web/gaia/dr3; science/reviews/acceptance/README.md; qa/public-release/smoke.txt.

### 7. Try a complete investigation

Open https://perigee.lokesathvik.workers.dev/?preset=epsilon_indi_b for the main demonstration; Barnard’s Star is the moving-star backup. Curated cases work from bundled products when IRSA is unavailable; live coordinate searches still depend on the archive. Repeat use is supported by five targets, arbitrary coordinates, local notes and Reopen, rather than a claim of existing retained users. The app is a hackathon prototype and does not measure calibrated brightness or proper motion. All project code and data provenance are public at https://github.com/sathvikloke/perigee. AI assistance: Claude Code and Codex contributed implementation and these presentation materials; no AI model runs in the app. Full project account: https://github.com/sathvikloke/perigee/blob/main/docs/AI_USE.md. Sources: qa/public-release/README.md; qa/production-journey/README.md; backend/content/cases/moving_star.json.

## Verification

Created and reviewed on 2026-11-15. The saved presentation contains exactly seven slides; all seven were individually rendered and visually reviewed. The PDF was reopened with a PDF parser, confirmed to contain seven 960 × 540 point pages, rendered with Poppler, and all seven rendered pages were inspected. There are no unresolved placeholders, cropped main text, or added simulated NASA images. The screenshots are real rehearsal captures. The evidence notebook contains clearly illustrative rehearsal notes, not user research results.

PDF SHA-256: `ffab44ce1f9fe182d2b9f427ae186c30e18e2cfc7ff6ea24099ecbd8d05ca89e`.
