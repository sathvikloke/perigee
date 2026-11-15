# Space Apps project page: ready-to-paste draft

This draft is for the submission owner (Sagar) and Sathvik, reconciled with the 15 November released app. **No submission confirmation has been inspected.** Use the [current video script and Sunday schedule](presentation/SUBMISSION_VIDEO.md) for recording and timing.

The fields below follow the official [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/), read on 2026-11-15. The guide states no character limits for these fields. Every fact here comes from the released app (`main`), the README, `docs/presentation/` and the science reviews.

Items marked **OWNER** are personal team facts that only the team can confirm.

---

## Project Name

Perigee

## High-Level Project Summary

Perigee is a free web app that lets anyone investigate NASA SPHEREx infrared images of a real object and evaluate claims about change with evidence. Two pictures of the same patch of sky can look different for reasons that have nothing to do with change:
- they were taken at a different infrared wavelength;
- they were contrast-stretched differently for display;
- an unreliable pixel sits next to the target.

Perigee puts real SPHEREx observations from NASA/IPAC IRSA on one fixed sky grid, in date order. It keeps the date, the wavelength at the target and the image-quality flags beside every image, and walks the learner through telling those causes apart. The learner finishes with an evidence card that states what they saw, what they still cannot tell, and exactly which archive files support it.

It addresses Planet X and SPHEREx through three guided investigations (Barnard's Star, Epsilon Indi B and WISE 0855), five preset targets, and live archive search by object name or sky coordinates. The intended benefit is a learner-authored conclusion that a teacher, club leader or fellow observer can follow back to the data.

## Link to Project Demo

**OWNER: paste the public link to the final video after recording, uploading and checking it logged out.** The [59-word script and shot plan](presentation/SUBMISSION_VIDEO.md) target a 29-second export. This is the only unfilled media field; do not paste this instruction into the official form.

The refreshed [seven-slide PDF](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf) is the ready alternative for this field. Use one primary Project Demo link. If the video is primary, include the deck and report as supporting links in Detailed Project Description.

## Link to Final Project

https://perigee.lokesathvik.workers.dev

This is the public web app; no login is needed. The source code is at https://github.com/sathvikloke/perigee and is public.

## Detailed Project Description

Supporting materials: [Seven-slide project deck](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf) · [Technical report: methods, validation and reproducibility](https://perigee.lokesathvik.workers.dev/demo/perigee-technical-report.pdf). The report is optional supporting documentation, hosted publicly; the form does not upload documents directly.

**What it does.** A learner opens an investigation and compares two SPHEREx observations of the same target.

In the **Epsilon Indi B** case (a pair of brown dwarfs about 12 light-years away):
- Frames A and B were taken five months apart at nearly the same wavelength (2.323 and 2.322 µm). That makes them a fair test of change over time.
- Frame C was taken at the same moment as A but at 4.94 µm, and looks very different. Each frame there has its own contrast stretch, and the app says plainly that this pair compares wavelengths, not time.
- A bright dot beside the target in A is marked by the mission's quality flags. Those flags make it unreliable evidence; they do not prove the physical cause of the dot.

In the **Barnard's Star** case:
- Barnard's Star has the largest known proper motion of any star. Its catalog-predicted position shifts about 7 display pixels (about 10 arcseconds) between August 2025 and August 2026.
- Its glow shifts against field stars that stay put.
- Its center is saturated and flagged. The visible shift is consistent with the catalog prediction, but Perigee does not measure proper motion or calibrated brightness.

In **WISE 0855, "A dot that jumps"**:
- A bright dot appears to jump between observations three days apart at closely matched wavelength.
- The quality overlay marks the relevant pixel as unreliable. The learner checks the tempting interpretation and records why these images do not support a moving-object claim.
- The case makes a justified refusal to claim a discovery a useful outcome. It does not identify the cause of every artifact.

Beyond the cases:
- Learners can step or play through a target's frames in time order, filter a narrow wavelength range, or search the live archive by object name, decimal coordinates or sexagesimal coordinates. Advanced search settings are optional.
- The main journey stays together: notice something, check it, and record it. Optional full-frame exploration sits after the notebook. The reference appears after the learner reviews the checks and records their own reasoning.
- Their claim, observations and uncertainty are saved in the browser. They can be reopened later, exported as a JSON evidence card, or printed to PDF. The card carries the frame IDs, dates, wavelengths, quality results, archive links, processing details and the case's stated limitations.

**How it works.**
- **Frontend:** a React/TypeScript web app.
- **Hosting and API:** Cloudflare serves the frontend and curated catalog. A fixed-origin proxy sends live searches and frame requests to the existing Python/FastAPI service on Vercel.
- **Live searches** query the IRSA archive for SPHEREx Level 2 images (DR1 and QR3) at the requested coordinate. A bounded selection is cut out and processed on request, with two concurrent frame requests, bounded automatic retries for transient failures, and a completed-frame cache. The first ready image is usable while others load. Object names resolve through CDS's SIMBAD/Sesame service; known presets use their verified finder centers.
- **Processing** puts every image onto one north-up sky grid using the file's own coordinate system. It reads the wavelength at the target's actual position on the detector; SPHEREx's wavelength varies across each detector. It screens the SPHEREx quality flags in a small circle around the target and makes a display image with a stated contrast stretch.
- **Marker:** the target marker is a catalog prediction from SIMBAD/Gaia proper motion, and is always labelled as a prediction, not a detection.
- **Curated investigations** use the same processing, run ahead of time on archived cutouts, so they work even if the archive is busy.

**How we checked it.**
- A historical acceptance sweep re-derived 189 processed records (183 unique cutouts plus six case copies) from the original FITS bytes with a separate code path. This checks processing consistency; it is not all-frame astrometric validation.
- The independent Gaia-based alignment check passed 128 of 183 unique cutouts, returned unknown for 55 with too few usable stars, and failed none. Unknown is not a pass. Its negative controls caught the tested 1-, 2- and 5-native-pixel shifts. See the [registration audit](../science/reviews/registration-audit/README.md) for the test bounds.
- The final usability release passed 186 frontend tests, 428 backend tests (33 raw-data-dependent tests skipped), 16 Cloudflare build/parity tests and 24 Worker tests. Public checks passed 28/28 edge checks and 29/29 release/API checks. A real browser name search completed 12/12 frames. These bounded checks do not guarantee archive availability.

**Benefits.**
- A learner practices the habit at the heart of observational science: check that a comparison is fair before claiming a change.
- They do it with real NASA data, and they leave with a conclusion someone else can check line by line.
- A teacher or club can use one investigation as a short activity, with no accounts and no installation. The evidence card makes the reasoning reviewable. These are intended uses; no measured classroom learning or user adoption is claimed.

**What we hope to achieve.** We want more investigations built on the same pattern, classroom activity sheets, and revisits to the same targets as new SPHEREx releases arrive.

**Tools.**
- **Frontend:** TypeScript, React 19, Vite 7.
- **Backend:** Python 3.12, FastAPI, Astropy, NumPy, Pillow, httpx.
- **Tests:** pytest and Vitest.
- **Hosting:** Cloudflare Workers and Vercel (live Python API).
- **Source:** GitHub.
- **AI coding assistance:** see "Use of SI" below.

## Use of Super Intelligence (SI)

The guide says this answer is for data collection and is not shown to judges, but SI use must also be visible in the project's own text and metadata. That is covered by `docs/AI_USE.md`, the README and the app's "AI illustration" label.

Answer, from `docs/AI_USE.md`:

> Perigee was built by our team with help from AI tools: Claude Code (Anthropic) and OpenAI Codex. We used them to help implement the backend and the frontend, and to help edit our demo video. The idea and approach were our own, and our team directed the project throughout. We monitored the AI tools while they worked, then went back and reviewed what they produced: we read the code, tested the app, and checked that the science and the explanations made sense before we kept anything. The small spacecraft drawing on the landing page was made with OpenAI image generation and is labelled "AI illustration" in the app. Perigee itself runs no AI. Every image in an investigation is a real NASA SPHEREx observation, and dates, wavelengths, positions and quality flags are computed directly from the archive data.

Any SI-generated image or video shown in the demo needs a visible watermark. Screenshots of the app itself are not generated images.

## NASA Data

- **SPHEREx Level 2 spectral images (Data Release 1 and Quick Release 3)**, from the NASA/IPAC Infrared Science Archive (IRSA). Perigee searches them live through IRSA's image-search service and downloads small cutouts on request. The three curated investigations draw on the five-target dataset of 183 retained cutouts, each recorded with its archive URL and file hash. https://irsa.ipac.caltech.edu/Missions/spherex.html
- **IRSA SPHEREx documentation and tutorials**, used to read the files correctly: the wavelength lookup, quality flags and coordinate systems.
  - https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
  - https://caltech-ipac.github.io/irsa-tutorials/spherex-intro
- **The Planet X and SPHEREx challenge**, the source of the target list and goals: https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/

## Space Agency Partner Data and Other References

- **ESA Gaia DR3** (ESA is a 2026 Space Apps partner), through the ESA Gaia Archive. It gives the field-star positions used to check image registration, and the astrometry behind several target positions.
  - https://www.cosmos.esa.int/web/gaia/dr3
  - https://gea.esac.esa.int/archive/
- **SIMBAD** (CDS, Strasbourg), for target identities, positions and proper motions. The case source links use CDS's official CfA Harvard mirror while the Strasbourg site is offline. https://simbad.cfa.harvard.edu/simbad/
- **Software**, all open source: React, Vite, TypeScript, FastAPI, Pydantic, Astropy, NumPy, Pillow and httpx. Testing used pytest, Vitest and Playwright.
- **Hosting:** Cloudflare Workers and Vercel (live Python API). **Source code:** GitHub.
- **AI tools:** Claude Code (Anthropic) and OpenAI Codex, as described under "Use of SI" and in `docs/AI_USE.md`.
- **Presentation imagery:** processed SPHEREx observations and screenshots of Perigee, with NASA/IPAC source attribution. If the landing artwork appears, keep its AI-illustration label and include the [artwork provenance](../qa/landing-motion/ASSET.md).

## Known limits (short; also in the app and README)

- Perigee measures no brightness (no photometry), measures no motion and makes no discovery claims. A passed quality screen is not a detection.
- Live searches depend on the IRSA archive. Perigee automatically retries transient frame failures within a fixed limit, then offers a manual retry with a readable explanation. The three curated investigations use bundled products and do not need a live archive query.
- Notes are saved in the browser on one device unless exported.
- The final app was checked in the in-app browser at desktop and narrow viewports, including 390 px and 320 px, with keyboard/focus checks. Safari PDF output was inspected, including backgrounds-off hatching and flag colors. Physical-phone touch and full screen-reader testing were not performed.

## OWNER checklist before "Submit for Judging"

1. Record and upload the final video at **30 seconds or less**, or use the refreshed **seven-slide deck**. Check the public demo link logged out. Identify the team and selected challenge; decks must also name the team members. Do not include under-18 likenesses, including audio.
2. Paste the "Use of SI" answer above into the project page.
3. Confirm that every team member is registered for the same Local Event; the team page is https://www.spaceappschallenge.org/2026/find-a-team/perigee/.
4. Click **Submit for Judging** before **Sunday 15 November 2026, 11:59 p.m. Local Event time**.
5. Confirm the local judging and presentation times with the Local Lead. They may differ from the global submission times.
