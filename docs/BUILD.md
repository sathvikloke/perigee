# Build specification

Build application and processing code from scratch during the event. The sections below specify intended behavior; no endpoints exist yet.

# The exact weekend product

The core journey is **choose a case or enter coordinates → inspect a chronological image sequence → check wavelength and quality → record a claim, evidence, and limitation → save or share the investigation**. A first-time visitor gets a clear starting question. An experienced visitor can go straight to coordinates.

| Priority | Deliverable | Completion condition |
|---|---|---|
| Required | Public RA/Dec viewer | A coordinate outside the five presets produces a real archive query and a chronological result or an honest empty/error state |
| Required | Time and wavelength controls | Time order uses observation dates; each frame shows its wavelength; changing wavelength is distinct from advancing time |
| Required | Five challenge presets | Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae, and R Draconis are accessible with correct labels and provenance |
| Required | Quality and coverage context | Missing coverage and flagged pixels are visible; a near wavelength match is not labeled a scientifically validated comparison |
| Required | Two complete investigations | Epsilon Indi B and Barnard’s Star have prompts, usable imagery, and a supported conclusion with limitations |
| Required | Evidence card | Records selected observations, dates, wavelengths, source links, learner claim, and uncertainty; saves locally and exports JSON or prints |
| Required | Share and failure handling | Target coordinates survive a URL; saved observations retain IDs; loading, partial results, no coverage, and archive errors are distinct |
| Optional after acceptance | Third investigation | WISE 0855 demonstrates why image coverage is not the same as detecting an object |
| Deferred | Quantitative science and platform features | Full spectra, calibrated light curves, proper-motion measurements, asteroid chemistry, ML classification, accounts, community feeds, and all-sky searches |

The challenge explicitly asks for a public website that accepts coordinates and shows time-ordered images. Spectra, image arithmetic, overlays, and other additions are optional. A preset-only story site would therefore leave the central requirement unfinished. [Official Planet X and SPHEREx challenge](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/).

## The two investigations

**1. Is this a fair comparison? — Epsilon Indi B.** Start with the candidate April 29 and September 27, 2026 observations identified in the research audit. Their audited predicted-source wavelengths are approximately 2.3232 and 2.3220 micrometers, and the selected central apertures passed the conservative flag screen. Regenerate their display products and verify these properties with the new processor before selecting them for the app. Let the learner examine dates, wavelength differences, and flags before making a statement. The supported finding is that this pair passes initial comparison checks; that does not establish a brightness change or measured motion.

**2. Follow a nearby moving star — Barnard’s Star.** Generate new display products from the retained original observations, blink them on the same sky grid, and compare the bright target with the surrounding field. Explain its known motion and distinguish a catalog-predicted marker from a measured centroid. Bright central pixels were flagged in the audited data, so verify and carry that limitation into the card. Do not report a new proper-motion value or precise brightness result.

A possible third case is **What does an empty-looking image tell us? — WISE 0855**. It would teach the distinction between coverage, visual appearance, and a statistically supported detection. An apparently empty preview alone does not prove that the object is absent or provide a calibrated upper limit. Author and implement this optional case during the event if the two core cases are complete.

## Small architecture

Use the current [integration contract](INTEGRATION_CONTRACT.md) for architecture and endpoint definitions. The selected product is a responsive React/TypeScript web app with a Python FastAPI backend hosted through Vercel. The contract replaces the earlier persistent-server/job-queue outline with bounded metadata searches and individual frame-processing requests. Vercel Services is the preferred single-project deployment and is currently Beta; Suhrit owns its early validation and the documented two-project fallback.

Align images to a fixed celestial grid so real motion remains visible. Do not center every frame on the predicted moving object and accidentally erase motion. Keep date and wavelength controls separate; the same detector does not guarantee the same wavelength. Display actual wavelength separation rather than inventing a universal comparison-confidence score. Do not use raw image subtraction as a proof of variability.

# Acceptance, risks, and cut order

Acceptance should test user-visible behavior: enter an unseen valid coordinate; verify the displayed frames are in observation-time order; inspect all five presets; distinguish out-of-coverage from HTTP failure; change wavelength without pretending time advanced; inspect a flagged example; save and reopen an evidence card; verify exported observation IDs and source URLs; and open the public deployment in a fresh browser without the developer’s credentials. Check phone, laptop, and presentation layouts, keyboard operation, and a pause control for blinking.

For scientific checks, trace the selected case frames back to raw metadata, verify fixed-grid registration against surrounding sources, keep predicted markers explicitly labeled, and confirm that no UI text claims a measured discovery, flux change, or composition that the pipeline has not established. A clean central flag screen is not a certificate of scientific validity.

If time permits, ask someone who has not built the app to complete one case and explain what they learned and what remains uncertain. This is a small usability check, not a requirement for recruited users or a statistically credible impact study. A recorded complete flow and a reproducible evidence card are already useful demonstration evidence.

| Risk | Already observed or plausible failure | Response |
|---|---|---|
| Archive reliability | Five selected downloads returned HTTP 503 after retries | Prepared cache, bounded retries, partial results and explicit unavailable status |
| Scientific overclaim | Bright targets are flagged; wavelength, background, PSF and coverage vary | Explain limits; defer calibrated measurements; show actual metadata |
| Live-query scope | A polished preset experience can hide an unfinished requirement | Make a new coordinate the Saturday acceptance gate |
| Integration | Parallel frontend, backend and data work diverges | One manifest contract, early deployed slice, shared fixture data |
| Presentation timing | Exact Sunday local slot is not published in the checked sources | Ready by noon or earlier if instructed; retain a backup demo |
| Excess features | AI, spectra, accounts and custom infrastructure consume the weekend | Cut them before cutting the viewer, evidence flow or verification |

Cut optional AI first, then the third investigation, elaborate animation, optional catalog overlays, and visual extras. Preserve actual NASA data, general coordinate input, chronological viewing, essential wavelength/quality context, the two completed investigations, attribution, and the public submission.
