# Perigee: pitch outline and five-minute demo script (DRAFT)

This is a draft for Sathvik, who owns the pitch and makes every final call. It was written by parallel worker 20 on 2026-11-14 against `claude/perigee-integration` @ `007b6aa`.

Sources of truth:
- `coordination/claude-dispatch.md`
- `science/reviews/acceptance/README.md`
- `science/reviews/barnard/README.md`
- the two case JSON files
- the frontend QA screenshots in `screens/`

**Ground rules applied throughout:**
- **No invented people or results.** There are no invented users, quotes, learning metrics, discoveries or win claims. The learner below is illustrative, and the script says so.
- **A passed flag screen is not a detection.** "Flag screen passed" means only that no problem flags were found in a small circle around a *predicted* position.
- **Brightness is never measured.** Each plate is contrast-stretched for viewing. Perigee does no photometry.
- **The marker is a prediction.** It is a catalog prediction (SIMBAD/Gaia proper motion), not a position Perigee measured.
- **Barnard's Star wording uses the corrected science.** The marker moves about 7 display pixels (about 10″, under two SPHEREx pixels) from A to C, August 2025 to August 2026. Sathvik accepted the corrected text (PR #22, `b4fcc8c`), and `moving_neighbor.json` on the integration branch now uses it.

---

## 1. Seven-slide outline

The Space Apps guide allows seven slides including the title. The same deck carries the five-minute local talk, with slide 3 replaced by the live app.

| # | Slide | On screen | Point to land |
|---|---|---|---|
| 1 | **A real question about a real object** | Title "Perigee: a closer look at our infrared sky". Below it, the case's opening question in large type: *"Did Epsilon Indi B change between April and September 2026?"* Add one line under it: "Epsilon Indi B: a pair of brown dwarfs, about 12 light-years away." | A learner can ask this and answer it with real NASA SPHEREx observations. Label the learner "illustrative". |
| 2 | **Why the obvious comparison can mislead you** | Three labelled tiles: **Date** (when the picture was taken), **Wavelength** (which infrared color, which varies across each SPHEREx detector), **Image quality** (flags near the object). Under the tiles: "Two pictures of the same spot can differ because of any of these, not only because time passed." | This is the fairness problem. The same detector does not mean the same wavelength, so you must check it at the object's position. |
| 3 | **Live demo** (local talk) / **the bench** (global deck) | Global deck: request S2 (A+C). Local talk: switch to the app. | Compare, check, explain: the three steps the app shows. |
| 4 | **The learner's own evidence card** | Request S4: the notebook with claim, observations and uncertainty filled in, plus the exported JSON fields. Add a small inset of the live coordinate search (request S6). | The result is a claim the learner can defend, with the frame IDs, wavelengths, quality status and archive links needed to check it. Any sky coordinate works, as the challenge requires. |
| 5 | **What Perigee adds next to existing tools** | Two short rows, citing only what the design handoff observed. **IRSA's SPHEREx visualization docs:** a full archive viewer that keeps image metadata close to the image. **Backyard Worlds (Zooniverse):** a concrete human question and an explicit availability status. Under them: "Perigee: one guided bench that keeps date, wavelength, quality and your reasoning together, ending in a claim you wrote." | This is a contribution, not a first. PRODUCT.md says existing viewers and citizen-science tools overlap and that no first-ever claim is established. |
| 6 | **How we checked the science** | Request S7 (Barnard phone, guide line plus flag legend) or the Barnard `contact_sheet.png`. List three numbers: **189/189** processed records pass independent re-derivation; Gaia DR3 field stars land within a median **0.45 display px**; the Barnard's Star prediction moves **≈7 px (≈10″)** A→C while the Gaia field stars stay within **0.77 px**. | An independent reviewer rebuilt every image from the original FITS bytes and checked it against Gaia DR3. Wavelength, time, flags and provenance were each re-derived separately. |
| 7 | **What works, what doesn't yet, what's next** | The working-vs-future table from section 3, condensed. Add the source links, acknowledgments (NASA/IPAC IRSA, SPHEREx, CDS/SIMBAD, ESA Gaia) and the team. | Be candid: what runs today, what is still unverified in public, and what we will not claim. |

---

## 2. Five-minute narration (local presentation)

Times are cumulative. The normal path is about 700 spoken words, roughly 4:40 at a steady pace before clicks, so it is tight. The demo segment is 2:15 long and needs the app already open on the Epsilon Indi B investigation, with **A + B selected**, an **empty notebook**, and the coordinate search tab preloaded in a second browser tab. Square brackets are stage directions.

### 0:00–0:35 · Slide 1: the question

> "Imagine a student, and this is an illustration, not someone we interviewed, who learns that NASA's SPHEREx telescope photographs the whole sky in infrared, again and again. They pick one object: Epsilon Indi B, a pair of brown dwarfs twelve light-years away. And they ask a simple question: *did it change between April and September?* SPHEREx has pictures from both months. So they can just look. Or can they?"

### 0:35–1:05 · Slide 2: the fairness problem

> "Two pictures of the same spot can look different for three reasons. **Time**: something actually changed. **Wavelength**: SPHEREx records a different infrared color depending on where the object lands on the detector, so the same camera doesn't mean the same color. And **image quality**: a cosmic-ray hit or a saturated pixel near the object. Perigee is built around one idea: before you claim a change, check that the comparison is fair."

### 1:05–3:20 · Live demo (2 min 15 s)

**1:05–1:40 · A + B, different dates** [A + B already selected; click **Blink pair**, let it alternate 3–4 times, then pause]

> "Real SPHEREx observations from NASA's IRSA archive, on one fixed sky grid. The circle is where star catalogs *predict* Epsilon Indi B should be on each date. It's a prediction, not a detection. Frame A is April 29, frame B is September 27: five months apart. Wavelengths are 2.323 and 2.322 microns, a difference of about a thousandth of a micron, far less than each band's width. Same color, different dates: a fair pair to start with."

**1:40–2:05 · A + C, same moment, different wavelength** [click **A + C**]

> "Now frame C. It was taken at *the same moment* as A, by a different detector, at 4.94 microns: more than twice the wavelength. Look how different it is. Nothing changed in time here; this is color. Perigee says so right under the plates: *a different appearance is not evidence that time changed the object*. And because each frame has its own contrast stretch, the app says brightness isn't directly comparable."

**2:05–2:25 · Quality disclosure** [back to **A + B**; open the quality panel below the plates, which lists A and B side by side]

> "Third check: quality. Both A and B pass the flag screen: no problem flags in a small circle around the predicted position, and the panel shows the pixel counts behind that. Notice what that does *not* say. It doesn't say the object was detected, and it doesn't measure how bright it is. It says these pixels are usable for a visual comparison. That's all."

**2:25–2:50 · Write and export the evidence card** [type or paste the claim; click **Export evidence card**]

> "Now the learner writes what they can support." [type:] *"A and B are a fair pair (five months apart, 2.323 and 2.322 µm, no flags at the target), and Epsilon Indi B looks the same in both. A and C look different because C shows 4.94 µm light, where Epsilon Indi B stands out and most stars fade."* (This is the case's accepted example claim, PR #31.) "Export saves an evidence card with the claim plus every frame's ID, detector, release, date, wavelength, quality status and archive link, so a teacher or a club can check it."

**2:50–3:20 · One live coordinate search** [switch to the preloaded **Search coordinates** tab; click **Use Epsilon Indi A, J2000 catalog position**, then **Search the archive**]

> "The challenge asks for any coordinate, not just our examples. This goes live to the IRSA archive right now and processes each matching image one at a time, in time order. This is the J2000 catalog position of Epsilon Indi A. The star has moved about two arcminutes since then, and the app says so."

**Fallback line if IRSA is slow or errors** (IRSA returned intermittent 502/503 responses during our testing): stop waiting after about 10 seconds.

> "The archive is busy. That happened in our testing too, and Perigee doesn't pretend otherwise. It says the request failed, says it's *not a result about the sky*, and keeps your previous images and notes. Here's the same search, captured earlier today." [show backup screenshot S6, labelled on screen "captured earlier"; do not present it as live]

### 3:20–3:50 · Slide 5: what Perigee adds

> "None of this data is new, and we're not the first SPHEREx viewer. IRSA's own tools are far more powerful, and projects like Backyard Worlds already invite the public into real searches. What Perigee adds is a short, guided bench where the date, the wavelength, the quality check and *your reasoning* stay together. It ends in a claim you wrote and can defend."

### 3:50–4:25 · Slide 6: how we checked it

> "An independent check rebuilt every processed image from the original FITS files: 189 out of 189 records pass. Field stars from ESA's Gaia DR3 catalog land within half a display pixel on average. Our second investigation is Barnard's Star, the fastest-moving star in the sky. Between August 2025 and August 2026 its predicted position moves about seven display pixels, about ten arcseconds, under two SPHEREx pixels. You can see its glow shift while the surrounding stars stay put. Its center is saturated, so we show the shift; we don't measure it."

### 4:25–5:00 · Slide 7: working, limits, next

> "What works today: two complete investigations, five preset targets, live coordinate search and an exportable evidence card, all on real NASA data. What we don't claim: brightness measurements, measured motion, or discoveries. A clear flag screen is never a detection. Next: more investigations, classroom-ready activity sheets, and revisiting targets as new SPHEREx releases arrive. Perigee is about the moment someone stops following an explanation and makes one of their own. Thank you."

*If running long:* cut the A + C sentence about the contrast stretch and the Gaia sentence on slide 6. *If the app fails entirely:* present slides 3–4 from screenshots S1–S6 and say plainly that they are screenshots.

---

## 3. Working vs future

"Working" means the dispatch log or a QA screenshot records it being exercised. Everything here is **local** (vite → uvicorn on a laptop) unless stated otherwise.

| Capability | Status | Evidence / caveat |
|---|---|---|
| Five presets with real frame counts | **Working locally** | Dispatch 17:59Z (gate 1) |
| `fair_comparison`: A+B / A+C switching, blink, per-frame date + wavelength, comparison note | **Working locally** | Frontend A integrated (`6e855a2`, follow-up `41d8b42`); screenshots `after-desktop-1280-AB/AC` |
| Catalog-prediction marker labelled "not a detection" | **Working locally** | Screenshots; acceptance: marker within 0.0007 display px of independent prediction |
| Flag screen status + flagged-pixel overlay + legend | **Working locally** | Screenshots incl. Barnard phone view |
| Evidence card saved with `data_origin: api`, frame_key, detector, DATE-AVG, λ, IRSA URL | **Working locally** | Dispatch 17:59Z (`localStorage['perigee.evidence.v1']`) |
| Evidence card JSON export | **Partly verified** | At 17:59Z the button was present but the download was not triggered. A later QA screenshot shows the status "Evidence file downloaded". The exported file's contents are not inspected in the log. |
| Print / save PDF | **Present, not verified** | Button visible; no print check in the log |
| "Check your claim against the case guide" | **Present, not verified** | Visible in screenshots; not exercised in the log |
| Live coordinate search → real IRSA frames | **Working locally** | `/search` 330.84, −56.786 → ready, 460 matches (DR1+QR3); `/frame` HTTP 200, 2.5–7.4 s; UI showed 24 of 460 |
| IRSA failure handling (retry, honest error, keep old images + notes) | **Working locally** | 14 R1: 4/16 live cutout GETs were 503, and after the fix 8/8 returned 200. Screenshot `after-search-failure-keeps-old-1280`. |
| Science acceptance of processed products | **Done** | 189/189 PASS; 1 UNKNOWN (no Gaia star in fair_comparison C) |
| `moving_neighbor` (Barnard's Star) imagery | **Done** | Review 10: PASS with display conditions. Corrected case text (PR #22) accepted and merged. |
| Phone layout | **In progress** | Plate starts ~735 px down at 390×844; worker 17 running |
| **Public deployment** | **Not verified** | Vercel preview builds (status success), but every path redirects to Vercel Authentication, so no response was checked on a public URL. Judge access, `PERIGEE_TOKEN_SECRET` and the protection setting are open decisions. |
| Rate limiting | Not implemented | Decision D2 (Vercel Firewall suggested) |
| Brightness measurement (photometry) | **Not planned for the weekend** | Display stretch only, by design |
| Measured proper motion / centroiding | **Future** | Barnard's core is saturated; not supported by these images |
| More investigations, teacher activity sheets, revisits as new SPHEREx releases arrive | **Future** | Product hypotheses, not validated demand |

---

## 4. Screenshot requests for Sathvik

Take all of these from the same build you will demo, in a clean browser profile (no stale `localStorage`), at the viewport stated. Use 1280×800 for desktop and 390×844 for phone, at device pixel ratio 2 for slides.

| ID | Screen | Exact state | Viewport | Used on |
|---|---|---|---|---|
| S1 | Investigations → Epsilon Indi B, "Is this a fair comparison?" | **A + B** selected, blink paused on A, "Show predicted position" on, "Show flagged pixels" off, notebook empty | 1280×800, first viewport only | Slide 3 / fallback |
| S2 | Same | **A + C** selected, scrolled so both plates **and** the amber "Same moment, a different infrared color" note with "brightness is not directly comparable" are visible | 1280, crop from step strip to bottom of note | Slides 2–3 |
| S3 | Same | **A + B**, the quality panel below the plates **open**, showing A and B side by side ("Problem flags: none reported", pixel counts) and the "Known limits" line saying a passed screen is not a detection | 1280, crop the panel | Slide 3 / fallback |
| S4 | Same, notebook | Claim, "What did you notice?" and "What remains uncertain?" filled with the example claim; "Attached observations A + B" | 1280, crop the notebook panel | Slide 4 |
| S4b | Exported evidence JSON | The downloaded file opened in an editor, showing `data_origin: "api"`, two frames with `frame_key`, `detector`, `collection_id`, `observed_at_utc`, `wavelength_um`, quality status, `source_url` | Editor window, ~1000 px wide | Slide 4 inset |
| S5 | Print / save PDF | Browser print preview of the same card | Print preview | Optional backup |
| S6 | Search coordinates | After **Use Epsilon Indi A, J2000 catalog position** → results loaded, "N observations found", frame 1 with its metadata column. Caption it "captured <time>" when used as the fallback. | 1280×800 | Slide 4 inset + demo fallback |
| S7 | Investigations → Barnard's Star | A ↔ C, "Guide line through A" **on**, "Show flagged pixels" **on**, legend visible. | 390×844 phone (or 1280 if worker 17's phone fix lands late) | Slide 6 |
| S8 | Search failure state | "The archive search failed. This is not a result about the sky." banner + "Still showing the previous images and notes" | 1280 | Backup only |
| S9 | Public URL | App loaded in a **logged-out** private window on the production/judge URL | 1280 | Proof of judge access; required before submission |

Draft stand-ins from the QA run are in `screens/`. Use them for layout only. They predate worker 17's phone fixes, and the A+C one already has a claim typed in the notebook.

- `screens/draft-fair-comparison-AC-1280.jpg` (≈ S2)
- `screens/draft-live-search-1280.jpg` (≈ S6)
- `screens/draft-barnard-flagged-390.jpg` (≈ S7)

---

## 5. Source links

- **SPHEREx data at NASA/IPAC IRSA:** https://irsa.ipac.caltech.edu/Missions/spherex.html
- **IRSA SPHEREx tutorial (spectral image overview):** https://caltech-ipac.github.io/irsa-tutorials/spherex-intro
- **IRSA SPHEREx visualization docs (as observed in the design handoff):** https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/visualization.html
- **SPHEREx archive access documentation:** https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
- **Backyard Worlds: Planet 9 (as observed in the design handoff, landing page only; its classifier was out of data, so no classifier behavior is claimed):** https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9
- **SIMBAD targets** (CDS SIMBAD via its official CfA Harvard mirror; the Strasbourg site has been offline since a CDS security incident, notice dated 9 Nov 2026; the same `sim-id?Ident=` paths work on `simbad.cds.unistra.fr` once it is restored):
  - Epsilon Indi B: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=eps+Ind+B
  - Barnard's Star: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=Barnard%27s+star
  - WISE 0855: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=WISEA+J085510.74-071442.5
  - RW Aurigae: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=RW+Aur
  - R Draconis: https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=R+Dra
- **Planet X and SPHEREx challenge (cited in both case JSON files):** https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/
- **Gaia DR3, used for the acceptance and Barnard field-star checks:** https://www.cosmos.esa.int/web/gaia/dr3 (the mission page cited in the Barnard case is https://www.cosmos.esa.int/web/gaia). The queries went to `gaiadr3.gaia_source` through the ESA Gaia archive: https://gea.esac.esa.int/archive/
- **Judging and awards guide:** https://www.spaceappschallenge.org/resources/judging-awards-guide/
- **Project submission guide (seven-slide rule):** https://www.spaceappschallenge.org/resources/project-submission-guide/

---

## Open decisions for Sathvik

1. ~~**Barnard text (PR #22, `b4fcc8c`)**~~ Accepted and merged. S7 can be taken.
2. **Judge access:**
   - Decide whether the public URL comes out from behind Vercel Authentication, and set `PERIGEE_TOKEN_SECRET`.
   - Until S9 exists, demo from the local build and do not say "live on the web".
3. **Live-search coordinate:** keep the shipped J2000 link, which the app labels honestly, or switch to the 2026.0 position (330.8925, −56.8043) so Epsilon Indi A sits near the center of the plate?
4. **Opening hook:** Epsilon Indi B's fairness question (matches the demo, recommended) or Barnard's Star's motion (more vivid; its text is now final)?
5. **Case-guide check:** show "Check your claim against the case guide" in the demo? It is not yet exercised in the log, and showing it costs about 15 s.
6. **Team slide:** names and roles, and whether to name the parallel AI-assisted build.
7. **Timing:** the local presentation slot is still unconfirmed. Rehearse to 4:45.
