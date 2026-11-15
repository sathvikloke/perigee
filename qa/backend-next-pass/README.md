# Backend next pass (B1–B4): reproductions and results

- **Assignment:** `coordination/backend-next-pass.md`, in Codex's release-verification worktree.
- **Branch:** `claude/backend-next-pass`, from `origin/main` @ `9cb850b`.
- **Scope:** backend, platform, Cloudflare and CI only. **No `frontend/**` file was changed.**
- **Date:** 2026-11-15. All runs are local (macOS, Python 3.12.16, Node 26, Wrangler 4.162.0) unless stated otherwise.

## B1: Worker failures obey the API contract

**Reproduction with tests.** New tests in `cloudflare/test/worker.test.mjs` (`B1.1`–`B1.5`) were run against the Worker on `main` **before** the fix:

| Test | Result on `main` |
|---|---|
| B1.1: catalog document returned as HTML 200 | **FAIL** (served as 200 `application/json`) |
| B1.1b: valid JSON of the wrong shape | **FAIL** (200) |
| B1.2: asset binding throws while reading | **FAIL** (the promise rejects; no envelope) |
| B1.3: proxied body labelled `application/json` but `not-json` | **FAIL** (passed through as 200 or 503) |
| B1.4: missing, non-JSON or malformed manifest | pass, but only incidentally (a missing field produced a 404 path) |
| B1.5: asset fetch returns 5xx or HTML | pass (the hash check rejected it) |

After the fix, all 21 Worker tests pass.

**Real Workers runtime** (`wrangler dev` on a deliberately corrupted copy of `cloudflare/build/public`):
- `cases/fair_comparison.json` was replaced by HTML;
- `presets/wise_0855/frames.json` was replaced by `[1,2,3]`;
- one PNG had one byte appended.

| Request | Worker from `main` (before) | This branch (after) |
|---|---|---|
| `GET /api/v1/cases/fair_comparison` | `200 application/json`, body `<!doctype html><div id=root></div>` | `503 application/json`, `no-store`, `CONTENT_UNAVAILABLE` |
| `GET /api/v1/presets/wise_0855/frames` | `200 application/json`, body `[1,2,3]` | `503 application/json`, `no-store`, `CONTENT_UNAVAILABLE` |
| `GET /api/v1/assets/<tampered png>` | — | `404 application/json`, `no-store`, `ASSET_NOT_FOUND` |
| `GET /api/v1/cases/moving_neighbor` (intact) | — | `200 application/json`, served unchanged |

With a malformed manifest (`{"schema_version":1}`) on this branch:
- `/api/v1/presets` and `/api/v1/cases/fair_comparison` return `503 CONTENT_UNAVAILABLE` (`no-store`);
- `/api/v1/nope` returns `404 NOT_FOUND`;
- `/` still returns 200 (SPA).

**Not reproducible in the real runtime:** a binding that *throws* (B1.2), and an upstream that answers `application/json` with a non-JSON body (B1.3; the upstream origin is a fixed constant). Both are covered only by the Node tests.

## B2: CI for the deployed code

- **`.github/workflows/ci.yml` (new, secret-free).** It runs on PRs touching `backend/`, `frontend/`, `cloudflare/`, `tools/ingest/`, `science/reviews/acceptance/`, the Vercel config or the workflows, and on pushes to `main`.
  - **Backend job:** `pytest backend -q -rs`, reporting raw-data skips in the summary.
  - **Frontend + Cloudflare job:** `npm ci`, typecheck, Vitest, build, then `cloudflare/build.py`, `pytest cloudflare/tests`, `node --test cloudflare/test/*.test.mjs`. The CI build's identity is written to the job summary.
  - It uses no new third-party actions; the existing pinned checkout, setup-python and setup-node SHAs are reused.
- **`.github/workflows/cloudflare-release-verify.yml` (new, manual).** It builds the expected release from `ref`, then runs `smoke_local.py --cloudflare-edge` and `smoke --expect-build` against `base`. Secret-free. One live search and frame run only if `live` is set.
- **`release-smoke.yml`:** a Vercel-status-triggered run now says plainly that it does not show Cloudflare serves that commit, and points to the verify workflow.
- **Checks:**
  - `actionlint` 1.7.7 passes all four workflows.
  - `test_workflows_pin_actions_to_full_shas` now checks every workflow file.
  - A deliberately failing test makes the CI commands exit non-zero: `node --test cloudflare/test/*.test.mjs` exited 1, and `set -o pipefail; pytest backend -q -rs | tee …` exited 1. The temporary test files were removed.
  - **First real CI run (run 43666247129): `backend` passed and `frontend-cloudflare` failed.** On Node 22 (CI), `node --test cloudflare/test/` treats the directory as a module path (`Cannot find module …/cloudflare/test`); Node 26 (local) accepts a directory. Every earlier step in that job passed (typecheck, Vitest, build, export, `pytest cloudflare/tests`). Fixed by passing the files explicitly (`node --test cloudflare/test/*.test.mjs`) in CI and in the docs. **Follow-up run 43666365184 on `da1e2e8`: all jobs passed.** `backend` 340 passed / 18 skipped (no raw data in CI); `frontend-cloudflare`: typecheck, Vitest 121/121, build, export, `pytest cloudflare/tests` 13 passed, `node --test` 21/21.

## B3: Deployed build identity

`/perigee-build.json` is written by `cloudflare/build.py`; the format is in `docs/CLOUDFLARE.md` under "Build identity".

**Tests:** `cloudflare/tests/test_build_identity.py` has 6 tests:
- identical content gives the same identity;
- changing `index.html` changes only the frontend digest and the release digest;
- an edited case title changes only the catalog digest and the release digest;
- a changed PDF is detected;
- the identity has no timestamps and no secret-like fields;
- the source label is honest.

`backend/tests/platform/test_platform_smoke.py` has 6 more: a match passes, while a mismatched digest, a wrong PDF type or bytes, stale served `index.html` or script bytes, or a missing identity each fails.

**Real runs:**
- Local `wrangler dev` of this branch's build (release `59a3ee54bbeacc40…`, source `9cb850b…+uncommitted`):
  - `smoke_local.py` passed **24/24**, including "static build identity equals local build".
  - `smoke --expect-build cloudflare/build/build-info.json` passed **26/26**. That covers the release, frontend and catalog digests; the served index (`ea982beb…`) and entry script (327,624 B); the deck PDF (`application/pdf`, 2,369,713 B, sha `ffab44ce…`); and a live search and frame through the proxy.
- Current production, `https://perigee.lokesathvik.workers.dev` (version `979e0619…`, built before this file existed), with `--expect-build` and `--no-live`: **FAIL 18/19**, failing only on "static build identity". `/perigee-build.json` falls back to the SPA, so this is the correct verdict for an older release.
- The report printed the static release and the live Python API (`health ok`, `token_signing env`; commit not exposed) as separate sections.

## B4: Search guidance

- **Old text (wrong):**
  - "…evenly spaced in time. Narrow the request or raise the limit (max 48) to see others."
  - On an archive cap: "…A smaller field of view returns fewer."
- **What the search actually does:** it matches images whose footprint contains the query position (a fixed 3.6″ radius, `SEARCH_RADIUS_DEG`). `fov_arcmin` only sets the cutout.
- **New text:**
  - "…evenly spaced in time from the earliest to the latest. Raising the limit (up to 48) shows more; the field of view sets the cutout size, not which images match."
  - The cap warning now says the search matches images that cover the position, and that the field of view does not change which match.
- **Docs:** the contract's "Search" section and `backend/tests/api/REVIEW.md` (D1) now describe the coverage search, the evenly spaced sample and the absence of a date filter or pagination.
- **Tests** (4 new in `backend/tests/api/test_search.py`):
  - the wording of both warnings;
  - `ready` versus `partial` and known versus unknown totals are preserved;
  - deterministic, FOV-independent selection that keeps the first and last match;
  - IRSA SIA query parameters identical at 2′ and 10′ (`POS=CIRCLE 83.822 -5.391 0.001`).

  On `main`'s `search.py`, the two wording tests **fail**; on this branch all 62 search tests pass.
- **Not changed:** search semantics, the response schema and status logic.
- **Deployment:** this is a source fix only. The live Python API is still Vercel commit `058a2a6`, so production keeps the old wording until a Vercel deploy, which is quota-blocked. Recorded live examples (`backend/tests/api/examples/search_response.ready.live.json`, and the frontend fixture, which is reserved for Codex) still contain the old sentence, as historical captures.

## Test totals on this branch

| Suite | Result |
|---|---|
| Backend (`PERIGEE_DATA_ROOT` set) | 358 passed (baseline 348 + 10 new) |
| Backend (without raw data) | 340 passed, 18 skipped |
| Frontend | typecheck ok; Vitest 121/121; build ok (no frontend change) |
| `pytest cloudflare/tests` | 13 passed (7 parity + 6 identity) |
| `node --test cloudflare/test/*.test.mjs` | 21/21 |
| actionlint | 4 workflows clean |

## Deployment status (separate from source)

Nothing was deployed.
- Cloudflare is still version `979e0619…` (source `fd7933d`). B1 and B3 reach users only after a manual `wrangler deploy` of this branch's build.
- The Vercel API is still `058a2a6`. B4 reaches users only after a Vercel deploy, which is quota-blocked.
