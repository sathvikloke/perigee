# Perigee project plan

Implementation starts from scratch during the November 14–15, 2026 event. This repository currently contains documentation and research records.

# The decision

Build **Perigee: guided investigations of the changing infrared sky** for the Planet X and SPHEREx challenge. The promise is: **Explore real NASA observations, make a comparison, and explain what the evidence supports.** Keep the public coordinate-and-time viewer at the center. Add two complete investigations and a saved evidence card around it. This is the final recommended scope for six people over November 14–15, 2026; it supersedes the earlier conditional Afterglow/outburst direction.

The first audience is motivated learners in astronomy clubs and classrooms, with teachers and club organizers helping them get started. The broader vision is a growing collection of investigations using new observations. A discovery engine, research-grade photometry service, and general astronomy chatbot are outside this weekend’s scope.

The team roster, challenge, relevant competitors, and archive methods have been reviewed, and the original NASA data is downloaded locally. The application has not been built or deployed. Start implementation from scratch on Saturday November 14 after the event begins. Scientific measurements and user demand have not been validated.

# The human reason to build it

**The human change we want is from following an explanation to making an evidence-based observation.** A curious learner should be able to ask whether something moved, inspect actual observations, notice why a comparison might mislead them, and explain their conclusion. That combines agency, the pleasure of finding something, and confidence in their own reasoning.

An illustrative journey—not a real user interview or testimonial: a student hears that a nearby star moves across the sky. They open Perigee, blink observations from different dates, compare the star with the surrounding field, check wavelengths and image flags, and write what they can support. They leave with an evidence card they can show their club or teacher. A later investigation asks a different question about a cooler object or an uncertain observation.

The scientific context is substantial: infrared observations help investigate cool objects and the material involved in stars and planets. SPHEREx has already produced brown-dwarf and interstellar-ice science. Perigee’s weekend contribution is making a small part of that observational process accessible; it is not claiming to discover a new planet or derive an asteroid’s composition from a few images. [NASA brown-dwarf results](https://www.nasa.gov/missions/spherex/nasas-spherex-telescope-sees-menagerie-of-brown-dwarfs/), [JPL interstellar-ice results](https://www.jpl.nasa.gov/news/interstellar-glaciers-nasas-spherex-maps-vast-galactic-ice-regions/).

| Audience | What they want | Product response | Reason to return |
|---|---|---|---|
| Motivated student or independent learner—primary | A real question they can investigate and a result they can explain | Short guided cases, real observations, clear evidence and uncertainty | Another case, a different object, revisiting a saved investigation |
| Teacher or astronomy-club organizer—initial adopter | A manageable activity with a clear learning outcome | A 10–15 minute case, discussion prompts, printable evidence card, no account required | New cohorts and different activities |
| Amateur astronomer—secondary | Convenient inspection and traceable data | Coordinate input, date/wavelength controls, quality context, archive links | Their own targets and later available epochs |
| Outreach educator or science communicator—secondary | An understandable example of how an astronomical conclusion is made | A shareable target view and an honest visual explanation | New events, classes, and demonstrations |
| Professional researcher—future collaborator | Reliable measurement, reproducibility, calibrated errors | Provenance is useful now; precision-analysis features require later validation | Do not promise a research workflow this weekend |

These motivations are product hypotheses informed by adjacent educational and citizen-science projects, not evidence that Perigee already has demand. Guided real-data learning already exists in Rubin’s education program, and classroom participation already exists on Zooniverse. There is no need to invent a new human motivation; the team needs to execute a useful SPHEREx experience. [Rubin education products](https://rubinobservatory.org/education/educators/program-guide/our-education-products), [Zooniverse education](https://www.zooniverse.org/get-involved/educate).

Repeat use should follow worthwhile new questions. Start with saved cases and a second investigation; later add a curated case library and revisits when new epochs become available. Avoid a daily-use or live-alert promise: archive ingestion and release schedules are not real-time. A successful single classroom session is also a legitimate benefit. No existing users or retention statistics are required by the judging criteria. [Archive access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/), [judging guide](https://www.spaceappschallenge.org/resources/judging-awards-guide/).

# What is distinct, and what already exists

| Closest existing work | What it already covers | Perigee’s contribution to demonstrate |
|---|---|---|
| IRSA’s SPHEREx interface and documentation | Archive access, images, flags, provenance, and spectrophotometry | A short, coherent investigation for a learner, ending in their own supported conclusion |
| SPXQuery and SPHEREx analysis packages | Programmatic retrieval and analysis workflows | A browser experience without requiring Python or archive expertise |
| SPHEREx timelapse and blink projects | Time browsing, image comparison; some also include masks, differences, curves, or exports | Put observation date, wavelength, quality, and the learner’s reasoning into the same guided flow |
| Driftnet and similar Planet X projects | Overlapping motion-review and evidence-report concepts | Do not claim evidence cards alone are new; demonstrate the complete educational interaction |
| Rubin and Zooniverse | Guided authentic-data education and public participation | Apply that approach carefully to SPHEREx’s particular time/wavelength/quality constraints |

References reviewed include [IRSA spectrophotometry](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html), [SPXQuery](https://spxquery.readthedocs.io/en/latest/), [SPHEREx timelapse](https://github.com/ShivenKhurana1/spherex-timelapse), [SPHEREx Blink](https://andrei25ciuta.github.io/SPHEREx/results.html), and [Driftnet](https://spherex-planet-x.vercel.app/about/). These comparisons are based on published interfaces, documentation, and selected code inspection, not a full performance benchmark of every project.

**Defensible contribution:** a focused educational workflow that helps a newcomer make and document a scientifically cautious comparison using real SPHEREx data. This is a proposed improvement in usability and learning, not an exclusive technical invention. The weekend must demonstrate that improvement. Do not claim “first SPHEREx citizen-science platform,” “first time viewer,” or “first evidence report.” NASA has also selected a SPHEREx-related citizen-science effort, Rogue Worlds. [NASA’s 2026 citizen-science selections](https://science.nasa.gov/get-involved/citizen-science/nasa-selects-19-new-citizen-science-proposals-in-2026/).

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

# What the research and downloads actually establish

The decision pass reviewed the challenge and current judging/submission rules, the official descriptions of 30 global winners from 2023–2025, relevant competing viewers and educational workflows, SPHEREx archive/access/quality documentation, and the feasibility of the earlier outburst proposal. Winner descriptions show recurring combinations of a clear purpose, tangible experience, relevant science/data, and understandable presentation; they do not establish a causal winning formula. Losing entries and private judge scores were not available for a controlled comparison. [2023 winners](https://science.nasa.gov/directorates/smd/2023-nasa-international-space-apps-challenge-announces-10-global-winners/), [2024 winners](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-international-space-apps-challenge-announces-2024-global-winners/), [2025 winners](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).

**Downloaded source data:** 1,986 returned archive metadata records across five target positions, querying DR1 and QR3 wide-survey collections. From 188 selected cutout requests, 183 FITS files downloaded successfully; five requests returned HTTP 503 after retries. The original FITS files, archive metadata, source URLs/hashes, and official explanatory-supplement PDF remain local. Generated previews, frontend manifests, case files, preparation scripts, and the old starter ZIP have been removed. Build the application and processing pipeline from scratch during the event.

| Target | Saved FITS cutouts | Adequate central coverage | Central apertures passing the conservative screen |
|---|---:|---:|---:|
| Barnard’s Star | 34 | 34 | 0 |
| Epsilon Indi B | 44 | 43 | 29 |
| WISE 0855 | 34 | 34 | 21 |
| RW Aurigae | 35 | 33 | 1 |
| R Draconis | 36 | 35 | 0 |

The screen counts finite, sufficiently covered pixels without selected adverse flags near a catalog-predicted position. It is not a source-detection test or certified photometry. The bright-star flags and the earlier outburst data’s quality problems are reasons to keep quantitative scientific inference out of the critical path.

All 183 downloaded FITS files were structurally read and their SHA-256 hashes verified during the data audit. The audit also checked coordinate consistency and inspected candidate images. Those observations inform the research findings below, but the display pipeline and generated assets have been removed. A new implementation still needs its own validation; the audit does not establish calibrated fluxes or discovery performance.

Earlier work separately inspected 1,406 archive records, 1,544 NEOWISE rows, and 25 successful FITS downloads for three outburst-oriented targets. Published work already combines NEOWISE and SPHEREx in this area, while good photometry can require coadds, deblending, additional spectra, and stronger validation. The earlier files remain available, but they are not the weekend dependency. [Relevant outburst study](https://arxiv.org/abs/2602.07129), [NEOWISE quality documentation](https://irsa.ipac.caltech.edu/data/WISE/docs/release/NEOWISE/expsup/sec2_3.html).

This was a targeted feasibility audit, not a scan of all NASA data. It did not exhaust SPHEREx’s deep fields, all-sky positions, every wavelength/epoch pairing, or every competitor’s code. No PSF-matched photometry, measured proper motion, sensitivity-calibrated nondetection, prospective user study, or live application test has been completed. Further exhaustive archive exploration would not remove the immediate need to build and test the chosen interaction.

## Local handoff

Original source data is stored at **research/build_data/**. **Only Sathvik and Sagar need the full data download.** They own raw data processing, scientific checks, and the image/metadata outputs to be created during the event. Akshobya, Aditya, and Suhrit can develop against an agreed JSON contract, then use the shared backend; they do not need the full dataset locally. The repository contains research and planning documents, not a working application or reusable processing scripts. Keep raw FITS and virtual environments out of Git and the frontend bundle.

The source-data manifest records observation time, release, original URL, wavelength, coverage, flags, and file hashes from the audit. Preserve provenance in the eventual application. Design display previews as visualizations rather than flux measurements. Recheck coordinate handling in the new implementation: catalog epoch, proper motion, annual parallax, and binary motion are distinct considerations. Test the official WISE 0855 challenge coordinate separately from a predicted current position.

# Implementation and AI

**No AI model, model weights, GPU, or training dataset is required for this version.** Dates, wavelengths, coordinates, and flag decoding are deterministic. Use authored explanations and case-specific guidance for the demo.

If the complete core works by Saturday evening, an optional language-model helper could explain only the selected metadata and prewritten case material. It must link its sources and never infer an object’s composition, classify an apparent change as a discovery, or turn a missing measurement into a confident answer. This feature is the first thing to cut. There is no need to download a local model.

## Small architecture

Use the current [integration contract](INTEGRATION_CONTRACT.md) for architecture and endpoint definitions. The selected product is a responsive React/TypeScript web app with a Python FastAPI backend hosted through Vercel. The contract replaces the earlier persistent-server/job-queue outline with bounded metadata searches and individual frame-processing requests. Vercel Services is the preferred single-project deployment and is currently Beta; Suhrit owns its early validation and the documented two-project fallback.

Align images to a fixed celestial grid so real motion remains visible. Do not center every frame on the predicted moving object and accidentally erase motion. Keep date and wavelength controls separate; the same detector does not guarantee the same wavelength. Display actual wavelength separation rather than inventing a universal comparison-confidence score. Do not use raw image subtraction as a proof of variability.

# Six people and a credible schedule

The live team page lists **Sagar Raut, Akshobya Rao, Aditya R, Neeraj Movva, Sathvik Loke, and Suhrit Bestavemula**. The assignments below reflect Sathvik’s updated direction: Sathvik and Sagar own all data work, Akshobya owns frontend, Aditya and Suhrit own backend, and Neeraj has a light support role outside the critical path. [Perigee team page](https://www.spaceappschallenge.org/2026/find-a-team/perigee/).

| Owner | Workstream | Concrete handoff |
|---|---|---|
| Sathvik Loke | Data analysis, scientific validation, investigation content and pitch | Own the full dataset with Sagar; select case frames, check alignment/wavelength/flags, write supported conclusions, and own the final story/slides |
| Sagar Raut | Data engineering and archive processing; final submission owner | Own the full dataset with Sathvik; retrieval, FITS-to-preview processing, manifests and callable data functions for the backend team |
| Akshobya Rao | Frontend and visual design | Coordinate form, five presets, viewer, timeline/wavelength controls, case screens, evidence card, local save/export/print and loading/error states |
| Aditya R | Backend query API and job orchestration | Input validation, search/job endpoints, progressive results, retries and integration with the data functions supplied by Sathvik and Sagar |
| Suhrit Bestavemula | Backend storage, content serving and deployment | Cache/storage integration, image/manifest/case endpoints, public deployment, health checks and backend integration checks |
| Neeraj Movva | Light testing and submission support | Fresh-browser checks, broken-link reports, screenshots and optional slide assembly; no required feature or deadline depends on his availability |

Plan for **five active builders**, with Neeraj providing optional support. At roughly 14–18 focused hours per active builder, budget about 70–90 person-hours total, including integration and presentation; do not count Neeraj’s availability toward required delivery. Akshobya is the single frontend owner, so Sathvik supplies finished case copy and conclusions, while Aditya and Suhrit deliver stable endpoints and data shapes. Sathvik owns the pitch/slides; Neeraj can help assemble them. In the first hour, Sathvik and Sagar agree the processing interface with Aditya and Suhrit, and all five agree the frontend manifest contract. The existing scope and milestones remain the ceiling; cut optional work early.

All times below are **Chicago time, CST**. The organizer email says the event starts Saturday November 14 at 9 AM. The local page says presentations are five minutes on Sunday, but neither the public schedule nor the retrieved final-details email gives the exact presentation slot. Be presentation-ready by Sunday noon, and move that earlier if the organizer supplies an earlier slot. The global submission deadline is Sunday November 15 at 11:59 PM local time. [Chicago event](https://www.spaceappschallenge.org/2026/local-events/chicago/), [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/).

| Time | Milestone | Gate |
|---|---|---|
| Saturday 9–10 AM | Agree API/manifest, divide files, create the first deployed shell | Every owner can run the same initial app |
| Saturday 10 AM–noon | One cached target works from selection to evidence card | First usable vertical slice is public |
| Saturday noon–4 PM | General RA/Dec query, progressive frames, dates/wavelengths/flags | A coordinate outside the presets reaches the archive and renders or reports an honest result |
| Saturday 4–7 PM | Two investigations, five presets, saving and export | Complete core journey works without manual database/file edits |
| Saturday 7–10 PM | Integration, failure states, first slides and narrated demo | Core feature freeze; cut optional work if any required gate is failing |
| Overnight | Rest and short handoff notes | Avoid making scientific or deployment fixes while exhausted |
| Sunday 8–10 AM | Acceptance checks and fixes | Public build, source attribution, data boundaries and evidence exports verified |
| Sunday 10 AM–noon | Rehearse local pitch, finish seven slides, capture backup demo | Presentation-ready; earlier organizer slot takes precedence |
| Sunday after local judging | Only critical fixes and final submission | Aim to submit by 8 PM, with buffer before the 11:59 PM hard deadline |

The critical path is **manifest/API agreement → one complete case → arbitrary coordinates → second case → verification → submission**. Sathvik prepares case copy and presentation content while Akshobya builds the screens. Aditya and Suhrit split the backend work against the same contract. If the live-query gate fails Saturday afternoon, both backend owners pair with Sagar to resolve it and drop optional features. Cached presets help reliability but do not substitute for the challenge’s coordinate requirement.

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

# Story and judging evidence

Suggested opening: **“Imagine hearing that a nearby star is moving across the sky. With Perigee, you can open real NASA observations, compare them yourself, and explain what you found. We guide you through the checks that make that comparison meaningful—because the exciting part of science is learning how to tell what the evidence actually says.”** This is a pitch framing, not a claim that a usability study has already proved the effect.

| Criterion | What the team can show by Sunday |
|---|---|
| Impact | A specific learner and teacher use case, a complete activity, and a clear learning outcome |
| Creativity | The integrated comparison-to-evidence interaction and a candid explanation of how it improves on related tools |
| Validity | Real downloaded observations, provenance, metadata checks, and visible limits on inference |
| Relevance | Public RA/Dec input and chronological SPHEREx imagery satisfying the challenge |
| Presentation | One understandable human journey, a working demonstration, and a realistic expansion path |

The official rubric uses Impact, Creativity, Validity, Relevance, and Presentation. Existing users are not a prerequisite. A good pitch helps explain the project, but the working artifact, scientific coherence, and submission also matter. These criteria support the plan; they cannot guarantee a win. [Judging and awards guide](https://www.spaceappschallenge.org/resources/judging-awards-guide/).

Use seven slides for the global demo: **1** team and promise; **2** the learner’s question; **3** real coordinate/time viewer; **4** wavelength and quality checks; **5** the completed evidence card; **6** comparison with existing tools and realistic future use; **7** what works, sources, limitations, and team. The guide allows seven slides including the title or a video of at most 30 seconds. Prepare a separate five-minute spoken version for Chicago’s local presentation. [Submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/).

Five-minute local outline: 0:00–0:40 human question; 0:40–1:10 why SPHEREx data makes the investigation possible; 1:10–3:10 live journey through one case, with the second case briefly visible; 3:10–3:50 what is distinctive and who benefits; 3:50–4:30 what is working and the limits; 4:30–5:00 expansion and closing. Avoid spending the opening explaining the software stack.

Submission checklist: confirm the public app and project links work; include NASA/SPHEREx and CDS/SIMBAD acknowledgments and the appropriate release citations; distinguish cached observations from live queries; describe built features rather than planned ones; follow the official project submission requirements. [Project submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/).

Build the application and processing code from scratch after the event starts on Saturday November 14. The first milestone is one complete investigation with a coordinate viewer; keep the current role assignments and two-day checkpoints.
