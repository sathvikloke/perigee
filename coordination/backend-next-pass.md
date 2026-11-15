# Claude backend completion assignment

Sathvik has reopened implementation after the release freeze. His latest instruction is to keep working on backend quality and a defensible contribution against previous Space Apps winners. Codex owns the frontend, but Sathvik will give the frontend instructions separately: **do not edit `frontend/**` or redesign the UI.** This document is the new backend assignment, not a request to repeat already completed work.

## Start from the current release

- Fetch `origin/main`; the audited head was `9cb850bc2729b6ca45ceb356d6ad8099602d950b` (PR #45). Use a separate worktree/branch. Preserve all existing worktrees and teammates' commits.
- Primary app: https://perigee.lokesathvik.workers.dev
- Deck: https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf
- Cloudflare serves the frontend, catalog and assets. Live `/health`, `/search`, `/frame` proxy to https://perigee-liard.vercel.app.
- Vercel still serves API commit `058a2a6`; its new builds hit the quota. Do not repeatedly trigger builds or change billing. Cloudflare publication is manual, not automatic on a merge.
- PR #44 and #45 are merged. The current Cloudflare release already contains the WISE source-label correction and the seven-page PDF. Do not redo this migration.
- Keep processor A, the API contract, image IDs, quality meanings, fixed sky grids, and source allowlists. Do not bulk-merge the old processor or frontend candidates.
- Read the current integration contract and existing review decisions. D1–D3 are settled; rate limiting was deliberately not implemented as a fake per-instance global limit.

Aditya's latest verified work is public at:

- https://github.com/sathvikloke/perigee/issues/4#issuecomment-6887141847
- https://github.com/sathvikloke/perigee/pull/19#issuecomment-6887382417

He reports no new PR. His Vercel deck/source-label blocker is superseded by the Cloudflare release. Preserve his successful API checks. His PR #19 comment describes compatibility constraints, not authorization to replace the processor. For exact budgets, prefer the current implementation: 40 seconds is the total frame budget; the fetch portion is 60% by default.

## Work packet B1 — Make Worker failures obey the API contract

`cloudflare/src/app.js` assumes successful asset responses contain valid JSON and lets some asset-binding errors escape. These cases were reproduced directly against `handle()` with controlled dependencies:

1. A manifest points to a catalog document whose asset binding returns HTTP 200 HTML. `jsonDocument()` returns 200 `application/json` containing that HTML.
2. An asset binding throws while reading a document. The handler rejects without the normal JSON envelope.
3. A proxied response advertises `application/json` but contains `not-json`. The Worker passes it through as a successful JSON response.

These are injected failures, not a claim that production is currently corrupt. The existing tests simulate missing files as HTTP 404 only, so they miss the first case.

Implement a bounded, compatible fix. Validate the necessary document/manifest structure, handle rejected reads, and return the existing appropriate JSON envelope on unusable content. Preserve request IDs, `no-store` on failures, valid upstream statuses, limits, no redirects, fixed upstream origin, and the exact bytes of successful catalog documents. Do not return a fake empty catalog on failure. Do not serialize credentials or tokens into logs.

Acceptance: tests fail before the change and pass afterward for all three cases, plus missing/malformed manifest and a failed asset fetch. Existing parity, valid-content hashes, asset immutability, and proxy tests still pass. Confirm actual Workers behavior with a local Wrangler run; do not infer deployment behavior from Node mocks alone.

## Work packet B2 — Add checks for the code actually deployed

`.github/workflows/deploy-check.yml` currently excludes `cloudflare/**` from its PR path filter. It builds the frontend and runs a platform check, but does not run the Vitest suite, backend pytest suite, or Worker/parity suites. The current public smoke trigger follows Vercel statuses even though Cloudflare is the primary frontend host.

Add economical, secret-free CI for relevant PRs: frontend typecheck/build and Vitest; backend tests with honest raw-data skips; Cloudflare export, parity and Worker tests in their required order. Include Cloudflare/config/test paths in triggers. Do not download the full FITS archive in CI. Pin third-party actions consistent with the existing repository. Preserve the useful live release smoke as an intentional bounded check rather than running IRSA requests on every unrelated change.

Add a clear manual Cloudflare release verification path. A passing Vercel status must not be described as proof that the latest Cloudflare code was deployed. A deployment workflow requiring a new secret or permission may be prepared, but do not create credentials or expand account access.

Acceptance: a Cloudflare-only PR runs the relevant checks; a deliberate failing existing unit test would fail the job; ordinary PR checks need no secrets or live archive; release evidence clearly identifies what origin and build were checked.

## Work packet B3 — Make the deployed build identifiable

The exporter already writes `cloudflare/build/build-info.json`, but it sits outside the public assets directory. The current health endpoint is proxied to Vercel and does not identify the frontend/catalog release. A green smoke run can therefore check an older Cloudflare bundle.

Expose minimal non-secret build provenance for the static release, reusing the exporter rather than inventing a second build system: source commit, frontend entry/bundle digest, and a catalog/content digest. Define how uncommitted builds are labeled honestly. Keep timestamps from making a content digest meaningless. Extend release verification to compare an expected static build identity and report the live Python API separately where known. Do not break the v1 health contract or claim the two hosts are on one commit.

Acceptance: identical content has stable identity; changed frontend/catalog content is detectable; a mismatched expected release makes verification fail; the report separates Cloudflare static identity from Vercel API status. Verify the PDF's MIME type and actual bytes, not just HTTP 200.

## Work packet B4 — Correct search guidance without changing search semantics

`backend/routes/search.py` tells a user that a smaller field of view returns fewer matches and says to narrow a request to see other observations. `backend/routes/_archive.py` actually performs a fixed-radius coverage search at the query center; FOV determines the cutout, not which center-covering observations match. The app has no date filter or pagination. The live audit returned the same 377 Orion matches at 2′ and 10′.

Correct the warning text and contract explanation to describe the real bounded, evenly spaced sample. Raising the limit can show more up to 48; a smaller FOV does not narrow that archive search. Do not add a pagination/date-filter protocol just to make the old sentence true.

Acceptance: a regression check covers the capped/subset wording and preserves `ready` versus `partial`, known versus unknown totals, and deterministic selection. Make the underlying warning correct in Python; deployment on Vercel is a separate gate while quota is blocked. Do not hide an old deployed backend behind a claimed source-only fix.

## Work packet B5 — Produce evidence for the contribution

### New priority comparator from Suhrit's 7:48 p.m. email

Inspect **SPHEREx Explorer**, https://spherex-explorer.vercel.app/, especially `/about`, `/discover`, `/tour`, `/play` and the actual explorer. Suhrit originally read only its video description, so his email's proposed feature gaps are hypotheses. Codex has now directly inspected the live home, About and loaded Discover pages. They already describe quality masking, saturation caveats, matched-wavelength rules, shared brightness scales, and several authored cases with evidence and limitations. Therefore **do not claim that educational cases, quality awareness, wavelength honesty, or evidence/limitations are absent from that project**. Its Discover page loaded Iris, Hebe, Andromeda and north-ecliptic-pole cases with actual frame identifiers and demo links. Its numeric performance claims remain the authors' claims until independently reproduced.

Reassess our distinction around **learner-authored reasoning and its reviewable artifact**: does the user first make a claim, inspect contradictory evidence, revise it, save the source-linked reasoning, and apply the lesson to an unfamiliar pair? Check whether their tour/game/explorer already supports this before asserting uniqueness. Perigee currently supports claim/evidence/limitation cards but has not demonstrated learning gains or a fully validated transfer exercise. Do not relabel an existing text box as proven educational impact. Include this comparator prominently in B5 and replace weaker conclusions if the evidence warrants it. No feature arms race or frontend edits.

The strongest defensible contribution is a guided, traceable investigation that helps a learner distinguish motion/time, wavelength, display stretch and quality problems. Blink viewers, alignment and quality metadata already exist. We are not claiming a new discovery, new photometry, measured proper motion, or a novel detector.

Make a concise comparison using primary sources and reproducible demonstrations. Inspect these closest tools as well as the official 2025 category winners:

- https://github.com/ShivenKhurana1/spherex-timelapse
- https://andrei25ciuta.github.io/SPHEREx/results.html
- https://spherex-planet-x.vercel.app/about/
- https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/

The five previously reviewed winner examples were SpaceGenes+ (Science), Resonant Exoplanets (Data), Twisters/SkySense (Technology), HerCode Space/A Solar Tale (Storytelling), and Zumorroda-X/Henry's Farm Adventures (Art and Technology). They are category winners across challenges, not five SPHEREx winners or a ranked top five. Do not turn their submission claims into independently verified capability.

For each comparison, distinguish existing capability, Perigee's measured capability, and an unresolved gap. Test the same scientific question wherever possible. Report actual steps, outputs and limitations; do not invent task-time improvements, adoption, learner gains, or superiority. Do not add complex features simply to resemble a winner's technology stack.

Prepare a small **draft transfer exercise** from already verified observations, different from the taught A/B and A/C pairs, with an answer rationale, source hashes, dates, wavelength/quality checks and a concise rubric. First determine whether the existing data supports such an exercise. If not, document that limitation instead of manufacturing one. Keep it under a review/research path, separate from the shipped cases, until science review and frontend instructions. This gives Sathvik and Sagar a concrete way to test whether an unfamiliar learner can apply the reasoning again. Do not represent agent-written answers as human testing.

Acceptance: the comparison has direct source links and evidence; the proposed contribution is precise and bounded; any transfer exercise is reproducible and scientifically reviewable; remaining human validation is stated as pending.

## Frontend findings are reserved for Codex

Do not fix these in this branch. Preserve the API semantics they depend on:

- Live cache keys omit RA/Dec/FOV/release/source, allowing a 2′ cutout to appear under a 10′ query. Confirmed on production; a fresh direct backend frame correctly returns a 10′ grid.
- Same-view navigation can change the URL while retaining old search results.
- Quality-overlay image failures are silent; the checkbox and legend still imply an available overlay.
- A case-product fetch failure silently substitutes the general sequence's individually stretched products.
- My evidence scroll/focus, required-pair remove controls, placeholder contrast, and stale case context need frontend attention.

## Verification and delivery

Continue through implementation, relevant tests, review and a concrete PR; do not stop after writing a plan or after one packet passes. Prioritize B1–B4 before expanding B5. You may split independent backend work if your current environment supports it, but coordinate owned files and integrate the results yourself.

Current audit baseline on main: 121/121 frontend tests, frontend production build; 348/348 backend tests with `PERIGEE_DATA_ROOT`; 15/15 Worker tests; 7/7 export parity tests. The app and deck are public. New failures must be investigated, not dismissed because an older smoke passed.

Useful local Python: `/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/.claude/worktrees/perigee-parallel-coord-4aa087/.venv/bin/python`.
Raw data: `/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data`.

Deliver a backend-only PR, exact tests and failure reproductions, changed public contracts if any, source/deployment status separately, and an honest contribution comparison. Send Codex the PR and any blocker as soon as actionable. Keep the last working release available. Do not edit frontend files, auto-submit the competition form, write personal team attestations, send teammates email, change billing/security settings, or merge superseded PRs.

Working toward winner-level quality means a clear human need, a distinctive evidence-backed contribution, sound science, a dependable demonstration and understandable presentation. It does not mean promising a win or declaring parity without checking the actual work.
