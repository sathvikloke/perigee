# QA-F1: evidence card export carries limitations

Finding from the fresh-user QA (issue #6, `qa/fresh-pass/README.md` on `codex/neeraj-qa` @ 31d98f7): the exported evidence card JSON had no limitations. The API supplies `limitations` for the case (`GET /api/v1/cases/<id>`) and for every frame (`FrameRecord.limitations`), but `frontend/src/evidence/card.ts` dropped both. Only the learner's own `uncertainty` text was exported.

## What changed

- `frontend/src/evidence/card.ts`
  - `EvidenceCard.title?: string | null` holds the case title for a case card or the preset display name for a preset without a case. It is `null` for a coordinate search, and older cards are normalized to `null`. QA-F3 asked for this field for the My evidence list.
  - `EvidenceCard.case_limitations?: string[] | null` holds the active case's `limitations`, copied verbatim from the API. It is `null` when no case is active, which includes every coordinate search.
  - `EvidenceFrame.limitations?: string[] | null` holds the frame record's `limitations`, verbatim. `[]` means the API reported none. `null` means the frame was attached before this field existed.
  - `cleanLimitations` keeps only strings and drops exact duplicates. It never rewords, trims or truncates a string. As a defensive bound it keeps at most 20 items and skips any item longer than `TEXT_MAX`; real API lists have 4–5 short items.
  - `normalizeEvidenceCard` runs on every load (`validateEvidenceCard`) and every export (`serializeEvidenceCard`). A missing or malformed additive field becomes `null`; the card is not rejected, so learner text is never lost. Every other field is returned unchanged.
  - `fillCardContext`: when a card is reopened, a missing title or missing case limitations are filled from a freshly made card for the same case and preset. It never takes values from a different investigation.
  - `fillFrameLimitations`: when the same case pair is attached again, pair frames that lack limitations get them from the frame records.
  - `withCaseContext` runs at export time. If a case card still lacks its case title or limitations and the case content is loaded, they are added. Existing values always win.
  - `printedLimitations` builds the short list for print. A case card prints its case limitations; a card without a case prints its frames' limitations with duplicates removed.
  - Export key order: `title` follows `preset_id`, and `case_limitations` follows `uncertainty`, so the dataset's stated limits sit next to the learner's own. All fill steps keep `updated_at_utc` and the learner's claim, observations and uncertainty untouched.
- `frontend/src/evidence/useEvidenceCard.ts`: when a stored card is reopened, `fillCardContext` is applied. If anything was filled, the copy is written back quietly with the same `updated_at_utc`, so saved-card lists can show the title. A refused write is harmless.
- `frontend/src/components/Notebook.tsx`: export and print use `withCaseContext(exportCard, caseContent)`. The print-only provenance section gains one short "Stated limitations (from the case | observation records)" list. It uses the existing `.print-provenance` 10px print styling and adds no new visual treatment. Nothing changes on screen: CaseBench and FrameDetails already show limitations there. Frame IDs, detector/release, UTC, wavelength, flag screen, source URL, processing/SHA and notes are still printed.
- **Outside my ownership, two lines:** `frontend/src/components/PresetInvestigation.tsx` `makeCard` now passes `title: caseContent?.title ?? preset?.display_name ?? null` and `case_limitations: caseContent?.limitations ?? null` to `createEvidenceCard`. Without these lines, case cards still export and print case limitations through `withCaseContext` in the Notebook, but a preset card without a case gets no title. `QueryInvestigation.tsx` is unchanged, because coordinate searches default to `title: null` and `case_limitations: null`.

### Schema version: not bumped (stays 1)

The new fields are additive and optional. Stored v1 cards load without them, and `normalizeEvidenceCard` fills `null`. A bump would cost more than it gains. Older deployed builds check `schema_version === 1`, so they would silently drop every card a newer build saves, and those notes would disappear from their browsers. With v1, older builds ignore the extra keys. The storage key `perigee.evidence.v1` is unchanged.

### Size and safety

Cards hold only text: no images, data URLs, FITS or tokens. The test asserts the export has no `data:image`/`base64`/`.png`. `MAX_STORED_CARDS` (50), `CLAIM_MAX`/`TEXT_MAX` and the storage-failure handling (`persistStore` returning `false`, plus session drafts) are unchanged. Limitation lists add about 1–2 KB per case card.

## Exported shape

```jsonc
{
  "schema_version": 1, "id": "…", "created_at_utc": "…", "updated_at_utc": "…",
  "app_version": "0.1.0", "data_origin": "api",
  "case_id": "fair_comparison", "preset_id": "epsilon_indi_b",
  "title": "Is this a fair comparison?",            // null for a coordinate search
  "query": { … },
  "frames": [ { "ref": "A", "frame_key": "…", …, "source_url": "…",
                "limitations": [ "…verbatim FrameRecord.limitations…" ],   // null = attached before this field
                "processing": { … } } ],
  "claim": "…", "observations": "…", "uncertainty": "…",
  "case_limitations": [ "…verbatim case limitations…" ],  // null without a case
  "sources": [ … ]
}
```

## Evidence: real exported files

Backend `PERIGEE_DEV_MODE=1 uvicorn backend.main:app --port 8060`, Vite dev on `localhost:5391` proxying `/api` to it. The pages were opened in the built-in browser. Download blobs were captured in page JS by wrapping `URL.createObjectURL` after clicking the real **Export evidence card** button, then written byte-for-byte through a local receiver. The file's SHA-256 matched the in-page hash.

- `fair_comparison-export.json`: `?preset=epsilon_indi_b`, default A + B pair, claim/observations/uncertainty typed into the notebook, then exported.
  - `case_limitations` has **5 items**, equal to `backend/content/cases/fair_comparison.json` `limitations` and to `GET /api/v1/cases/fair_comparison` (5 today; the brief said "e.g. 4").
  - Per-frame `limitations`: A (`2026W18_1A_0516_1_D3`) has 4 and B (`2026W39_2A_0597_4_D3`) has 5. Each list is exactly equal to that frame record's `limitations` in `backend/content/presets/epsilon_indi_b/case-fair_comparison/`.
  - `title`: "Is this a fair comparison?".
  - Excerpt:
    ```json
    "uncertainty": "No brightness was measured, so I cannot say whether it changed.",
    "case_limitations": [
      "The quality screen checks for problem flags in a small circle around the predicted position. It is not a detection test or a brightness measurement.",
      "A is from Data Release 1 and B is from Quick Release 3 (both pipeline version v27). Quick-release products may be reprocessed later.",
      …
    ```
- `query-export.json`: a live IRSA coordinate search at RA 83.82, Dec −5.39, 6′, limit 3. Three frames processed. Frames `2025W36_2B_0338_1_D1` and `2026W11_1A_0124_4_D2` were attached, then the card was exported. It has `title: null` and `case_limitations: null`, and each frame has its 4 API limitations (including "Per-frame stretch: brightness is not directly comparable with other frames."). IRSA did not return a 502 during this run.
- `v1-reopened-export.json`: the legacy card check below, exported after reopening.

### Seeded v1 card (no new fields)

A card was written straight to `localStorage["perigee.evidence.v1"]` in the old shape: no `title`, no `case_limitations`, no frame `limitations`. It had distinctive learner text with an em dash, ±, µ, curly quotes and a newline, and was mapped to the `api:preset:epsilon_indi_b` context. Then:

1. **Lists:** the page was reloaded at `/`. My evidence shows it ("fair_comparison · Updated 13 Nov 2026 · 2 observations · “LEGACY claim …”") next to the query card.
2. **Exports without loss, before reopening:** the list's Export JSON was used. Every original key and every original frame key is JSON-identical to the seeded card. The new keys export as `null`.
3. **Opens:** `?preset=epsilon_indi_b` shows "Restored from this device", and all three textareas hold the legacy text exactly. The stored copy now has `title` and the 5 `case_limitations`. Its `updated_at_utc` is still `2026-11-13T09:30:00.000Z`, and every original field is unchanged.
4. **Exports after reopening:** the notebook's Export button produced `v1-reopened-export.json`. Every original field is identical, and it adds the title, 5 case limitations and per-frame limitations (4 and 5), filled from the re-attached pair.

## Tests

- `frontend/tests/evidence-limitations.test.ts` (new, 12 tests)
  - Construction: verbatim lists, only exact duplicates removed, `[]` vs `null`, coordinate-search shape.
  - Export: key order, case limitations after `uncertainty`, round-trip, no image data, export-time case context.
  - Print: the case list printed once each, frame lists for a query card, nothing extra when no limitations are known, existing provenance still printed.
  - v1 normalization: every existing field kept, malformed new fields nulled rather than the card being rejected.
  - Reopen fill: learner text and `updated_at_utc` untouched, never borrowed from another case, frame limitations filled on re-attach, idempotent.
- `frontend/tests/evidence.test.ts`: the key-order contract now includes `title` and `case_limitations`.
- `frontend/tests/play-and-export.test.ts`: the export-shape frame includes `limitations`.

## Regression gates

Run after rebasing onto `origin/claude/perigee-integration` @ 6f08d56:

```
PERIGEE_DATA_ROOT=".../research/build_data" qa/regression/run.sh     # commit 77fa179 (pre-README)
PASS  backend pytest                       299 passed
PASS  deploy_check --app                   deploy_check: ok
PASS  frontend vitest                      9 files, 99 tests passed
PASS  frontend build                       tsc + vite build ok
PASS  audit_all (183 frames)               183/183 processed
PASS  check_acceptance --all (189 records) 189 records, no False column
SKIP  live_check                           (not requested)
```

The exports were captured before the rebase, at base ebdc0a0. After the rebase, the case limitations and both frames' limitations in the content still equal the exported lists exactly; only the case `status` changed.

## Left open

- Old *non-pair* frames, and frames on old coordinate-search cards, keep `limitations: null` until re-attached. Their FrameRecords are not available to the evidence module when a card is reopened.
- The print list was checked as DOM text in the browser and in tests. No printed PDF was rendered.
