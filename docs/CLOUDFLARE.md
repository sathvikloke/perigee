# Perigee on Cloudflare Workers (static assets + API router)

This is a release candidate for hosting Perigee on Cloudflare, prompted by the Vercel deployment quota. **Nothing here deploys anything**: the deployment owner runs Wrangler. The planned public URL is `https://perigee.lokesathvik.workers.dev`; it must be verified after deploy.

## What runs where

| Path | Served by | Notes |
|---|---|---|
| `/`, client routes, `/assets/*`, `/favicon.svg`, `/demo/perigee-demo.pdf` | Workers static assets (a copy of `frontend/dist`) | SPA fallback (`not_found_handling: single-page-application`) |
| `GET /api/v1/presets` | Worker, from the exported catalog | Same JSON as FastAPI |
| `GET /api/v1/cases/{case_id}` | Worker, exported | Unknown case gives 404 `CASE_NOT_FOUND` with `available_case_ids` |
| `GET /api/v1/presets/{id}/frames[?case_id=]` | Worker, exported | 5 default lists plus the valid case lists (`epsilon_indi_b`/`fair_comparison`, `barnards_star`/`moving_neighbor`). Unknown preset gives 404 `PRESET_NOT_FOUND`; unknown or empty `case_id` gives 404 `CASE_NOT_FOUND`; if `case_id` repeats, the last value wins (all as in FastAPI) |
| `GET /api/v1/assets/{asset_id}` | Worker, exported bytes | 952 IDs (574 canonical, 378 processor aliases). Exact bytes. Each response is SHA-256-checked again before serving. Same `Content-Type`, `ETag`, `Cache-Control` and `nosniff` as FastAPI |
| `GET /api/v1/health`, `POST /api/v1/search`, `POST /api/v1/frame` | **Proxied** to the fixed origin `https://perigee-liard.vercel.app` (the existing public Vercel Python API) | Live archive search and FITS processing stay in Python. Nothing is ported to WASM |
| anything else under `/api` | Worker | JSON 404 `NOT_FOUND`, never the SPA's HTML |

`wrangler.jsonc` sets `run_worker_first: ["/api", "/api/*"]`, so every API path goes through `cloudflare/src/app.js`. The exported files under `build/public/api/` are reachable **only** through the Worker's routing; for example, `/api/__perigee/catalog-manifest.json` and `/api/v1/presets.json` return JSON 404s. `preview_urls: false` keeps unreleased Worker versions private. `workers_dev: true` serves the `*.workers.dev` URL. `account_id`, routes and custom domains are left for the deployment owner to add.

### Proxy rules (`cloudflare/src/app.js`)

- **Destination:** only the three paths above, to one hard-coded origin. The incoming query string, `Host` and every other request header are dropped. Forwarded headers are only `content-type` (for POST), `accept`, `user-agent: perigee-cloudflare-proxy`, and a validated `x-request-id`. No `Cookie`, `Authorization`, `x-vercel-protection-bypass`, `x-forwarded-*` or `cf-*` header is forwarded.
- **Methods:** `GET` for health, `POST` for search and frame. Any other method gets a local 405 `METHOD_NOT_ALLOWED` and the upstream is never contacted.
- **Redirects:** `redirect: "manual"`, so redirects are never followed. A 3xx answer from upstream becomes a 502 `UPSTREAM_UNAVAILABLE`, and its `Location` is not passed on.
- **Request bodies:** at most 64 KiB, otherwise 413 `INVALID_REQUEST`. Real search and frame bodies are under 2 KiB.
- **Upstream bodies:** at most 8 MiB (Vercel caps responses at 4.5 MB). A larger body, or a non-JSON answer, becomes a 502 envelope.
- **Timeout:** 70 s (the Python function's `maxDuration` is 60 s). On timeout the response is 504 `UPSTREAM_TIMEOUT`; on a transport error it is 502 `UPSTREAM_UNAVAILABLE`, both `retryable: true`, in the API's usual error envelope.
- **Passthrough:** upstream status codes (for example 410 `TOKEN_EXPIRED`, 422, 429, 503) and the `content-type`, `cache-control`, `retry-after` and `x-request-id` headers pass through unchanged. `set-cookie` does not.

### Differences from the Vercel deployment (intentional)

- `/api/v1/docs` and `/api/v1/openapi.json` are not exposed on Cloudflare: they return a JSON 404. They remain available on the Python origin.
- Proxied request bodies over 64 KiB are refused with 413. The Python API has no explicit body cap.
- Catalog JSON is sent with `Cache-Control: public, max-age=0, must-revalidate`, the value Vercel adds in production.
- A path with a double-encoded slash (`%252F`) is a JSON 404 in both, but the error code may be `NOT_FOUND` or `ASSET_NOT_FOUND`.

## Build

Run from the repository root. You need Python with `backend/requirements.txt` (for example the repo `.venv`; the research venv lacks pydantic) and Node 18 or later.

```bash
(cd frontend && npm ci && npm run build)        # frontend/dist, including demo/perigee-demo.pdf
.venv/bin/python cloudflare/build.py             # writes cloudflare/build/ (git-ignored)
```

`cloudflare/build.py` uses `backend.platform.catalog.CatalogStore` directly. `list_presets()`, `get_case()` and `get_frames()` are serialized with `model_dump(mode="json")`, and asset bytes come from `AssetIndex.read()`, which re-checks the SHA-256. The script then:
- checks every exported asset's hash again;
- checks that every frame's `image.src` and `flag_image.src` resolve;
- refuses to export raw FITS;
- refuses to clear any directory that is not a previous build;
- writes `cloudflare/build/build-info.json` with the source commit, content version, deck hash and counts.

Build on `a8608c6`: content `targets-2026-11-15a` (with the corrected WISE 0855 source label); 5 presets, 2 cases, 2 case frame sets and 952 assets (8.1 MB); 968 static files and 14 MB in total. That should be within the Workers static-assets limits (20,000 files, 25 MiB per file, from memory; not re-checked against the current Cloudflare docs): confirm them for the account's plan.

## Tests

Run in this order:

```bash
.venv/bin/python -m pytest -q cloudflare/tests    # export == FastAPI (TestClient); writes build/route-expectations.json
node --test cloudflare/test/                      # Worker logic against the real build
```

- **`cloudflare/tests/test_export_parity.py`** (7 tests). It builds into a temporary directory and compares, against the real FastAPI app:
  - the presets document;
  - both cases;
  - all 5 + 2 frame documents;
  - all 952 assets: bytes, SHA-256, `Content-Type`, `ETag` and cache policy.

  It also checks that all 34 WISE 0855 records carry the corrected label. It records FastAPI's status, error code and redirect for 58 normal and hostile requests: traversal (`..%2F`, `%2e%2e%2f`), `__proto__`/`constructor` IDs, NUL and invalid escapes, repeated or empty `case_id`, wrong methods, HEAD, trailing slashes and internal paths.
- **`cloudflare/test/worker.test.mjs`** (15 tests, Node's built-in runner, no dependencies). It covers:
  - replaying all 58 recorded FastAPI answers through the Worker;
  - exact catalog bodies;
  - every asset's bytes, type, ETag and cache policy;
  - refusing a tampered asset;
  - a missing manifest returning JSON 503;
  - the proxy: fixed destination, query and credential stripping, `redirect: "manual"`, passthrough of 3xx/HTML/status/`Retry-After`, timeouts, transport errors, body caps, and methods that never reach upstream;
  - the entry module exporting only `default`;
  - the default `fetch` being called unbound.

## Local smoke (live, `wrangler dev`)

```bash
(cd cloudflare && npx wrangler@4.162.0 dev --port 8799 --ip 127.0.0.1)
.venv/bin/python cloudflare/tests/smoke_local.py --base http://127.0.0.1:8799     # static + catalog + route parity over HTTP
.venv/bin/python -m backend.platform.smoke --base http://127.0.0.1:8799           # release smoke incl. live search + frame via the proxy
```

Results on 2026-11-15 (build of `a8608c6` plus this branch):
- **`smoke_local.py`: PASS 23/23.**
  - The SPA, deep links, the deck PDF (`application/pdf`, 2,366,246 B, identical bytes), the favicon and the JS bundle all load.
  - All 10 catalog documents equal the export, and the canonical and alias assets are served correctly.
  - All 58 recorded FastAPI answers match over real HTTP, and the internal paths return JSON 404s.
- **`backend.platform.smoke`: PASS 20/20.** Health came through the proxy from production (`status: ok`, `token_signing: env`). A live Orion search returned 377 matches, and a frame returned 200 with a PNG that decodes.
- **Two runtime-only defects were found by these runs and fixed before the PR:**
  - The entry module may not have named exports (workerd treats them as entrypoints), so the logic moved to `src/app.js`.
  - The global `fetch` must be called unbound ("Illegal invocation"). Both now have regression tests.

## Deploy (deployment owner)

```bash
(cd frontend && npm ci && npm run build) && .venv/bin/python cloudflare/build.py
.venv/bin/python -m pytest -q cloudflare/tests && node --test cloudflare/test/
cd cloudflare && npx wrangler@4.162.0 deploy          # account_id via wrangler.jsonc or CLOUDFLARE_ACCOUNT_ID
```

Then verify the deployed origin logged out:

```bash
.venv/bin/python cloudflare/tests/smoke_local.py --base https://perigee.lokesathvik.workers.dev
.venv/bin/python -m backend.platform.smoke --base https://perigee.lokesathvik.workers.dev
```

## Limits and dependencies

- **The live path depends on the Vercel deployment.** If `https://perigee-liard.vercel.app` stops serving, live search and frames show the app's honest "archive unavailable" states (502 or 504 envelopes). The two curated investigations, all presets, assets, the evidence notebook and export, and the deck keep working, because they make no upstream calls.
- **Content changes need a rebuild and redeploy** (`build.py`, then `wrangler deploy`). The Worker serves only what was exported.
- **No secrets are needed on Cloudflare.** Frame-token signing stays on the Python origin, which issues and verifies the tokens.
