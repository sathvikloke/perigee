# Production browser journey and contract checks (post-release QA)

**What was tested:**
- **Target:** `https://perigee-liard.vercel.app`, Vercel deployment `dpl_4gggyXwZGgMaUtSPRUSJx6iJUMjq`.
- **Code:** `main` @ `ef298900aa5769c47ec32f2bdb7c94ac27af14f3` (PR #27 merge). Codex's docs-only PR #37 (`c02adab`) leaves the app code unchanged, so it was not re-tested.
- **When (from the output files' timestamps), 2026-11-15, coordinator Claude session:**
  - journey: export at 00:29:14Z, log written at 00:30:59Z;
  - performance probe written at 00:32:48Z;
  - final contract-check run written at 00:34:29Z.

**Method:**
- Headless Google Chrome driven by `playwright-core@1.49.1`.
- Fresh, logged-out browser contexts with no stored evidence. No team browser profile was touched.
- Scripts in this folder:
  - `journey.mjs`: the full narrated journey;
  - `contract-checks.mjs`: focused contract behaviors.
- `node journey.mjs <origin> <out>` reproduces the run; it refuses `perigee.vercel.app`, which is an unrelated app. The same script was first run against a local production build to prove it.
- Evidence is in `2026-11-15-ef29890/`, a curated subset of the captures: `journey-log.json`, `contract-checks-log.json`, the exported card JSON, the print PDF and screenshots.

Codex ran an independent production browser pass with matching results (Epsilon A+B/A+C, flags, notebook autosave, real JSON download, Reopen; no console errors; no Vercel error logs). Codex's own records are in `qa/public-release/`.

## Journey matrix (production, `ef29890`)

| Area | Steps | Result | Evidence |
|---|---|---|---|
| First visit | `GET /` (logged out) | PASS: 200, title "Perigee", 5 preset cards, network idle in 0.97 s | `journey-log.json` `first_visit` |
| API health | `GET /api/v1/health` | PASS: 200 `application/json`, `status: ok`, `token_signing: env`, processor-A adapter | `health` |
| Keyboard | Tab from first load; keyboard **A + C** | PASS: visible 3 px solid focus ring; Enter on **A + C** selects it (`aria-pressed=true`) | `keyboard_first_tab`, `keyboard_AC` |
| A + B | `/?preset=epsilon_indi_b` | PASS: 29 Apr / 27 Sep 2026, 2.3232 / 2.3220 µm, "Different dates, nearly the same wavelength… 151 days" | `d02b-eps-AB-bench-1280.jpg` |
| Blink | **▷ Blink pair** | PASS: toggles to **Ⅱ Pause blink** | `blink` |
| A + C | **A + C** | PASS: 2.3232 vs 4.9399 µm; "Same moment, a different infrared color"; "Each frame has its own contrast stretch…" | `d03b-eps-AC-bench-1280.jpg` |
| Flags | **Show flagged pixels** | PASS: red problem-flag overlay; legend shows "Problem flag", "Saturated / non-finite" and the hatched no-data key | `d04-eps-AB-flags-bench-1280.jpg` |
| Flag-screen meaning | **What does "flag screen passed" mean?** | PASS: A and B side by side, 19/18 usable, 0 problem pixels, "not a detection and not a brightness measurement" | `flag_meaning` |
| Notebook | Fill claim, notice and uncertainty | PASS: 238/280, "Saved on this device" | `d06-notebook-filled-1280.jpg` |
| Claim guide | **Check your claim against the case guide** | PASS: supported and unsupported claims shown | `claim_guide` |
| JSON download | **↓ Export evidence card** | PASS: real download `perigee-evidence-fair_comparison-2026-11-15-….json`. It has `data_origin: api`, title, 5 case limitations, and per-frame limitations 4 and 5. Each frame carries processor 0.1.2, SHA-256 and its IRSA URL | `evidence-card-fair_comparison.json` |
| Print PDF | **Print / save PDF** + Chrome print engine | PASS: the button calls `window.print`. The PDF is 3 Letter pages and contains provenance for both frames, SHA-256, IRSA URLs and the stated limitations. The native print dialog was not driven | `evidence-card-fair_comparison-print.pdf` |
| Save, Reopen, reload | Home → My evidence → **Reopen** → reload | PASS: the card is titled "Epsilon Indi B · Is this a fair comparison?". All three notes are restored, focus lands on the `h1`, and the notes survive the reload | `d08-my-evidence-1280.jpg`, `reopen`, `reload` |
| Curated fallback | Both cases, export, print, Reopen | PASS: **0** `/api/v1/search` or `/api/v1/frame` requests, so curated cases do not depend on IRSA | `irsa_calls_during_case`, `irsa_calls_after_presets` |
| Barnard backup | `/?preset=barnards_star` | PASS: A + C (25 Aug 2025 / 19 Aug 2026), guide line, flagged near target | `d09b-barnard-AC-bench-1280.jpg` |
| Validation | RA `400`, Dec `12abc` | PASS: field messages shown and **0** search requests sent | `d12-validation-1280.jpg` |
| Live archive and partial | **Use Epsilon Indi A, J2000 catalog position** → **Search the archive** | PASS: 24 of 460 matches. The first pass gave 21 ready and 3 failed on real IRSA 502s, which stayed in their slots. **Retry 3 failed** then gave 24 ready, 0 failed | `d10-coordinate-search-1280.jpg`, `retry_failed` |
| Coordinate link | `/?view=query&ra=83.82&dec=-5.39&fov=6` | PASS: the form prefills 83.82 / −5.39 | `coordinate_link` |
| Error state | `/api/v1/search` forced to 502 (simulated) | PASS: "The archive search failed. This is not a result about the sky." | `d11-simulated-archive-failure-1280.jpg` |
| Narrow screens | Epsilon A+B, A+C and flags, notebook, Barnard and My evidence at 390×844 and 320×700 | PASS: `scrollWidth == innerWidth` on every view | `p01`, `p04`, `p05` |

Console errors in the journey run: 3 × `502`, the IRSA-refused frames above. No application errors.

## Focused contract checks (production)

`contract-checks.mjs` covers behaviors that the journey and earlier QA had only unit-tested.

| Contract behavior | Result |
|---|---|
| Expired frame token (`410 TOKEN_EXPIRED` forced on every `/frame`, simulated) | PASS: "This search has expired. Run it again to continue; your notes are kept." with a **Run the search again** button. The notebook text is kept. Removing the simulation and clicking the button sent 1 new search and gave 3 ready, 0 failed, with the notes still kept (`c01-expired-token-simulated.jpg`) |
| Stale response after a coordinate change | PASS: search A (330.84, −56.786) was held for 4 s while search B (83.822, −5.391) started. A's request was cancelled and only B's response arrived; the viewer shows "RA 83.822°, Dec -5.391°" and the URL follows B (`c02-stale-response.jpg`) |
| Shared URL never carries notes | PASS: `?view=query&ra=83.822&dec=-5.391&fov=6`, with no notebook text in the URL |

## Performance on the deployed path (task 19)

Raw data: `performance-2026-11-15-ef29890.json`, from logged-out requests to production on 2026-11-15.

| Path | Measured |
|---|---|
| `GET /` (edge `HIT`) | 181 ms, 509 B HTML |
| JS bundle `index-yzmhwLOW.js` | Brotli **transfer** 105,250 B (the probe had no Brotli decoder, so this is the compressed body). The same hashed file from the local build is 327,624 B uncompressed and 102,051 B gzipped. CSS: 7,476 B Brotli transfer |
| `GET /api/v1/health` | 78 ms |
| `GET /api/v1/presets`, `…/frames?case_id=fair_comparison` | 162 ms / 8 KB; 131 ms / 16 KB |
| `POST /api/v1/search`, limit 6 | 1.84 s, 1.60 s, 2.85 s |
| `POST /api/v1/frame` | n = 8 OK: 2.3–5.5 s, **median 3.67 s**, median 19.6 KB; 1 × `UPSTREAM_UNAVAILABLE` |

**The dominant cost is likely outside our processing.** Processor A's own work, measured locally, is 32 ms per frame across 183 cutouts (`coordination/processor-compare/bench_live_path_A.json`). Even Sagar's eager read on a 4.1 MB cutout takes 84–88 ms (PR #35). The hosted frame median is 3.67 s.

The IRSA fetch time was **not measured separately**: no server-side timing breakdown was collected. The likely dominant cost is the external cutout fetch (with the occasional 502 and bounded server retry) plus hosting and function overhead. That is an inference from the two measurements, not a measured split.

Responses are already small: a frame is about 20 KB, and curated cases make no archive calls.

**Recommendation: no code change.** One optional low-value tweak is left for the deployment owner because `vercel.json` belongs to the release owner: hashed `/assets/*` files are served `max-age=0, must-revalidate`, so returning visitors revalidate them. Cold versus warm start was not separated, because a cold start cannot be forced from outside.

## Observations (not defects)

- On first load and after client-side navigation, focus moves to the page `h1` (the QA-F3 design). The next Tab goes into the main content. The skip link and nav sit earlier in DOM order and are reached with Shift+Tab.
- IRSA intermittently refuses individual cutouts with 502. The app shows them as failed in place, with retry; in this run the retry recovered all of them.
- Locally (Vite preview only), the console showed a `/favicon.ico` 404. It was not seen on production. PR #38 (`f797b34`, after this run) adds the existing orbit SVG as the browser icon.

## Not covered

- a physical phone;
- a screen reader;
- the native print dialog;
- browsers other than Chrome;
- a separate cold-start measurement.
