# Loading, partial results and recovery (worker 18)

This report covers the live coordinate search when IRSA is slow or failing. It was tested on the real stack, with faults injected between the frontend and the API.

**Base commit:** `claude/perigee-integration` at `5518359`, plus this branch.

**Environment:**
- macOS (Darwin 25.5), Python 3.12 `.venv` built from `backend/requirements-dev.txt`, `npm ci`, vite 7.3.8, vitest 4.1.12.
- Chain: browser → vite :5199 (dev proxy) → `fault_proxy.py` :8081 → API :8080 → IRSA.
- The browser checks ran in the Claude built-in browser at 1280×900.

**Real IRSA load for the whole run:** 3 SIA searches and 21 cutouts.
- The planned load was one search plus 12 cutouts, recorded once and replayed afterwards.
- The other 2 searches and 9 cutouts came from a Vite hot reload. It re-mounted the page while its URL still pointed at a search that had never finished. That URL behaviour is gap G5 below.

## Reproduce

```bash
PERIGEE_DEV_MODE=1 PERIGEE_TOKEN_TTL_S=86400 .venv/bin/python -m uvicorn backend.main:app --port 8080
.venv/bin/python qa/loading-recovery/fault_proxy.py --listen 8081 --upstream http://127.0.0.1:8080 \
    --force-limit 12 --cache /tmp/perigee-fault-cache
(cd frontend && PERIGEE_DEV_API=http://127.0.0.1:8081 npx vite --port 5199 --strictPort)
# open http://localhost:5199/?view=query&ra=330.84&dec=-56.786&fov=6 once (records 1 search + 12 frames)
curl -XPOST localhost:8081/__faults -d '{"frame_fail_once":[3,8],"frame_delay_s":{"0":9}}'   # then reload
curl localhost:8081/__stats    # max concurrent /frame, attempts per result index
```

**How faults are injected:**
- `fault_proxy.py` is stdlib only. It replays recorded `/search` and `/frame` answers, and its `POST /__faults` endpoint accepts these rules:
  - `search_delay_s`
  - `search_error` (a 504 `UPSTREAM_TIMEOUT` or 503 envelope)
  - `search_partial` (rewrites the answer to `partial` with `collections_failed`)
  - `search_partial_empty`
  - `frame_delay_s` (per result index)
  - `frame_fail_once` (a 502 `UPSTREAM_UNAVAILABLE` on the first attempt only)
- Its `GET /__stats` endpoint reports the maximum number of concurrent `/frame` requests.
- "Offline" means an in-page `window.fetch` that rejects with `TypeError('Failed to fetch')`, restored afterwards. This is the same technique worker 23 used.

## Case matrix

| # | Case | How | Before (5518359) | After (this branch) | Result |
|---|---|---|---|---|---|
| 1a | Search that takes 15–25 s | `search_delay_s: 20`, reload | "Searching the archive for RA 330.84°, Dec -56.786°, 6′ field…". No elapsed time and no expectation. Cancel works. | Adds an elapsed counter ("… 12 s"). After 8 s it also says the NASA/IPAC archive is slow to answer, that Perigee stops waiting after 45 seconds, and that you can cancel sooner. The button reads "Cancel search". | **Fixed** (G1). [01](01-slow-search-after.jpg) |
| 1b | A new search cancels the old one | Search A (−56.70), then 3 s later search B (−56.60); a `fetch` wrapper records `signal` aborts | A's `/search` signal aborted after 3040 ms; B stayed live | Same | PASS |
| 1c | Fast double-click, Enter ×5, double-clicked "Try again" | Double-click Search; Enter five times in Dec plus one click; double-click Try again. Count with proxy `search_calls` | 1 search for the double-click | 1 search in each case. All starts now go through `startSearch` + `isDuplicateSubmit`. A different query always supersedes the old one. | PASS (hardened) |
| 2a | Timeout (504 `UPSTREAM_TIMEOUT`) | `search_error` 504 | `role=alert`: "The archive search failed. This is not a result about the sky." with the message, Try again, "Still showing the previous images and notes…" | Unchanged for archive codes | PASS |
| 2b | Partial (one collection failed) | `search_partial: ["spherex_qr3"]` | "12 observations found **in spherex_dr1, spherex_qr3**". The failed collection was listed as searched. Generic partial notice; no retry. | "12 observations found in spherex_dr1". The notice reads "Partial results: spherex_qr3 could not be searched, so some images may be missing." It has a **Search again** button. The API's duplicate warning sentence is hidden. | **Fixed** (G4). [02](02-partial-after.png) |
| 2c | Partial with 0 results | `search_partial: ["spherex_dr1"], search_partial_empty: true` | "**0 observations found** in spherex_dr1, spherex_qr3 … 0 ready". This reads like an empty sky. | "No images from spherex_qr3, and spherex_dr1 could not be searched. This is an incomplete answer, not a result about the sky." plus **Search again**. The screen-reader status says "Search incomplete". | **Fixed** (G4) |
| 3a | 2 of 12 frames fail with 502, then retry | `frame_fail_once: [3, 8]` | Only a summary count ("2 failed"). The learner had to step through 12 frames to find them. Per-frame retry worked. | The summary has **Retry 2 failed frames** and "Not loaded: #4, #9" jump links. Per-frame retry still works. After the retries all 12 frames were ready, in the same date order. | **Fixed** (G3). [03](03-failed-frames-after.jpg) |
| 3b | Concurrency ≤ 2 including retries | "Retry 1 failed frame" clicked mid-pass while 2 lanes were busy; per-frame retries | First pass ≤ 2. A retry bypassed the limit (`api.frame` directly), so during a pass it could reach 3+. | One shared `createLimiter(2)` queues every frame request. Proxy `frame_max_inflight` was 2 in every run, including mid-pass retry, retry-all of 6 and load-all of 10. | **Fixed** (G3) |
| 4 | Slow frame (9–20 s) | `frame_delay_s: {"0": 9}` and `{"0": 20}` | "Processing this frame…" with no time. Other frames completed and were reachable, and the counts updated. | "Processing this frame… 11 s", in the sky-label colour. Frames waiting for a slot show "Waiting…" until the request actually starts. | PASS, improved. [04](04-slow-frame-after.jpg) |
| 5 | Offline mid-search | Old results shown; `fetch` rejects; new search; `fetch` restored | "The **archive** search failed…" for `NETWORK_ERROR`. Old images and notes were kept. **"Retry this frame" on an old failed frame did nothing**, because retry required `phase === "searched"` and a live ticket. | The title reads "The search did not reach the archive. This is not a result about the sky." Old images and notes are kept. Per-frame retry and retry-all work after a failed or cancelled search. | **Fixed** (G2). [05](05-offline-after.jpg) |
| 5b | Offline mid-frames | 3 s per frame; `fetch` rejects from 4 s to 8 s | 6–8 frames failed with `NETWORK_ERROR`, each needing its own retry | "Retry 6 failed frames" brought back all 12, in order, with at most 2 concurrent | **Fixed** (G3) |
| 5c | Cancel a newer search while old frames are loading | 4 s frames; new search (10 s, 504); Cancel after 1.5 s | 10 old frames became non-retryable "failed" (`SUPERSEDED`, `retryable: false`) with no way to load them | "2 ready · 0 failed · 10 stopped by a newer search" and **Load 10 stopped frames**, which brought back all 12 | **Fixed** (G2). [07](07-cancel-stopped-after.png) |
| 6 | Notes survive, including reload | A claim was typed and then each case above was run. The page was reloaded while `/search` returned 503. | The claim stayed in `localStorage`. **After a reload with the archive failing, the notebook was not rendered at all**, because it needed a successful search. Separately, the URL switched to the unfinished query at submit, so a reload opened a different position whose notes are empty. | The notebook shows the opened position's saved notes during loading and failure, with "Your notes for RA 330.84°, Dec -56.786°, 6′ field are kept. Images appear once the search succeeds." The URL changes only when a search succeeds. In every case the claim was intact. | **Fixed** (G5). [06](06-reload-during-outage-after.jpg) |
| 7 | Play and blink with failures | 2 failed frames; Play sampled every 250 ms; Blink sampled every 500 ms | — | Play visited 5,6,7,8,10,11,12,1,2,3 and skipped #4 and #9. After the retry, Play covers all frames. Blink alternated #1 and #12. Failed frames are disabled in the blink pair picker. | PASS |

N1–N3 from `qa/regression/README.md` were not redone. N1 (failed frame keeps order) is covered again by 3a/5b. N3 (expired token) now uses `startSearch` for "Run the search again".

## Fixes by file

- `frontend/src/components/QueryInvestigation.tsx`:
  - Splits search and frame request generations (`searchGate`, `frameGate`). This is G2: retry works after a failed or cancelled search.
  - Adds a shared frame limiter, retry-all, jump links and an honest label for stopped frames (G3).
  - `SearchProgress` shows elapsed time and the slow-archive copy (G1).
  - Partial labelling uses the collections that answered, names the failed collections, offers "Search again", and has a separate partial-empty state (G4).
  - `notesQuery` keeps the notebook on the opened position, and the URL updates only on success (G5).
  - All search starts go through a duplicate guard.
- `frontend/src/api/client.ts`:
  - Adds `createLimiter(limit)` (FIFO; an abort while queued rejects without running).
  - Keeps `collections_failed` from the API.
  - Exports `SEARCH_TIMEOUT_MS`.
- `frontend/src/api/types.ts`: `SearchResponse.collections_failed`.
- `frontend/src/lib/requestState.ts` (new): pure helpers. These are `sameQuery`, `isDuplicateSubmit`, `formatElapsed`, `searchScope`, `retryableFailedIndices`, `stoppedCount`, `retryActionLabel` and `searchFailureTitle`.
- `frontend/src/components/common.tsx`: `useNow` and `Elapsed`.
- `frontend/src/components/FrameViewer.tsx`:
  - Per-frame elapsed time while processing.
  - "stopped by a newer search" wording for `SUPERSEDED`.
- `frontend/src/styles/app.css`: `.sky-empty .counter` uses the existing `--sky-label` token, so the counter is readable on the dark plate.
- `frontend/src/fixtures/devFixture.ts`: `collections_failed: []`.
- `frontend/tests/loading-recovery.test.ts` (new): 11 tests.
  - The limiter stays ≤ 2 with a first pass, single-frame retries and retry-all running together. It keeps FIFO order, aborts while queued and releases its slot on a throw.
  - 2 of 12 frames fail and retry-all refills them in order.
  - Retryable-index rules.
  - Stopped versus failed labels.
  - Partial `collections_failed` normalisation.
  - The duplicate-submit guard.
  - Elapsed formatting.
  - Failure titles never claim an empty sky.

## Verification

- `npm run build`: clean (tsc plus vite).
- `npm test`: 71 passed. That is 60 on the base commit plus 11 new. The brief said 56; the base actually had 60.

## Limitations

- **Browser checks are manual.** They were driven through the built-in browser with DOM reads; there is no committed E2E harness. The vitest tests pin the logic, but no component is rendered in tests, because the repo has no jsdom or testing-library.
- **Replay artefacts.**
  - The partial rewrite in `fault_proxy.py` keeps the recorded qr3 observations in the list. A real partial answer would not include them.
  - The counts and warnings ("of 460", "Showing 12 of 460") come from the recorded limit-12 search.
- **StrictMode double search in dev.** In development, StrictMode starts the opening search twice; the first is aborted. Production builds do not do this.
- **The frame list gives no per-frame status.** The slider and pair picker still say nothing about which frames failed. The summary's "Not loaded" jump links cover that need without redesigning the stepper.
- **Phone width was checked only briefly.** At 375×812 there was no horizontal overflow (`scrollWidth` 375). The retry row ("Retry 2 failed frames · Not loaded: #4, #9") fits on one 343 px line. The new controls reuse the existing button, link, notice and counter styles.
- **Not tested on Vercel.**
