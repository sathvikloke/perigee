# Perigee on Cloudflare Workers (static assets + API router)

**Public release:** https://perigee.lokesathvik.workers.dev. The deployment owner verified the final bundle on 2026-11-15; see [deployment identity](DEPLOYMENT.md) and [public checks](../qa/final-investigation/README.md). The earlier local candidate results below are retained with their build/date.

## What runs where

| Path | Served by | Notes |
|---|---|---|
| `/`, client routes, `/assets/*`, `/favicon.svg`, `/demo/perigee-demo.pdf` | Workers static assets (a copy of `frontend/dist`) | SPA fallback (`not_found_handling: single-page-application`) |
| `GET /api/v1/presets` | Worker, from the exported catalog | Same JSON as FastAPI |
| `GET /api/v1/cases/{case_id}` | Worker, exported | Unknown case gives 404 `CASE_NOT_FOUND` with `available_case_ids` |
| `GET /api/v1/presets/{id}/frames[?case_id=]` | Worker, exported | 5 default lists plus the valid case lists (`epsilon_indi_b`/`fair_comparison`, `barnards_star`/`moving_neighbor`, `wise_0855`/`wise_0855_quality_trap`). Unknown preset gives 404 `PRESET_NOT_FOUND`; unknown or empty `case_id` gives 404 `CASE_NOT_FOUND`; if `case_id` repeats, the last value wins (all as in FastAPI) |
| `GET /api/v1/assets/{asset_id}` | Worker, exported bytes | 968 IDs (584 canonical, 384 processor aliases). Exact bytes. Each response is SHA-256-checked again before serving. Same `Content-Type`, `ETag`, `Cache-Control` and `nosniff` as FastAPI |
| `GET /api/v1/health`, `POST /api/v1/search`, `POST /api/v1/frame` | **Proxied** to the fixed origin `https://perigee-liard.vercel.app` (the existing public Vercel Python API) | Live archive search and FITS processing stay in Python. Nothing is ported to WASM |
| anything else under `/api` | Worker | JSON 404 `NOT_FOUND`, never the SPA's HTML |

`wrangler.jsonc` sets `run_worker_first: ["/api", "/api/*"]`, so every API path goes through `cloudflare/src/app.js`. The exported files under `build/public/api/` are reachable **only** through the Worker's routing; for example, `/api/__perigee/catalog-manifest.json` and `/api/v1/presets.json` return JSON 404s. `preview_urls: false` keeps unreleased Worker versions private. `workers_dev: true` serves the `*.workers.dev` URL. The deployment account is set in `wrangler.jsonc`; no custom domain is configured.

### Proxy rules (`cloudflare/src/app.js`)

- **Destination:** only the three paths above, to one hard-coded origin. The incoming query string, `Host` and every other request header are dropped. Forwarded headers are only `content-type` (for POST), `accept`, `user-agent: perigee-cloudflare-proxy`, and a validated `x-request-id`. No `Cookie`, `Authorization`, `x-vercel-protection-bypass`, `x-forwarded-*` or `cf-*` header is forwarded.
- **Methods:** `GET` for health, `POST` for search and frame. Any other method gets a local 405 `METHOD_NOT_ALLOWED` and the upstream is never contacted.
- **Redirects:** `redirect: "manual"`, so redirects are never followed. A 3xx answer from upstream becomes a 502 `UPSTREAM_UNAVAILABLE`, and its `Location` is not passed on.
- **Request bodies:** at most 64 KiB, otherwise 413 `INVALID_REQUEST`. Real search and frame bodies are under 2 KiB.
- **Upstream bodies:** at most 8 MiB (Vercel caps responses at 4.5 MB). A larger body, a non-JSON content type, or a body labelled `application/json` that does not parse as JSON becomes a 502 `UPSTREAM_UNAVAILABLE` envelope (`retryable: true`). It is never passed on as a success or as an upstream error body.
- **Timeout:** 70 s (the Python function's `maxDuration` is 60 s). On timeout the response is 504 `UPSTREAM_TIMEOUT`; on a transport error it is 502 `UPSTREAM_UNAVAILABLE`, both `retryable: true`, in the API's usual error envelope.
- **Passthrough:** upstream status codes (for example 410 `TOKEN_EXPIRED`, 422, 429, 503) and the `content-type`, `cache-control`, `retry-after` and `x-request-id` headers pass through unchanged. `set-cookie` does not.

### Unusable bundled content (backend next pass, B1)

The Worker never answers a catalog route with content it cannot vouch for:
- **Manifest:** the route table (`/api/__perigee/catalog-manifest.json`) is parsed and structurally validated on first use. A missing, non-JSON or malformed manifest gives 503 `CONTENT_UNAVAILABLE` and is not cached, so the next request tries again.
- **Catalog documents:** each one is parsed and must have its response model's required shape. Presets need `schema_version`, `presets` and `count`; a case needs `case_id`, `title` and `target_id`; frames need `preset_id`, `status`, `frames` and `frame_count`. A document that comes back as HTML, invalid JSON or the wrong shape gives a JSON 503 `CONTENT_UNAVAILABLE`. Valid documents are still served byte-for-byte.
- **Asset binding:** if the static-assets binding throws while reading, the response is 503 `CONTENT_UNAVAILABLE`. A non-2xx answer, or bytes that fail the SHA-256 check, give 404 `ASSET_NOT_FOUND`, as the Python asset route does.
- **Last resort:** any unexpected error returns 500 `INTERNAL_ERROR` (`retryable: true`), the same as FastAPI's handler. Logs carry the error name and message only, never headers, cookies or tokens.

All of these keep the request ID and `Cache-Control: no-store`.

### Differences from the Vercel deployment

- On the deployed edge, Cloudflare converts the strong ETag to a weak ETag for compressed JSON. Decompressed bytes still match SHA-256; `Accept-Encoding: identity` preserves the strong ETag. [Cloudflare ETag documentation](https://developers.cloudflare.com/cache/reference/etag-headers/).
- An encoded NUL (`/api/v1/assets/x%00.png`) is rejected by Cloudflare with HTTP 400 HTML before the Worker runs. Ordinary unknown API routes still return JSON 404. The deployed smoke uses `--cloudflare-edge` to check these two narrow differences explicitly.
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

Build on `a8608c6`: content `targets-2026-11-15a` (with the corrected WISE 0855 source label); 5 presets, 2 cases, 2 case frame sets and 952 assets (8.1 MB); 968 static files and 14 MB in total. This fits Cloudflare's [documented static-asset limits](https://developers.cloudflare.com/workers/platform/limits/), verified 2026-11-15: 20,000 files on Free (100,000 on Paid), and 25 MiB per file.

## Tests

CI (`.github/workflows/ci.yml`, secret-free) runs the steps below on PRs that touch `backend/`, `frontend/`, `cloudflare/`, `tools/ingest/`, `science/reviews/acceptance/`, the Vercel config or the workflows, and on pushes to `main`:
- a backend job: `pytest backend`, with raw-data tests reported as skips;
- a frontend + Cloudflare job: typecheck, Vitest, build, then export, then `pytest cloudflare/tests`, then `node --test cloudflare/test/*.test.mjs`.

It makes no live archive calls and does not deploy.


Run in this order:

```bash
.venv/bin/python -m pytest -q cloudflare/tests    # export == FastAPI (TestClient); writes build/route-expectations.json
node --test cloudflare/test/*.test.mjs                      # Worker logic against the real build
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
.venv/bin/python -m pytest -q cloudflare/tests && node --test cloudflare/test/*.test.mjs
cd cloudflare && npx wrangler@4.162.0 deploy          # account_id via wrangler.jsonc or CLOUDFLARE_ACCOUNT_ID
```

Then verify the deployed origin logged out, **against the build you just deployed**:

```bash
.venv/bin/python cloudflare/tests/smoke_local.py --base https://perigee.lokesathvik.workers.dev --cloudflare-edge
.venv/bin/python -m backend.platform.smoke --base https://perigee.lokesathvik.workers.dev --expect-build cloudflare/build/build-info.json
```

Alternatively, run the **cloudflare-release-verify** GitHub workflow (manual; inputs `base`, `ref`, `live`). It rebuilds the expected release from `ref` in CI and runs both checks above, without secrets.

## Build identity (backend next pass, B3)

`cloudflare/build.py` writes a public, non-secret identity to `/perigee-build.json`, and the same object to `cloudflare/build/build-info.json` under `identity`:
- `release_digest`: a SHA-256 over the frontend, catalog **and Worker** digests;
- `worker.digest`: a SHA-256 over sorted `path<TAB>sha256` lines for `cloudflare/src/**/*.js` and `cloudflare/wrangler.jsonc`. Wrangler's custom build step (`node worker-identity.mjs`, run before every `wrangler dev` and `wrangler deploy`) computes it from the code actually bundled. `build.py` computes the same digest, and a test checks that both agree. **The deployed Worker reports its own digest in an `X-Perigee-Worker` header on every `/api` response**, so a release check sees the Worker version that is actually running;
- `frontend.digest` and `catalog.digest`: each a SHA-256 over sorted `path<TAB>sha256` lines, covering every file copied from `frontend/dist` (including the deck PDF) and every exported `api/` file respectively;
- `frontend.index_html_sha256` and `frontend.entry_scripts`;
- `demo_pdf`: path, `application/pdf`, size and SHA-256;
- `catalog.content_version`;
- `source`: `commit`, `tree_clean` and `label`. The label is `<commit>` only when the build inputs (`frontend`, `backend/content`, `backend/platform`, `cloudflare`) have no uncommitted or untracked changes. Otherwise it is `<commit>+uncommitted`, `<commit>+unverified` when git cannot tell, or `unknown (no git)`.

The identity contains no timestamps, so identical content always gets the same digests. The commit is reported separately and is not part of the digest.

`backend.platform.smoke --expect-build PATH` (or `--expect-release-digest HEX`) fetches `/perigee-build.json` and compares the release, frontend, catalog and Worker digests. With `--expect-build` it also requires the same **source label**, so it checks the build that was meant to be deployed, not just identical content. It requires the `X-Perigee-Worker` header from a Worker-served route to equal both the published and the expected Worker digest; that catches an older Worker even when the static files are unchanged (PR #47 review). It also checks that the **served** `index.html` and entry scripts hash to what the identity claims, and that the deck PDF is served as `application/pdf` with the expected SHA-256. Any mismatch, or a missing identity, fails the run.

The report prints the static release (this origin) and the live Python API (Vercel; `/health` does not expose its commit) as **separate** sections, and never as one version. The identity is a separate static file; `/api/v1/health`'s v1 contract is unchanged.

The earlier deployment at `979e0619…` (source `fd7933d`) predates this identity. Version `4031abf8…` (source `fbb6647`) now publishes it and passed the expected-build check, including its running Worker header. See [release evidence](../qa/cloudflare-release/README.md).

## Limits and dependencies

- **The live path depends on the Vercel deployment.** If `https://perigee-liard.vercel.app` stops serving, live search and frames show the app's honest "archive unavailable" states (502 or 504 envelopes). The three curated investigations, all presets, assets, the evidence notebook and export, and the deck keep working, because they make no upstream calls.
- **Content changes need a rebuild and redeploy** (`build.py`, then `wrangler deploy`). The Worker serves only what was exported.
- **No secrets are needed on Cloudflare.** Frame-token signing stays on the Python origin, which issues and verifies the tokens.
