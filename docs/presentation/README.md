# Perigee: judge demo handoff

**Current release:** the [app](https://perigee.lokesathvik.workers.dev), [source code](https://github.com/sathvikloke/perigee), and [seven-slide PDF](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf) are public. The [deck notes and validation](DECK.md) describe the finished presentation. Nothing has been submitted for judging.

For Sathvik, who owns the pitch and makes every final call. The rehearsal below remains a historical record of its stated build; the production evidence is linked in section 5.
- The first draft was written by worker 20 at `007b6aa`.
- This version was refreshed by the coordinator on 2026-11-14/15 against `claude/perigee-integration` @ **`c194d92`**, where the frontend code is unchanged since `a416c9e`.
- It was checked by a full rehearsal of the narrated journey on that build (see section 6).

Sources of truth:
- the two case JSON files (`backend/content/cases/`);
- `science/reviews/acceptance/README.md`, `science/reviews/barnard/README.md` and `science/reviews/epsilon/README.md`;
- `coordination/claude-dispatch.md`, `docs/DEPLOYMENT.md`, `docs/AI_USE.md`;
- the rehearsal assets in `rehearsal/`.

**Ground rules:**
- **Nothing invented.** No invented users, quotes, uptake, learning metrics, discoveries, win claims or "first" claims. The learner is illustrative, and the script says so.
- **"Flag screen passed" is not a detection.** It means only that no problem flags were found in a small circle around a *predicted* position.
- **No brightness is measured.** Each plate is contrast-stretched for viewing; Perigee does no photometry.
- **The ring is a prediction.** It is a catalog prediction (SIMBAD/Gaia proper motion), not a position Perigee measured.
- **Barnard's Star uses the accepted case text:** the marker moves about 4 display px A→B and about 7 display px (about 10″, under two SPHEREx pixels) A→C on the 6′ grid.

---

## 1. Why someone should care

Two pictures of the same patch of sky can look different for reasons that have nothing to do with the object changing:
- they were taken at a different infrared wavelength;
- they were stretched differently for display;
- a bad pixel sits next to the target.

Perigee gives a learner real NASA SPHEREx observations and walks them through telling those apart. **They separate a real change from wavelength, display and artifact differences, and they leave with an evidence card that says what they saw, what they can't yet tell, and exactly which archive files support it.** A teacher or club can check that card line by line.

This is a learning outcome we designed for. It has not been measured with users (`docs/PITCH.md`: the audiences are product hypotheses).

**Primary story: Epsilon Indi B, "Is this a fair comparison?"** Recommended because it teaches the core skill directly:
- **A + B** is a fair pair: five months apart at nearly the same wavelength.
- **A + C** looks very different at the same moment, because of wavelength. Each of A and C also has its own contrast stretch, so their brightness is not directly comparable.
- A dot that "appears" next to the target in A turns out to be a flagged pixel.
- Every curated step works without the live archive, using bundled products (section 4).

**Backup story: Barnard's Star, "Follow a nearby moving star."** It is more vivid, because the star's glow visibly shifts against stable field stars over a year. But its core is saturated (flagged), so it can show motion but not measure it. Use it if the audience needs a "something moved" moment, or as slide 6.

---

## 2. Official requirements (verified) versus our local rehearsal

These were read from the official pages on 2026-11-14. Quotes are short.

- **Global submission demo.** The demo is either a slide deck of up to seven slides *including title and intro slides*, or a video of 30 seconds or less. *"Projects that exceed these limits will not be eligible for Global Judging."* ([Project submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/))
  - The slides should show an image of the project, describe the user experience, and say how NASA and space-agency data make it possible.
  - The slides must include the team name, the team members' names and the chosen challenge.
  - Slides must be in English.
- **Links.** The demo and final-project links must be publicly accessible, with no password, permission or registration.
- **Deadline.** Submission closes Sunday 15 November 2026, 11:59 p.m. in the Local Event's time zone ("Submit for Judging").
- **No minors.** No images or likeness of anyone under 18.
- **Judging criteria.** Impact, Creativity, Validity, Relevance and Presentation. For Presentation, *"Judges evaluate the demo and full project"*. ([Judging and awards guide](https://www.spaceappschallenge.org/resources/judging-awards-guide/))
- **Local judging.** Local judging and awards are run by the Local Lead, and their times *may differ* from global submission times. **No official rule found sets the length of a local spoken presentation.** The "five-minute" talk below is our own rehearsal target. Confirm the actual slot with the Local Lead.
- **AI disclosure.** The guide requires SI use to be indicated in descriptive text and metadata, and AI-generated images or videos to carry a visible watermark. This handoff adds no new disclosure scope; follow `docs/AI_USE.md`. The rehearsal screenshots are captures of the app itself, not generated imagery.

---

## 3. Seven-slide outline and completed deck

| # | Slide | On screen (asset) | Point to land |
|---|---|---|---|
| 1 | **Title** | "Perigee: a closer look at our infrared sky". Team name, member names, challenge: *Planet X and SPHEREx*. | Required identification. |
| 2 | **The question** | *"Did Epsilon Indi B change between April and September 2026?"* with `rehearsal/d02b-eps-AB-bench-1280.jpg` | A learner can ask this of real NASA SPHEREx observations. The learner is illustrative. |
| 3 | **Why the obvious comparison misleads** | `rehearsal/d03b-eps-AC-bench-1280.jpg` (A + C, "Same moment, a different infrared color") beside the A + B plates | The same moment at a different wavelength looks different. Check date, wavelength and quality before claiming change. |
| 4 | **Checking quality** | `rehearsal/d04-eps-AB-flags-bench-1280.jpg` plus `d05-flag-screen-meaning-1280.jpg` | The dot by the target is a red "Problem flag" pixel. A passed screen is not a detection. |
| 5 | **The learner's evidence card** | `rehearsal/d06-notebook-filled-1280.jpg`, a short excerpt of `evidence-card-fair_comparison.json` and page 3 of the print PDF | A claim the learner can defend, with frame IDs, wavelengths, quality, archive links, processing and stated limitations. |
| 6 | **How NASA data makes it possible, and how we checked it** | `rehearsal/d10-coordinate-search-1280.jpg` (any coordinate → IRSA) and `d09b-barnard-AC-bench-1280.jpg` | Public SPHEREx L2 images from NASA/IPAC IRSA. 189/189 processed records pass independent re-derivation from the original FITS files. Gaia DR3 field stars land a median 0.45 display px from their predicted positions. |
| 7 | **What works, limits, sources** | The condensed table from section 5, the acknowledgments (NASA/IPAC IRSA, SPHEREx, CDS/SIMBAD, ESA Gaia) and the public links | Candid scope: no photometry, no measured motion, no discovery claims. |

The finished deck follows this story with the final slide arrangement in [DECK.md](DECK.md). The phone captures (`rehearsal/p0*-390.jpg`) can replace any desktop capture if a slide needs a phone view.

---

## 4. Demo script

Square brackets are stage directions. Labels in **bold** are the app's exact visible text.

**Setup:**
- The app is open on `/?preset=epsilon_indi_b` with **A + B** selected and an empty notebook.
- A second tab is on `/?view=query&ra=330.84&dec=-56.786&fov=6`.
- Use a fresh browser profile, so a presenter's saved notes do not appear.

**Length.** About 670 spoken words across the slides and the demo, counted from the quotes below. That is 4:10–4:50 at 140–160 words per minute, before clicks and pauses. **This timing is an estimate, not a timed rehearsal with a speaker.**

### Primary demo: Epsilon Indi B (works without the live archive)

**Opening, slide 2 (≈30 s).**

> "Imagine a student, and this is an illustration, not someone we interviewed, who hears that NASA's SPHEREx telescope photographs the whole sky in infrared, again and again. They pick Epsilon Indi B, a pair of brown dwarfs about twelve light-years away, and ask: did it change between April and September? SPHEREx has pictures from both months. So they can just look. Or can they?"

**Why it misleads, slide 3 (≈30 s).**

> "Two pictures of one spot can differ because time passed. They can also differ because they record a different infrared color: SPHEREx's wavelength depends on where the object lands on the detector. Or because of image quality: a bad pixel right next to the object. Perigee is built around one habit: check that the comparison is fair before you claim a change."

**In the app (≈2:15).**

1. **A + B** [already selected; click **▷ Blink pair**; it becomes **Ⅱ Pause blink**; let it alternate 3–4 times, then pause].

   > "Real SPHEREx observations from NASA's IRSA archive, on one fixed sky grid, north up. The ring is where star catalogs *predict* Epsilon Indi B should be on each date, labelled *Catalog prediction, not a detection*. A is 29 April at 2.3232 microns; B is 27 September at 2.3220 microns. The note under the plates says they're 151 days apart and the wavelengths differ by 0.0012 microns, well inside one band's width. Same color, different dates: a fair pair to start with."

2. **A + C** [click **A + C**].

   > "Frame C was taken at the *same moment* as A, by another detector, at 4.94 microns. Look how different it is: most field stars fade, and Epsilon Indi B stays bright. The app says it plainly: *Same moment, a different infrared color. A different appearance is not evidence that time changed the object.* And each frame here has its own contrast stretch, so brightness isn't comparable."

3. **Quality** [click **A + B**, tick **Show flagged pixels**, point at the small red pixel just below and right of the ring in A; then open **What does "flag screen passed" mean?**].

   > "In A, a bright dot sits right next to the target. Turn on flagged pixels: it's marked red, a problem flag, so it's a bad pixel, not a change. The flag-screen panel lists A and B side by side: 19 and 18 usable pixels at the target, none flagged. That says the pixels are usable for a visual comparison. It does *not* say the object was detected, or how bright it is."

4. **Notebook and evidence card** [type or paste the claim; optionally open **Check your claim against the case guide**; click **↓ Export evidence card**].

   > "Now the learner writes what they can support." [the claim:] *"A and B are a fair pair (five months apart, 2.323 and 2.322 µm, no flags at the target), and Epsilon Indi B looks the same in both. A and C look different because C shows 4.94 µm light, where Epsilon Indi B stands out and most stars fade."*

   > "The case guide lets them check that against what these images do and don't support. Export saves an evidence card: the claim, every frame's ID, detector, release, time, wavelength, quality, archive link and processing version, plus the case's stated limitations. A teacher can check it."

   **Optional, 10 s:** [go to **My evidence**, click **Reopen**]

   > "It's saved on this device. Reopen brings back the same investigation and notes."

5. **Any coordinate, live** [switch to the second tab; click **Use Epsilon Indi A, J2000 catalog position**, then **Search the archive**].

   > "The challenge asks for any coordinate. This goes live to NASA's IRSA archive now and processes each matching image in time order. This is Epsilon Indi A's J2000 position; the app notes the star has moved about two arcminutes since."

   - In the rehearsals this returned **24 of 460 matches**. 20–22 frames processed, and IRSA refused 2–4 frames with 502s.
   - Each refused frame stayed in its slot, marked failed, with a retry button.
   - If that happens, say so: *"The archive refused a few images just now. Perigee shows that instead of hiding it."*

**What Perigee adds, slide 6 (≈30 s).**

> "None of this data is new, and IRSA's own tools are far more powerful. Projects like Backyard Worlds already invite the public into real searches. What Perigee adds is a short, guided bench where the date, the wavelength, the quality check and *your reasoning* stay together, ending in a claim you wrote and can defend. We checked our processing independently: all 189 processed records pass a re-derivation from the original FITS files."

**Limits and close, slide 7 (≈30 s).**

> "What we don't claim: brightness measurements, measured motion, or discoveries. A clear flag screen is never a detection. Next: more investigations, classroom activity sheets, and revisiting targets as new SPHEREx releases arrive. Perigee is about the moment someone stops following an explanation and makes one of their own."

### Fallback when the live archive fails

**The rehearsal confirmed that both investigations need no live archive.** Through the whole Epsilon Indi B and Barnard's Star journey (blink, A + C, flags, notebook, case guide, export, print, My evidence, Reopen, reload), the browser made **zero** `/api/v1/search` or `/api/v1/frame` calls; the case images are bundled products. So during an IRSA outage, run steps 1–4 unchanged and replace step 5 with:
- `rehearsal/d10-coordinate-search-1280.jpg`, captioned *"captured during rehearsal, 2026-11-15"*;
- optionally `rehearsal/d11-simulated-archive-failure-1280.jpg`, captioned *"simulated archive failure"*. It shows *"The archive search failed. This is not a result about the sky."*

Never present a screenshot as live.

### Backup story: Barnard's Star (`/?preset=barnards_star`)

The case opens on **A + C** with **Guide line through A** and **Show flagged pixels** already on. Asset: `rehearsal/d09b-barnard-AC-bench-1280.jpg`.

> "Barnard's Star moves across our sky faster than any other known star. Between 25 August 2025 and 19 August 2026, its predicted position moves north by about seven display pixels, about ten arcseconds, under two SPHEREx pixels. Blink it: its glow shifts past the guide line while the field stars stay put. Its core is saturated, flagged near the target in every frame, so we show the shift; we don't measure it."

*If running long:* cut the contrast-stretch sentence in step 2 and the Reopen beat. *If the app fails entirely:* present the rehearsal screenshots and say plainly that they are screenshots.

---

## 5. Working vs future (reconciled 2026-11-15)

The app is released at **https://perigee.lokesathvik.workers.dev** with no login. The [Cloudflare release check](../../qa/cloudflare-release/README.md) records the current hosting verification; the Vercel checks below are earlier evidence. [Production journey](../../qa/production-journey/README.md) and [independent public-release verification](../../qa/public-release/README.md) record the logged-out checks. The older local rehearsal is retained in section 6. Neither run substitutes for a physical-phone or screen-reader test.

| Capability | Status | Evidence |
|---|---|---|
| Five presets; two guided investigations (Epsilon Indi B, Barnard's Star) | **Verified on production** | Rehearsal `d01`, `d02`–`d09`; regression gate |
| A + B / A + C switching, blink, per-frame date and wavelength, comparison notes | **Verified on production** | Rehearsal `d02b`, `d03b`; notes match the narration word for word |
| Catalog-prediction ring labelled "Catalog prediction, not a detection" | **Verified on production** | Rehearsal; acceptance review: the marker is within 0.0007 display px of an independent prediction |
| Flag screen, problem-flag overlay and legend; "flag screen passed" explanation | **Verified on production** | Rehearsal `d04`, `d05` |
| Evidence notebook with autosave ("Saved on this device") and the claim-guide check | **Verified on production** | Rehearsal `d06`, `d07`; `qa/fresh-pass` (Neeraj) |
| **Evidence card JSON export** with case and per-frame limitations | **Verified (real files)** | Rehearsal `evidence-card-fair_comparison.json`; `qa/export-limitations/`; Codex checked an actual saved download |
| **Print / save PDF** | **Verified on production (rendered PDF)** | Rehearsal `evidence-card-fair_comparison-print.pdf`: 3 Letter pages with plates, legend, comparison note, notebook text, provenance for A and B (IDs, detector, release, UTC, wavelength, IRSA URL, processing, SHA-256) and the 5 stated limitations; readable, no clipping. Rendered by Chrome's print engine (`page.pdf` with print media), not the native dialog; the **Print / save PDF** button was confirmed to call `window.print` |
| My evidence: human titles, Reopen, reload | **Verified on production** | Rehearsal `d08`; Reopen restored all three notes and focused the heading; `qa/my-evidence/` |
| **Phone layout** | **Verified on production (headless Chrome)** | Rehearsal at 390×844 and 320×700: no horizontal overflow (`scrollWidth == innerWidth`) on either case, the notebook or My evidence; `qa/mobile/`; Codex's independent 320 px check. No physical phone, no screen reader |
| Live coordinate search → real IRSA frames, in time order | **Verified on production (live IRSA)** | Rehearsal `d10`: 24 of 460, 20–22 ready, 2–4 IRSA 502s shown as failed with retry |
| Honest archive-failure handling | **Verified on production** | Rehearsal `d11` (simulated); real 502s during rehearsal; `qa/loading-recovery/` |
| Tests | **Pass** | `qa/regression/run.sh` on `2956e67`: backend 348 with raw data (330 passed / 18 skipped without), frontend 121, 183-frame audit (0 stale), 189-record science acceptance; release smoke 20/20 locally |
| Science acceptance | **Done** | 189/189 records pass; Gaia DR3 median 0.45 display px; Barnard and Epsilon case reviews merged and accepted |
| **Public deployment** | **Live, logged-out access verified** | PR #27 released the app; `/` and `/api/v1/health` return 200, health is `ok` with environment signing, and release smoke run 43658316997 passed 20/20. The repo is public. Preview deployments remain protected. See `docs/DEPLOYMENT.md` |
| **Seven-slide deck** | **Complete** | Public PDF, editable Spaces deck, presenter notes and seven-page visual verification in [DECK.md](DECK.md) |
| Rate limiting | Not implemented | Review D2: per-request bounds only; a Vercel Firewall rule is an owner option |
| Brightness measurement (photometry) | Not planned | Display stretch only, by design |
| Measured proper motion | Future | Barnard's core is saturated |
| More investigations, activity sheets, revisits on new releases | Future | Product hypotheses, not validated demand |

---

## 6. Rehearsal record (2026-11-15, coordinator)

**Build and environment:**
- Source `claude/perigee-integration` @ `c194d92`, with a clean worktree.
- Frontend production build (`npm run build`, served by `vite preview` with its `/api` proxy).
- Backend `uvicorn backend.main:app` in local dev mode (`PERIGEE_DEV_MODE=1`), which is needed for live search locally.
- Headless Google Chrome driven by `playwright-core@1.49.1` from a scratch folder.
- **Fresh browser contexts** on a new local origin (`http://localhost:5299`). No existing saved evidence was read or overwritten.
- The production build shows no "Use development fixture" button.

**Routes exercised:**
- `/`
- `/?preset=epsilon_indi_b`, with A + B, Blink, A + C, flags, the flag-screen panel, the notebook, the claim guide, Export and Print
- `/` → My evidence → **Reopen** → `/?preset=epsilon_indi_b`, then a reload
- `/?preset=barnards_star`
- **Search coordinates** → **Use Epsilon Indi A, J2000 catalog position** → `/?view=query&ra=330.84&dec=-56.786&fov=6`, live
- the same query route with `/api/v1/search` intercepted to return a 502, as the simulated failure

**Results:**
- Every narrated label and quoted sentence matched the screen.
- Two narration errors were fixed in this document:
  - the flagged pixel is shown **red ("Problem flag")**, not hatched; hatching means no usable data;
  - the flag-screen breakdown is the **What does "flag screen passed" mean?** section below the steps, not a panel directly under the plates.
- The notebook showed 238/280 and "Saved on this device".
- The export file is `data_origin: api`. Its title is "Is this a fair comparison?". It carries 5 case limitations, and 4 and 5 frame limitations for A and B, with processor 0.1.2, SHA-256 and IRSA URLs.
- Reopen restored the claim, the observations and the uncertainty, and focused the `h1`; a reload kept them.
- There were 0 search or frame calls during both cases.
- At phone width, 390 and 320 px, there was no overflow on any captured view.
- The console showed a missing `/favicon.ico` (404, cosmetic) and the IRSA 502s for refused live frames.

**Not covered:** a hosted or public URL, a physical phone, a screen reader, the native print dialog (the PDF came from Chrome's print engine), and a timed rehearsal with a human speaker.

**Assets in `rehearsal/`:**
- **Desktop 1280×800 at 2×:**
  - `d01-home`
  - `d02-eps-AB` and `d02b-eps-AB-bench`
  - `d03-eps-AC` and `d03b-eps-AC-bench`
  - `d04-eps-AB-flags-bench`
  - `d05-flag-screen-meaning`
  - `d06-notebook-filled`
  - `d07-claim-guide`
  - `d08-my-evidence`
  - `d09-barnard-AC-guide-flags` and `d09b-barnard-AC-bench`
  - `d10-coordinate-search` (live, captured 2026-11-15)
  - `d11-simulated-archive-failure` (**simulated**)
- **Phone at 3×:** `p01`–`p06` at 390 and 320 (Epsilon A + B, A + C, flags, notebook, Barnard, My evidence).
- **Exported card:** `evidence-card-fair_comparison.json`.
- **Print rendering:** `evidence-card-fair_comparison-print.pdf`.
- **Step log:** `rehearsal-log.json`.

The earlier stand-ins in `screens/`, which predated the fixes, were removed.

**Public capture completed:** the former S9 request is fulfilled in `qa/public-release/notebook-restored.jpg` and `qa/production-journey/2026-11-15-ef29890/`. The local rehearsal above predates publication; the app is now live on the web.

---

## 7. Source links

- **SPHEREx data at NASA/IPAC IRSA:** https://irsa.ipac.caltech.edu/Missions/spherex.html
- **IRSA SPHEREx tutorial (spectral image overview):** https://caltech-ipac.github.io/irsa-tutorials/spherex-intro
- **IRSA SPHEREx visualization docs (as observed in the design handoff):** https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/visualization.html
- **SPHEREx archive access documentation:** https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
- **Backyard Worlds: Planet 9** (as observed in the design handoff, landing page only; no classifier behavior is claimed): https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9
- **SIMBAD targets.** These are CDS SIMBAD links through its official CfA Harvard mirror. The Strasbourg site has been offline since a CDS security incident (notice dated 9 Nov 2026); the same `sim-id?Ident=` paths work on `simbad.cds.unistra.fr` once it is restored.
  - Epsilon Indi B: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=eps+Ind+B
  - Barnard's Star: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=Barnard%27s+star
  - WISE 0855: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=WISEA+J085510.74-071442.5
  - RW Aurigae: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=RW+Aur
  - R Draconis: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=R+Dra
- **Planet X and SPHEREx challenge:** https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/
- **Gaia DR3** (used for the acceptance and Barnard field-star checks): https://www.cosmos.esa.int/web/gaia/dr3, queried via https://gea.esac.esa.int/archive/
- **Project submission guide** (7-slide or 30-second demo, public links, deadline): https://www.spaceappschallenge.org/resources/project-submission-guide/
- **Judging and awards guide** (criteria, local versus global judging): https://www.spaceappschallenge.org/resources/judging-awards-guide/

---

## 8. Open decisions for Sathvik

1. **Demo format:** the seven-slide PDF is ready. The submission owner can use its public link; a video is not needed in addition to the deck.
2. **Local slot:** confirm the length and format with the Local Lead. The 5-minute script is our own target.
3. **Judge access:** completed. App, repository and deck have public links. Previews remain protected; use the production URL.
4. **Live-search coordinate:** keep the J2000 link, which the app labels honestly, or use the 2026.0 position (330.8925, −56.8043) to center Epsilon Indi A.
5. **Opening hook:** Epsilon Indi B (recommended; it matches the demo and works without the live archive) or Barnard's Star.
6. **Team slide:** names and roles, and how to state the AI-assisted build (per `docs/AI_USE.md`; the `[TO CONFIRM]` items there are the team's to fill).
