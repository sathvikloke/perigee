# Release handoff (N6): backend candidate and origin state

**Audience:** Codex, owner of the final shared deployment. Nothing was deployed from this branch, Cloudflare was not touched, and nothing was pushed to `main`.

## 1. Candidate

- **Branch:** `claude/overnight-science-backend`.
- **Candidate:** the PR head recorded in `coordination/overnight-status.md` → N9, once exact-head CI is green. Until then there is no approved candidate.
- **Base:** `origin/main` `0ffff6f`, unchanged since this branch started. The branch merges cleanly with no conflicts.

The runtime diff against `main` is one file. Everything else in the branch is tests, science artifacts, staging, QA fixtures and coordination documents.

| Path | Runtime effect |
|---|---|
| `backend/data/process.py` (+21 lines, `_check_wave_table_index`) | **D1 fix (P1).** A damaged WCS-WAVE lookup table (a repeated or non-finite index value) made wcslib abort the whole Python process with SIGABRT. The frame route now returns the frame with `wavelength_um: null` and the existing "Wavelength unavailable: spectral WCS (key W) could not be evaluated" note instead. Valid data is unchanged: all 183 retained cutouts give identical records before and after, and `PROCESSING_VERSION` stays `perigee-processor-a/0.1.2` |
| `tools/ingest/admit_case.py` | offline authoring tool; not imported by the app |
| `.github/workflows/ci.yml` | adds the registration-audit pytest step and path triggers; no secrets, no deploy |

There are **no** changes to `frontend/**`, `cloudflare/**`, `backend/content/**`, the API contract or the route semantics.

## 2. What is live now (checked once, 2026-11-15 ~04:00 UTC)

| Component | State | Evidence |
|---|---|---|
| Cloudflare Worker `perigee` (static app, catalog, Worker router) | version `4031abf8-c0fb-4689-8205-3211ea0c673c`, source `fbb6647` | `docs/DEPLOYMENT.md` (release owner's record); not re-deployed or re-smoked here |
| Vercel Python origin `https://perigee-liard.vercel.app` | **`main` `0ffff6f`**. The quota reset, and Vercel's GitHub status is `success` at 03:26:36Z (`vercel.com/sathviklokes-projects/perigee/AxnZUxaeYCGgvPCxtsqHysJdJ8uj`) | `GET /api/v1/health` gives `ok`, `token_signing: env`. One search (83.822, −5.391, limit 1) returns PR #47's corrected B4 warning wording |

**B4 is live.** `docs/DEPLOYMENT.md` still says the origin runs `058a2a6` and that the B4 correction "remains undeployed"; both statements are now **stale**. That file is the release owner's, so it was not edited here. Correct it at the next release.

**D1 is not live.** The origin runs `0ffff6f`, which predates the fix.

- **User impact:** a damaged cutout transfer from IRSA would crash the function. The Worker then shows its generic 502 `UPSTREAM_UNAVAILABLE` envelope instead of a frame with "wavelength unavailable".
- **Who can trigger it:** it needs a damaged file from the allowlisted archive. A user cannot trigger it by choosing a URL. No such file has been seen in production.

## 3. Pending deployment steps (Codex)

**Python origin only.** The Cloudflare bundle does not need a redeploy for this backend change.

1. **Merge the PR** after review. On Vercel's Git integration, a push to `main` builds production automatically, if the build quota allows.
   - If the quota blocks the build again, do not retry repeatedly. D1 is a robustness fix, and the current origin is otherwise correct.
2. **Confirm the build** with the Vercel GitHub status `success` for the merge commit.
3. **Run the logged-out checks** against the public app, which proxies live routes to the origin:
   ```bash
   .venv/bin/python -m backend.platform.smoke --base https://perigee.lokesathvik.workers.dev --expect-release-digest 548e7202640872b3ea524061ac50a28d0be5d3b3a930048bf1ffac0b5b88024d
   .venv/bin/python cloudflare/tests/smoke_local.py --base https://perigee.lokesathvik.workers.dev --cloudflare-edge
   ```
   - Use `--expect-release-digest`, **not** `--expect-build`, unless you also redeploy Cloudflare from the merge commit.
   - `--expect-build` deliberately requires the same *source label*. The deployed label is `fbb6647`, while a local build of the candidate reports its own commit. That mismatch is intentional, not a fault.
   - The release, frontend, catalog and Worker digests are identical, as the next point shows.
4. **Optional local identity check, before or after merging:**
   ```bash
   .venv/bin/python cloudflare/build.py   # needs frontend/dist (npm run build --prefix frontend)
   ```
   On this branch the build gave:

   | Identity | Value | Same as deployed `4031abf8…`? |
   |---|---|---|
   | release digest | `548e7202640872b3…` | yes |
   | Worker digest | `4a4073ba9fd628fc…` | yes |
   | catalog content version | `targets-2026-11-15a` | yes |
   | frontend digest | `82e0c264…` | yes |

   So a Cloudflare redeploy would change nothing users see.
5. **If you are also shipping the UI redesign or the staged third case:** that changes the frontend and catalog digests and needs the full Cloudflare deploy in `docs/CLOUDFLARE.md` → "Deploy". Then run the `--expect-build cloudflare/build/build-info.json` smoke against *that* build.
6. **Record the result** in `docs/DEPLOYMENT.md`: the origin commit and the Cloudflare version.

**Secrets, by name only:**

- `PERIGEE_TOKEN_SECRET` stays on the Vercel project for Production and Preview. It is unchanged, and no value is in this repository.
- `PERIGEE_DEV_MODE` stays unset in production.
- Cloudflare needs no secret; the account comes from `wrangler.jsonc` or `CLOUDFLARE_ACCOUNT_ID`.
- `VERCEL_AUTOMATION_BYPASS_SECRET` is used only for `smoke --bypass` against protected previews.

**Compatibility with the current UI:** full.

- `/api/v1` fields, status codes, error codes, token semantics, the 3.6″ search cone, the 48-result temporal sampling, coordinate conventions, quality meanings and display defaults are all unchanged.
- The only behavioural difference is on a damaged spectral table: before, the process crashed and the client saw a 502; now the client gets a 200 frame with `wavelength_um: null`. The UI already renders a null wavelength (`no_coverage.json` shows the same field state).

## 4. Rollback

| Layer | Rollback reference |
|---|---|
| Python origin | Vercel Instant Rollback to the current production deployment (GitHub status target `…/perigee/AxnZUxaeYCGgvPCxtsqHysJdJ8uj`, `main` `0ffff6f`). Or revert the merge commit: the change is self-contained in `backend/data/process.py` |
| Cloudflare | Not changed by this candidate. If a later UI deploy needs reverting, use `npx wrangler@4.162.0 rollback 4031abf8-c0fb-4689-8205-3211ea0c673c` from `cloudflare/` (the current verified version) |

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
| Cloudflare | none for users: same release and Worker digests. Only the source label differs |
| Python origin | yes, by one robustness fix (D1). Closing it needs the Vercel build in step 1 |
| Not yet integrated | the staged third case and every frontend item in `coordination/overnight-ui-handoff.md` |
