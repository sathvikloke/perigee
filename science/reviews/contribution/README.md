# Contribution evidence (B5): Perigee compared with the closest tools


> **Coordinator review (2026-11-15, PR #47):** I checked the claims for overreach (no first, unique, superior or learning-gain claims; human validation pending). I kept the SPHEREx Explorer row as the primary comparator. Its "not found" findings are explicitly limited to a static reading of the shipped bundle and two API calls, because the UI was never rendered; a rendered walkthrough may show more.

**Status: draft for Sathvik's review.** Prepared 2026-11-15 (UTC) on branch `claude/b5-contribution-evidence`, from `origin/main` at `9cb850b`. Every external source, with its retrieval time, HTTP status and SHA-256, is in [`sources/retrieval.json`](sources/retrieval.json).

**How to read this comparison:**
- Statements about other projects describe **what their own pages or code show**.
- Numeric or performance statements by other teams are **their claims**. They were not reproduced here.
- Perigee statements cite the repository's own QA and science reviews.
- Nothing here measures learning, task time, adoption or superiority.

## The contribution, stated precisely

Perigee is a **guided, traceable investigation** of real SPHEREx Level 2 frames. It helps a learner sort a visible difference between two frames into four causes:

- **time** (observation dates);
- **wavelength** (the wavelength at the target, compared with the band width);
- **display stretch** (per-frame vs shared contrast);
- **quality** (pipeline flags at and near the target).

The learner then writes a claim, the supporting observations and the uncertainty into an evidence card. The card carries each frame's provenance: observation ID, IRSA URL, SHA-256, date, wavelength and quality.

What Perigee does **not** do:
- discover anything, do photometry, measure proper motion or run a detector;
- offer anything unique in blinking, alignment, wavelength labels, flag masks or authored cases: SPHEREx Explorer and other comparators already have these (see below).

**What Perigee has measured** (from QA and science reviews):
- both shipped cases run end to end on the public release;
- the notebook autosaves, reopens and exports JSON and PDF with per-frame provenance;
- the case guide lists supported and unsupported claims;
- the science numbers behind both cases were independently re-derived.

**What has not been demonstrated:**
- that any learner reasons better with Perigee;
- that the reasoning transfers to new data;
- that the card is reviewed by anyone.

A draft transfer exercise for that test is in [`../transfer-exercise/`](../transfer-exercise/README.md). It is untested.

## 1. Primary comparator: SPHEREx Explorer

**Source and access.**
- **What was read:** <https://spherex-explorer.vercel.app/> at 02:00–02:03Z. Every route (`/`, `/about`, `/discover`, `/tour`, `/play`, `/explore`) returns the same 1,823-byte JavaScript shell.
- **Browser:** the in-app browser pane refused the domain (site permissions), so **the UI was not rendered or clicked here**.
- **Method instead:**
  - the production bundle `assets/index-CL_lrgjf.js` (844,512 B) was read statically, including its English UI strings;
  - the JSON its own Discover page loads (`/api/cases`) and `/api/health` were fetched once each.
- **Earlier inspection:** Codex inspected the live home, About and Discover pages directly (assignment file, B5). The findings below agree with that.
- **Suhrit's email:** the feature gaps it proposed came from a video description. They are treated as hypotheses, and most are contradicted below.

**What the project already has.** Each item below was read from its bundle or API, not observed in a running UI.

- **Authored cases with evidence and limits.** `/api/cases` (built 2026-09-28) has four cases:
  - asteroid (7) Iris;
  - asteroid (6) Hebe;
  - the Andromeda core spectrum;
  - the north ecliptic pole.

  Each case has real frame keys (for example `qr2/level2/2025W49_1A/.../level2_2025W49_1A_0332_1D2_...fits`), mid-exposure times, the wavelength at the target, two evidence statements and a "caution" note. The Discover intro says each case lists what was measured and what the evidence cannot tell you. Each case also has "Explore this case" and "Open the demo snapshot" links.
- **Wavelength honesty:**
  - every frame is labeled with "the wavelength that fell on your target", read from WCS-WAVE;
  - a difference image is shown only for two frames from the same detector within half a spectral channel; otherwise the app explains why;
  - a limits note says a brightness difference "may be the source's colour rather than a change in time".
- **Display stretch:** one shared brightness scale, taken from a reference frame, with per-frame background subtraction ("so brightness changes you see are in the data").
- **Quality:**
  - flagged pixels (cosmic rays, hot/dead pixels, ghosts, persistence) are masked, and for display they are filled from their surroundings;
  - when the target's pixels are flagged, the app says that the image there "is not a measurement; do not read a change into it";
  - there is a saturation caveat and a QR2/QR3 calibration caveat.
- **Measurement and checks** (the authors' claims, not reproduced):
  - 12″ aperture photometry;
  - a transparent moving-source search checked against JPL SBIdent/Horizons, with SPHEREx-centred parallax ("within 1.4 arcseconds" on Iris);
  - pixel reads checked against IRSA cutouts.
- **Tour (`/tour`, "Judge mode"):** narrated slides (eight topic strings in the bundle). They include Iris, "75 years of one fast star" (Barnard's Star on Palomar 1950, 2MASS, WISE and SPHEREx), the colours, and an honest statement of what Planet X cannot be.
- **Play (`/play`, "Spot the mover"):**
  - rounds blink two real frames, hours apart, on one brightness scale;
  - the learner taps the jumping point;
  - a hit is scored within 4 grid px of JPL's predicted position, with a running score;
  - at the end it points to Backyard Worlds.
  - The rounds come from the moving-object cases (Iris, Hebe).
- **Assistant:**
  - a local language model (Qwen3 4B by default) phrases answers from server-gathered evidence, with numbered sources;
  - the About page warns that its reasoning is not checked;
  - chats are kept in browser storage (`spherex-explorer.chats.v1`, up to 50).
- **Exports:** an image/video export that "carries the dates, wavelengths and credits".

**Learner-authored reasoning: the specific check the assignment asked for.**

In the shipped bundle:
- the only free-text input is the assistant's question box (`textarea#chat-question`);
- browser storage holds language, theme and assistant chats;
- no strings or storage keys for a learner's claim, observations or uncertainty were found;
- no editable or exportable learner-written evidence record tied to frame provenance was found;
- Play scores where you tap, not a written explanation.

Within that limited view, the loop "make a claim, inspect contradicting evidence, revise, save source-linked reasoning, apply it to an unfamiliar pair" is **partly present**:
- Play is repeated practice on new pairs with immediate feedback for one skill (spotting a mover);
- the assistant lets a learner ask questions;
- a saved, source-linked written claim was not observed.

This is a static reading. A feature hidden behind a lazily loaded route, or added after 02:01Z, would be missed.

**Perigee's measured capability on the same ground:**
- **Claim, observations and uncertainty fields:**
  - they autosave on the device and restore on reopen and reload;
  - they export as JSON with per-frame provenance (processor version, SHA-256, IRSA URL, date, wavelength, quality, stretch mode);
  - they print to PDF;
  - the case guide shows supported and unsupported claims.

  Evidence: `qa/production-journey/README.md` (production `ef29890`), `qa/cloudflare-release/README.md` and [`evidence-card.json`](../../qa/cloudflare-release/evidence-card.json) (Cloudflare, 2026-11-15).
- **Revision is not tracked.** The card keeps only the latest text, with `created_at_utc` and `updated_at_utc`. There is no record of a claim being revised.
- **No transfer exercise is shipped.** A [draft](../transfer-exercise/README.md) exists.

**Unresolved gap and honest conclusion.**
- Explorer covers more of the sky and measures more. It also already teaches wavelength, stretch and quality caveats, and has a practice game.
- Perigee's defensible difference is narrower: the learner writes and saves their own reasoning, linked to the exact frames, and checks it against a guide.
- **That difference has not been shown to help anyone.**
- A fair head-to-head (same learners, same question, both tools) has not been run.
- Perigee's stretch choice differs: per-frame in the general viewer, shared only inside authored case pairs. Explorer uses one shared scale. Neither choice was tested with learners.

## 2. Same-question test: "Did Barnard's Star move between two dates, and is a difference caused by time, wavelength, stretch or a flagged pixel?"

| Tool | What was actually done here | Output |
|---|---|---|
| **Perigee** | Existing evidence: the `moving_neighbor` case on production (`qa/production-journey`, row "Barnard backup") and `science/reviews/barnard/` | Frames: A/B/C at 2.006/2.012/2.028 µm, one shared stretch.<br>Catalog marker shift A→C: 7.29 display px (10.25″). The glow's visual centre moves 6.9–7.2 px; field stars move ≤ 0.77 px.<br>The core is flagged OVERFLOW/BLOOM in all 34 frames, so no centroid or photometry.<br>This is a visual demonstration, **not a measured proper motion** |
| **SPHEREx Explorer** | One request to its demo-snapshot API at Perigee's Barnard query centre | `404 not_in_snapshot`. Live mode (IRSA-backed) deliberately not called. The tour describes a 75-year multi-survey view of Barnard's Star; **not tested** |
| **spherex-timelapse** | Read `js/app.js` at commit `d305370` | Has a featured "Barnard's Star" target (RA 269.4464, Dec 4.7673) with the note "watch it creep north"; shared stretch with per-frame background removal. The live site was blocked in the browser pane; **not run** |
| **SPHEREx Blink** (andrei25ciuta) | Read `data/real_results.json` and `docs/VALIDATION.md` | Their claim: a blind "Find movers" run measured Barnard's motion to 0.20″/yr of the catalog (D2+D6, 21/21 images); a bad-pixel mask fix reduced D2 error from 3.72 to 0.31″/yr. Images are not published; the public site runs on synthetic data. **Not reproduced** |
| **Driftnet** | Read the About page | Solar-system movers pipeline; stars are removed as "fixed sky", so this is not the same question. It labels wavelength differences and judges motion by position |

**Result.** Only Perigee's answer to this question was produced and checked from data in this repository. The others were not run, for the reasons given. This is a statement about what was tested here, not a ranking.

## 3. Other SPHEREx comparators

| Tool | Existing capability (their pages and code; numbers are their claims) | Perigee measured capability | Unresolved gap |
|---|---|---|---|
| **spherex-timelapse** ([repo](https://github.com/ShivenKhurana1/spherex-timelapse), HEAD `d305370`, 2026-11-14) | **Data:** browser-only; static index of about 1.2 M QR2+QR3 images; range-reads FITS from S3; TAN-SIP alignment; FLAGS decoded in JS.<br>**Views:** time-lapse, blink, difference, trail and stack; wavelength per visit from WCS-WAVE.<br>**Analysis:** change scan, tracklets and light curves/spectra with CSV export; "finds and names Pluto" (claim).<br>**Tests:** offline unit tests against astropy.<br>**Learner text:** none found in `app.js`/`index.html` (storage holds only a frame-count setting) | Fixed processor-A products with per-frame provenance and reproducible hashes (`qa/cloudflare-release`: 952 asset IDs byte-compared). Two authored cases plus a general live search (377 Orion matches, 1.6–1.8 s, one smoke run) | Far broader search and analysis than Perigee. Perigee adds guided cause-sorting and a learner evidence card; its value is unmeasured |
| **SPHEREx Blink** ([results](https://andrei25ciuta.github.io/SPHEREx/results.html); validation in `Andrei25Ciuta/SPHEREx`, commit `3f1e538`) | **Interface:** blink, difference, stack and trail; flag display with a skip-flagged option; SIMBAD/SkyBoT overlays.<br>**Analysis:** "Find movers" detector; spectrum and light curve; Planet X parallax mode.<br>**Self-reported tests:** fake-source injection, empty-sky false-alarm rates, Makemake (one recovery among chance candidates, by their own account).<br>**Data:** the public site runs on **synthetic** data; real-data results are numbers only.<br>The validation link on the page (`mateibut/SPHEREx`) returned 404 | No detector or measurement (by design) | They measure; Perigee explains a comparison. These are different goals, not a comparison of quality |
| **Driftnet** ([About](https://spherex-planet-x.vercel.app/about/)) | **Pipeline:** automated solar-system moving-object search; detection limit AB 17.0–17.7 (their measurement); orbit fits.<br>**Catalog checks:** two independent catalogs (JPL SBIdent/Horizons and SkyBoT).<br>**Reporting:** evidence reports per object; honest limits; an expert walkthrough is named.<br>**AI:** LLM write-ups checked for numbers | Not a discovery pipeline | Their evidence reports are machine-generated per object; Perigee's card is learner-written. Do not claim evidence cards as new |

## 4. 2025 Space Apps category winners (context, not SPHEREx)

These are category winners across different challenges, not SPHEREx winners and not a ranked top five. Source: NASA, 18 Dec 2025 (`article:published_time 2025-12-18T16:00-05:00`).

The five project pages on spaceappschallenge.org are client-rendered. Their content loads from a GraphQL API that was not queried here, and the in-app browser refused the domain. So **only NASA's one-paragraph summaries were read**, and they describe submission claims.

| Award: team | NASA's summary (paraphrased; claims, not verified) | What it suggests for Perigee | Perigee evidence | Gap |
|---|---|---|---|---|
| Best Use of Science: SpaceGenes+ | Interactive dashboard to help researchers find molecular effects of radiation and microgravity on astronaut health | A named user and a decision the tool supports | Learner use case and case questions (`docs/presentation/`) | No user testing |
| Best Use of Data: Resonant Exoplanets | AI system ingesting large telescope/satellite datasets, including JWST spectra, to flag possible biosignatures automatically | Scale of data use | Live coordinate search over IRSA plus curated products | Perigee deliberately covers a small set of frames; no automation claim |
| Best Use of Technology: Twisters (SkySense) | Web app using NASA Earth data and AI for ultra-local weather risk and safe time windows | A dependable, usable product | Public Cloudflare release, 20/20 and 24/24 smoke checks, mobile widths | No adoption data |
| Best Use of Storytelling: HerCode Space ("A Solar Tale") | Illustrated story teaching children how space weather affects daily life | A clear narrative for a non-expert | Seven-page deck; narrated journey | No audience test |
| Art & Technology: Zumorroda-X (Henry's Farm Adventures, name from the earlier review) | Mini-games where a farmer learns to adapt to heat waves and floods | Interactive practice | Guided steps; no game | Explorer already has a scoring game. Do not add one just to match a winner |

## 5. Human validation still pending

None of the following has been done. All are needed before any claim of educational effect:

1. **Learner trial.** An unfamiliar learner, not an agent, works through a taught case and then the [draft transfer exercise](../transfer-exercise/README.md). Score with its rubric. Owners: Sathvik and Sagar.
2. **Science review** of the transfer exercise's answer key: NONFUNC/TRANSIENT interpretation, field-star identification, WISE 0855 visibility at 1.26 µm.
3. **Head-to-head.** The same learners answer the same question in Perigee and SPHEREx Explorer. Not planned or run.
4. **Teacher or judge review** of whether the evidence card is easy to read.
5. **Interaction checks.** Screen reader and physical phone (still open from `qa/production-journey`).

## Limitations of this comparison

- **Unrendered pages.** SPHEREx Explorer, spherex-timelapse and the Space Apps project pages were not rendered in a browser here. Bundle and README reading can miss behaviour that exists only at runtime or arrived after retrieval.
- **No live calls to comparators.** Their live archive modes were not exercised, to avoid unrequested load on their services and IRSA.
- **Limited winner sources.** Winner descriptions are NASA's summaries only; the teams' own pages were not read.
- **Perigee's evidence is our own QA.** It is browser automation and science scripts in this repository, not independent review.
