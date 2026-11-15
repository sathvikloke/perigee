# Release handoff (N6): backend candidate and origin state

> Release update: PRs #50 and #51 are merged and deployed. The third investigation and completion flow are live, as is the Python crash fix. This handoff preserves the earlier candidate state; see [current release evidence](../qa/final-investigation/README.md).

**Audience:** Codex, owner of the final shared deployment. Nothing was deployed from this branch, Cloudflare was not touched, and nothing was pushed to `main`.

## 1. Candidate

- **Branch:** `claude/overnight-science-backend`.
- **Candidate:** the PR head recorded in `coordination/overnight-status.md` → N9, once exact-head CI is green. Until then there is no approved candidate.
- **Base:** `origin/main` `0ffff6f`, unchanged since this branch started. The branch merges cleanly with no conflicts.

The runtime diff against `main` is two files: one code fix and one shipped-content text correction. Everything else in the branch is tests, science artifacts, staging, QA fixtures and coordination documents.

| Path | Runtime effect |
|---|---|
| `backend/data/process.py` (+21 lines, `_check_wave_table_index`) | **D1 fix (P1).** A damaged WCS-WAVE lookup table (a repeated or non-finite index value) made wcslib abort the whole Python process with SIGABRT. The frame route now returns the frame with `wavelength_um: null` and the existing "Wavelength unavailable: spectral WCS (key W) could not be evaluated" note instead. Valid data is unchanged: all 183 retained cutouts give identical records before and after, and `PROCESSING_VERSION` stays `perigee-processor-a/0.1.2` |
| `backend/content/cases/fair_comparison.json` (text only; `content_version` `fair_comparison-2026-11-14b` → `-2026-11-15a`) | **Science wording correction from the N9 adversarial review.** The case said a flagged dot was "not something in the sky" / "not a change in the sky", which rests on flags alone (A and B are on different detector positions, so no same-pixel test exists). It now says the flagged pixel "gives no reason to claim a change in the sky". The supported A/B conclusion now names the remaining differences (DR1 vs QR3 release, pipeline build, pointing and rotation), and the background no longer calls a flag type "cosmic-ray hits" (no SPHEREx flag has that name). Frames, products, assets, the answer structure and `example_claim` (quoted in the deck narration) are unchanged. `admit_case.py` still admits it. This changes the catalog digest |
| `tools/ingest/admit_case.py` | offline authoring tool; not imported by the app |
| `.github/workflows/ci.yml` | adds the registration-audit pytest step and path triggers; no secrets, no deploy |

There are **no** changes to `frontend/**`, `cloudflare/**`, any image or frame product, the API contract or the route semantics.

## 2. What is live now (checked once, 2026-11-15 ~04:00 UTC)

| Component | State | Evidence |
|---|---|---|
| Cloudflare Worker `perigee` (static app, catalog, Worker router) | version `4031abf8-c0fb-4689-8205-3211ea0c673c`, source `fbb6647` | `docs/DEPLOYMENT.md` (release owner's record); not re-deployed or re-smoked here |
| Vercel Python origin `https://perigee-liard.vercel.app` | **`main` `0ffff6f`**. The quota reset, and Vercel's GitHub status is `success` at 03:26:36Z (`vercel.com/sathviklokes-projects/perigee/AxnZUxaeYCGgvPCxtsqHysJdJ8uj`) | `GET /api/v1/health` gives `ok`, `token_signing: env`. One search (83.822, −5.391, limit 1) returns PR #47's corrected B4 warning wording |

**B4 is live.** `docs/DEPLOYMENT.md` still says the origin runs `058a2a6` and that the B4 correction "remains undeployed"; both statements are now **stale**. That file is the release owner's, so it was not edited here. Correct it at the next release.

**D1 is not live.** The origin runs `0ffff6f`, which predates the fix.

**Vercel quota is close to its limit.** The PR's Vercel preview for `ead104a` (04:51:05Z) failed with "Deployment rate limited — retry in 24 hours" (`api-deployments-free-per-day`). That is a platform quota, not a build or test failure, and it was not retried. The next push's preview (`cc52c87`) then completed successfully at 04:53:23Z. The production build of the merge commit may still hit the daily limit, so confirm its status. Until it deploys, the only source-vs-production difference on the Python origin is D1.

- **User impact:** a damaged cutout transfer from IRSA would crash the function. The Worker then shows its generic 502 `UPSTREAM_UNAVAILABLE` envelope instead of a frame with "wavelength unavailable".
- **Who can trigger it:** it needs a damaged file from the allowlisted archive. A user cannot trigger it by choosing a URL. No such file has been seen in production.

## 3. Pending deployment steps (Codex)

**Both layers.** The Python origin needs the D1 fix, and Cloudflare needs a content redeploy for the `fair_comparison` text correction. The Worker code is unchanged. The Cloudflare step can wait for, and ride along with, your UI redesign deploy.

1. **Merge the PR** after review. On Vercel's Git integration, a push to `main` builds production automatically, if the build quota allows.
   - If the quota blocks the build again, do not retry repeatedly. D1 is a robustness fix, and the current origin is otherwise correct.
2. **Confirm the build** with the Vercel GitHub status `success` for the merge commit.
3. **Cloudflare content redeploy**, from the merge commit (or from your UI branch once it contains this merge). Follow `docs/CLOUDFLARE.md` → "Deploy":
   ```bash
   (cd frontend && npm ci && npm run build) && .venv/bin/python cloudflare/build.py
   .venv/bin/python -m pytest -q cloudflare/tests && node --test cloudflare/test/*.test.mjs
   cd cloudflare && npx wrangler@4.162.0 deploy
   ```
   On this branch, with the shipped frontend, the build gave:

   | Identity | This branch | Deployed `4031abf8…` | Same? |
   |---|---|---|---|
   | Worker digest | `4a4073ba9fd628fc…` | `4a4073ba9fd628fc…` | yes |
   | frontend digest | `82e0c264…` | `82e0c264…` | yes |
   | catalog digest | `69bd6c4c531514e9…` | `a82761e7…` | **no** (the `fair_comparison` text) |
   | release digest | `c5f419e067f766b4…` | `548e7202640872b3…` | **no** |

   A UI redesign changes the frontend and release digests again. Smoke whatever you actually deploy.
4. **Run the logged-out checks** against the build you deployed:
   ```bash
   .venv/bin/python cloudflare/tests/smoke_local.py --base https://perigee.lokesathvik.workers.dev --cloudflare-edge
   .venv/bin/python -m backend.platform.smoke --base https://perigee.lokesathvik.workers.dev --expect-build cloudflare/build/build-info.json
   ```
   - Do not run `--expect-build` with this branch's local build against the current production. Production is still `548e7202…` (source `fbb6647`), so the mismatch is expected and is not a fault.
   - If you deploy only the Python origin first, check the unchanged Cloudflare release with `--expect-release-digest 548e7202640872b3ea524061ac50a28d0be5d3b3a930048bf1ffac0b5b88024d`.
5. **If you also ship the staged third case:** copy it as in `science/staging/README.md`, rebuild, and smoke as in step 4.
6. **Record the result** in `docs/DEPLOYMENT.md`: the origin commit and the Cloudflare version.

**Secrets, by name only:**

- `PERIGEE_TOKEN_SECRET` stays on the Vercel project for Production and Preview. It is unchanged, and no value is in this repository.
- `PERIGEE_DEV_MODE` stays unset in production.
- Cloudflare needs no secret; the account comes from `wrangler.jsonc` or `CLOUDFLARE_ACCOUNT_ID`.
- `VERCEL_AUTOMATION_BYPASS_SECRET` is used only for `smoke --bypass` against protected previews.

**Compatibility with the current UI:** full.

- `/api/v1` fields, status codes, error codes, token semantics, the 3.6″ search cone, the 48-result temporal sampling, coordinate conventions, quality meanings and display defaults are all unchanged.
- The `fair_comparison` change is copy only. Every field the UI reads keeps its type and position, and the steps, frames and refs are unchanged.
- The only API behavioural difference is on a damaged spectral table: before, the process crashed and the client saw a 502; now the client gets a 200 frame with `wavelength_um: null`. The UI already renders a null wavelength (`no_coverage.json` shows the same field state).

## 4. Rollback

| Layer | Rollback reference |
|---|---|
| Python origin | Vercel Instant Rollback to the current production deployment (GitHub status target `…/perigee/AxnZUxaeYCGgvPCxtsqHysJdJ8uj`, `main` `0ffff6f`). Or revert the `process.py` change, which is self-contained |
| Cloudflare | `npx wrangler@4.162.0 rollback 4031abf8-c0fb-4689-8205-3211ea0c673c` from `cloudflare/`, the current verified version |

## 5. Resilience evidence (bounded, local)

The full matrix is in `qa/overnight-backend/README.md` §3. All results come from local mocked upstreams. NASA and the public service were not load-tested; there was exactly one live IRSA search.

**Deadlines bind:**

- frame budget 2 s gives a 504 at about 1.2 s;
- a slow-drip stream is abandoned at the overall deadline;
- the processor budget gives a retryable 500 `PROCESSING_FAILED`.

**Byte caps bind:**

- frame fetch: at most cap + one 4 KiB chunk pulled;
- SIA body: at most 12 MiB + one chunk;
- a declared 1 GB `Content-Length` is refused before download.

**Partial and failed searches stay distinct from empty:**

- one collection hanging or malformed gives `partial` with `total_matches: null`;
- both failing gives 502 or 504;
- a malformed collection next to an empty good collection gives an error, never `empty`.

**Worker with the origin down:**

- all curated presets, cases, frames and assets are byte-exact (74 of 74 routes);
- live routes return JSON envelopes;
- the build identity is kept.

This was checked in Node (8 failure modes) and in real `wrangler dev`/workerd with a closed-port origin.

**Overlay failure:** a missing overlay is a 404 `ASSET_NOT_FOUND`, and the backend never synthesizes "clear". The frontend gap (no `onError` on the overlay) is in the UI handoff (F3).

**Measurements** (descriptive, one laptop, n = 3 to 10, not capacity figures):

| Measure | Result |
|---|---|
| cold import + first `/frame` | 0.29–0.43 s + 43–45 ms |
| warm `/frame` p50 | 31–41 ms |
| peak RSS | 127.6 MB |
| processor peak allocation (10′) | 12.95 MB |
| warm `/search` p50 | 24.8 ms (468 matches → 48) |

Responses are 14–42 KB against a 4 MB cap.

**Concurrency:** Perigee configures no concurrency limit. anyio's thread pool caps a process at 40, and Vercel scales by instances. This is stated rather than implied.

**D1 verification by the coordinator:** with the pre-fix `process.py` from `0ffff6f`, the regression file gives **5 failed, 1 passed**. The 5 are four synthetic bad index tables plus the real retained cutout with the zeroed block; the passing test is the valid-table control. With the fix it gives **6 passed**. Without `PERIGEE_DATA_ROOT`, the real-cutout case skips, which leaves 4 failed.

## 6. Does the public release still differ from source?

| Layer | Difference |
|---|---|
| Cloudflare | yes, by the `fair_comparison` wording correction (catalog digest). Worker and frontend are identical. Closing it needs step 3 |
| Python origin | yes, by one robustness fix (D1). Closing it needs the Vercel build in step 1 |
| Not yet integrated | the staged third case and every frontend item in `coordination/overnight-ui-handoff.md` |
