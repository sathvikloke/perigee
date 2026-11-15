# Perigee: seven-slide project demo

Updated 15 November 2026. This replaces the historical deck.

[Editable presentation](https://chatgpt.com/space/page_c2bdc1167fb481918cc92fabeb2bfc58) · [Public PDF](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf) · [Technical report](https://perigee.lokesathvik.workers.dev/demo/perigee-technical-report.pdf)

The deck uses Avenir Next, the app’s black/citron palette and original processed NASA/IPAC SPHEREx imagery. Text stays editable in Spaces. The public PDF packages the reviewed 1280×720 renders at 16:9; this preserves the exact layout. The transcript below provides selectable text. Speaker notes in Spaces retain detailed sources and scientific scope.

## Slide 1

PERIGEE   /   THE IDEA

NASA Space Apps 2026   ·   Planet X and SPHEREx

1 / 7

Perigee

Investigate change in
NASA’s infrared sky

A moving dot can be a star, a different infrared view, or an unreliable pixel.

Perigee guides learners through SPHEREx observations so they can explain what changed—and save the evidence behind their conclusion.

AUG 2025

AUG 2026

Same field. A year apart.
What does the change support?

NASA/IPAC SPHEREx images
Saturated centers: visual comparison only

Sagar Raut · Akshobya Rao · Aditya Raut · Neeraj Movva · Sathvik Loke · Suhrit Bestavemula

## Slide 2

PERIGEE   /   THE LEARNER’S JOURNEY

Follow Barnard’s Star across a year

NASA Space Apps 2026   ·   Planet X and SPHEREx

2 / 7

A · 25 AUG 2025

C · 19 AUG 2026

2.0062 µm

2.0284 µm

NASA/IPAC SPHEREx · same sky grid · saturated centers

01   NOTICE

Play the comparison. Watch the glow shift against the surrounding field stars on a fixed sky grid.

02   CHECK

Read dates, wavelengths and flags. The catalog predicts about 10 arcseconds of movement; saturation limits exact position measurements.

03   RECORD

Save what you noticed, your explanation and its limits. Reopen, export or print the source-linked notebook.

## Slide 3

PERIGEE   /   THREE CASES

A visible difference has several explanations

NASA Space Apps 2026   ·   Planet X and SPHEREx

3 / 7

25 Aug 2025 / 19 Aug 2026

CHANGE OVER TIME

Barnard’s Star

A year apart, near 2.0 µm. The glow shifts relative to field stars, consistent with the catalog prediction. Its saturated center limits precise measurements.

29 Apr 2026 · A / C wavelengths

CHANGE IN WAVELENGTH

Epsilon Indi B

A+B: nearly the same wavelength, five months apart. A+C: the same moment at 2.3232 and 4.9399 µm. Different stretches prevent a brightness ratio.

7 Nov 2025 / 10 Nov 2025

UNRELIABLE EVIDENCE

WISE 0855

A bright dot jumps over three days at closely matched wavelength. Quality flags make it unreliable evidence for motion; they do not identify the physical cause.

Images: NASA/IPAC SPHEREx. Transparent / missing values are not dark sky. Sources and case records in speaker notes.

## Slide 4

PERIGEE   /   DATA & METHOD

Trace each comparison back to NASA data

NASA Space Apps 2026   ·   Planet X and SPHEREx

4 / 7

01

Archive

NASA/IPAC IRSA supplies SPHEREx Level 2 FITS cutouts from DR1 and QR3: science pixels, times, wavelength maps and quality masks.

02

Processing

Python maps images to a common north-up grid, computes target-position wavelength, decodes quality flags and records contrast mapping.

03

Investigation

Curated cases or a live name / coordinate search lead to a learner-written explanation, attached to the exact observations and their limitations.

EVIDENCE EXPORT

IDs · dates · wavelengths · quality · archive URLs · raw-file hashes · processing version

SIMBAD: target context · Gaia DR3: field-star checks · Resampling adds no spatial resolution · React / FastAPI / Cloudflare

## Slide 5

PERIGEE   /   VALIDATION

What the checks establish

NASA Space Apps 2026   ·   Planet X and SPHEREx

5 / 7

189

PRODUCTS IN THE PROCESSING AUDIT

183 unique cutouts + six case re-renders

The 14–15 November sweep recomputed wavelengths, times, flags, coverage, contrast mapping and provenance. Image reconstruction checked consistency with the FITS headers.

183 unique cutouts

INDEPENDENT FIELD-STAR REGISTRATION

128

55

0

PASS

UNKNOWN

FAIL

UNKNOWN means too few usable field stars.
It is not a pass.

Negative controls

Every injected 1-, 2- and 5-pixel shift was detected in the tested fixtures. Scripts and results are public.

Audit scope: 14–15 Nov 2026. Methods, retained results and validation scripts are published in science/reviews.

## Slide 6

PERIGEE   /   CONTRIBUTION & AUDIENCE

Reasoning that stays connected to its sources

NASA Space Apps 2026   ·   Planet X and SPHEREx

6 / 7

Notice → explain → revisit

Perigee brings observations, comparison checks and a written explanation into one guided workflow. Every conclusion stays attached to the images that support it.

Keep the result

Reopen saved reasoning, export the observations as JSON, or print an evidence card for discussion. Follow another target or a new archive query.

EXAMPLE EVIDENCE RECORD

I noticed…

The bright glow shifts north against field stars.

This supports…

Motion consistent with the catalog prediction.

Limit: saturation prevents a precise position.

Students · teachers · astronomy clubs

Five targets, three guided cases and live archive search give learners several ways to continue exploring.

Example evidence record. Observation IDs, archive URLs and processing details travel with the exported reasoning.

## Slide 7

PERIGEE   /   IMPACT & NEXT STEP

Turn a sky image into an explanation you can check

NASA Space Apps 2026   ·   Planet X and SPHEREx

7 / 7

A complete investigation

Notice an apparent change. Check the dates, wavelengths and image quality. Write an explanation, compare it with the case reference, and keep the observations and sources together.

The result is a piece of scientific reasoning that another person can inspect and discuss.

Why it matters

Learners can practice explaining evidence. Teachers and astronomy clubs can discuss both the conclusion and how it was reached.

perigee.lokesathvik.workers.dev

Code, methods and validation: github.com/sathvikloke/perigee

Three guided cases · Five targets · Saved evidence · Reproducible processing · Public methods and validation
