# Space Apps project page: ready-to-paste draft

This draft is for the submission owner (Sagar) and Sathvik. **Nothing has been submitted.**

The fields below follow the official [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/), read on 2026-11-14. The guide states no character limits for these fields. Every fact here comes from the released app (`main`), the README, `docs/presentation/` and the science reviews.

Items marked **OWNER** are personal team facts that only the team can confirm.

---

## Project Name

Perigee

## High-Level Project Summary

Perigee is a free web app that lets anyone investigate NASA SPHEREx infrared images of a real object and decide, with evidence, whether it changed. Two pictures of the same patch of sky can look different for reasons that have nothing to do with change:
- they were taken at a different infrared wavelength;
- they were contrast-stretched differently for display;
- a bad pixel sits next to the target.

Perigee puts real SPHEREx observations from NASA/IPAC IRSA on one fixed sky grid, in date order. It keeps the date, the wavelength at the target and the image-quality flags beside every image, and walks the learner through telling those causes apart. The learner finishes with an evidence card that states what they saw, what they still cannot tell, and exactly which archive files support it.

It answers the Planet X and SPHEREx challenge directly. Two guided investigations (Epsilon Indi B and Barnard's Star) and five challenge targets are built in, and any sky coordinate can be searched live against the archive.

## Link to Project Demo

https://perigee-liard.vercel.app/demo/perigee-demo.pdf

This is the seven-slide deck from PR #42; the guide's limit is 7 slides including the title and intro slides. **Before pasting, open the link in a private window and confirm it shows the PDF.** When checked on 2026-11-15 at 00:56 UTC, before PR #42 was deployed, this path still returned the app page (HTTP 200, `text/html`).

## Link to Final Project

https://perigee-liard.vercel.app

This is the public web app; no login is needed. The source code is at https://github.com/sathvikloke/perigee and is public.

## Detailed Project Description

**What it does.** A learner opens an investigation and compares two SPHEREx observations of the same target.

In the **Epsilon Indi B** case (a pair of brown dwarfs about 12 light-years away):
- Frames A and B were taken five months apart at nearly the same wavelength (2.323 and 2.322 µm). That makes them a fair test of change over time.
- Frame C was taken at the same moment as A but at 4.94 µm, and looks very different. Each frame there has its own contrast stretch, and the app says plainly that this pair compares wavelengths, not time.
- A bright dot that "appears" beside the target in A turns out to be a flagged pixel once the quality overlay is switched on.

In the **Barnard's Star** case:
- Barnard's Star has the largest known proper motion of any star. Its catalog-predicted position shifts about 7 display pixels (about 10 arcseconds) between August 2025 and August 2026.
- Its glow shifts against field stars that stay put.

Beyond the cases:
- Learners can also step or play through every frame of a target in time order. They can filter the frames to one wavelength, or search any right ascension and declination against the live archive.
- Their claim, observations and uncertainty are saved in the browser. They can be reopened later, exported as a JSON evidence card, or printed to PDF. The card carries the frame IDs, dates, wavelengths, quality results, archive links, processing details and the case's stated limitations.

**How it works.**
- **Frontend:** a React/TypeScript web app.
- **API:** a Python/FastAPI service, hosted together on Vercel.
- **Live searches** query the IRSA archive for SPHEREx Level 2 images (DR1 and QR3) at the requested coordinate. Each matching image is cut out and processed on request.
- **Processing** puts every image onto one north-up sky grid using the file's own coordinate system. It reads the wavelength at the target's actual position on the detector; SPHEREx's wavelength varies across each detector. It screens the SPHEREx quality flags in a small circle around the target and makes a display image with a stated contrast stretch.
- **Marker:** the target marker is a catalog prediction from SIMBAD/Gaia proper motion, and is always labelled as a prediction, not a detection.
- **Curated investigations** use the same processing, run ahead of time on archived cutouts, so they work even if the archive is busy.

**How we checked it.**
- All 189 processed records were independently re-derived from the original FITS files.
- Field stars from ESA Gaia DR3 land a median 0.45 display pixels from their predicted positions.
- The app also has automated backend and frontend tests and a public smoke check.

**Benefits.**
- A learner practices the habit at the heart of observational science: check that a comparison is fair before claiming a change.
- They do it with real NASA data, and they leave with a conclusion someone else can check line by line.
- A teacher or club can use one investigation as a short activity, with no accounts and no installation.

**What we hope to achieve.** We want more investigations built on the same pattern, classroom activity sheets, and revisits to the same targets as new SPHEREx releases arrive.

**Tools.**
- **Frontend:** TypeScript, React 19, Vite 7.
- **Backend:** Python 3.12, FastAPI, Astropy, NumPy, Pillow, httpx.
- **Tests:** pytest and Vitest.
- **Hosting:** Vercel.
- **Source:** GitHub.
- **AI coding assistance:** see "Use of SI" below.

## Use of Super Intelligence (SI)

The guide says this answer is for data collection and is not shown to judges, but SI use must also be visible in the project's own text and metadata. That is covered by `docs/AI_USE.md` and the in-app footer line.

Draft answer, from `docs/AI_USE.md`:

> Perigee was built with AI coding assistance. The team directed the work. Claude Code (Anthropic) agents wrote most of the application code, tests and review documents as parallel candidates, and OpenAI Codex set the UI design direction and helped coordinate the release. Decisions that change scientific meaning were left to the team. Every processed SPHEREx frame was independently re-derived from the original FITS files and checked against Gaia DR3. The app itself runs no AI model: dates, wavelengths, positions and quality flags are computed deterministically from archive data. **OWNER:** "The idea and challenge approach are the team's own." Keep this sentence only if it is true; the guide says SI should not be used to come up with the idea.

**OWNER:** settle the open `[TO CONFIRM]` items in [`docs/AI_USE.md`](AI_USE.md) before submitting:
- the tools used outside this repository;
- who reviewed which merges;
- any human spot checks;
- Sagar's own AI use;
- the image tool used for any mock-ups.

Any SI-generated image or video shown in the demo needs a visible watermark. Screenshots of the app itself are not generated images.

## NASA Data

- **SPHEREx Level 2 spectral images (Data Release 1 and Quick Release 3)**, from the NASA/IPAC Infrared Science Archive (IRSA). Perigee searches them live through IRSA's image-search service and downloads small cutouts on request. The two curated investigations and five preset targets use 183 retained cutouts, each recorded with its archive URL and file hash. https://irsa.ipac.caltech.edu/Missions/spherex.html
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
- **Hosting:** Vercel. **Source code:** GitHub.
- **AI tools:** Claude Code (Anthropic) and OpenAI Codex, as described under "Use of SI" and in `docs/AI_USE.md`.
- **No copyrighted images** from third parties are used. All imagery is processed SPHEREx data or screenshots of Perigee.

## Known limits (short; also in the app and README)

- Perigee measures no brightness (no photometry), measures no motion and makes no discovery claims. A passed quality screen is not a detection.
- Live searches depend on the IRSA archive. If IRSA refuses an image, Perigee shows that frame as failed with a retry button. The two curated investigations do not need the live archive.
- Notes are saved in the browser on one device unless exported.
- The app was tested in Chrome at desktop, 390 px and 320 px widths, and with keyboard navigation. Physical phones, screen readers and other browsers were not tested.

## OWNER checklist before "Submit for Judging"

1. Confirm the deck shows the **team name, team member names and the challenge**, as the guide requires. Confirm it opens as a PDF at the demo link, logged out.
2. Settle the AI-use items above.
3. Confirm that every team member is registered for the same Local Event; the team page is https://www.spaceappschallenge.org/2026/find-a-team/perigee/.
4. Click **Submit for Judging** before **Sunday 15 November 2026, 11:59 p.m. Local Event time**.
5. Confirm the local judging and presentation times with the Local Lead. They may differ from the global submission times.
