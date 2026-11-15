# Perigee deployment handoff

## Current public release — Cloudflare and Python origin, 2026-11-15

**App:** https://perigee.lokesathvik.workers.dev · **Third investigation:** https://perigee.lokesathvik.workers.dev/?preset=wise_0855 · **Deck:** https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf · **Source:** https://github.com/sathvikloke/perigee

PRs [#50](https://github.com/sathvikloke/perigee/pull/50) and [#51](https://github.com/sathvikloke/perigee/pull/51) are merged and released. Both runtime layers use source **`4db9eff40714633dabc3da92bd988b3ae237060b`**. Documentation-only commits afterward do not change this deployed source identity.

- **Cloudflare:** Worker `perigee`, version **`3263fb1d-ab12-45e2-8a64-67abcf58b99c`**, built from clean release inputs. Release digest **`f655b567420a31aa2b86629586ffd914c291c7cb95f937463f85c9d9aace1c21`**. Five presets, three investigations, 968 assets, content `targets-2026-11-15b`.
- **Python origin:** https://perigee-liard.vercel.app, Vercel deployment **`dpl_9ULajTQKdW4sZ26PQVptMCNVnw3U`**. Connected deployment API verified `READY`, production target, matching source and production alias. The malformed spectral-table crash fix is live. PR preview builds hit quota; both production merges succeeded.
- **Verified logged out:** Cloudflare hosting smoke **28/28**, release smoke **29/29** against the exact build, including real archive search and frame processing. Public browser confirmed the third case, six steps and complete images. [Release logs, build identity and screenshots](../qa/final-investigation/README.md).

The redesigned frontend, curated catalogs/images and deck are served on Cloudflare. Only live search, frame processing and health are proxied to Vercel. Keep that project while it supplies the live path.

“A dot that jumps” uses the reviewed shared-scale A/B images and explicitly labels C's separate contrast stretch. Guided cases save reviewed steps and require a saved claim, observations and uncertainty before the first reference comparison. The learner's claim stays separate from the reference. Completion is not grading. Older WISE free-exploration notes keep their own saved context.

**Deployment remains manual on Cloudflare.** Merging GitHub does not publish a new Worker version. Rebuild/export, deploy with Wrangler, and run both smoke commands in [the Cloudflare handoff](CLOUDFLARE.md). Version preview URLs remain disabled; no signing secret was copied to Cloudflare.

For the demo, open a curated investigation first and use live coordinate search after it. Notes are tied to each browser origin; old Vercel notes remain on the Vercel URL. The existing deck is unchanged (SHA-256 `ffab44ce1f9fe182d2b9f427ae186c30e18e2cfc7ff6ea24099ecbd8d05ca89e`).

Rollback references: previous Cloudflare version `521d15bc-93f1-44a7-b465-1a13d8d9abb2` (source `20fb03f9b97654492eb014f3941aa224bae3bf7f`); previous Python production `dpl_38xwbjVx6PYUUgtxzYRTGRfdS3rd` (source `38ccb9bc20ed9b086d3d9ed1bf43c9bab7df1a24`, already includes the crash fix).

The Vercel setup and rehearsal records below are historical context.

## Historical Vercel release — 2026-11-15 00:28 UTC

**Open the app:** https://perigee-liard.vercel.app. **Source:** https://github.com/sathvikloke/perigee (public).

PR [#27](https://github.com/sathvikloke/perigee/pull/27) was merged at 00:27:09 UTC. Vercel built production from `main` at **`ef298900aa5769c47ec32f2bdb7c94ac27af14f3`**, deployment **`dpl_4gggyXwZGgMaUtSPRUSJx6iJUMjq`**. The connected Vercel API confirmed `READY`, the production target, this commit, and the `perigee-liard.vercel.app` alias.

**Verified without login:** the production homepage returns 200 HTML; `/api/v1/health` returns 200 JSON with `status: ok` and `token_signing: env`. The [production release-smoke run](https://github.com/sathvikloke/perigee/actions/runs/43658316997) passed **20/20**, including live non-preset archive search and one processed frame. The search returned 377 matches in 2.1 seconds; the requested frame returned a valid PNG in 4.5 seconds. These are observations from this run, not performance guarantees.

Separate sensitive `PERIGEE_TOKEN_SECRET` variables were configured for Production and Preview before the production build. `PERIGEE_DEV_MODE` remains unset. No values are stored in this repository. The repository variable `PERIGEE_PUBLIC_URL` is set to the public app origin.

Vercel Authentication retains **Standard Protection** (`all_except_custom_domains`): production domains are public; preview and generated deployment URLs remain protected. An unauthenticated request to the latest pre-release preview returned 302 to Vercel login after publication. This matches [Vercel's documented scope](https://vercel.com/docs/deployment-protection).

The smoke workflow was triggered manually. Automatic `deployment_status` delivery has not been demonstrated for this repository; see the trigger notes below. The [independent public browser pass](../qa/public-release/README.md) verified comparisons, quality overlays, notebook saving/reopen and a real JSON download separately from the HTTP smoke results.

**Re-check of `main` @ `f797b34` (Suhrit, 2026-11-15 ~00:45 UTC, logged out):** smoke **PASS 20/20**, exit 0. Live search took 2.4 s and the frame 1.9 s.
- All five presets serve their frame lists in ≤ 0.6 s, and every image asset is a valid PNG: 183/183 (34 + 44 + 34 + 35 + 36).
- Both cases load in about 0.1 s.
- Presets and cases are bundled with the app and do **not** call NASA's archive.
- From PR #40, `release-smoke` also runs automatically on Vercel's "Deployment has completed" status for `main` commits.

### Demo-day checklist

1. **After any merge to `main`:** confirm a `release-smoke` run passed (Actions tab), or run `python -m backend.platform.smoke --base https://perigee-liard.vercel.app` (expect exit 0).
2. **10 minutes before presenting:**
   - Open https://perigee-liard.vercel.app in a private window. This warms the function; the first request after idle is slower.
   - Open the preset you will demo once.
3. **Lead with a preset**, for example Barnard's Star ("Follow a nearby moving star") or Epsilon Indi B ("Is this a fair comparison?"). Presets are bundled and do not depend on NASA's archive.
4. **Show the coordinate search second, as a bonus.** IRSA can be slow:
   - The search may show **partial** results. One collection timed out at limit 24 in rehearsal.
   - A frame may fail with a retryable upstream error while the others load.
   - Say what the app shows. It is reporting the archive's state honestly; it is not broken.
5. **Never use `perigee.vercel.app`.** It is an unrelated app.

Resource identifiers:

- Dashboard: https://vercel.com/sathviklokes-projects/perigee
- Project: `perigee` / `prj_7JhA3Inkh0euYF4UVwhyDYJusAfQ`
- Team: `sathviklokes-projects` / `team_blm7QlnXb2J53PuzDBnv9TcO`
- Production branch: `main`
- Architecture: React/Vite `web` service plus FastAPI `api` service, same origin, defined in `vercel.json`.

The dated preview and local rehearsal sections below are historical evidence. Their pre-release missing-secret, private-repository and 404 observations were resolved by this release.

## First deployment

Follow [the integration contract](INTEGRATION_CONTRACT.md). The preferred setup is React/TypeScript/Vite in `frontend/` plus Python/FastAPI in `backend/`, deployed together using Vercel Services. Services is Beta. Check its current configuration documentation when creating `vercel.json`; use the schema supported by the actual project and CLI.

Validate the smallest shell first. Route `/api/(.*)` to the Python service before the frontend catch-all, and make the backend handle the original path received. Check the frontend, a direct frontend URL, `/api/v1/health`, a catalog response and one small asset. Inspect response content types; frontend HTML returned at an API URL is a failure.

Then deploy one bounded archive search and one processed frame. Measure cold-start behavior, request duration, response size and the packaged Python dependencies. Exclude raw FITS, the research environment and download directories from the deployment. Do not assume a successful local run establishes deployed performance.

If Services blocks progress for more than 30 minutes, coordinate a two-project Vercel fallback with one explicit frontend API origin. Keep the same API contract. Verify CORS from the deployed frontend and record both project URLs. Do not add a persistent worker, database or queue without an actual measured need and coordinated contract change.

## Services configuration (validated 2026-11-14, worker 07)

Checked against the current Vercel docs for [Services](https://vercel.com/docs/services), [Services routing](https://vercel.com/docs/services/routing), the [service config reference](https://vercel.com/docs/services/config-reference), [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), the [Python runtime](https://vercel.com/docs/functions/runtimes/python) and [Functions limits](https://vercel.com/docs/functions/limitations). The current syntax is the `services` key. The older `experimentalServices`/`routePrefix` model is rejected for projects created on or after 2026-07-06, so it is not used here.

`vercel.json` (repository root) defines two services and orders the public rewrites:

| Request | Rule | Service | Path the service sees |
|---|---|---|---|
| `/api`, `/api/...` | first two rewrites | `api` (FastAPI, Python 3.12) | original path, e.g. `/api/v1/health` (Vercel does not strip the prefix) |
| everything else | `/(.*)` catch-all | `web` (Vite static build of `frontend/`) | files from `frontend/dist`, else `/index.html` (SPA fallback inside the service) |

Routing into a service is final. An unknown `/api/...` path gets FastAPI's own JSON 404 and never falls through to the SPA. A missing static file under `web` gets `index.html`.

Layout rules for the integration branch:

- The backend service root is the repo root (`"root": "./"`) with `"entrypoint": "backend.main:app"`. This keeps package imports (`from backend.x import y`, or relative imports) working, as with `uvicorn backend.main:app` locally. Do **not** use `"root": "backend/"` with `main:app`. That puts `backend/` first on `sys.path`, so the `backend/platform/` package shadows the stdlib `platform` module. This was reproduced locally: `import platform` resolved to `backend/platform/__init__.py`.
- Vercel resolves Python dependencies and version next to the entrypoint: `backend/requirements.txt` and `backend/.python-version` (`3.12`). The local build log confirmed both. During a build, the Python builder writes `backend/pyproject.toml` and `backend/uv.lock` into the working tree. Do not commit those by accident. If the backend owner adopts `pyproject.toml`/`uv.lock`, they replace `requirements.txt`.
- Function settings belong inside the service: `services.api.functions["backend/main.py"]`. A top-level `functions`, `buildCommand`, `outputDirectory` or `framework` is invalid in services mode. The `backend/main.py` key was verified with a local `vercel build`: `maxDuration: 60` reached `.vc-config.json`, and `excludeFiles` removed frontend/docs/prompts/research from the bundle.
- `backend/content/**` (targets.json, cases, presets PNG+JSON) is bundled automatically and read-only, verified with a probe file in a local build. Read it relative to the module (`Path(__file__).parent / "content"`), not the CWD. Raw FITS, `research/`, `prompts/`, `docs/`, venvs and `node_modules` are excluded twice: by `.vercelignore` (deployment source) and by `excludeFiles` (function bundle).
- The frontend keeps the same-origin API base `/api/v1`. Services needs no `VITE_API_BASE` or CORS.

Python packaging and runtime constraints (Hobby/Pro, Fluid compute):

- Bundle: 500 MB uncompressed for Python (Large Functions beta up to 5 GB). Placeholder bundle measured with `VERCEL_ANALYZE_BUILD_OUTPUT=1`: 10.8 MB, of which `pydantic_core` is 4.8 MB. Astropy + NumPy + Pillow will add tens of MB, which is well within the limit. Re-measure after the real requirements land.
- Duration: 300 s default and the maximum on Hobby. Pro allows up to 800 s. We set 60 s so a stuck archive fetch fails fast. Raise it only with measured evidence.
- Memory: 2 GB / 1 vCPU default. Request and response bodies are capped at 4.5 MB, so keep PNG data URLs per frame small.
- Filesystem writes are temporary scratch space only. The default region is `iad1`.

Local verification without a Vercel login: `npx vercel@65.12.1 build` needs `uv` on PATH and a hand-written `.vercel/project.json` (`projectId`/`orgId` from above, `settings.framework: "services"`). It produces `.vercel/output` with per-service configs. `vercel dev --local` currently fails for the `api` service because its dev sync does not install `backend/requirements.txt` when the service root is `./`. For local development, run `uvicorn backend.main:app` plus `vite` with a `/api` proxy. `python -m backend.platform.deploy_check --app` checks rewrite order, entrypoint layout, raw-FITS hygiene and the JSON 404. The `deploy-check` GitHub workflow runs it without secrets.

### Historical preview evidence (placeholder shell)

Branch `codex/parallel-07-deployment` contains clearly labeled placeholder `frontend/` and `backend/main.py`. Vercel's Git integration built preview deployments for it, and the commit status was `success` ("Deployment has completed"). Commit `d842dab` built deployment `DvQaAHzpNw9fjEUfFL1QMosmpa6s`. Commit `5f54d60` added service `functions` (`maxDuration`/`excludeFiles`) and built deployment `EURzfquPhs9yQA6yYhpn7prwEgpE`, which shows the in-service `functions` key is accepted by the cloud build. The `deploy-check` workflow passed on `5f54d60`. Preview alias: `https://perigee-git-codex-parallel-07-deployment-sathviklokes-projects.vercel.app`.

Public access was **not** verified. Every path (`/`, `/api/v1/health`, `/api/v1/does-not-exist`, `/deploy-probe.txt`) returns `302` to `vercel.com/sso-api` with "Protected by Vercel Authentication". Preview deployments are behind Deployment Protection, so an unauthenticated agent cannot observe the response bodies. Sathvik or Suhrit must open the URLs while logged in, or use `vercel curl <url>` from an authenticated CLI, and record each status and content type here. Expected results:

- `/` and `/some/client/route`: `200 text/html` with the placeholder page
- `/api/v1/health`: `200 application/json` with `{"status":"ok","placeholder":true,...}`
- `/api/v1/does-not-exist`: `404 application/json` with `{"detail":"Not Found"}`
- `/deploy-probe.txt`: `200 text/plain`

### Historical hosted Preview verification (integrated app)

**Authenticated check (Codex, through the connected Vercel fetch tool, 2026-11-14 22:18Z).** No secret values were read or set.
- Deployment `dpl_Fo2Vz63JvLSM8HpSHRZeu9DYHDZx`, URL `https://perigee-57upr0z5p-sathviklokes-projects.vercel.app`, commit `bc03f40`.
- `GET /`: `200` HTML with the Perigee Vite assets.
- `GET /api/v1/health`: `200 application/json`. It reports `status: degraded`, `capabilities.search: false`, `frame: false`, `token_signing: missing`, and the processor-A adapter present.
- `GET /api/v1/cases/fair_comparison`: `200` JSON with the accepted revised case text and five limitations.

What this shows: hosted routing, Python service startup, the catalog and case endpoints work on Vercel. Live search and frame processing are switched off **only** because `PERIGEE_TOKEN_SECRET` is not configured. That matches the local production-mode check: with `VERCEL_ENV=production` and no secret, health is `degraded` with `token_signing: missing`; with a ≥32-byte secret it is `ok` with `token_signing: env`.

What it does **not** show: logged-out (judge) access, or end-to-end browser behaviour on a hosted URL.

**Logged-out check (coordinator, 2026-11-14 ~22:20Z).** These preview and team aliases, and only these, returned `302` to `vercel.com/sso-api` (Vercel Authentication):
- the branch preview alias `https://perigee-git-claude-perigee-integration-sathviklokes-projects.vercel.app/`, and the same host at `/api/v1/health`;
- the team alias `https://perigee-sathviklokes-projects.vercel.app/`.

The team alias turned out **not** to be the production domain (see below).

**Production domain (2026-11-14 ~23:45Z).**
- **Registered domain.** The connected Vercel API (`list_project_domains`, project `prj_7JhA3Inkh0euYF4UVwhyDYJusAfQ`, team `team_blm7QlnXb2J53PuzDBnv9TcO`, `production=true`) returns exactly one verified domain: **`https://perigee-liard.vercel.app`**, with `gitBranch: null` and `redirect: null`. This is the project's registered production domain.
- **Not serving the app yet.** Unauthenticated requests to `/` and to `/api/v1/health`, with redirects not followed, both return **HTTP 404**. The coordinator's smoke check from a clean environment with only the declared smoke dependencies gives exit 1: not redirected to Vercel login, but every app check fails. Production builds from `main`, which has no app until PR #27 is merged.
- **Environment and repository.** The project has no environment variables (`filter_project_envs`, values not decrypted) and the repository has no Actions variables (`gh variable list`). The repository is **PRIVATE** and its default branch is `main`.

`https://github.com/sathvikloke/perigee` and the app footer link `…/blob/main/docs/AI_USE.md` both return `404` (private repository; `AI_USE.md` is not on `main` yet).

GitHub commit statuses show the Vercel Preview build `success` for integration pushes (for example `ebdc0a0`).

**Signing on hosted Preview (review D3).** Hosted Preview now refuses the public development secret exactly as Production does:
- `PERIGEE_DEV_MODE=1` on Preview gives `token_signing: dev_mode_refused`;
- the dev value supplied as `PERIGEE_TOKEN_SECRET` gives `dev_secret_refused`.

A Preview therefore needs a real `PERIGEE_TOKEN_SECRET` for search and frames, just like Production. Local development (`uvicorn` or `vercel dev`, with `PERIGEE_DEV_MODE=1`) is unchanged.

**Never present `https://perigee.vercel.app` as Perigee.** It is an unrelated third-party app.

### Release configuration completed

With Sathvik's explicit publication approval, Codex made the repository public, configured separate production/preview signing secrets, set `PERIGEE_PUBLIC_URL`, preserved Standard Protection, and merged PR #27. The production smoke result is above.

For a subsequent release:

1. Review the candidate and its checks; preserve the last working deployment while checking its replacement.
2. Set any changed environment variables before triggering the build. Environment changes require a new deployment to take effect.
3. Merge the reviewed commit into `main` and verify the actual production deployment's commit and `READY` state.
4. Run `python -m backend.platform.smoke --base https://perigee-liard.vercel.app` without a bypass, or dispatch `release-smoke.yml` on `main` with that origin and `live=true`.
5. Exercise a curated investigation, live search, saved notebook/reopen, JSON export and print on the production domain. Record outcomes and remaining external limitations.

The API bounds each request; it has no global application rate limiter. An optional Vercel Firewall rule was not enabled as part of publication.

### Two-project fallback (documented, not created)

Use this only if Services blocks a deploy for more than 30 minutes. Services built successfully on the first push, so the fallback is not needed now. Steps:

1. The existing `perigee` project gets Root Directory `frontend`, the Vite preset and env `VITE_API_BASE=https://<api-project>.vercel.app/api/v1` (a public origin, not a secret). Remove `services` from `vercel.json`, or move the frontend's own SPA rewrite into `frontend/vercel.json`.
2. A new `perigee-api` project, created by Sathvik only, gets Root Directory `.` with `[tool.vercel] entrypoint = "backend.main:app"` in a root `pyproject.toml`, the FastAPI preset and `PERIGEE_TOKEN_SECRET`.
3. FastAPI adds `CORSMiddleware` allowing only the frontend production origin, plus the preview pattern if needed. Verify CORS from the deployed frontend. The frontend API client reads `import.meta.env.VITE_API_BASE ?? "/api/v1"`.

## Release smoke check (Suhrit, PR #34; hardened in review)

One command checks a deployment the way a judge reaches it:

```bash
python -m backend.platform.smoke --base https://<deployment-host>
```

It checks, in order:
- logged-out access;
- `/` plus three deep links return the SPA;
- `/api/v1/health` is JSON with `token_signing: "env"` and `status: "ok"`;
- five presets, and Barnard's Star frames, whose first image asset is a PNG that decodes;
- the `fair_comparison` case, with its limitations;
- JSON 404s for unknown `/api` paths and a traversal attempt;
- a **non-preset** search (Orion Nebula, 83.822, −5.391). It must return at least one observation with a frame token; an empty result is a FAIL, not a skip. One frame from it is then processed, and its image must decode as a PNG.

Exit codes:
- `0`: pass.
- `1`: app or config defect. This includes invalid JSON, network errors and timeouts, which are reported as FAIL rows, never a traceback.
- `2`: access restricted by Deployment Protection. This is not a code failure.

Options and safeguards:
- `--base` must be an https origin with no path. http is accepted only for loopback, for local runs.
- `perigee.vercel.app` (an unrelated app) is refused in any spelling: case, trailing dot or port.
- For a protected preview, add `--bypass` with `VERCEL_AUTOMATION_BYPASS_SECRET` in the environment. The header goes **only** to the `--base` origin, never to another host such as an absolute asset URL. A bypassed run proves the app works, not judge access.
- `--no-live` skips the archive calls.

Tests: `backend/tests/platform/test_platform_smoke.py` (33, offline, at the release candidate).

Runs of the merged script (coordinator, integration after `d859e62`):
- **Local:** Vite serving the frontend, proxying to uvicorn with a throwaway local signing value. **PASS 20/20**: live search `ready` with 377 matches, and a frame `2025W36_2B_0338_1` that returned 200 with a 10 KB PNG that decodes.
- **Logged-out Preview:** `perigee-git-claude-perigee-integration-sathviklokes-projects.vercel.app` gives **exit 2** (Vercel Authentication).
- **Failure paths:**
  - `no-such-host.invalid` gives exit 1, "could not be reached".
  - `https://PERIGEE.vercel.app.` and `https://perigee.vercel.app:443` are refused with exit 1.
  - With the API stopped behind a live frontend, the run gives exit 1 with FAIL rows and no traceback.

**Earlier report, superseded.** Suhrit's run on `ebdc0a0` (Vercel deployment `6qeSegbawa4qLbyJbmuvmo6VAKyw`, READY): logged out he got exit 2. The same commit run locally passed every API check (search `ready`, 377 matches in 1.6 s; frame `2025W36_2B_0338_1` 200 in 3.0 s, 18 KB). He recorded deployed responses as "not yet verified". That has since changed: Codex's authenticated check of `bc03f40` (see **Hosted Preview verification** above) confirmed the hosted app HTML, health JSON (`token_signing: missing`) and the case endpoint. Judge (logged-out) access was unverified at that point. See the current release above.

Release details from Suhrit's report, kept alongside the numbered **Owner actions** above:
- Environment variable changes apply only to new deployments. Redeploy after setting `PERIGEE_TOKEN_SECRET`, then confirm that health shows `token_signing: "env"`.
- To verify a protected preview before merge, have an owner run the smoke check with `--bypass`. Adding Suhrit to `sathviklokes-projects` is not an option on Hobby: Vercel requires Pro for team members. Making the repo public (owner action 1) also lets Vercel build his commits.
- The production domain registered on the project is `https://perigee-liard.vercel.app`. That domain, not a preview alias, the team alias or `perigee.vercel.app`, is the judge URL. After release, run the smoke check **without** `--bypass` and record the URL, commit and output here.
- Risk: on a Hobby team, Vercel can block preview builds of private-repo commits authored by non-members. A teammate's PR that shows "blocked" instead of a build is an access issue, not a code failure.

### Production-mode dress rehearsal (Suhrit, `8f577fa`, 2026-11-14 ~23:25Z): LOCAL evidence only

This ran on Suhrit's machine with production settings. It is **not** a hosted production result: no Vercel production deployment of the app exists yet.

Setup:
- `VERCEL_ENV=production`, plus a throwaway local `PERIGEE_TOKEN_SECRET` (48 random bytes, never written down).
- `uvicorn backend.main:app`, with `vite preview` of the production frontend build proxying `/api`.
- Windows 11, Python 3.12.10.

Results:
- **Smoke: PASS 20/20, exit 0.**
  - Health `ok`, with `token_signing: env`.
  - Live non-preset search: `ready`, 377 matches, 7.8 s.
  - Frame `2025W36_2B_0338_1`: 200 in 4.7 s, 18 KB.
- **Unit tests:**
  - Backend: 311 pass. The only failures are 2 symlink tests that need Windows admin rights. The vercelignore regression test now passes on Windows.
  - Frontend: vitest 121/121 pass. The build is 102 KB gzipped JS.
- **In the browser:**
  - Barnard's Star loads 6 images, all decoded, with no console errors.
  - The evidence card autosaves to `perigee.evidence.v1` with the claim, uncertainty, observation IDs, dates, wavelengths, flags and IRSA source URLs.
  - The deep link `/?view=query&ra=83.822&dec=-5.391&fov=6` runs the search. It returned 24 of 237 matches in time order, and frames loaded progressively.
- **Live archive behavior seen:**
  - At limit 24, IRSA's QR3 query did not answer within the search budget. The UI showed honest **partial** results: "spherex_qr3 could not be searched".
  - One frame got an IRSA `502 UPSTREAM_UNAVAILABLE` and the rest continued.
  - These are archive slowdowns, not app defects. Expect them during the demo too, and prefer a preset for the live walk-through.

### Automatic post-deploy smoke (`.github/workflows/release-smoke.yml`)

Suhrit's workflow, PR #36, hardened in review. It runs `python -m backend.platform.smoke` logged out, with no bypass and no secrets. The output goes to the run summary: exit 2 means an access setting, exit 1 means an app defect. The summary names the origin tested, the commit of the smoke harness, and, for a deployment event, the commit and environment the event reported. It states that it did **not** verify that the origin was serving that commit.

**Triggers, as they actually behave:**

- **`deployment_status` (automatic).**
  - **What GitHub does.** GitHub fires this event for GitHub *Deployments*, and runs it with `GITHUB_SHA`/`GITHUB_REF` set to the deployed commit/ref. The event has no default-branch requirement ([GitHub docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#deployment_status)).
  - **Filter.** The job runs only for `state: success` and the `Production` environment. It tests the stable `PERIGEE_PUBLIC_URL`, not the URL in the payload. It checks out the smoke harness from the default branch with `persist-credentials: false`; it does not check out the payload's commit.
  - **Status here: has never fired, unverified.** As of 2026-11-14, `GET /repos/sathvikloke/perigee/deployments` returns `[]`. Vercel posts commit statuses for this repository but has created no GitHub Deployments, so nothing can trigger this path. It fires only if Vercel starts creating GitHub Deployments for production. Vercel also documents `repository_dispatch` events (for example `vercel.deployment.ready`) as an alternative; they are not configured or tested here.
  - **Before the variable is set,** a run is skipped with a notice.
- **`workflow_dispatch` (manual).** Actions → release-smoke → Run workflow, with any https origin. This is now available on `main` and was successfully exercised in run `43658316997` with `live=true`.
- **Without GitHub Actions:** `python -m backend.platform.smoke --base https://perigee-liard.vercel.app`, from any checkout. It needs only `pip install -r backend/platform/requirements-smoke.txt` (`httpx==0.28.1`, `pillow==13.0.0`, the same pins as `backend/requirements.txt`). That manual path is supported now.

**CI hygiene:**
- `actions/checkout`, `actions/setup-python` and `actions/setup-node` are pinned to the commit SHAs of v4.2.2, v5.6.0 and v4.4.0 in both workflows, resolved through the GitHub API on 2026-11-14.
- Both workflows check out with `persist-credentials: false` and have `contents: read` only.
- Payload and input values reach shell steps only through `env`, never inline.
- Tests in `test_platform_smoke.py` enforce the SHA pins and the dependency pins.
- `actionlint` 1.7.7 reports no findings for either workflow.

**Historical clean-environment check (coordinator, 2026-11-14, before release).** In a new virtualenv containing only `requirements-smoke.txt`, `import fastapi` fails, which confirms the environment is minimal.
- **Local stack:** with `VERCEL_ENV=production`, a throwaway local secret, and Vite proxying to uvicorn, the smoke check gives **PASS 20/20, exit 0**. Both PNG checks decoded through Pillow; the live frame was 10 117 B. This is local evidence.
- **`https://perigee-liard.vercel.app`:** exit 1, because the domain returns 404, as noted above.

## Configuration and release checks

Use backend-only environment configuration for the frame-token signing secret. Keep an example configuration containing names and descriptions, never real values. Preview and production environments may differ; test the environment intended for the public demonstration. Use supported Python and package versions, and commit the appropriate dependency lockfiles through their owners.

Treat local filesystem writes as temporary request scratch space. Small curated assets can be packaged read-only. Optional caching must tolerate a miss and must not become the only copy of user-authored evidence or job state. Browser evidence cards remain local in this version.

Before marking a release ready, test the public URL without a team login, including a curated investigation, a non-preset coordinate search, a frame result and an evidence export. Preserve the last verified working deployment while checking its replacement. Record the actual deployment URL, commit and remaining limitations here after implementation.

Official references: [Vercel Services](https://vercel.com/docs/services), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [Functions limits](https://vercel.com/docs/functions/limitations), [Deployment Protection](https://vercel.com/docs/deployment-protection).
