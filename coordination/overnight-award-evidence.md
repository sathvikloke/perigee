# Award evidence (N8): contribution, claims, story

**What this is:** a few-minute bridge from the backend and science results to the pitch. It feeds Codex and Sathvik; it is not an edit to the shipped deck. Every number links to a file in this repository.

**What it excludes:** no users, testimonials, adoption figures, learning gains or award odds, and none are needed.

## 1. Audience and benefit (one sentence)

A curious student or newcomer who sees a dot "jump" between two real SPHEREx images can use Perigee to check date, wavelength, display stretch and pixel quality before deciding. They leave with a short, source-linked evidence card that someone else can inspect. The potential benefit is a justified claim, or a justified refusal to claim a discovery.

## 2. Contribution (one sentence)

Perigee's contribution is the complete, source-linked investigation and reasoning record:

- reviewed cases whose answer keys are computed from the frames themselves;
- the learner's own claim tied to exact archive files;
- a repeatable admission check that lets a new comparison be added the same way.

The components (blinking, alignment, wavelength labels, flag masks, shared stretch, authored cases, export) already exist in other tools. The combination, serving this one task, is the contribution.

## 3. The five 2025 winners: patterns and what closes the gap

These are category winners from different challenges, not SPHEREx winners. Their patterns come from their own project pages, and their performance claims are theirs, not reproduced here. Sources: NASA's [announcement](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/) and each team's project page, listed in `coordination/claude-overnight-science-backend.md` §3. Nothing here scores Perigee against them.

| Winner pattern | What closes it now (evidence) | Still needs UI |
|---|---|---|
| **SpaceGenes+ (Science):** a focused question, a NASA dataset, a stated research use | One question ("is this difference evidence of change?") with five controls that test its traps, each with a written invariant and a reproducible output: `science/reviews/overnight-controls/`. A positive control (Barnard) and false-positive controls (WISE flagged pixel, stretch, wavelength) | Show the controls' outcomes inside the cases (copy already in `case.json`) |
| **Resonant Exoplanets (Data):** a chain from input to an interpretable report | Archive file → processor A → frame record → checks → claim card. Each link is checked: raw cutout SHA-256 = record = card (`qa/ui-fixtures/case_evidence_check.json`, 72/72); live route = curated product byte for byte (`qa/overnight-backend/README.md` §2); independent star registration check on 128 frames (`science/reviews/registration-audit/`) | None for the chain. The card UI already exports provenance |
| **SkySense (Technology):** a recurring decision for a named audience, with the tool built into the task | Repeat use without new infrastructure: three investigations, each exposing a different trap, plus open coordinate search. A saved card can be reopened, and a new card is made per investigation (`coordination/overnight-ui-handoff.md` §5) | Ship the third case; completion contract; separate card per visit (F8) |
| **A Solar Tale (Storytelling):** a clear audience and a narrative built on the science | Story beats with real outcomes: a real moving star, a convincing false positive, a revised claim (§6) | Deck and narration are Codex's and Sathvik's |
| **Henry's Farm (Art & Technology):** learner decisions with consequences, tied to NASA data | Each step changes what the learner may claim. The illustrative initial → revised card (`qa/ui-fixtures/evidence_card.wise_0855_quality_trap.illustrative.json`) shows one flag check flipping "may be moving" to "nothing supports a moving object" | Show the reference answer only after the learner records a claim |

## 4. Claims registry

**Status key:** `observed` (seen in the data), `computed` (a script output), `interpretation` (reasoned from computed facts), `proposed` (not built).

| # | Claim | Status | Source (file or command) | Limitation | Safe pitch wording |
|---|---|---|---|---|---|
| 1 | Barnard's Star's glow shifts north relative to the field stars between Aug 2025 and Aug 2026 | computed | N2 control D: `overnight-controls/results/D_barnard_proxies.csv` | Core saturated and flagged in every frame; image proxies, not a centroid | "The glow moves north against the stars, as catalogs predict" |
| 2 | That shift is 6.87–8.87 display px across 11 proxies, against a catalog prediction of 7.29 px (10.25″); field stars move ≤ 0.83 px | computed | same; `results.json` → `controls.D` | Proxy spread is method-dependent; not a proper-motion measurement | "About 7 pixels, about 10 arcseconds, consistent with the catalog prediction" |
| 3 | The WISE "jumping dot" is one detector pixel, (1709, 1364), in both frames. It appears 5.36″ apart because pointing changed, and the stars predict 5.38″ | computed | N2 control B: `B_features.csv`, `B_field_sources.csv`; `transfer-exercise/answer_evidence.json` A2 | Flags say "do not trust"; the physical cause is unknown | "The dot that jumps is one flagged detector pixel, so it is not a moving object" |
| 4 | One sky value (1.0 MJy/sr) is drawn as grey 156 and grey 174 under the per-frame stretches, and 159 in both under a shared stretch | computed | N2 control A: `A_stretch_probes.csv` | Display only; not photometry | "The same sky can look brighter only because of contrast settings" |
| 5 | Epsilon Indi A and C are the same exposure, 69.6 band widths apart in wavelength | computed | N2 control C: `C_pairs.csv` | Two detectors; brightness not compared | "Same moment, different colour of light, so a different picture" |
| 6 | 4 of 16 investigation questions (cause, identity, proper motion, photometry) cannot be answered from any of 11 representations | computed | N2 control E: `E_information_matrix.csv` | Derived from computed facts; no human or AI trial | "Some questions these images cannot answer, and Perigee says so" |
| 7 | An independent star-position check passes 128 of 183 unique frames, with 55 unknown (too few stars) and none failing. Shifting a test frame by 1, 2 or 5 px made it fail on all three real test frames | computed | N3: `science/reviews/registration-audit/results/`, `tests/test_negative_control.py` | 27 cutouts have no usable star; unknown ≠ pass. The shift test used 3 real frames plus a synthetic field: frames with fewer than 3 stars return UNKNOWN even when shifted, and shifts of 0.5 native px or less go undetected | "Frame alignment is checked against Gaia stars, and the check caught every 1–5 px shift we tested" |
| 8 | The acceptance gate covers 189 records: astrometry PASS 133, UNKNOWN 56, FAIL 0 | computed | `science/reviews/acceptance/check_acceptance.py` (run by `qa/regression/run.sh`) | Same limits as #7 | (internal; no pitch line) |
| 9 | A live archive frame equals the curated product byte for byte (7 frames, 4 geometries) | computed | N5: `qa/overnight-backend/n5_parity_evidence.json` | Retained frames only | "What you see live is what we reviewed" |
| 10 | Curated investigations keep working when the live origin is down | computed | N6: `qa/overnight-backend/worker_origin_failure.test.mjs`, `wrangler_dev_origin_down.py` (74/74 routes byte-exact) | Local fault injection, not a production outage | "Reviewed investigations work even if the archive service is down" |
| 11 | A corrupt spectral table no longer crashes the API process (D1, P1, fixed) | computed | `backend/tests/api/test_regression_wave_table_abort.py` (5 fail before, 6 pass after) | Fix not yet deployed to the Python origin | (internal) |
| 12 | A third investigation passes 12 automated admission checks: 30 of 30 quoted numbers matched to records, and 18 deliberately broken copies each fail their intended check | computed | `tools/ingest/admit_case.py`; `backend/tests/data/test_admit_case.py`; `science/staging/README.md` | Heuristic text checks, not a proof. Staged, not shipped | "New investigations are added through an automated check against the data" |
| 13 | The dot near the WISE 0855 marker lies within about 1″ of a Gaia DR3 star | computed | `answer_evidence.json` A6 | Positional association only | "The dot by the marker lines up with a catalogued Gaia star" |
| 14 | WISE 0855 is expected to be too faint at 1.26–1.44 µm | interpretation | published J-band photometry and the SPHEREx design depth, cited in `case.json` | Not measured; not an upper limit. 1.44 µm is just beyond J band, where it is expected to be fainter still | "It should be too faint to see here, from other telescopes' measurements" |
| 15 | Perigee's card records a claim with per-frame provenance (observation ID, IRSA URL, SHA-256, date, wavelength, quality, stretch) | observed | `frontend/src/evidence/card.ts`; `qa/cloudflare-release/evidence-card.json` | Saved per browser | "Your claim is saved with the exact files behind it" |
| 16 | Claim revision history and curated/live source labels | proposed | `coordination/overnight-ui-handoff.md` §4 | Not built | Say only "planned" |
| 17 | Learners reason better with Perigee | not claimed | none | no study (not required) | Do not say it |

## 5. Three strongest demonstrations

| Demonstration | Frames | Visible event | Learner action | Supported conclusion | Caveat (plain) |
|---|---|---|---|---|---|
| **Real motion: Barnard's Star** (`moving_neighbor`) | A `2025W35_1A_0008_1_D3` (2025-08-25, 2.006 µm) → C `2026W34_1A_0431_1_D3` (2026-08-19, 2.028 µm), shared stretch | the glow shifts north while the stars stay put | blink A↔C; compare with the catalog marker | it moved about 10″ in a year, consistent with the catalog prediction | "The centre is saturated, so we see the shift but do not measure its speed" |
| **Convincing false positive: WISE 0855** (staged `wise_0855_quality_trap`) | A `2025W45_2A_0278_1_D2` (2025-11-07) ↔ B `2025W46_1A_0108_1_D2` (2025-11-10), both 1.257 µm, shared stretch | a bright dot jumps while the stars do not | turn on "Show flagged pixels" | the dot is one flagged detector pixel; nothing supports a moving object | "Flags tell us not to trust it, not what caused it" |
| **Wavelength, not time: Epsilon Indi** (`fair_comparison`) | A `2026W18_1A_0516_1_D3` (2.323 µm) vs C `2026W18_1A_0516_1_D6` (4.940 µm), the same exposure on 2026-04-29 | the field looks completely different | read the wavelength at the marker | the difference is the colour of light, because the time is identical; A vs B (`2026W39_2A_0597_4_D3`, 150.8 d later, 2.322 µm) shows no visible change | "Different wavelengths show different things; no brightness was measured" |

## 6. Story

**30-second narrative (draft):**

> You blink two SPHEREx pictures taken three days apart, and a bright dot jumps while the stars stay put. Did you just find something? Perigee lets you check the way a scientist would. Same wavelength? Yes. Same contrast? Yes. Then you turn on the mission's own quality flags, and the dot is covered: one bad detector pixel that only *seemed* to move because the telescope pointed slightly differently. You rewrite your claim, "nothing here supports a moving object", and save it with the exact NASA files behind it. Then you open Barnard's Star and watch a real star creep north, consistent with the catalog prediction. Knowing which is which is the discovery.

**Seven-slide evidence outline** (inputs only; matches the existing seven-slide structure):

1. **The moment:** a dot jumps. "Did I find something?" (WISE A↔B blink.)
2. **Why it is hard:** four look-alike causes, namely time, wavelength, display stretch and flagged pixels. Control E: some questions cannot be answered from pixels alone.
3. **The check:** flags on; the dot is one detector pixel, 5.36″ vs 5.38″ predicted (claim #3). The claim is revised (illustrative card, labelled illustrative).
4. **The real thing:** Barnard moves north, 6.9–8.9 px across methods vs 7.29 predicted; stars ≤ 0.83 px (claims #1–2).
5. **The record:** an evidence card with observation IDs, IRSA URLs, SHA-256, dates, wavelengths and quality, all traceable (claim #15).
6. **Why it holds up:** every answer key is computed from the frames. Live = curated byte for byte. Alignment is checked against Gaia stars. New cases pass an automated admission check (claims #7, #9, #12).
7. **Honest limits and next:** no photometry, measured motion or discovery claims. Next: the third case and claim history (proposed).

## 7. Today, awaiting UI, future

| Today (public release, verified by the release owner) | Awaiting UI integration (data ready) | Future possibility (not built) |
|---|---|---|
| Two guided investigations; live SPHEREx search and frames; evidence card with provenance; save, reopen, JSON/PDF export. Curated content survives an origin outage (shown by local fault injection, not a production outage) | Third investigation "A dot that jumps"; the completion contract; reference answer shown after the claim; geometry-safe frame cache (F1); overlay-failure state (F3); separate card per visit (F8) | Claim revision history and curated/live source labels (§4 of the UI handoff); teacher or class views; more admitted cases through `admit_case.py` |

The D1 backend fix waits on the Python origin redeploy (`coordination/overnight-release-handoff.md`).

## 8. What NASA data contributes that a toy animation cannot

- **Real changes and real confounds in the same frames.** A star that truly moves (Barnard), a detector pixel that only seems to move (WISE), and the same instant looking different at another wavelength (Epsilon Indi). A synthetic animation would have to invent the confounds; SPHEREx supplies them.
- **Mission quality metadata.** Pipeline flags (NONFUNC, TRANSIENT, PERSIST and others) and per-pixel wavelength from the spectral WCS. These decide the answer, and they come from the files.
- **Traceable frames.** Every image links to an IRSA file with a SHA-256, so a reviewer can re-open the exact data. The answer keys are re-computed from those files by scripts in this repository.

**Contribution comparison (bounded):** `science/reviews/contribution/README.md`. SPHEREx Explorer already teaches wavelength, stretch and quality caveats with cases, a tour and a game. Its absence of a saved learner claim was observed only in the surfaces inspected; that is not proof the feature exists nowhere.
