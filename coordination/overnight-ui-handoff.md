# UI handoff (N4): third investigation, evidence record, failure states

> Release update: PRs #50 and #51 are merged and deployed. The third investigation and completion flow are live, as is the Python crash fix. This handoff preserves the earlier candidate state; see [current release evidence](../qa/final-investigation/README.md).

**Audience:** Codex, owner of `frontend/**` and the release. Nothing below changes `frontend/**`. Every file named here is outside it.

**Status:** the data and contracts are ready. **All of the outcomes listed in §7 still need UI work, and none is marked done here.**

## 1. Files

| What | Path | How it is produced |
|---|---|---|
| Staged third investigation | `science/staging/wise_0855_quality_trap/case.json` and `presets/wise_0855/case-wise_0855_quality_trap/` | `tools.ingest.ingest`; admitted by `tools/ingest/admit_case.py` (verdict admit). The copy steps are in `science/staging/README.md` → "Integration handoff" |
| Reviewed answer key, numbers with tolerances | `science/reviews/transfer-exercise/answer_evidence.json` (A1–A7, 29 quantities), `science/staging/wise_0855_quality_trap/evidence_map.json` (16 conclusions → answer ids) | `check_transfer.py --out` |
| Illustrative evidence record (initial and revised claim) | `qa/ui-fixtures/evidence_card.wise_0855_quality_trap.illustrative.json` | `node qa/ui-fixtures/make_case_evidence_fixture.mjs --data-root <build_data>`. Records go through the shipped `normalizePresetFrames`; cards are built with the shipped `createEvidenceCard` / `toggleEvidenceFrame` / `updateEvidenceText` and validated with `validateEvidenceCard` |
| Reproducibility check (case ↔ records ↔ assets ↔ raw cutouts ↔ cards) | `qa/ui-fixtures/case_evidence_check.json` | same script: **72/72 checks pass**, raw cutout SHA-256 verified against `build_data` |
| Failure-state fixtures | `qa/ui-fixtures/{missing_overlay,case_unavailable,unknown_case,live_origin_unavailable,no_coverage,reused_api_examples}.json` | `node qa/ui-fixtures/make_fixtures.mjs`, run after `cloudflare/build.py`. Responses come from the real Worker `handle()` with fault-injected assets |
| Same frame at a different geometry | `qa/overnight-backend/fixtures/request_identity_fixture.json` | N5: the live route with a real retained cutout. One `frame_key`, four grids/scales/hashes |

The evidence script needs Node ≥ 22.18 because it imports `.ts` directly. Re-running both scripts gives no git diff (the evidence script with `--data-root`; without it, the raw-hash checks are recorded as skipped).

## 2. Third investigation: "A dot that jumps" (`wise_0855_quality_trap`)

**Why it is worth a slot:** it is a convincing false positive, a flagged detector pixel that *appears to move* while the stars stay still. Its refusal is traceable, and it adds a target-identity trap and an honest "these frames cannot test motion" ending. The shipped cases do not cover that trap.

### Frames, in sequence order

| Ref | frame_key | Date (UTC, mid-exposure) | λ at marker | Quality at marker | Stretch |
|---|---|---|---|---|---|
| A | `2025W45_2A_0278_1_D2` | 2025-11-07 18:48 | 1.2572 µm (band 0.0301) | clear, 0 of 20 screened | shared A+B, asinh 0.2319–2.6719 MJy/sr |
| B | `2025W46_1A_0108_1_D2` | 2025-11-10 10:31 | 1.2572 µm (band 0.0301) | **flagged PERSIST**, 2 of 19 | shared A+B |
| C | `2026W20_1A_0214_1_D2` | 2026-05-11 13:37 | 1.4443 µm (band 0.0353) | clear, 0 of 19 | own, 0.2070–2.2294; label it "Brightness not directly comparable" |

All three are on grid `f448bdf044c35cf1`, processor `perigee-processor-a/0.1.2`, detector 2, `spherex_dr1`. Asset ids are `wise_0855.case-wise_0855_quality_trap.<frame_key>.png` and `….flags.png`.

### Copy

Use the text in `case.json` verbatim; it passed the admission checks. The reviewed text lives in these fields:

- `opening_question`;
- six `steps[].prompt` with `hint`;
- `claim_prompt`;
- `conclusion_guide.supported` (7 items) and `not_supported` (9 items, each with its reason);
- `example_claim`;
- `limitations`.

| Step | Learner action | The point (from the hint) |
|---|---|---|
| `matched_pair` | read date and λ for A, B and C | A/B: 2.7 d apart, Δλ 0.2% of the band, so the better pair. Pointing, pipeline build and B's PERSIST flag still differ |
| `jumping_dot` | blink A↔B, then turn on flags | single native pixel, NONFUNC/TRANSIENT/SUR_ERROR, same detector pixel; it lands about 5″ apart because pointing changed |
| `only_in_a` | find the left-edge dot, then check flags | TRANSIENT/OUTLIER/HALO/SUR_ERROR; B and C show background there |
| `stretch` | compare A or B with C | 1.0 MJy/sr is grey 159 in A/B and grey 177 in C: a display effect, not a measurement |
| `marker` | marker on | the marker is a catalog prediction. The dot to its upper right lies within about 1″ of Gaia DR3 5756956644387831296, not WISE 0855 |
| `motion_test` | A vs C | cannot test motion: the target is not identified and C is at another wavelength |

### Required display states

- **Flags:** "Show flagged pixels" must work for A, B and C in steps 2 and 3. The flagged dots are away from the marker, so the marker's quality chip alone hides them.
- **Marker:** label it "Catalog prediction (not a detection)". No guide line: A→B is 0.04 display px and A→C is 2.9 px.
- **Products:** A and B must use the case products (shared stretch), never the per-frame preset products. If the case fails to load, show an error; do not fall back silently (F4).
- **Optional hint highlights** (display px, origin top-left), from `B_features.csv` and `answer_evidence.json`:
  - jumping dot A (114.9, 82.9) and B (117.9, 80.6);
  - A-only dot (32.4, 111.8);
  - dot near the marker, first moment about (132.3, 125.8);
  - marker (127.1, 128.1) in A.

### Answer key

The answer key is `conclusion_guide`, with every item mapped to evidence in `evidence_map.json`. Never auto-grade free text against it. It is shown to the learner as the reference after they record their claim (see §5).

## 3. Illustrative evidence record

`qa/ui-fixtures/evidence_card.wise_0855_quality_trap.illustrative.json` holds `initial_card` and `revised_card`, both valid schema-1 cards (A and B attached), plus a `revision` block.

> **The learner text is illustrative.** The coordinator wrote it to show the shape of a revision. It is not from a participant, and it must never be shown as user feedback or a testimonial. Labelled the same way in the file.

| | Claim (learner words) | Justifying observation |
|---|---|---|
| Initial | "A bright dot moved between 7 and 10 November while the stars stayed still, so something near WISE 0855 may be moving." | blink only; "I have not checked … flagged pixels yet" |
| Revised | "A and B match in wavelength, but the dot that jumps is one flagged detector pixel in both, and the dot only in A is flagged too. Among the dots I checked, nothing supports a new or moving object." | the flag overlay covers the jumping dot in A and B; one native pixel wide; flag names read |

**What is authored and what is computed:**

- `claim`, `observations` and `uncertainty` are learner text.
- Per-frame fields are copied from the FrameRecord by `frameToEvidence`: dates, λ, band, `quality_status`, flag names, `display_scale_mode`, `source_url`, `processing.file_sha256`, `processing.pipeline_version` and limitations.
- The reference answer exists only in `case.json`. The fixture check asserts that neither claim equals `example_claim`.
- `revision.computed_facts_backing_the_reference_answer` cites the files for each number:
  - detector pixel (1709, 1364);
  - an apparent 5.36″ jump against 5.38″ predicted from the stars' pointing shift;
  - the Gaia match.

**Reproducibility (`case_evidence_check.json`, 72 checks).** For each of A, B and C, the case and record agree on:

- `observation_id`, detector, collection, `source_url`, `mjd`, `time_basis` and `observed_at_utc`;
- λ and band to 4 dp;
- expected quality, against the record's status;
- SHA-256, against provenance and against the raw cutout on disk;
- MJy/sr unit, grid, catalog-prediction marker and processing version.

All image and overlay assets are present (with their hashes). The check also confirms A and B share identical stretch limits, C is `per_frame`, and the `display_requirements` text says so. Both cards pass the shipped validator, and every card frame equals its record.

## 4. Small compatible schema addition (optional; no migration needed)

The current card cannot express two distinctions:

1. Whether a frame came from **curated** content or a **live** query. `data_origin` is only `api` / `fixture`.
2. The **revision history** of a claim. Only the latest text is stored.

Proposed additive fields, still `schema_version: 1`, following the existing normalize-on-load pattern used for `title` and `limitations`:

| Field | Type | Fill rule | Old cards |
|---|---|---|---|
| `frames[].source_kind` | `"curated_case" \| "curated_preset" \| "live_query"` | the card has a `case_id` and the frame came from `/presets/{id}/frames?case_id=` → `curated_case`; preset frames → `curated_preset`; `/frames` via a search token → `live_query` | normalize missing to `null` (unknown). Never guess |
| `claim_history` | `[{claim, saved_at_utc}]`, at most 10 entries, each `claim` ≤ `CLAIM_MAX` | append the previous `claim` when a *saved* card's claim changes; never edit entries | `[]` |
| `reference_shown` | `boolean` | true once the learner has opened `conclusion_guide` for this card | `false` |

Rules:

- Export keeps the learner's words exactly as typed.
- Never copy `conclusion_guide` text into `claim`, `observations` or `uncertainty`.
- The printed card labels the claim "Your claim" and, if shown, prints the reference under a separate "Reference answer (from the case)" heading.

If you skip the addition, the fallback is to print `case_id`/`preset_id` and the existing `data_origin`, and say "revision history not recorded".

## 5. Contracts the UI must keep

**Completion.** An investigation is complete only when **all** of these hold:

1. The card has the required refs: `evidence_requirements.must_include_refs_any_of`, here A and B, with at least 2 frames.
2. `claim` is non-empty and `uncertainty` is non-empty.
3. The learner has visited each step: steps viewed, a client-side state only.
4. The card is saved.

The following are **not** completion: a PNG loading, a notebook existing, an auto-created draft, or the learner opening the reference answer. No backend grading and no LLM judging of free text. After completion, show the reference `conclusion_guide` next to the learner's words, never in place of them.

**Second visit.** Use existing primitives only:

1. Reopen a saved card from the saved list (`reopen.ts`). Its frames, claim and query come back as saved.
2. Choose another reviewed case (`fair_comparison`, `moving_neighbor`, and this one once shipped) or an independent coordinate search.
3. That creates a **new, separate** card. It never mutates the reopened one, and never carries over `case_id` or title (F8).
4. Export each card on its own.

A teacher view, comparing classes, or shared storage are **future possibilities**. They are not shipped and must not be described as shipped.

**Distinctions to keep visible:**

| Keep apart | Rule |
|---|---|
| Curated vs live | Curated (case or preset) frames are reviewed content served from the bundle and keep working when the origin is down. Live frames come from a search token and may expire. Label live frames "from your search" |
| Asset missing vs quality flagged | A 404 overlay (`missing_overlay.json`, `ASSET_NOT_FOUND`) is "overlay could not be loaded". Keep the record's `quality.status` text unchanged, disable the toggle and hide the legend. Never show "clear" or "no flags" because an image failed (F3; `Plate.tsx:102` has no `onError` on the overlay `<img>`) |
| Selected comparison vs unrelated stored cards | Only the frames attached to *this* card are its evidence. Other saved cards are not part of it, even for the same target |
| Draft vs completed claim | Draft is any unsaved or incomplete card. Completed means the contract above |
| Catalog prediction vs image measurement | The marker is always "Catalog prediction (not a detection)". Nothing in Perigee measures a position, brightness or motion |

**Request identity (F1).** Cache a frame on `(mode, observation_id, detector, collection_id, source_url, ra_deg, dec_deg, fov_arcmin, grid_px)`, store `processing_version`, and invalidate when it changes. Never key on `frame_token`, `request_id` or `retrieved_at`. Today `QueryInvestigation.tsx:93` keys on `${api.mode}:${frame_key}` only. `request_identity_fixture.json` shows the same `frame_key` at 2′, 10′, a shifted centre and off-cutout, with four different `grid_id` and PNG hashes. A UI check: request fov 2 then fov 10 for that frame; the second must show `grid_id d93587c261ed4894`, not `b038ca97a9ce825e`.

## 6. Failure-state fixtures → expected UI

| Fixture | Response | Expected UI |
|---|---|---|
| `missing_overlay.json` | 404 `ASSET_NOT_FOUND` for the flags PNG; record says `clear` | keep "clear" from the record; overlay "could not be loaded"; toggle disabled; no legend |
| `case_unavailable.json` | 503 `CONTENT_UNAVAILABLE` (JSON) | "investigation images unavailable, retry"; no silent per-frame fallback |
| `unknown_case.json` | 404 `CASE_NOT_FOUND` with `available_case_ids` | "investigation not found"; offer the available cases; keep notes |
| `live_origin_unavailable.json` | presets 200; health 502 `UPSTREAM_UNAVAILABLE` | curated investigations keep working; live search shows "archive unavailable, retry", never an empty result |
| `no_coverage.json` | real record `2025W17_4B_0077_2_D1`, `not_covered` | "target outside this image"; no wavelength at target; not "flagged" or "clear" |
| `reused_api_examples.json` → `search_response.partial.fixture.json` | partial search | show results **and** the per-collection failure; never "complete" |
| → `search_response.empty.fixture.json` | `status: empty`, `collections_failed: []` | "no SPHEREx images in these collections cover this position". Show its scope warning: zero here does not mean never observed. Distinct from failure |
| → `error.token_expired.json` | 400 `TOKEN_EXPIRED`, `details.action = "refresh_search"` (`backend/routes/frames.py`) | re-run the same search to get fresh tokens; keep the card and its notes |
| → `error.invalid_coordinates.json`, `error.invalid_field_of_view.json` | 400 | field-level messages |
| `request_identity_fixture.json` | same frame, different FOV or centre | stale/mismatched selection: never reuse a cached image across geometries; a card's attached frame keeps the geometry it was attached with |

## 7. UI work that remains (Codex)

Not done here, and not marked complete:

1. **Ship the third case:** copy the files (`science/staging/README.md`), wire it as a case, and implement the display states in §2.
2. **Completion contract and reference-after-claim display** (§5).
3. **Optional:** the additive fields in §4, or the fallback.
4. **Known frontend findings:**
   - F1: cache key omits geometry. Fix with the identity tuple above.
   - F2: URL/history leaves stale results or notes; the result limit is not serialized.
   - F3: overlay failure leaves an enabled legend. `Plate.tsx` overlay `<img>` has no `onError` (P2, confirmed by N5/N6).
   - F4: a failed case load silently falls back to the per-frame stretch.
   - F5: notebook current-record vs collection state; timer-driven focus.
   - F6: removing a required comparison member reattaches it.
   - F7: placeholder contrast.
   - F8: unrelated searches keep the case identity in notebook and export labels.
   - Copy and accessibility: Barnard date labels; two- vs three-frame wording; flag glossary; accurate draft status; phone and keyboard/screen-reader behaviour.
5. **Browser check:** drive this case in a browser after integration. It has not been driven here, and the public API does not serve it yet.
