# Perigee: seven-slide project demo

Updated 15 November 2026. This self-contained edition explains the project without a presenter.

[Editable presentation](https://chatgpt.com/space/page_c2bdc1167fb481918cc92fabeb2bfc58) · [Public PDF](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf) · [Technical report](https://perigee.lokesathvik.workers.dev/demo/perigee-technical-report.pdf)

The deck uses Avenir Next, the app’s black/citron palette and original processed NASA/IPAC SPHEREx imagery. Text stays editable in Spaces. The public PDF packages the reviewed 1280×720 renders at 16:9; this preserves the exact layout. The transcript below provides selectable text. Speaker notes in Spaces retain detailed sources and scientific scope.

## Slide 1

PERIGEE   /   PROJECT & PURPOSE

NASA Space Apps 2026 · Planet X and SPHEREx

1 / 7

Perigee

Investigate change in NASA’s infrared sky

A free web app for students, teachers and astronomy clubs to compare observations from NASA’s SPHEREx infrared telescope and explain what the evidence supports.

The problem

Two images of the same sky can look different because a star moved, the telescope sampled another infrared wavelength, or a pixel is unreliable. Seeing a change is only the start; the observer needs a way to decide what caused it.

What we built

Perigee combines aligned images, guided comparison checks and a saved evidence notebook. A learner finishes with their own explanation, the observations behind it and links back to NASA’s archive. Three cases teach the process; five targets and live search extend it.

Team Perigee · Planet X and SPHEREx challenge

Sathvik Loke · Sagar Raut · Akshobya Rao · Aditya Raut · Suhrit Bestavemula · Neeraj Movva

## Slide 2

PERIGEE   /   PRODUCT WALKTHROUGH

From a first look to a supported explanation

NASA Space Apps 2026 · Planet X and SPHEREx

2 / 7

1  Choose and play

Open a guided case and press Play comparison. The two images alternate in the same position, making small changes easier to spot against nearby stars.

2  Check the comparison

Barnard’s Star is shown on 25 Aug 2025 and 19 Aug 2026 at nearly the same infrared wavelength. Its glow shifts north against the field stars, consistent with the catalog prediction of about seven display pixels (10 arcseconds).

3  Explain and keep the evidence

The learner records what they noticed, what it supports and what is uncertain. After the checks and notes are complete, a reference answer helps them reflect. Their own words remain saved and can be reopened, printed or exported.

Actual app screenshot · NASA/IPAC SPHEREx images · The ring is a catalog prediction; the saturated center limits precise position measurements.

## Slide 3

PERIGEE   /   THREE GUIDED INVESTIGATIONS

Each case teaches a different comparison

NASA Space Apps 2026 · Planet X and SPHEREx

3 / 7

Wavelength is the “color” of infrared light, measured here in micrometers (µm). Problem flags mark pixels the mission pipeline considers unreliable.

25 Aug 2025 / 19 Aug 2026

Barnard’s Star · Can you see a star move?

Across a year near 2.0 µm, the glow shifts north while field stars stay nearly fixed. This agrees with the predicted motion. The bright core overloads the detector, limiting its exact image position.

Same exposure · 29 Apr 2026

Epsilon Indi B · Is this a fair comparison?

One pair compares dates five months apart near 2.323 µm. Another compares 2.3232 and 4.9399 µm at the same moment. The latter tests wavelength, not time. The learner also checks display contrast before interpreting a difference in gray level.

7 Nov 2025 / 10 Nov 2025

WISE 0855 field · A dot that jumps

A bright dot appears to jump over three days at closely matched wavelength. The quality overlay identifies the unreliable feature. The learner can explain why this apparent jump is insufficient evidence for a moving celestial object.

## Slide 4

PERIGEE   /   NASA DATA & IMPLEMENTATION

How archive files become a usable investigation

NASA Space Apps 2026 · Planet X and SPHEREx

4 / 7

1  Retrieve the data

NASA/IPAC’s Infrared Science Archive (IRSA) provides SPHEREx Level 2 observations from Data Release 1 and Quick Release 3. We retrieve small FITS cutouts: scientific files containing pixels, observation times, wavelength information and quality flags.

Object names resolve through SIMBAD/Sesame. Search also accepts decimal or sexagesimal sky coordinates, such as hours:minutes:seconds.

2  Process consistently

Python uses each file’s sky coordinates to place observations on one fixed, north-up grid. It reads the wavelength at the target’s detector position, converts pixel values into a stated display contrast, and preserves quality information.

Display contrast maps measurements to gray; different scales can make the same value look different. The target marker is a catalog prediction.

3  Deliver in the browser

React and TypeScript provide comparison playback, optional flag overlays, guided checks and the notebook. Cloudflare serves the app and prepared cases; a Python/FastAPI service on Vercel handles live archive requests.

Two frame requests run at once, with bounded retries and a cache of completed results. The first ready image is usable while others load.

NASA/IPAC IRSA: irsa.ipac.caltech.edu/Missions/spherex.html · SIMBAD: target context · ESA Gaia DR3: independent field-star checks

## Slide 5

PERIGEE   /   PROCESSING & SCIENTIFIC VALIDATION

Checks that make the comparisons inspectable

NASA Space Apps 2026 · Planet X and SPHEREx

5 / 7

We checked the processed images against their source files and tested alignment against an external star catalog. The checks answer different questions.

189 image records

SOURCE-FILE CONSISTENCY

The 14–15 November processing sweep covered 183 unique cutouts plus six case re-renders. A separate code path recomputed wavelengths, timestamps, quality flags, coverage, display mapping and source records. The results matched the published products, so the displayed evidence can be traced back to the original files.

128 PASS · 55 UNKNOWN · 0 FAIL

183 UNIQUE CUTOUTS · EXTERNAL ALIGNMENT

Independent field-star detections were compared with Gaia DR3 positions. PASS means the alignment met the validator’s thresholds; UNKNOWN means too few usable stars supported a verdict. Unknown cases stay visible as uncertainty. This check tests the sky grid separately from the moving target.

Deliberate error test

The validator rejected every injected 1-, 2- and 5-native-pixel shift on the three tested real-frame fixtures.

## Slide 6

PERIGEE   /   OUR CONTRIBUTION

A saved explanation with the data behind it

NASA Space Apps 2026 · Planet X and SPHEREx

6 / 7

One continuous investigation

Perigee connects image comparison, scientific checks and learner-written reasoning in one workflow. The learner chooses an interpretation and explains it using the selected observations. The reference appears after they record their own thinking.

Someone else can inspect the reasoning

Each export retains the observation IDs, dates, wavelengths, quality results, archive URLs, raw-file SHA-256 fingerprints and processing details. The notes autosave in the browser. JSON preserves the structured record; printing creates a PDF for a teacher, classmate or club.

EXAMPLE COMPLETED EVIDENCE CARD

Observation

In images A and C, the bright glow shifts north relative to the surrounding stars.

Explanation

The shift is consistent with Barnard’s Star moving across the sky, as the catalog predicts.

Evidence and uncertainty

A: 25 Aug 2025, 2.0062 µm. C: 19 Aug 2026, 2.0284 µm. The core is saturated, so its exact center is uncertain. The exported card links both observations to IRSA.

Illustrative completed record, not a user testimonial. The contribution is the integrated reasoning workflow and retained provenance.

## Slide 7

PERIGEE   /   PEOPLE, REUSE & PROJECT LINKS

Why this is useful beyond a single demonstration

NASA Space Apps 2026 · Planet X and SPHEREx

7 / 7

For a student

Start with a concrete question and real NASA images. Practice separating what is visible from the explanation it supports. Leave with a written conclusion that can be discussed, rather than only a screenshot.

For a teacher or astronomy club

Use a guided case as a short activity. Compare explanations against the same observations, then discuss how dates, wavelengths or unreliable pixels shaped the conclusion. No account or installation is needed.

A reason to return

Reopen saved notes or try another target: Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae or R Draconis. Live search extends the workflow to your own object or coordinates.

OPEN THE PROJECT

perigee.lokesathvik.workers.dev

Start with Barnard’s Star. Play the comparison, follow the checks, then save an evidence card.

READ THE METHODS & CODE

github.com/sathvikloke/perigee

Technical report (8 pages)

Processing, experiments, source links and reproduction instructions are public.
