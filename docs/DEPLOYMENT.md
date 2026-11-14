# Perigee deployment handoff

## Current setup

The Vercel project `perigee` is connected to `https://github.com/sathvikloke/perigee` and builds the implemented app: a React/Vite `web` service and a FastAPI `api` service from `vercel.json`. The app lives on `claude/perigee-integration` (draft PR #27 into `main`). `main` has no app until PR #27 is merged, so production (which builds from `main`) does not serve Perigee yet.

Every push to `claude/perigee-integration` builds a Preview. The current state of the hosted Preview, and what still blocks judges, is under **Hosted Preview verification** below.

- Dashboard: https://vercel.com/sathviklokes-projects/perigee
- Project: `perigee`
- Project ID: `prj_7JhA3Inkh0euYF4UVwhyDYJusAfQ`
- Team: `sathviklokes-projects`
- Team ID: `team_blm7QlnXb2J53PuzDBnv9TcO`
- Repository: https://github.com/sathvikloke/perigee
- Intended production branch: `main`; verify the actual Git and build settings before the first deployment.
- Deployment owner: Suhrit, coordinating with Akshobya and Aditya.

These IDs identify resources; they are not credentials. Do not put tokens or signing secrets in this file.

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

### Preview evidence (placeholder shell)

Branch `codex/parallel-07-deployment` contains clearly labeled placeholder `frontend/` and `backend/main.py`. Vercel's Git integration built preview deployments for it, and the commit status was `success` ("Deployment has completed"). Commit `d842dab` built deployment `DvQaAHzpNw9fjEUfFL1QMosmpa6s`. Commit `5f54d60` added service `functions` (`maxDuration`/`excludeFiles`) and built deployment `EURzfquPhs9yQA6yYhpn7prwEgpE`, which shows the in-service `functions` key is accepted by the cloud build. The `deploy-check` workflow passed on `5f54d60`. Preview alias: `https://perigee-git-codex-parallel-07-deployment-sathviklokes-projects.vercel.app`.

Public access was **not** verified. Every path (`/`, `/api/v1/health`, `/api/v1/does-not-exist`, `/deploy-probe.txt`) returns `302` to `vercel.com/sso-api` with "Protected by Vercel Authentication". Preview deployments are behind Deployment Protection, so an unauthenticated agent cannot observe the response bodies. Sathvik or Suhrit must open the URLs while logged in, or use `vercel curl <url>` from an authenticated CLI, and record each status and content type here. Expected results:

- `/` and `/some/client/route`: `200 text/html` with the placeholder page
- `/api/v1/health`: `200 application/json` with `{"status":"ok","placeholder":true,...}`
- `/api/v1/does-not-exist`: `404 application/json` with `{"detail":"Not Found"}`
- `/deploy-probe.txt`: `200 text/plain`

### Hosted Preview verification (integrated app)

**Authenticated check (Codex, through the connected Vercel fetch tool, 2026-11-14 22:18Z).** No secret values were read or set.
- Deployment `dpl_Fo2Vz63JvLSM8HpSHRZeu9DYHDZx`, URL `https://perigee-57upr0z5p-sathviklokes-projects.vercel.app`, commit `bc03f40`.
- `GET /`: `200` HTML with the Perigee Vite assets.
- `GET /api/v1/health`: `200 application/json`. It reports `status: degraded`, `capabilities.search: false`, `frame: false`, `token_signing: missing`, and the processor-A adapter present.
- `GET /api/v1/cases/fair_comparison`: `200` JSON with the accepted revised case text and five limitations.

What this shows: hosted routing, Python service startup, the catalog and case endpoints work on Vercel. Live search and frame processing are switched off **only** because `PERIGEE_TOKEN_SECRET` is not configured. That matches the local production-mode check: with `VERCEL_ENV=production` and no secret, health is `degraded` with `token_signing: missing`; with a ≥32-byte secret it is `ok` with `token_signing: env`.

What it does **not** show: logged-out (judge) access, or end-to-end browser behaviour on a hosted URL.

**Logged-out check (coordinator, 2026-11-14 ~22:20Z).** Every path below returns `302` to `vercel.com/sso-api` (Vercel Authentication):
- `https://perigee-git-claude-perigee-integration-sathviklokes-projects.vercel.app/`
- the same host at `/api/v1/health`
- `https://perigee-sathviklokes-projects.vercel.app/`

`https://github.com/sathvikloke/perigee` and the app footer link `…/blob/main/docs/AI_USE.md` both return `404` (private repository; `AI_USE.md` is not on `main` yet).

GitHub commit statuses show the Vercel Preview build `success` for integration pushes (for example `ebdc0a0`).

**Signing on hosted Preview (review D3).** Hosted Preview now refuses the public development secret exactly as Production does:
- `PERIGEE_DEV_MODE=1` on Preview gives `token_signing: dev_mode_refused`;
- the dev value supplied as `PERIGEE_TOKEN_SECRET` gives `dev_secret_refused`.

A Preview therefore needs a real `PERIGEE_TOKEN_SECRET` for search and frames, just like Production. Local development (`uvicorn` or `vercel dev`, with `PERIGEE_DEV_MODE=1`) is unchanged.

**Never present `https://perigee.vercel.app` as Perigee.** It is an unrelated third-party app.

### Owner actions (not done by agents)

1. **Make the code public:** change `sathvikloke/perigee` to public, or publish a public mirror. Then `https://github.com/sathvikloke/perigee` and the footer link `https://github.com/sathvikloke/perigee/blob/main/docs/AI_USE.md` resolve once PR #27 is merged.
2. **Merge draft PR #27** (`claude/perigee-integration` → `main`) after review, so production builds the app from `main`.
3. **Set `PERIGEE_TOKEN_SECRET`** as a sensitive variable for Production, and for Preview if previews should run live search. Use at least 32 random bytes and never the development value. Leave `PERIGEE_DEV_MODE` unset on Vercel. `/api/v1/health` reports only `token_signing` (`env` / `missing` / `too_short` / `dev_secret_refused` / `dev_mode_refused`), never the value.
4. **Judge-facing access:** turn off Vercel Authentication for **production only** (Project Settings → Deployment Protection; Standard Protection keeps previews protected).
5. **Optional (review D2):** add a Vercel Firewall rate-limit rule on `/api/v1/frame` and `/api/v1/search` for the judging window. The API has per-request bounds but no global limiter.
6. **Verify logged out**, in a private window, on the production domain `https://perigee-sathviklokes-projects.vercel.app/` (or the domain Vercel assigns to production):
   - `/` returns 200 HTML;
   - `/api/v1/health` returns 200 JSON with `status: ok` and `token_signing: env`;
   - an unknown `/api/v1/x` returns a JSON 404;
   - a live search at 330.84, −56.786 returns frames.

   Then rerun `qa/fresh-pass` steps 1–8 there and record the deployed commit. `qa/regression/run.sh --live <production base>` automates part of this.

### Two-project fallback (documented, not created)

Use this only if Services blocks a deploy for more than 30 minutes. Services built successfully on the first push, so the fallback is not needed now. Steps:

1. The existing `perigee` project gets Root Directory `frontend`, the Vite preset and env `VITE_API_BASE=https://<api-project>.vercel.app/api/v1` (a public origin, not a secret). Remove `services` from `vercel.json`, or move the frontend's own SPA rewrite into `frontend/vercel.json`.
2. A new `perigee-api` project, created by Sathvik only, gets Root Directory `.` with `[tool.vercel] entrypoint = "backend.main:app"` in a root `pyproject.toml`, the FastAPI preset and `PERIGEE_TOKEN_SECRET`.
3. FastAPI adds `CORSMiddleware` allowing only the frontend production origin, plus the preview pattern if needed. Verify CORS from the deployed frontend. The frontend API client reads `import.meta.env.VITE_API_BASE ?? "/api/v1"`.

## Release smoke check and current status (Suhrit, 2026-11-14)

One command checks a deployment the way a judge reaches it:

```bash
python -m backend.platform.smoke --base https://<deployment-host>
```

It checks, in order: logged-out access; `/` plus three deep links return the SPA; `/api/v1/health` is JSON with `token_signing: "env"`; five presets; Barnard's Star frames; the first image asset is a real PNG; `fair_comparison` case; JSON 404s for unknown `/api` paths and a traversal attempt; and a **non-preset** search (Orion Nebula, 83.822, −5.391), followed by one processed frame. Exit `0` = pass, `1` = app/config defect, `2` = access restricted by Deployment Protection (not a code failure). For a protected preview, add `--bypass` with `VERCEL_AUTOMATION_BYPASS_SECRET` in the environment. That proves the app works, not judge access. `--no-live` skips the archive calls. The script refuses `perigee.vercel.app` (unrelated app).

Status on integration commit `ebdc0a0` (PR #27):

| What | Result |
|---|---|
| Vercel build | READY, deployment `6qeSegbawa4qLbyJbmuvmo6VAKyw`, `check` workflow passed |
| Preview URL | `https://perigee-git-claude-perigee-integration-sathviklokes-projects.vercel.app` |
| Logged-out access | **Restricted**: every path, including `/api/*`, returns `302` to `vercel.com/sso-api`. Smoke exit `2`. |
| Deployed responses | **Not yet verified.** Needs a team login or bypass secret. |
| Same commit, local `uvicorn backend.main:app` | All API checks pass. Search `ready`, 377 matches DR1+QR3, 1.6 s. Frame `2025W36_2B_0338_1` 200 in 3.0 s, 18 KB. Asset PNG with `immutable` cache. JSON 404s. `deploy_check --app` ok. |

Owner actions for release (Sathvik; agents do not change these):

1. Set `PERIGEE_TOKEN_SECRET` as a Sensitive env var (≥ 32 bytes, random) for **Preview and Production**. Leave `PERIGEE_DEV_MODE` unset. Redeploy, because env changes apply to new deployments only. Health must then show `token_signing: "env"`. `missing` means search and frame are disabled.
2. Give Suhrit team access to `sathviklokes-projects`, or run the smoke check yourself with `--bypass`, so the preview is verified before merge.
3. Merge PR #27 to `main` after the preview passes.
4. Deployment Protection: switch to **Standard Protection**, which keeps previews protected and leaves production domains public, or turn it off for this project only.
5. Record the production domain shown on the project's Domains page. That domain, not a preview and not `perigee.vercel.app`, is the judge URL. Then run the smoke check without `--bypass` and record the URL, commit and output here.

Risk: on a Hobby team, Vercel can block preview builds of private-repo commits authored by non-members. If a teammate's PR shows "blocked" instead of a build, that is an access issue, not a code failure.

## Configuration and release checks

Use backend-only environment configuration for the frame-token signing secret. Keep an example configuration containing names and descriptions, never real values. Preview and production environments may differ; test the environment intended for the public demonstration. Use supported Python and package versions, and commit the appropriate dependency lockfiles through their owners.

Treat local filesystem writes as temporary request scratch space. Small curated assets can be packaged read-only. Optional caching must tolerate a miss and must not become the only copy of user-authored evidence or job state. Browser evidence cards remain local in this version.

Before marking a release ready, test the public URL without a team login, including a curated investigation, a non-preset coordinate search, a frame result and an evidence export. Preserve the last verified working deployment while checking its replacement. Record the actual deployment URL, commit and remaining limitations here after implementation.

Official references: [Vercel Services](https://vercel.com/docs/services), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [Functions limits](https://vercel.com/docs/functions/limitations), [Deployment Protection](https://vercel.com/docs/deployment-protection).
