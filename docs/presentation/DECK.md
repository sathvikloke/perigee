# Perigee: seven-slide project demo

Updated 15 November 2026. This self-contained edition explains the project without a presenter.

[Editable presentation](https://chatgpt.com/space/page_c2bdc1167fb481918cc92fabeb2bfc58). [Public PDF](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf). [Technical report](https://perigee.lokesathvik.workers.dev/demo/perigee-technical-report.pdf)

The deck uses Avenir Next, the app’s black/citron palette and original processed NASA/IPAC SPHEREx imagery. Text stays editable in Spaces. The public PDF packages the reviewed 1280×720 renders at 16:9; this preserves the exact layout. The transcript below provides selectable text. Speaker notes in Spaces retain detailed sources and scientific scope.

## Slide 1

PERIGEE   /   PROJECT & PURPOSE

NASA Space Apps 2026. Planet X and SPHEREx.

1 / 7

Perigee

An investigation of NASA’s infrared sky

Enter an object name or sky position. Explore a sequence of SPHEREx observations, then explain what the images support.

The learner’s question

A student sees a star shift between two images. Is it motion, a different infrared wavelength, or an unreliable pixel? Dates and quality information help the student test that first impression.

Our contribution

A public time-sequence viewer, three guided investigations and a portable evidence notebook. The learner’s explanation stays attached to the observations and exact archive sources that support it.

Team Perigee. Planet X and SPHEREx challenge.

Sathvik Loke, Sagar Raut, Akshobya Rao, Aditya Raut, Suhrit Bestavemula and Neeraj Movva

## Slide 2

PERIGEE   /   THE LEARNER EXPERIENCE

A student follows the evidence

NASA Space Apps 2026. Planet X and SPHEREx.

2 / 7

1  Notice the shift

Play Barnard’s Star’s comparison. Its bright glow shifts north against surrounding stars between August 2025 and August 2026.

2  Check the explanation

The pair uses nearly the same wavelength. The shift agrees in direction and approximate size with the catalog prediction. The saturated core limits precise position measurements.

3  Keep a reasoned conclusion

The student records what changed, what it supports and what remains uncertain. A reference helps them reflect. The saved evidence lets a teacher revisit the observations behind the answer.

Actual app screenshot. NASA/IPAC SPHEREx observations. The target ring marks a catalog prediction.

## Slide 3

PERIGEE   /   THREE GUIDED INVESTIGATIONS

Three decisions a learner can explain

NASA Space Apps 2026. Planet X and SPHEREx.

3 / 7

Each case makes a different question concrete. Wavelength is the “color” of infrared light. Quality flags identify pixels that need care.

25 Aug 2025 / 19 Aug 2026

Barnard’s Star: Recognize apparent motion

At similar wavelengths near 2.0 µm, the glow shifts north while neighboring stars remain nearly fixed. The learner can support a qualitative motion interpretation and explain why saturation limits a precise measurement.

Same exposure, 29 Apr 2026

Epsilon Indi B: Choose a fair comparison

A five-month pair explores time at similar wavelengths. The pictured pair shows 2.3232 and 4.9399 µm at the same moment. The learner separates wavelength from time and checks display contrast before comparing gray levels.

7 Nov 2025 / 10 Nov 2025

WISE 0855 field: Test an apparent jump

A flagged bright dot appears to move over three days. A detector-coordinate control explains its sky shift as the pointing changes. The learner can reject a moving-object claim using the flags and a testable alternative.

## Slide 4

PERIGEE   /   CHALLENGE IMPLEMENTATION

Public search. Five reviewed target fields.

NASA Space Apps 2026. Planet X and SPHEREx.

4 / 7

An object name or a sky position

Name resolution or decimal/sexagesimal coordinates locate a field. NASA/IPAC IRSA supplies SPHEREx Level 2 FITS observations from Data Release 1 and Quick Release 3.

A sequence with context

Python places images on a fixed north-up sky grid and retains dates, wavelengths, quality flags and source links. The browser can play the sequence while completed frames remain cached.

React/TypeScript frontend on Cloudflare. Python/FastAPI service with Astropy, NumPy and Pillow.

RETAINED TARGET REVIEW

Barnard’s Star

Apparent northward shift. Saturation limits precision.

Epsilon Indi B

Time and wavelength comparisons, with display context.

WISE 0855 field

A detector-fixed feature tests a moving-object interpretation.

RW Aurigae

An unresolved binary calls for system-level interpretation.

R Draconis

Saturation must be checked before comparing brightness.

All five: catalog identity, position/epoch, propagated marker and shipped records reviewed. RW Aurigae and R Draconis have no variability claim.

## Slide 5

PERIGEE   /   RETAINED SCIENTIFIC CHECKS

A convincing jump has a testable explanation

NASA Space Apps 2026. Planet X and SPHEREx.

5 / 7

5.36″ observed. 5.38″ predicted.

The shifts above are in arcseconds. The feature stays at detector pixel (1709, 1364). Three usable stars predict almost the same apparent sky shift for that fixed pixel as the pointing changes. Their own sky positions agree within 0.76″.

Adverse mission flags support the check. The feature’s physical cause remains unknown.

183 unique cutouts. 189 records.

The historical processing audit includes six case re-renders. A separate code path reproduced source-file values, display mapping and provenance from the FITS inputs.

128 PASS. 55 UNKNOWN. 0 FAIL.

Independent Gaia field-star alignment checks cover the 183 unique cutouts. UNKNOWN means too few usable stars. Alignment verdicts do not certify source identity.

Control test: all nine deliberate 1-, 2- and 5-native-pixel shifts on three real-frame fixtures were rejected. Methods and inputs are retained.

## Slide 6

PERIGEE   /   OUR CONTRIBUTION

The explanation travels with its evidence

NASA Space Apps 2026. Planet X and SPHEREx.

6 / 7

A learner-authored result

The student writes an observation, an explanation and remaining uncertainty. A completed investigation produces a record someone else can inspect and question.

The exact observations remain attached

The export retains frame IDs, dates, wavelengths, quality results, display settings and archive URLs. File fingerprints and processing details trace the images to their inputs.

Existing viewers already compare images. Perigee connects that activity to a short investigation and a portable record of the learner’s reasoning.

COMPLETED EVIDENCE CARD

Excerpts of an actual evidence card authored for this demonstration. JSON preserves the structured record and its source references.

## Slide 7

PERIGEE   /   PEOPLE & PROJECT LINKS

A conclusion a class can discuss

NASA Space Apps 2026. Planet X and SPHEREx.

7 / 7

A student has something to explain

The activity starts with a visible change. The student tests an interpretation and leaves with their own conclusion, supported by named observations.

A teacher can inspect the reasoning

Give a class the same image pair, then compare their explanations. Each saved record shows which dates, wavelengths and quality evidence shaped the answer.

A new question gives a reason to return

Try another investigation, reopen saved work or search a new object. Astronomy clubs can debate the WISE feature and inspect the retained control together.

OPEN THE PROJECT

perigee.lokesathvik.workers.dev

Start with Barnard’s Star. Play the comparison, follow the checks and save an evidence record.

READ THE METHODS & CODE

github.com/sathvikloke/perigee

Technical report (10 pages)

Processing, control experiments and source records are public.
