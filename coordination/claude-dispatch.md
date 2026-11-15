# Claude dispatch log — Perigee parallel implementation

Coordinator + integration worktree: `.claude/worktrees/perigee-parallel-coord-4aa087`, now on branch `claude/perigee-integration` (from `origin/main` @ `fa92766`). The harness forbids this session from writing into other worktrees, so the coordinator's own worktree is the dedicated integration worktree.
Source of task pack: `prompts/parallel/` on `origin/main` @ `fa92766`.

Only rows marked **running** have an actually launched agent. "Queued" means not started.

## Launch mechanism

Native Claude Code subagents (`Agent` tool, `general-purpose`, `isolation: worktree`, background). Each has its own git worktree under `.claude/worktrees/agent-<id>`, created from `fa92766` (verified with `git worktree list` at 17:38Z). Each worker is instructed to `git checkout -b codex/parallel-NN-<task>` and push only that branch. `worktree-agent-<id>` is the harness default branch before the worker renames it.

## Shared seams set by the coordinator (in every brief)

- Backend package `backend/`; `backend/main.py` exposes `app`; route modules export `router = APIRouter()` with paths relative to `/api/v1`, mounted with `prefix="/api/v1"`. 03 owns main/models/requirements; 08 delivers `backend/routes/catalog.py` router only; integration wires it.
- Processor seam (05): pure `backend/data/process.py::process_frame(fits_bytes, FrameInput) -> ProcessedFrame` (FrameRecord-shaped dict + PNG bytes); network in `backend/data/archive.py`; ingest CLI in `tools/ingest/`; products in `backend/content/presets/<preset_id>/`.
- Frontend (01): `frontend/`, one API client `frontend/src/api/client.ts`, same-origin `/api/v1`, visibly labeled dev fixtures, neutral replaceable token layer until Codex's `design/HANDOFF.md`.
- 07 may push tiny files labeled "DEPLOYMENT PLACEHOLDER" to prove a preview; those never enter integration.
- Science: PR #8 (`origin/codex/sathvik-science`) used read-only via `git show`; 08 imports `backend/content/targets.json` + `cases/` in a separate attributed commit. Binding decisions: `science/INTEGRATION_BOARD.md` (frame_key, DATE-AVG/MJD-AVG, quality rules, null wavelength off-image, fixed grid). The original checkout (science session) is never touched.
- Gate-2 known-covered non-preset coordinate: Eps Ind A, RA 330.8400, Dec −56.7860.
- Raw data read-only at `NASA Space Comp/research/build_data/` (738 MB, 183 FITS); never committed.
- Frontend workers must read/apply `/Users/sathvikloke/.codex/skills/bloody-coconut-design/SKILL.md` (present, verified 17:38Z) + Impeccable. Codex owns `design/**`, PRODUCT.md and visual direction. `design/HANDOFF.md` not present as of 17:38Z.
- Local toolchain: python 3.9.6 only (workers install uv → Python 3.12), node 26, no Vercel CLI auth.

## Wave 1 — launched 2026-11-14 17:38Z

| ID | Task | Status | Worktree | Target branch | Output / blockers |
|---|---|---|---|---|---|
| 03 | API A: live coordinate and frame path | **done 17:57Z, integrated** | `.claude/worktrees/agent-aa1e6a902a4de7062` | `codex/parallel-03-api-a` @ `88e3772`, draft PR #12 | 121 API tests. Live /search Eps Ind A → 460 matches (DR1+QR3), bounded retry for IRSA 502s; real /frame via processor A. Wraps processor A natively (`_adapters.processor_a_adapter`). No rate limiting yet. |
| 05 | Processor A: one FITS → browser frame | **done 17:52Z, integrated (provisional base)** | `.claude/worktrees/agent-ac9eda3765a9fcaa0` | `codex/parallel-05-processor-a` @ `9c9049a`, draft PR #11 | All 6 case frames match case JSON (λ ≤1e-4, date, quality, sha256); 183 frames match science audit, 0 mismatches. 574 product files (~6 MB). 0.04 s/frame. Notes: moving_neighbor text "~2 px at 5″/px" vs ~7 display px on 256/6′ grid; gate-2 coord is J2000 (star moved ~2′). |
| 08 | Catalog, presets, assets | **done 17:49Z, integrated** | `.claude/worktrees/agent-aff3329b79a0deb37` | `codex/parallel-08-catalog-assets` @ `faaf6ba`, draft PR #10 | GET /presets (5 descriptors from targets.json), /cases/{id}, /presets/{id}/frames (mjd→frame_key, honest `status: missing`), /assets/{id} (opaque allowlist, traversal-safe, hash re-check). 58 pass/1 skip; 59 pass merged with 05 `47c812e` against the real Eps Ind B frame A (wavelength 2.32317 vs case 2.3232, mjd, quality clear, sha256 match). Contract additions to ratify: `?case_id=`, `sets`, `warnings`, `cases[].frames_available`, `image.asset_id`. Notes: 07 `.vercelignore` `data/` would drop `backend/data/`; 05 `observed_at_utc` has `Z` suffix, case JSON doesn't. |
| 07 | Vercel deployment preparation | **done 17:46Z** | `.claude/worktrees/agent-a9da251dd88b21712` | `codex/parallel-07-deployment` @ `8b57241`, draft PR #9 | Services config builds on preview (2 deployments, Vercel status success) but every path 302s to Vercel Authentication, so responses unverified on preview. Local `vercel build` confirms route order `/api`→api before SPA. Placeholders (`frontend/*`, `backend/main.py`, `backend/__init__.py`, `backend/requirements.txt`) must not be adopted. Needs Sathvik: view preview while logged in, decide judge access/protection, add `PERIGEE_TOKEN_SECRET` (Preview+Production). |
| 06 | Processor B (duplicate) | **done 18:08Z, not selected as base** | `.claude/worktrees/agent-af381359120abb365` | `codex/parallel-06-processor-b` @ `145c513`, draft PR #14 | 6 case frames match; identical geometry/masks/flags/markers/quality vs A. Differences: bilinear vs nearest intensity, median-subtracted stretch, no-Z timestamps, field names, SIP-aware native scale (B more correct, metadata only). PNGs 1.3–3× larger. |
| 24p | Port B pieces into A (task 24, processor) | **done 18:27Z, integrated** | `.claude/worktrees/agent-a7a1ac551d5c0ddfa` | `codex/parallel-24-processor-merge` @ `79552f1`, draft PR #21 | Processor A 0.1.1: SIP-aware native scale, 39 ported tests, `tools/ingest/audit_all.py` + `diff_products.py`. 574 products: 378 PNGs byte-identical; JSON changes only scale + processing_version. Acceptance 189/189, audit 183/183. |
| 14 | API reliability/security review | **done 18:25Z, integrated** | `.claude/worktrees/agent-abe2e7b3120baefe2` | `codex/parallel-14-api-review` @ `22c966c`, draft PR #20 | 6 defects fixed: R1 High `/frame` now retries IRSA fast 503s (4/16 live cutout GETs were 503; after fix 8/8 frames 200); R2 bounded validation details (17.5 MB error → 1 KB); R3 corrupt gzip → mapped not 500; R4 control chars in URLs; R5 4 MB response guard; R6 dev secret refused in production. R7 (catalog request_id) fixed by coordinator `454d027`. API B's body cap + rate limiter deliberately not ported. |
| 04 | API B (duplicate) | **done 18:12Z, not selected as base** | `.claude/worktrees/agent-a754c538d79c9a56f` | `codex/parallel-04-api-b` @ `15636c7`, draft PR #16 | 90 tests; live search 10/10 ready vs A 8/10 (worker attributes gap to archive variance, same retry policy); real /frame 200 via processor A. Same behaviour as A on all invalid-input/token/partial/timeout replays except: B caps body size (413), has per-instance rate limiter, 15 s vs 20 s read timeout. B's "A /frame → 503" applies to A `6e85130` only. B renames processor fields to `scale_arcsec_per_pixel`/`file_sha256`/`limits`, the opposite of the integrated alignment. |
| 15 | Science acceptance (review) | **done 18:05Z, integrated** | `.claude/worktrees/agent-a131bf088710ead19` | `codex/parallel-15-science-review` @ `14a154a`, draft PR #15 | Processor A: 0 FAIL over 189 records (byte-exact PNG reconstruction, Gaia DR3 median 0.45 display px, λ ≤3.3e-10 µm), 1 UNKNOWN (no Gaia star in fair C/D6). B's 6 case frames pass. No MWIR flip at L2. Escalations for Sathvik below. |
| 02 | Frontend B (duplicate) | **done 18:14Z, not selected** | `.claude/worktrees/agent-aac5358ff9243861c` | `codex/parallel-02-frontend-b` @ `e51027c`, draft PR #18 | Design A on real API; 13 vitest; 264 kB JS. First viewport closer to reference (plates visible at 1280; closed investigation picker). Live search 10/12 frames + retry. Screenshots `qa/frontend-b/`. |
| 01 | Frontend A: investigation flow + design A | **selected & integrated; follow-up `6632cef` integrated 18:22Z** | `.claude/worktrees/agent-a6fde9ea57d0b21dd` | `codex/parallel-01-frontend-a` @ `4d8ed91`, draft PR #17 | Design A applied; 38 vitest incl. contract tests from 03 examples; 306 kB JS. Gate 1 (card export `data_origin: api`) and gate 2 (live search 24/460, real frames) in UI; failure keeps old images + notes. Follow-up: move "Your steps"/background below bench so plates are in first viewport (from B). |
| 17 | Mobile & keyboard repair | **done 18:58Z, integrated** | `.claude/worktrees/agent-a1e1fc7523c40da54` | `codex/parallel-17-mobile-accessibility` @ `306af89`, draft PR #25 | Phone plate 735→653px at 390×844 (matches Codex mobile.jpg); 44px targets; 320px overflow fixed; long IDs wrap; stepper focus retained (aria-disabled); blink announcements 0–1; reduced motion pass; print pass; axe 0 violations (6 states). Open: no sky in first screen at 320px; compass contrast unmeasured. vitest 42. |
| 12p | Play-over-series + AI-use line + evidence export (task 12) | **done 19:15Z, integrated** | `.claude/worktrees/agent-a1941eac8ff04660d` | `codex/parallel-12-play-export` @ `abd2b29`, draft PR #30 | Play/Pause over full series (≈2 fps; reduced motion 1.5 s, starts paused; all stop rules pass). Footer AI-use line → `docs/AI_USE.md` on main (404 until merged). Real exported Barnard card: 57 field checks vs API, 0 mismatches; storage-refused path keeps notes + export works; URLs never carry notes. vitest 56. |
| 13 | Wavelength filter + quality states | **done 20:20Z, integrated** | `.claude/worktrees/agent-a5cce7cc450808be0` | `codex/parallel-13-quality-controls` @ `896da8b`, draft PR #33 | "Near X µm" filter (each frame's own band width) keeps exactly Barnard case A/B/C (3 of 34, ~2.01 µm, one-year loop); "Detector N only" coarser option (6 of 34, real λ range shown). Failed/not-loaded frames marked in slider/counter/picker. Clear/flagged/not_covered/unknown each distinct; unknown and not_covered say "not checked", never "none reported". vitest 86. |
| 18 | Loading/partial/recovery hardening | **done 19:52Z, integrated** | `.claude/worktrees/agent-abdd01fe02d7afaf5` | `codex/parallel-18-loading-recovery` @ `136a9c7`, draft PR #32 | Fixed G1 slow-search elapsed/cancel, G2 dead frame retry after failed/cancelled search, G3 retry-all + shared ≤2 limiter incl. retries (proxy-measured), G4 honest partial (names failed collection; no "0 observations"), G5 notes/URL across reload during outage. Fault proxy `qa/loading-recovery/fault_proxy.py`. vitest 71. IRSA load 3 searches/21 cutouts. |
| 10 | Barnard case review | **done; review and case-text revision integrated** | `.claude/worktrees/agent-a4ae98b4b4989f773` | `codex/parallel-10-barnard-case` @ `b4fcc8c`, draft PR #22 | Imagery supports demo (PASS with display conditions). Marker A→B 4.19 px, A→C 7.29 px (10.25″) north; 6 Gaia field stars stable ≤0.77 px; glow shift ~7 px by eye (±1 px). No better trio (longest baseline +4%; D5 trio breaks shared stretch). Review `eaa59fe` merged; case-text revision `b4fcc8c` accepted by Sathvik, merged `2a4273a`. |
| 23 | Regression suite | **done 19:02Z, integrated** | `.claude/worktrees/agent-a587eb2bc6118cd0e` | `codex/parallel-23-regression` @ `d6705e2`, draft PR #26 | No regressions on `efaa874`: seam, `.vercelignore`, case set, R1–R7, science display, audit defects, N1–N5 (failed frame order, stale response, expired token keeps notes, JSON 404 via proxies, export fields). `qa/regression/run.sh` + `live_check.py`. |
| 09 | Epsilon Indi B case review | **done; review and case-text revision integrated** | `.claude/worktrees/agent-a210a316699a1c312` | `codex/parallel-09-epsilon-case` @ `b5aff70`, draft PR #31 | Frames confirmed from raw FITS; acceptance re-run on 0.1.1 passes. Eps Ind A is 6.71′ away, outside the frames. A vs B look the same (field stars ≤0.39 px; marker 1.38 px sub-native-pixel → motion not claimable); shared stretch clips Eps Ind B to white → no brightness claim. Visible A-only dot is a flagged pixel (good teaching step). In C, Eps Ind B stays bright while most stars fade (qualitative). Proposed ending replaces "can't tell"; revision `b5aff70` accepted by Sathvik, merged `98fae22`. |
| 20 | Pitch + demo script draft | **done 18:36Z, integrated** | `.claude/worktrees/agent-ad68f2e9948f5b802` | `codex/parallel-20-pitch` @ `c27b96a`, draft PR #23 | `docs/presentation/README.md`: 7 slides, 5-min narration (demo 1:05–3:20, IRSA-slow fallback), working-vs-future table, screenshot requests S1–S9, sources. Open decisions for Sathvik listed there. |
| 21 | Independent judging critique | **done 18:50Z, integrated** | `.claude/worktrees/agent-aee4454798765b5f7` | `codex/parallel-21-judge-review` @ `ef0f68d`, draft PR #24 | Official rubric (Impact/Creativity/Validity/Relevance/Presentation, 1–5); est. 3/3/4/3/3. Findings: (1) no judge can open it — production is login-protected and `main` has no app; `perigee.vercel.app` is an unrelated third-party app, never submit it; (2) demo undersells challenge's motion-across-series ask — lead with Barnard A↔C, accept PR #22, optional Play over full series; (3) README stale + required AI-use disclosure text missing. |
| 22a | README + AI-use disclosure draft | **done 19:08Z, integrated** | `.claude/worktrees/agent-a30927e0088abbbaf` | `codex/parallel-22-readme-disclosure` @ `cafcd73`, draft PR #28 | Stale README replaced; `docs/AI_USE.md` with [TO CONFIRM] items for Sagar/Sathvik. Guide requires SI use indicated in descriptive text and metadata, visible watermark on SI images/video, and a link needing no password/permission. **Repo `sathvikloke/perigee` is PRIVATE** → judges can't open it. Coordinator corrected test counts (`c3f90eb`). |
| 24c | Compare Sagar's processor (PR #19) vs A | **done 18:44Z, integrated** | `.claude/worktrees/agent-abe7771e1bbba2e83` | `codex/parallel-24-processor-compare` @ `abec9c7` | Science tie (both 189/189; Sagar Gaia median 0.35 px vs A 0.45 px; Sathvik audit 0 diffs both). Sagar's products incompatible with tested catalog/frontend: case sets `missing`, 0/366 image srcs (asset IDs lack `.png`), no `flag_image.legend`, 4′ vs 6′ FOV, `frm_<hash>` frame_id, `l2b_retry` URL rejected. **Decision (c): keep A**, adopted `fetch_manifest.py` (`0b6bc6a`), registration check being ported (24r). |
| 24r | Port Sagar's field-registration check | **done 19:12Z, integrated** | `.claude/worktrees/agent-a64394056412a5c86` | `codex/parallel-24-registration-check` @ `8c3e672`, draft PR #29 | Reproduces Sagar's 0.92/0.35/0.44″ on his grid. On A's grid same-band field shifts 0.36–1.19″ (≪ 3.1″ half native px); ±0.5″ method systematics. fair A→B field shift 1.19″ vs marker 1.94″ → no motion claim on that pair (sent to 09). Cross-band pairs not measurable. 10 tests. |
| 24f | Trial-integrate Sagar's PR #19 on current integration (task 24 follow-up) | **done; decision: keep A, port quality rule** | `.claude/worktrees/agent-aee46a8a928cf273f` | `claude/24f-sagar-trial` @ `0225833` (trial only, not for merge) | 35-line catalog adapter + 1 regex fix make #19 serve the whole UI; all 9 browser checks pass; 0 status changes on 183+6 frames. Remaining gap to A ≈1–1.5 engineer-days + science re-review (4′ grid, case display-px text, A-layout tests/tools, flag legend, hatching meaning, frame_id). |

## Queue (by prerequisite; not running)

| ID | Task | Prerequisite | Planned slot |
|---|---|---|---|
| 24 | Compare duplicates + assemble | first competing results | coordinator, on this branch |
| 11 | Target audit | none | low priority |
| 16, 19, 21, 22, 23 | E2E, perf, judge, submission, regression | running deployed app | later |

## Integration log

- 17:38Z `claude/perigee-integration` created at `fa92766`. Nothing merged yet.
- 17:45Z observed pushes: 05 @ `47c812e` (pure processor + first real FrameRecord for Eps Ind B frame A, `backend/content/presets/epsilon_indi_b/frames/`); 08 @ `c85fd7d` (science content imported read-only, catalog routes, loader tested on real case metadata). 03 and 01 not yet pushed.
- 17:46Z 07 handed off; 06 launched into its slot (prerequisite met by 05 `47c812e`).
- Integration of 07 config deferred until 03 backend + 01 frontend exist, so the integration preview builds a real app rather than an empty Services config. Adopt: `vercel.json`, `.vercelignore`, `backend/.python-version`, `backend/platform/{runtime,deploy_check}.py`, `.github/workflows/deploy-check.yml`, `.gitignore` `.vercel/`, `docs/DEPLOYMENT.md` Services section. Import rule from 07: backend must run from repo root as `backend.main:app` (`backend/platform` shadows stdlib `platform` if cwd is `backend/`).
- 17:50Z 08 handed off; 04 launched into its slot. Merged `origin/codex/parallel-08-catalog-assets` (`faaf6ba`) into `claude/perigee-integration` (`9d0cf3f`); `pytest backend/tests/platform` → 58 passed, 1 skipped (skip needs bundled presets).
- 17:52Z merged 05 (`9c9049a`). 17:53Z launched 15.
- 17:54Z merged 03 snapshot + wired catalog router; found seam mismatch (API expected dict processor; `registration.scale_arcsec_per_pixel` vs processor `scale_arcsec_per_px`). Temporary bridge; then 03 final (`88e3772`) wrapped processor A natively with matching field names, so the bridge was removed (`8bcaf49`).
- Live check on integration (local uvicorn): `POST /search` 330.84,−56.786 limit 4 → `ready`, 460 matches, collections DR1+QR3; 4 × `POST /frame` → HTTP 200, 2.5–7.4 s, ~19 KB each, real IRSA cutouts (e.g. `2026W17_2A_0355_1_D2`, 1.294 µm, clear, per_frame). First attempts got IRSA 503 → `UPSTREAM_UNAVAILABLE` 502 (correct mapping). Gate 2 met locally, not yet deployed.
- 17:56Z adopted 07 config (`99d5f21`), `.vercelignore` anchored `/data/` `/tools/` so `backend/data/` ships. `deploy_check --app` ok; frontend build ok, vitest 34 passed; backend pytest 217 passed / 9 skipped.
- 17:58Z pushed integration; Vercel preview for `8bcaf49`: status success ("Deployment has completed"), deployment `J8MMvCvx1tXewEmNecAkSHEmRP5h`. Responses unverified (Vercel Authentication on previews).
- 17:59Z gate 1 locally (vite → uvicorn, real data): five presets render with real frame counts; Eps Ind B case viewer loads real asset `epsilon_indi_b--frames-2026W18_1A_0516_1_D3` (256 px); "Add this frame to evidence" saves card in `localStorage['perigee.evidence.v1']` with `data_origin: api`, frame_key, detector, DATE-AVG, λ 2.32317 µm, IRSA source URL. JSON export button present (download not triggered by coordinator). Gap: case plates use per_frame stretch set; told 01 to use `?case_id=`.
- 18:00Z Codex UI handoff received (`perigee-ui-direction/design/HANDOFF.md`, prototype served at :4175). 01 reassigned to port design A; 02 launched as competing design-A implementation.
- 18:05Z 15 handed off; merged review (`8234d6a`). Display escalations forwarded to 01 and 02: transparent saturated cores need a non-sky well background + flag overlay; not_covered copy "just outside this image"; parse times (Z suffix); label 330.84,−56.786 as J2000; read overlay colours from records; case plates via `?case_id=`.
- 18:06Z launched 14 against the integrated API.
- 18:08Z 06 handed off. **Processor decision: A is the base** (already integrated; compact nearest-neighbour PNGs, archive adapter, Z timestamps; science acceptance passed). Selective port of B launched (24p). Deferred product choices (not ported): bilinear intensity, median background subtraction, B field names/colours/timestamps.

## Escalations for Sathvik (science owner) — not changed by any agent
1. `moving_neighbor` text says marker moves "about 2 display pixels at 5 arcsec/pixel"; on the shipped 256 px / 6′ grid (1.406″/px) it moves 4.19 px A→B and 7.29 px (10.25″) A→C, glow visibly shifts 3.2/6.6 px. Suggested: "about 7 display pixels (about 10″, under two SPHEREx pixels)".
2. Gate-2 coordinate 330.84, −56.786 is Eps Ind A J2000; at 2026.0 the star is 122.7″ away (330.8925, −56.8043). Label as J2000 or use 2026 position.
3. `CASE_SELECTION.md` says 10–11 non-finite pixels within 2 px of Barnard marker; raw native arrays have 3/3/2 (status still flagged).
4. Flag policy: decision 3 treats OUTLIER/PHANMISS as adverse, while the supplement's CONTAINS_BAD_PIXEL rule excludes them. Both processors follow decision 3; per-flag counts are recorded if you revisit.
5. Case JSON timestamps lack "Z"; processor A writes Z (safer for JavaScript). Consider adding Z to case JSON.
- 18:13Z 04 handed off. **API decision: A is the base.** Re-verified on integration (`8bcaf49`+): health reports `backend.data.process.process_frame (processor-a adapter)`; live `/search` 330.84,−56.786 → ready/460; `/frame` 200 for `2025W19_1B_0344_4_D6` (4.48 µm, flagged, 4.3 s, 21.9 KB) and `2026W39_2A_0155_2_D6` (4.95 µm, clear, 4.5 s, 15.8 KB). B's body cap and rate limiter forwarded to 14 as candidate fixes.
- 18:14Z launched 10. 18:14Z 02 and 18:15Z 01 handed off. **Frontend decision: A is the base** (already integrated scaffold, chronological stepper over all frames, 38 tests incl. contract tests from real API examples, Gate 1+2 shown in UI). B's first-viewport ordering requested from 01 as a focused follow-up; B's code/state model not merged. Merged 01 `4d8ed91` (`6e855a2`): build ok, vitest 38 passed, backend 217 passed / 9 skipped.
- 18:17Z noticed PR #19 `codex/sagar-data` (Sagar, human data owner): third processor candidate with `process_frame_for_api` hook for API A, own presets layout + manifest. Not merged. Launched 24c to compare it against A with the independent acceptance checker and the integrated API/catalog/frontend tests before any switch. Sagar remains review contact.
- 18:22Z merged 01 follow-up `6632cef` (`41d8b42`): plates start in first viewport at 1280×800 (image tops at 654px); closed "Change investigation, target or coordinates" switcher. Build ok, vitest 38 passed. Phone plate still starts ~735px at 390×844.
- 18:23Z launched 17. Frontend follow-ups now run one writer at a time to avoid conflicts in `frontend/**`.
- 18:25Z merged 14 (`6508b55`), 229 passed; coordinator fixed R7 (`454d027`), 231 passed.
- 18:28Z merged 24p (`79552f1`): backend 263 passed / 16 skipped without raw data, 279 passed with `PERIGEE_DATA_ROOT`.

## Decisions needed (API owner Aditya / Sathvik)
- D1 IRSA OVERFLOW: `/search` returns `ready` + `truncated: true`; contract wording may call this `partial`.
- D2 Rate limiting: `RATE_LIMITED` never emitted; recommended Vercel Firewall rate limit on `/api/v1/frame` rather than per-instance code.
- D3 `PERIGEE_DEV_MODE=1` enables dev secret on Preview; safe only while Preview never sets it and stays behind Vercel Authentication.
- Limitation sentence in each record still says "~6.16 arcsec native pixels" while `native_scale_arcsec_per_px` is now SIP-aware (e.g. 6.1318); one-line change + regeneration if consistency is wanted.
- 18:30Z launched 23 and 20. 18:32Z merged Barnard review `eaa59fe` only; the case-text revision (PR #22, `b4fcc8c`) is Sathvik's call: corrected marker wording (≈4 px A→B, ≈7 px/10″ A→C), reworded opening question, reference line required, saturated-core display requirement, `must_recheck_against_processor_output` → false.
- 18:37Z merged 20 (`46debe0`); launched 21. Frontend follow-ups 12/13/18 wait for 17 (one frontend writer). 16/19 blocked on a publicly reachable deployment (Vercel Authentication); 22 after release candidate.
- 18:45Z merged 24c (`2494b04`); adopted Sagar's `tools/ingest/fetch_manifest.py` unchanged (`0b6bc6a`); A has no `l2b` URL filter (0 errors on 183 retained). 18:46Z launched 24r. Sagar's PR #19 left open and uncommented; coordinator does not post on teammates' PRs without Sathvik's go-ahead.
- 18:51Z merged 21 (`5b4c9c7`); launched 22a. Frontend queue after 17: Play-over-series in stepper (judging finding 2), in-app AI-use line, then 12/13/18.
- **Path to judge access (needs Sathvik):** after 23 regression is green → open integration PR `claude/perigee-integration` → `main` (coordinator may open, not merge) → Sathvik merges, disables Vercel Authentication for production only, sets `PERIGEE_TOKEN_SECRET`, leaves `PERIGEE_DEV_MODE` unset → logged-out check of `/`, `/api/v1/health`, one preset, one live search.
- 18:58Z merged 17 (`b9717d6`): build ok, vitest 42 passed. 18:59Z launched 12p. Note: 23 regression was started on `efaa874`; later merges (21, 24c, 17) will need a re-run before the main PR.
- 19:03Z merged 23; re-ran `PERIGEE_DATA_ROOT=… qa/regression/run.sh` on `cd4ef49`: backend pytest, deploy_check, vitest (42), build, audit_all 183, check_acceptance 189 — all PASS.
- 19:04Z opened **draft integration PR #27** `claude/perigee-integration` → `main` (not merged; Sathvik merges and owns Vercel settings). Bound to coordinator session.
- 19:05Z launched 09.
- 19:09Z merged 22a; README counts corrected to verified `cd4ef49` run (265/17, 282 with data, vitest 42). 19:12Z merged 24r (`5b518a6`): backend 274 passed / 17 skipped.

## Needs Sathvik / Sagar before submission (consolidated)
1. Make GitHub repo `sathvikloke/perigee` public (currently PRIVATE) — judges need no-permission access.
2. In this order (see `docs/DEPLOYMENT.md` → Owner actions): set `PERIGEE_TOKEN_SECRET` (≥32 bytes, never the dev value; keep `PERIGEE_DEV_MODE` unset) **before** merging, or redeploy afterwards; optionally set `PERIGEE_PUBLIC_URL=https://perigee-liard.vercel.app`; disable Vercel Authentication for production only; then merge PR #27 → main; then do the logged-out check on `https://perigee-liard.vercel.app` (step 7). Never submit `perigee.vercel.app` (unrelated third party).
3. Fill `[TO CONFIRM]` items in `docs/AI_USE.md` (idea is team's own; mockup tool; planning-doc tooling; Sagar's PR #19 AI use; human review record). Watermark `.impeccable/mocks` images if used in slides.
4. ~~Case revisions #22/#31~~ accepted and merged (`2a4273a`, `98fae22`).
5. ~~API decisions D1–D3~~ settled as implementation choices (`03bb179`); optional Vercel Firewall rate-limit rule remains an owner choice (D2).
6. Pitch decisions in `docs/presentation/README.md`.
- 19:16Z merged 12p; `qa/regression/run.sh` on `fcfa047`: all six offline gates PASS (backend 274/17, 291 with data; vitest 56; audit 183; acceptance 189). README counts updated (`5518359`). 19:17Z launched 18.
- 19:23Z merged 09 review `a4d2de9` only. Proposed `fair_comparison.json` revision (`b5aff70`, PR #31) awaits Sathvik. Note: current shipped `example_claim` is 382 chars vs 280-char notebook limit (proposal 238). Pitch narration 1:05–2:25 should follow the new ending if accepted.
- 19:53Z merged 18; `qa/regression/run.sh` on `4f57270`: all six offline gates PASS; vitest 71. README updated.
- 19:55Z launched 13 (only frontend writer).
- 20:21Z merged 13; `qa/regression/run.sh` on `5827a65`: all six offline gates PASS; vitest 86. README updated.

## Queue status at 20:21Z
All dependency-ready implementation, review and QA tasks have run. Remaining tasks are blocked on owner actions, not on code:
- 16 deployed E2E, 19 performance on deployed path, 22 final submission check: need a publicly reachable deployment (repo public, PR #27 merged, Vercel Authentication off for production, `PERIGEE_TOKEN_SECRET` set).
- 11 five-target audit: optional; targets already verified by the science session and re-checked by 15/09/10.
- Content: case revisions PR #22 and PR #31 accepted by Sathvik and merged (see below).

## Case-text revisions merged
- Sathvik answered "Merge both". Merged #22 Barnard `moving_neighbor` (`b4fcc8c` → `2a4273a`) and #31 Epsilon Indi B `fair_comparison` (`b5aff70` → `98fae22`). The Epsilon example claim is now 238 chars, under the 280-char notebook limit.
- `qa/regression/run.sh` on `98fae22`: all six offline gates pass (backend 291 passed with raw data, deploy_check, vitest 86, build, audit_all 183, check_acceptance 189).
- `docs/presentation/README.md` updated: Barnard is no longer slide-only, S7 can be taken, demo narration 2:25–2:50 uses the accepted example claim.

## PR #19 re-assessment against current integration (24f) — decision
Inputs: Sagar's PR #19 @ `cb1f36b` (unchanged since 24c); Codex ran its `backend/tests/data` in isolation (74 passed); worker 24f trial-integrated it on `bc03f40` (`claude/24f-sagar-trial` @ `0225833`, screenshots `qa/sagar-trial/` on that branch).

**Measured (24f):** with a 35-line catalog adapter (extensionless asset IDs, root manifest map with sha/size check, `sets/<case>.json` → `case-<case>`) and a 2-line `l2b_retry` regex fix, #19 serves the current frontend: 5 presets, 378/378 assets, both cases with shared stretch, wavelength filter keeps Barnard A/B/C, export with `data_origin: api`, print, live search 460 matches → 24/24 frames after retrying 3 IRSA 502s. Science: 183/183 audit 0 diffs; 189/189 acceptance on substance; **0 quality-status changes vs A** on 183 + 6 frames. Gates on the trial branch: backend 275/1 fail, vitest 85/86, audit_all and check_acceptance fail on A's layout/imports (substitutes pass), live 5/6 — all failures are A-specific names/layout, not science.

**Decision: keep processor A; port, don't replace.** Reasons:
1. Science is a tie (as in 24c); switching gains no validity.
2. Switching moves curated frames to a 4′ / 0.9375″ px grid while live search stays 6′ / 1.406″ px. The just-accepted case rewrites (#22, #31) state display-pixel motions on the 6′ grid (Barnard ~4 / ~7 px; Epsilon ~1.4 px). 24f lists 8 `moving_neighbor` and 4 `fair_comparison` strings that would have to change, two needing a science-owner re-look, and reviews 09/10 validated the visual claims on A's rendering.
3. Further work: flag legend absent (frontend shows the fallback), adverse flags drawn as hatching while the UI says hatching means no data, `frame_id` changes (saved cards mismatch), card `query.fov_arcmin` 6 vs 4′ frames, and ~10 A-layout tests/tools to port. Estimate 1–1.5 engineer-days plus science re-review, with no science gain.
4. Bilinear smoothing and the noise-based stretch look better, but they are display choices. Per instruction there is no wholesale switch for aesthetics. Not ported now: changing A's rendering would invalidate the 09/10 visual reviews and the case text this late. If adopted later, it must be labelled as display interpolation next to the plate and re-reviewed. #19's record says only "bilinear resample of intensity"; the word "interpolation" appears only in a code comment.

**Ported into A (`e7c263d`, processor A 0.1.2):** Sagar's stricter unknown screen, with flagged precedence kept. Any adverse or non-finite pixel → `flagged`. Otherwise `unknown` when the file has no VARIANCE extension (missing or wrong shape), or fewer than 10 usable pixels remain. A VARIANCE extension that exists but is non-finite or ≤0 in the circle marks those pixels invalid, so the screen is `flagged` (clarified in the PR #35 review; Sagar's optional change to `unknown` was not adopted); the note calls 10 "our screening heuristic, not a NASA or SPHEREx standard". Flag bits the header doesn't name now count as adverse (as in #19). Checked on the 183 raw files: all have VARIANCE, none use unnamed bits, clear frames have 18–21 usable pixels, so **no status changes**. Rebuilt 574 products: PNGs byte-identical, JSON differs only in `processing_version` (`diff_products` ok). 5 new tests. Gate: backend 296 passed, vitest 86, build, audit_all 183, check_acceptance 189 all pass.

**Already adopted earlier:** `fetch_manifest.py` (`0b6bc6a`), registration check port (24r). A's live path has no `l2b` URL filter, so the `l2b_retry` defect in #19 does not affect us.

PR #19 stays open and uncommented (teammate PR; the coordinator doesn't post there without Sathvik). Sagar remains processor reviewer.

## Fresh-user QA (Neeraj, issue #6, `codex/neeraj-qa` @ `31d98f7`, tested `cc2c3ca`) — triage against current integration
| # | Finding | Status on current integration | Outcome |
|---|---|---|---|
| B1 | No public app (Vercel Authentication on every URL) | Still true. Codex's authenticated check of deployment `dpl_Fo2Vz63JvLSM8HpSHRZeu9DYHDZx` (`bc03f40`): `/` 200 HTML, `/api/v1/health` 200 JSON `degraded` (`token_signing: missing`), `/api/v1/cases/fair_comparison` 200 | Owner action (see `docs/DEPLOYMENT.md` → Owner actions). Hosted routing and startup verified; live search/frames are blocked only by the missing secret |
| B2 | Private repo; footer `AI_USE.md` link 404 | Still true (logged-out 404 for both) | Owner action: make public or mirror; merge PR #27 |
| F1 | Exported card has no limitations | Confirmed, then **fixed**: QA-F1 `77fa179`/`dff3e34` | Export carries `case_limitations` (5, verbatim) and `frames[].limitations`, plus `title`; schema stays v1; old cards are normalized and filled in on reopen without touching learner text. Real files in `qa/export-limitations/`. Codex separately verified an actual saved download (titles, 5 case limitations verbatim, 4/5 per-frame, URLs and SHA-256) |
| F2 | SIMBAD links 404 | Confirmed: the CDS Strasbourg security incident (notice updated 9 Nov 2026) makes every `/simbad/*` path 404, even Vega. Not malformed: the same paths resolve on the official CfA mirror | **Fixed `1b87fe6`**: case sources point to `simbad.cfa.harvard.edu` with SIMBAD (CDS) attribution kept. Checked with curl; the built-in browser blocks the SIMBAD domain under site permissions |
| F3 | My evidence shows raw id; no reopen | Confirmed; **fixed** QA-F3 (`4505b66`, `0cf390d`) | Human titles (target · case, coordinate fallback, stored `title`), Reopen link restoring the right investigation and notebook |
| F4 | Shared vs own stretch confusing | Confirmed (labels differ by design); **fixed** `4505b66` | One sentence in the pair's processing note: "The pair shares one stretch so the plates can be compared by eye; the timeline below gives each frame its own." |

## API review leftovers (resolved 2026-11-14, `03bb179`)
R7 had been fixed in `454d027` (ContextVar request id), with a regression test. D1: an archive OVERFLOW is now `partial` + `collections_capped`, `truncated: true`, `total_matches: null`; a limit subset stays `ready`; mixed case tested. D2: no fake global limiter; bounds documented; a Vercel Firewall rule is an owner option. D3: dev secret and dev fallback refused on hosted Preview as well as Production; local dev unchanged. Details: `backend/tests/api/REVIEW.md`.

## Content metadata and docs (`6f08d56`)
Both cases: `status: science_owner_approved` plus a dated `verification.approval`; science text unchanged. `docs/DEPLOYMENT.md` rewritten (current setup, hosted Preview evidence, logged-out results, numbered owner actions with target URLs). `docs/AI_USE.md` and README: stale "Barnard fix unmerged / 2-px text shipped" and "D1–D3 owner decisions" corrected; no human attestations added; `[TO CONFIRM]` items left for the team.

## Final integration batch (QA-F1, QA-F3) — `a416c9e`
| Task | Worker worktree | Branch @ commit | Result |
|---|---|---|---|
| QA-F1 export limitations | `.claude/worktrees/agent-a8fd59d7be8486894` | `claude/qa-f1-export-limitations` @ `dff3e34` (fast-forwarded) | `case_limitations`, `frames[].limitations`, `title`; schema v1 kept; old cards normalized; print lists stated limitations. 12 tests. Real exports in `qa/export-limitations/`; Codex verified an actual saved download |
| QA-F3 My evidence + F4 | `.claude/worktrees/agent-aedbfcbfa039f7e04` | `claude/qa-f3-my-evidence` @ `a416c9e` (fast-forwarded) | Titles + Reopen (`4505b66`, `0cf390d`); 320 px timeline overflow and heading focus on client navigation fixed with layout and a MutationObserver, no timeouts (`2dacdd5`); false "not saved" after leaving before the debounce fixed by re-reading the list after unmount cleanups, refused writes still warn (`cf47026`). Evidence `qa/my-evidence/`. Codex independently confirmed 320 px, focus, Reopen and reload |

**Final verification on `a416c9e` (coordinator):**
- `qa/regression/run.sh`: all six offline gates pass (backend 299 with raw data; vitest 121 in 12 files; build; audit_all 183; check_acceptance 189).
- `--live` against local uvicorn: 6/6. Search 330.84, −56.786 → ready, 460 matches. A real `/frame` returns 200 with processor 0.1.2. JSON 404s echo `X-Request-ID`, including the catalog 404 (R7).
- Browser at 320 px: Barnard case `scrollWidth == innerWidth`, 6 plates and flagged labels from the records. Epsilon case: 3 "Flag screen passed", the F4 sentence present, focus on the `h1`.
- Non-preset live search, Orion 83.82, −5.39: 377 matches, still 320 px wide. With limit 4, one simulated 502 plus one **real** IRSA 502 (`UPSTREAM_UNAVAILABLE` after the server's retries): both stayed in date order, marked "failed to load", with "Retry 2 failed frames". The retry recovered the simulated frame; the real one failed again and stayed in its slot, with the other frames unaffected.

Not re-run (already recorded, no code change since): the export download (QA-F1, Codex), print preview (24f, 17, QA-F1), keyboard journey (17, QA-F3, Codex). Not covered by anyone: a physical phone, a screen reader, a printed PDF, a public URL.

PR #34 was handled in the next round (see below).

## PR #34 (Suhrit, `codex/suhrit-platform` @ `4101680`) — reviewed and integrated
- **Merged with authorship preserved:** a `--no-ff` merge `d859e62` keeps Suhrit's commit `4101680` intact. The review fixes are separate coordinator commits.
- **Review findings fixed in `backend/platform/smoke.py`:**
  1. An empty search, or observations without a frame token, gave a false PASS with no frame checked. Now it is a FAIL, plus a "live /frame not attempted" FAIL. Search and frame payloads are validated, and the frame's data-URL PNG and the preset asset must decode with Pillow.
  2. Invalid or non-object JSON and network errors or timeouts crashed the run. They are now FAIL rows with exit 1, and an unreachable host gets a clear message.
  3. The bypass header was set client-wide. It is now attached per request, only to the `--base` origin; absolute off-origin asset srcs are not fetched.
  4. `--base` is now validated: an https origin (http only for loopback), with no path, query or credentials. `perigee.vercel.app` is refused in case, trailing-dot and port variants, and `myperigee.vercel.app` is no longer wrongly refused.
- **Tests:** 31 offline tests in `test_platform_smoke.py` (Suhrit's 4 kept and adapted). Suhrit's UTF-8 `conftest.py` fix was kept.
- **Runs:**
  - local frontend+API origin: PASS 20/20, including a live Orion search (377 matches) and a frame whose PNG decodes;
  - logged-out Preview: exit 2;
  - unreachable host: exit 1;
  - `https://PERIGEE.vercel.app.` and `https://perigee.vercel.app:443`: refused;
  - API down behind the frontend: exit 1 with no traceback.
- **Docs:** `docs/DEPLOYMENT.md` reconciled. Suhrit's `ebdc0a0` status ("deployed responses not verified") is kept as a superseded earlier report, and the current hosted-Preview evidence (Codex's authenticated check of `bc03f40`) is kept as current. His release notes (redeploy after env changes, team access or `--bypass`, recording the production domain, the Hobby-plan preview risk) were kept, and the smoke command was added to owner step 6.
- **Gate:** all six offline gates pass; backend 330 with raw data (313 passed / 17 skipped without), vitest 121.
- **Disposition:** PR #34 is fully contained in `claude/perigee-integration`, so GitHub marks it merged on push. No comment was posted on the teammate PR.

## PR #35 (Sagar) and PR #36 (Suhrit) — reviewed and integrated (2026-11-14)
Both were merged with `--no-ff`, keeping the original commits and authors. Review fixes are separate coordinator commits.

**PR #35** (`codex/sagar-truncated-fits` @ `8063620`; commits `7e89ae2`, `8063620` by Sagar Raut) → merge `d6272c8`, review fix `eaa92f5`.
- **Truncated FITS → UNSUPPORTED_DATA: adopted.** Verified at the API: a synthetic cutout cut inside its IMAGE data unit, run through the real processor seam, gives **422 `UNSUPPORTED_DATA`** (`error_type: UnsupportedDataError`). The same test on the pre-#35 processor (`8f577fa`) gives 500. The intact file gives 200. The real Eps Ind B cutout cut at 1/3 gives 422 when raw data is present.
- **Wavelength tolerance 1e-9 µm: adopted and hardened.** `_wl_differs` used `abs(a-b) > tol`, so NaN compared equal. Replaced by module-level `wavelength_differs()`: both null are equal, one null differs, and NaN, ±inf, strings and booleans always differ. Tests cover 3e-15 relative noise (passes), 1e-6 µm (fails), a null mismatch (fails) and NaN/inf/invalid values (never accepted).
- **Good products unchanged:** `audit_all` reports 0 stale of 183, 6/6 case frames, and no product rebuild was needed.
- **VARIANCE policy: kept as is.** A missing or wrong-shape VARIANCE extension gives `unknown`; an existing one with no finite positive values gives `flagged`. Sagar's optional change to `unknown` was not adopted. Clarified in a code comment, in the edge-case note text and in this log; pinned by `test_existing_but_unusable_variance_is_flagged_not_unknown`.

**PR #36** (`codex/suhrit-release-checks` @ `bef9f90`, Suhrit Bestavemula) → merge `16776bd`, review fix `2956e67`, docs in the following commit.
- **Pillow:** the workflow installed only httpx, but `png_problem` imports PIL. Added `backend/platform/requirements-smoke.txt` (httpx==0.28.1, pillow==13.0.0, matching `backend/requirements.txt`, enforced by a test); the workflow installs it. In a clean venv with only those pins, a local production-mode stack gives PASS 20/20, with both PNG checks decoding.
- **Triggers corrected:** `deployment_status` has no default-branch requirement (it runs at the deployed SHA/ref, per GitHub docs). This repo has **no GitHub Deployments** (`GET /deployments` returns `[]`; Vercel posts commit statuses only), so the automatic path has never fired and is documented as unverified. `workflow_dispatch` needs the file on `main`. The manual CLI path works now.
- **Hardening:** the harness is checked out from the default branch with `persist-credentials: false`. Payload and input values reach shell steps only through env. The summary names the origin tested, the harness commit and the event-reported deployment, and says that the origin serving that commit is not verified.
- **Action pins:** checkout, setup-python and setup-node are pinned to the SHAs of v4.2.2, v5.6.0 and v4.4.0 in both workflows. `actionlint` 1.7.7 is clean, and a test enforces full-SHA pins.
- **Docs:** Suhrit's production-mode rehearsal is kept and labelled **local evidence only**. His `test_regression_vercelignore` Windows fix and his Hobby/Pro note were kept.

**Handoff correction (from the user's verified facts and the coordinator's re-check):**
- The registered production domain is **`https://perigee-liard.vercel.app`** (Vercel API: the only verified production domain).
- Unauthenticated, that domain returns **404** at `/` and `/api/v1/health`, with no redirect. A smoke run against it gives exit 1. It is not serving the app.
- The earlier 302 observations are scoped to the branch preview alias and the team alias `perigee-sathviklokes-projects.vercel.app`, which is not the production domain.
- The project has no environment variables and the repository has no variables. The repo is PRIVATE, with default branch `main`.
- `PERIGEE_PUBLIC_URL=https://perigee-liard.vercel.app` is documented as intended and **not set**.

**Gate on `2956e67`:** all six offline gates pass; backend 348 with raw data (330 passed / 18 skipped without), vitest 121, audit_all 183 (0 stale), check_acceptance 189.

**Owner-step order corrected (from Suhrit's email):** `PERIGEE_TOKEN_SECRET`, and optionally `PERIGEE_PUBLIC_URL`, now come **before** the PR #27 merge that builds production, with an explicit redeploy if they are configured after a build. The automatic trigger is still documented as unverified.

**Not done this round, per instructions:** no merge to `main`, no visibility, access or protection changes, no secrets or variables set, no emails, no comments on teammate PRs.

## Judge demo handoff refreshed (2026-11-15, coordinator) — docs only
`docs/presentation/README.md` was rewritten against `c194d92`. The frontend code is unchanged since `a416c9e`; no UI or product code changed in this round.
- **Official rules, re-read from the guides:**
  - the demo is ≤7 slides including the title and intro slides, or a ≤30 s video, or the project is ineligible for Global Judging;
  - the slides must show the team name, the members and the challenge;
  - links must be public;
  - the deadline is 15 Nov, 11:59 p.m. local event time.
  No official local talk length was found; the 5-minute script is our own target.
- **Story:** Epsilon Indi B is the primary story (works offline), Barnard's Star the backup. The human reason to care: telling a real change from wavelength, display and artifact differences, and leaving with a defensible evidence card. No invented users, metrics or "first" claims.
- **Full narrated journey rehearsed** on the production build in fresh headless-Chrome contexts (`playwright-core@1.49.1`, new local origin; no saved evidence touched):
  - A+B, Blink, A+C, flags, the flag-screen panel, the notebook, the claim guide, Export, Print, My evidence → Reopen, reload, Barnard, a live coordinate search (24 of 460; 20–22 ready, 2–4 real IRSA 502s shown as failed) and a simulated search failure;
  - **0 search or frame calls during both cases**, so the curated fallback works during IRSA outages;
  - no overflow at 390 or 320 px.
- **Narration fixes from the rehearsal:**
  - the flagged pixel is red ("Problem flag"), not hatched;
  - the flag-screen breakdown is under "What does 'flag screen passed' mean?".
- **Artifacts in `docs/presentation/rehearsal/`:**
  - 14 desktop and 12 phone captures;
  - a real exported card (`data_origin: api`, 5 case limitations, per-frame limitations, processor 0.1.2);
  - a 3-page Letter PDF from Chrome's print engine, inspected page by page: provenance and limitations readable, no clipping. It is not the native print dialog; the button was confirmed to call `window.print`;
  - `rehearsal-log.json`.

  The old `screens/` stand-ins were removed.
- **Working/future table reconciled** with: 348/121 tests, the audits, real export and phone QA, and the production domain returning 404.
- **Not covered:** hosted or public URL, physical phone, screen reader, native print dialog, a timed human rehearsal. Cosmetic: `/favicon.ico` 404 in the console (not changed).
