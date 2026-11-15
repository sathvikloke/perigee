# Regression checks: chosen implementation (worker 23)

**Tested commit:** `efaa874ba84451583cbcf77ce0a42d746f64982b`, the `claude/perigee-integration` head on 2026-11-14. This branch adds only tests and QA scripts on top of it.

The build under test:
- API A with the API-review fixes (R1–R7)
- processor A `perigee-processor-a/0.1.2` and its 574 products
- the catalog (08)
- the Vercel Services config (07)
- frontend A with design A (01 + follow-up)
- the science acceptance review (15)

**Environment:**
- macOS (Darwin 25.5), local time zone America/Chicago
- Python 3.12 in `.venv` from `backend/requirements-dev.txt`
- Node 26; `npm ci` installs vite 7.3.8 and vitest 4.1.12
- Raw data, read only: `PERIGEE_DATA_ROOT=…/NASA Space Comp/research/build_data` (183 retained FITS)
- Real stack:
  - API: `PERIGEE_DEV_MODE=1 uvicorn backend.main:app --port 8050`
  - Frontend dev server: `PERIGEE_DEV_API=http://127.0.0.1:8050 vite --port 5196`
  - Built frontend: `vite preview --port 5323`, which serves `frontend/dist` and proxies `/api` to :8050
  - Browser checks ran in the Claude built-in browser.
- Live IRSA load for the whole run:
  - 3 SIA searches
  - 5 cutout fetches
  - Every other frame and search was served from cache, injected or mocked in the browser.

## Run it

```bash
~/Library/Python/3.9/bin/uv venv --python /Users/sathvikloke/.local/bin/python3.12 .venv
~/Library/Python/3.9/bin/uv pip install --python .venv/bin/python -r backend/requirements-dev.txt
(cd frontend && npm ci)
PERIGEE_DATA_ROOT=/path/to/research/build_data qa/regression/run.sh                              # offline
PERIGEE_DATA_ROOT=/path/to/research/build_data qa/regression/run.sh --live http://127.0.0.1:8050  # + 1 search, 1 cutout
```

`run.sh` runs these steps:
- backend pytest
- `deploy_check --app`
- frontend vitest and build
- `audit_all.py`
- `check_acceptance.py --all`, which always exits 0, so `run.sh` fails the step on any `False` column
- optionally `live_check.py`

Steps that need raw data report SKIP, not PASS, when `PERIGEE_DATA_ROOT` is unset.

Result on `efaa874` + this branch's tests:
- all six offline steps PASS
- backend 282 passed with raw data (265 passed / 17 skipped without it)
- vitest 42 passed
- audit 183/183
- acceptance 189 records with 0 False

## New tests (only where existing coverage had a gap)

| File | Pins |
|---|---|
| `backend/tests/api/test_regression_seam.py` | Real `/frame` route + real processor A (via `processor_a_adapter`), upstream fetch scripted to return the retained Eps Ind B cutout. The response must validate as `FrameResponse` and carry `registration.scale_arcsec_per_px`. **Negative control:** renaming the field back to `scale_arcsec_per_pixel` makes the API return `500 PROCESSING_FAILED (fields: registration.scale_arcsec_per_px)` and the test fails. |
| `backend/tests/platform/test_regression_vercelignore.py` | Applies `.vercelignore` with `git check-ignore --no-index`. `backend/data/process.py`, `archive.py`, routes, content, presets, `requirements.txt` and `frontend/src` must ship. `research/`, `/data/`, `/tools/`, `science/`, `backend/tests/` and `*.fits` must not. **Negative control:** the original unanchored `data/` does ignore `backend/data/process.py`. `deploy_check` does not test this. |
| `frontend/tests/regression.test.ts` | Evidence export built from the committed processor-A 0.1.2 case records carries identity, detector, release, `Z` UTC time, wavelength, IRSA source and `processing`, and keeps full-length notes (280 + 2000 + 2000 chars, including non-ASCII). Bare and `Z` timestamps near midnight give the same UTC date; this passed under America/Chicago, Pacific/Kiritimati and America/Los_Angeles. A failed frame leaves every other result in its own slot. |
| `qa/regression/live_check.py` | Live: `/health` names processor A. One `/search` and one `/frame` → 200 and `FrameResponse` validates. Unknown `/api/...` paths give a JSON 404 with `X-Request-ID` echoed in the body and header, checked on every `--base`. |

## Results

| # | Check | How | Result | Evidence |
|---|---|---|---|---|
| 1a | Seam: processor found | `live_check.py`; `/api/v1/health` | PASS | `frame_processor: backend.data.process.process_frame (processor-a adapter)` |
| 1b | Seam: live `/frame` → 200, FrameRecord validates, `scale_arcsec_per_px` | `live_check.py --base :8050` | PASS | Search 330.84, −56.786 → ready, 460 matches, 3.3 s. Frame `2025W17_4B_0017_1_D2`: clear, λ 1.54499 µm, 0.1.1, scale 1.40625, 5.2 s, 18 KB. Also 4 more live frames via the UI, all 200. |
| 1c | Seam: offline reproduction with negative control | `test_regression_seam.py` | PASS | Fails as expected with the old field name (see above). |
| 2 | `.vercelignore` keeps `backend/data/` | `test_regression_vercelignore.py`; `deploy_check --app` | PASS | `/data/` is anchored. The negative control proves the check can fail. `deploy_check: ok`. |
| 3 | Case plates use the shared-stretch case set | `client.test.ts` "requests a case product set with ?case_id="; browser on :5196 and built :5323 | PASS | Requests `…/barnards_star/frames?case_id=moving_neighbor` and `…/epsilon_indi_b/frames?case_id=fair_comparison`. Case plates load `…--case-moving_neighbor-…png` and `…--case-fair_comparison-…png`. The sequence viewer separately uses `--frames-…` (per-frame) assets, as intended. |
| 4 | R1–R7 | Existing `test_review_api.py` (12 tests: R1 ×3, R2, R3 ×2, R4 param + token, R5, R6) and `test_platform_request_id.py` (R7 ×2) | PASS | Inside the 282 passed. Not duplicated. R7 also passed live: `X-Request-ID: qa-23-rid` echoed on `/api/v1/cases/__qa_none__` through :8050, :5196 and :5323. |
| 5a | Transparent pixels over a non-sky hatch, with legend | Browser, Barnard case (:5196 and :5323) | PASS | The plate's `.sky` parent has a `repeating-linear-gradient(135deg …)` hatch behind the PNG. The saturated core shows over the hatch and is painted yellow by the overlay. Legend: "Hatched: no usable data (outside the image, or saturated / non-finite pixels). It is not dark sky." |
| 5b | Flag overlay on by default for flagged frames | Browser, Barnard (all 3 case frames flagged) | PASS | Both "Show flagged pixels" checkboxes are checked on load. `img.flag-overlay` is present for A and C. |
| 5c | not_covered wording | Browser, Eps Ind B sequence frame 1 (`2025W17_4B_0077_2_D1`) | PASS | "Position just off image. The predicted position is just outside this image … not evidence the object is absent." Wavelength: "Not available — the position is off this image". |
| 5d | Times compared by parsed value (Z suffix) | `regression.test.ts`; `audit_all` case check | PASS | `formatDateShort` gives equal UTC dates for bare and `Z` input in three time zones. `audit_all` compares case times as parsed instants: 6/6 ok. |
| 5e | J2000 label on 330.84, −56.786 | Browser, query view | PASS | "Use Epsilon Indi A, J2000 catalog position (330.84, −56.786) … moved about 2′ from there by 2026" |
| 5f | No pixel-count claim | Browser text scan, Barnard and Eps Ind B case pages | PASS | No "10–11", "display pixels" or "5 arcsec/pixel" on the page. The case JSON's `display_requirements.marker` sentence ("about 2 display pixels") is not rendered. Only `reference_line` is used. |
| 6a | Wavelength not reported on uncovered positions | `audit_all.py` check 3; `check_acceptance --all` coverage column | PASS | 4 not_covered frames, all with null λ. 0 of 574 product records have a status/λ mismatch. Acceptance coverage 189/189. |
| 6b | Saturation not treated as not covered | `check_acceptance --all` flags and coverage; R Dra `2026W01_2A_0426_1_D3` | PASS | `flagged`, `covered: true`, λ 2.0764 µm. Flags 189/189. |
| N1 | Failed frame does not reorder others | Browser: live search limit 4, frame index 1 forced to 502 by a `fetch` wrapper; `regression.test.ts` | PASS | Slots in order: `…0017_1_D2` ready, #2 "could not be processed. The other frames are unaffected.", `…0355_1_D2` ready, `…0216_2_D5` ready. Order equals the search response order. |
| N2 | Stale query response never shown | Browser: mocked `/search`; RA 10 answers after 4 s, RA 20 answers at once; also `client.test.ts` stale-response guard | PASS | The RA 10 response arrived 4 s later and was dropped. The page shows only "RA 20°, Dec 10°". No frame request was made for the stale tokens. |
| N3 | Expired token offers refresh and keeps notes | Browser: notes typed, then "Retry this frame" answered with injected 410 `TOKEN_EXPIRED` | PASS | `role=alert`: "This search has expired. Run it again to continue; your notes are kept." plus a "Run the search again" button. The notes were unchanged and persisted to `localStorage`. Re-running (live) gave 4 ready / 0 failed with the notes still present. |
| N4 | Unknown `/api/...` is JSON, never SPA HTML | `live_check.py` on :8050 (API), :5196 (vite dev proxy) and :5323 (built `dist` + proxy); `deploy_check --app` | PASS | `/api/v1/__qa_unknown__`, `/api/__qa_unknown__` and `/api/v1/cases/__qa_none__` all return `404 application/json`. A non-API path `/some/page` on :5323 returns `200 text/html` (SPA). |
| N5 | Evidence export JSON content | Browser export on the live query (download intercepted, no file written); `regression.test.ts` | PASS | `perigee-evidence-query-2026-11-14-….json`, `data_origin: api`, query 330.84/−56.786/6. Each frame has `frame_id`, detector 6 and 5, `spherex_dr1` and `spherex_qr3`, `…Z` UTC, λ, IRSA `source_url`, and `processing` (0.1.1, sha256, `nearest_neighbour`, `asinh`). Claim, observations and uncertainty match what was typed. |

**Regressions found:** none.

## Remaining blockers and limitations

- **Not tested on Vercel.**
  - Previews sit behind Vercel Authentication, which needs Sathvik.
  - The proxy setups (vite dev and vite preview) emulate the `/api` → API, `/(.*)` → SPA route order. They do not exercise Vercel's rewrites or the 4.5 MB limits.
- **Moving-neighbor case text** (`display_requirements.marker`, "about 2 display pixels at 5 arcsec/pixel") is still wrong in `backend/content/cases/moving_neighbor.json`. It is open escalation 1 for Sathvik. It is harmless today only because the frontend does not render that field.
- **Unrendered card fields:**
  - `marker_kind` is `null` in exported cards for coordinate searches, because a live query has no catalog target. This is expected, but a reader of the card might want it labeled.
  - Curated case cards have `catalog_prediction`.
- **Browser checks are manual.**
  - N1–N3 and N5 used in-page `fetch` wrappers and a mocked `/search`, not a committed E2E harness. No Playwright is installed in the repo.
  - The steps are recorded above so they can be repeated.
  - Worker 17 is editing `frontend/src` now, so 5a–5f and N1–N5 should be re-run after that merges.
- **Live archive behavior** is one afternoon and one target, and IRSA 503 rates vary. No load testing was done.
- **Shared ports and browser tabs.** The browser pane and local ports are shared with other sessions. Port 5197 was taken by another worker's dev server mid-run, so its results were discarded and the built-frontend checks used :5323.
