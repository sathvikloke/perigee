# Overnight backend QA: N5 route parity and N6 local resilience

Branch `claude/n5-n6-backend`, cut from `origin/claude/overnight-science-backend` @ `0917ccc`
(assignment: `coordination/claude-overnight-science-backend.md`, sections 1–5, N5, N6).
Everything here was **run locally** on 2026-11-14/15 (America/Chicago). Nothing was deployed, and
nothing here says what the public origin is running. The coordinator owns the Vercel quota/origin
check and `coordination/overnight-release-handoff.md`.

## 0. Summary

| Item | Result |
| --- | --- |
| Route vs direct `process_frame`, same bytes and parameters | **Exact**: all record fields and image/flag PNG bytes equal for 7 retained frames + 4 geometries, plus 9 synthetic route runs |
| Live PNG vs curated per-frame asset (same raw bytes, same grid) | **Byte-identical** for all 7 retained frames compared (image and flag overlay) |
| Same observation at 2′ / 10′ / shifted / off-cutout | 4 distinct `grid_id`s and image hashes. Repeat requests reproduce their own geometry exactly. No backend cache exists. |
| Coordinate edges (RA 0/360 wrap, both poles, Dec = 90) | Correct through the route (synthetic) |
| Tokens, request IDs, upstream errors | Documented status, code, retryability and request-ID echo hold for 4 token cases, 6 bad-cutout cases, 4 malformed-archive cases, timeouts and caps |
| Time / byte limits | Enforced by wall clock and by counting the bytes actually pulled (see §2.2) |
| Partial / unavailable | Partial stays partial. Unavailable or malformed never turns into `empty` (real adapter, HTTP-level faults). |
| 3.6″ radius, 48 cap, temporal sampling | Confirmed in source and on the real cached SIA responses (Eps Ind B 468, Barnard 368 unique matches → 48 evenly spaced, first and last kept) |
| Worker with the origin down | Curated presets, cases, frames and assets are byte-exact, the live routes return a JSON envelope, and the build identity is kept. Checked in Node (8 failure modes) and in **real `wrangler dev`/workerd** with a closed-port origin. |
| Missing overlay vs no adverse flags | Distinguishable in the live record and the curated data. Frontend gap found (§3.4). |
| Defect found and fixed | **D1 (P1): process abort (SIGABRT) on a damaged WCS-WAVE table.** Fixed failing-first in `backend/data/process.py`. |
| One live archive smoke | One IRSA SIA search (DR1) through the candidate app: 200 `ready`, 338 matches, 48 returned, radius 0.001° |

## 1. Environment and commands

- Python 3.12.16 (coordinator `.venv`): fastapi 0.163.0, starlette 1.10.0, pydantic 2.14.3,
  httpx 0.28.1, anyio 4.16.0, numpy 2.5.4, astropy 8.0.2, pillow 13.0.0 (matches
  `backend/requirements.txt`). Node v26.13.0, npm 11.20.0, Wrangler 4.162.0. macOS arm64.
- Processor: `perigee-processor-a/0.1.2` (unchanged; see D1 for why it was not bumped).
- Raw data (read only): `research/build_data`, manifest 188 entries, 183 downloaded cutouts
  (3.97–4.08 MB each, sha256 checked against the manifest before every parity run).

```sh
PY=".../perigee-parallel-coord-4aa087/.venv/bin/python"
DATA=".../NASA Space Comp/research/build_data"
env -u PERIGEE_DATA_ROOT $PY -m pytest backend -q            # no raw data (CI equivalent)
PERIGEE_DATA_ROOT="$DATA" $PY -m pytest backend -q            # with raw data
(cd frontend && npm ci && npm run build); $PY cloudflare/build.py
$PY -m pytest -q cloudflare/tests && node --test cloudflare/test/*.test.mjs
node --test qa/overnight-backend/worker_origin_failure.test.mjs
PERIGEE_DATA_ROOT="$DATA" $PY qa/overnight-backend/n5_parity_evidence.py   # -> n5_parity_evidence.json + fixture
PERIGEE_DATA_ROOT="$DATA" $PY qa/overnight-backend/n6_measure.py           # -> n6_measurements.json
PERIGEE_DEV_MODE=1 $PY qa/overnight-backend/live_sia_smoke.py              # the one live IRSA call
```

Final counts on the committed head are in §5.

## 2. N5 route-level parity

### 2.1 Method (`backend/tests/api/test_route_parity.py`)

Only the network is replaced. The archive search runs the **real** `irsa_search_collection`
(SIA request, VOTable parsing, descriptor mapping) against a **subset of the real cached IRSA
SIA VOTables** in `research/build_data/metadata/` (only the rows of the frames under test, with
header, FIELDs and QUERY_STATUS intact). The cutout fetch returns the retained original FITS
bytes. Everything else is production code: strict request validation, token signing and
verification, `cutout_url_for`, the allowlist, `bounded_get` with budgets, the processor-A
adapter, `build_record`, data URLs, `FrameResponse` validation and JSON serialization.

Then, for the same bytes, `process_frame(raw, FrameInput(...))` is called directly with the
token's `ra/dec/fov`, `grid_size=256`, `target=None`, `include_flag_image=True`, and the
descriptor's identity. The direct record is given the route's own additions
(`provenance.data_origin="nasa_archive"`, PNG data URLs) and the route's
`provenance.retrieved_at` (fetch time). It is then passed through `FrameRecord` and JSON, and
compared **field by field** with the route's record. PNG bytes are compared by sha256.
**Tolerance: exact. No float tolerance is used.**

Invariants asserted on every route answer:

- registration center/FOV equal the signed query; `scale = fov·60/256`; 256×256; `grid_id == grid_id(ra, dec, fov, 256)`;
- the PNG really is 256×256. Overlay alignment: the flag PNG is 256×256 RGBA, every non-finite
  overlay pixel is transparent in the image, and no overlay pixel marks off-image area;
- `sampled_position` is the query center, and `marker` is null (live queries have no catalog target);
- provenance `sha256` is the sha256 of the raw bytes; `original_url` is the descriptor URL;
  `cutout_url` is the URL actually fetched (`center=<repr ra>,<repr dec>`, `size=fov·1.5/60`);
  `processing_version` is the processor's;
- identity (`observation_id, detector, frame_key, collection_id`) equals the descriptor;
- wavelength at the sampled position lies inside the archive's whole-detector range;
- time: the descriptor keeps `sia_t_min` and the record uses `DATE-AVG / MJD-AVG`. Mid-exposure
  minus exposure start is 57.5–57.6 s on every retained frame, within `t_exptime`.

### 2.2 Results (`n5_parity_evidence.json`)

| Case | Frame | Raw sha256 (16) | λ at query (µm) | Detector range | Status | Non-finite | Route PNG sha256 (16) | Route = direct | Curated per-frame PNG equal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| near-IR D3 | 2026W18_1A_0516_1_D3 | 3781422675f53d0a | 2.3231 | 1.630–2.435 | clear | 0 | 9a5c4f22988e8ff3 | yes | yes |
| shortest D1 | 2026W17_1B_0162_4_D1 | 85721c4740882e22 | 0.7737 | 0.746–1.117 | clear | 0 | da8850e51e6c29d0 | yes | yes |
| longer λ D6 | 2026W18_1A_0516_1_D6 | 74e32a3c1d7f8b7f | 4.9398 | 4.412–5.010 | clear | 0 | 18d433f057a67c62 | yes | yes |
| longer λ D6, WISE 0855 | 2025W19_1B_0116_1_D6 | 938da09e9dc277de | 4.9674 | 4.412–5.010 | clear | 0 | 5b87eb98debbcb61 | yes | yes |
| adverse + non-finite (R Dra) | 2025W29_2A_0288_1_D4 | bfda735d7bd466de | 2.6134 | 2.403–3.847 | flagged (BLOOM, OVERFLOW, SUR_ERROR) | 21 | 6f6b5a0b7930bb2d | yes | yes |
| adverse + non-finite (moving_neighbor A) | 2025W35_1A_0008_1_D3 | e7c0a6f7c4c69ceb | 2.0065 | 1.630–2.435 | flagged | 3 | dd282cc2f44408db | yes | yes |
| geometric no-coverage (retained) | 2025W17_4B_0077_2_D1 | bc539fed52034938 | null | 0.746–1.117 | not_covered | null | a8d1d8cfaffe1455 | yes | yes |

Normalized request for every row: `ra/dec` = the preset query center from the manifest, `fov_arcmin=6`, `limit=48`,
both collections, grid 256. SIA `POS=CIRCLE <ra> <dec> 0.001`. Full hashes (flag PNG and a
record hash that excludes fetch time) are in the JSON.

**Same observation, different geometry** (Eps Ind B 2026W18_1A_0516_1_D3; all route = direct):

| Request | Cutout `size` | grid_id | Scale ″/px | Native x, y | λ (µm) | Status | PNG sha256 (16) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2′ at center | 0.050000 | b038ca97a9ce825e | 0.46875 | 28.72, 28.87 | 2.32308 | clear | de5212565d67f037 |
| 10′ at center | 0.250000 | d93587c261ed4894 | 2.34375 | 28.72, 28.87 | 2.32308 | clear | 2be54d7cf9f289d6 |
| 6′ shifted 0.5′ N, 0.5′ E | 0.150000 | 0997f148b5deaaaf | 1.40625 | 22.25, 31.54 | 2.32190 | clear | d2efbf3660c4a263 |
| 6′ shifted 4′ E (off cutout) | 0.150000 | 9ab867c47322daf5 | 1.40625 | −6.97, 13.94 | null | not_covered | 7d37b31d1f8e0b7b |

The tests run these interleaved (2′, 10′, shifted, off, 2′, shifted, 10′). Each repeat
reproduces its first answer exactly, every request re-fetches its own cutout (no backend frame
cache; responses are `Cache-Control: no-store`), and `frame_key` is identical in all four.
Wavelength depends on the sampled position, not the FOV. A mutation check (forcing the
processor FOV to 6′ in `frames.py`) makes the geometry test fail, so the test catches stale
geometry.

**Synthetic layer (runs in CI, no raw data):** full trace parity, the same 2′/10′/shift matrix,
off-cutout `not_covered`, RA wrap (`359.999` vs a cutout at RA 0, and the reverse), across the
north pole, near the south pole, a query exactly at Dec = 90, non-finite holes (flag
non-finite mask == image transparency on a fully covered grid), and the overlay cases in §3.4.

### 2.3 Expected differences from curated and authored copies

With the same raw bytes and the same grid (preset center, 6′, 256), the **live PNG and flag
overlay are byte-identical to the curated per-frame assets** for all 7 frames. Record
differences are by design:

- `sampled_position`/`marker`: curated frames sample the **catalog-predicted target position**
  and carry a catalog marker; live frames sample the **query center** with `marker: null`. This
  moves the screen circle and wavelength by a few arcsec: |Δλ| ≤ 2.4·10⁻⁴ µm in the 7 frames.
  Quality status agreed in all 7.
- `wavelength_location`, the marker limitation line, `provenance.retrieved_at`/`cutout_url`/
  `retrieved_at_basis` and `data_origin` differ in text or provenance only.
- live `display_scale` carries the model's optional `comparable_brightness: null`, which curated files omit.
- **Authored case copies:** `fair_comparison` A/B and all three `moving_neighbor` frames use a
  **shared stretch** (`display_scale.mode="shared"`, common low/high), so their image PNGs differ
  from the live per-frame stretch. Their flag overlays are identical (the overlay does not depend
  on the stretch). `fair_comparison` C (D6) is authored per-frame and is byte-identical to live.
- A real live request asks IRSA for a `1.5×FOV` cutout (0.15° at 6′), while the retained
  cutouts are 0.10°. Against real IRSA bytes, pixels near a rotated grid's corners can
  therefore be filled live where the retained-based curated asset is transparent. Parity above
  is stated for identical bytes only.

### 2.4 Tokens, request IDs and upstream errors

Existing `test_frame.py`, `test_search.py` and `test_review_api.py` already cover tampering,
wrong secret, signature swap, expired, tampered+expired → invalid, non-allowlisted source, 5xx
retry, 404, redirect, byte cap, not-FITS and processor errors. New coverage in
`test_route_resilience.py`, through the real fetch path:

- expired → 400 `TOKEN_EXPIRED` (`details.action=refresh_search`). Bad signature, other secret
  and garbage → 400 `INVALID_FRAME_TOKEN`. All are `retryable:false`, with **zero upstream
  requests**.
- every envelope: JSON, `Cache-Control: no-store`, `schema_version 1`,
  `body.request_id == X-Request-ID == the client-supplied plain ID`. A non-plain client ID (with
  a space or newline) is replaced, never echoed.
- validation: a missing `frame_token` is 400 `INVALID_FRAME_TOKEN`, and `fov 11` is 422
  `INVALID_FIELD_OF_VIEW`, with the request ID kept.
- bad cutouts: HTML 200 → 502 `UPSTREAM_UNAVAILABLE`/`html_body`; JSON → 502
  `UNSUPPORTED_DATA`/`not_fits`; FITS magic + garbage → 422 `UNSUPPORTED_DATA`; a truncated
  FITS → 422; 429 → 502/`upstream_rate_limited`; 404 → 502/`upstream_404`. No traceback or
  local path leaks.

No validation was weakened, and no gap was found in this area.

### 2.5 Live archive smoke (exactly one)

`qa/overnight-backend/live_sia_smoke.py` at 2026-11-15T04:20:38Z made one POST /search through the
local candidate app to IRSA (DR1 only, Eps Ind B center, 6′, limit 48). Result: HTTP 200 in
2.72 s (`archive;dur=2403`), `ready`, `total_matches` 338, 48 returned, `evenly_spaced_in_time`,
no failed or capped collections, `search_radius_deg` 0.001. The two retained Eps Ind B 0516
frames were not in this 48-frame temporal sample, which is expected. No cutout was fetched,
and the public Perigee origin was not touched.

### 2.6 Request identity tuple for client caching

Use, for live frames:

```
(mode, observation_id, detector, collection_id, source_url,
 ra_deg, dec_deg, fov_arcmin, grid_px = 256, processing_version*)
```

Take `ra_deg`/`dec_deg`/`fov_arcmin` exactly as echoed in `SearchResponse.query` (unrounded
JSON numbers), and the identity fields from the `ObservationDescriptor`.

Why each field is needed:

- `observation_id + detector` (= `frame_key`) is **not** enough. The fixture
  `fixtures/request_identity_fixture.json` shows one frame_key with four different grids,
  scales, statuses and image hashes. Today's frontend key `${api.mode}:${frame_key}`
  (`frontend/src/components/QueryInvestigation.tsx:93`) returns old geometry. This is the known bug.
- `collection_id` + `source_url`: DR1 and QR3 copies of one observation are different files
  (release path, `l2b-vNN-YYYY-DDD` pipeline version), and the record's provenance, sha256
  and QR limitation follow the file. `source_url` also changes when IRSA reprocesses.
- `ra_deg, dec_deg, fov_arcmin, grid_px` are exactly what the backend's `registration.grid_id`
  hashes (`TAN|ra:.9f|dec:.9f|fov:.6f|size|NUEL`). They decide the cutout, grid, sampled
  position, wavelength and quality. Keying on the exact floats is at least as strict as
  `grid_id`. The grid is fixed at 256 today (`GRID_PX`), but keep it in the key.
- `mode` (live vs fixture) is already in the key. Keep it so curated, fixture and live records
  never share an entry. A curated record at the same grid differs: it has a marker and
  target-sampled wavelength.
- *`processing_version` is only known from the response (`provenance.processing_version`).
  Store it with the entry and drop the entry when a fresh response from the same backend reports
  a different version. In the current in-memory per-page cache this matters only across a
  mid-session backend deploy.
- Do **not** key on `frame_token` (it changes on every search: `iat`/`exp`),
  `request_id`, `retrieved_at` or `timing_ms`.

## 3. N6 local resilience (`backend/tests/api/test_route_resilience.py`, Worker tests in this folder)

All faults are injected at the HTTP level (`httpx.MockTransport` with async handlers) under the
real SIA adapter and the real `bounded_get`. Neither NASA nor any Perigee origin is involved.

### 3.1 Matrix and observed behaviour

| Scenario | Observed (asserted) |
| --- | --- |
| normal search + frame (real adapters) | 200 `ready`, 1 SIA call per collection, 1 cutout fetch |
| cutout upstream never answers, `frame_budget_s=2` | 504 `UPSTREAM_TIMEOUT` `{stage: fetch, reason: deadline}`, **~1.20 s** (= 0.6 × budget) |
| cutout drips 1 KiB / 0.1 s (each read well inside the 5 s read timeout) | 504 at ~1.2 s, stream abandoned mid-way: the **overall deadline** binds, not only the per-read timeout |
| processor exceeds budget (`frame_budget_s=1.5`) | 500 `PROCESSING_FAILED` `{stage: process, reason: budget}` at ~1.5 s, retryable |
| both SIA calls hang, `search_budget_s=1.5` | 504 `UPSTREAM_TIMEOUT`, both collections listed with reason `deadline`, ~1.5 s; **not `empty`** |
| one collection hangs | 200 `partial`, `collections_failed=[spherex_qr3]`, `total_matches=null` |
| declared `Content-Length: 1e9` cutout | 502 `UNSUPPORTED_DATA`/`content_length_cap`, ≤ 1 chunk pulled |
| undeclared ~40 MB cutout, cap 64 KiB | 502 `UNSUPPORTED_DATA`/`stream_cap`; **≤ cap + one 4 KiB chunk pulled** |
| SIA body > 12 MiB in one collection | that collection fails, so the search is `partial`. Pulled ≤ 12 MiB + one chunk. |
| truncated XML / non-VOTable XML / HTML 200 / `QUERY_STATUS=ERROR` (both) | 502 `UPSTREAM_UNAVAILABLE` with per-collection reason (`votable_parse`, `not_votable`, `html_body`, `query_status_error`) |
| same, one good collection with a match | 200 `partial`, `total_matches=null` |
| same, other collection good but empty | 502 error (`collections_succeeded_empty=[spherex_dr1]`), **never a false empty** |
| persistent 503 on QR3 | retried 2–5 times (bounded by `SIA_MAX_ATTEMPTS` and the budget), result `partial` |
| `QUERY_STATUS=OVERFLOW` with zero rows | `partial`, `collections_capped`, total unknown (not `empty`) |
| invalid / truncated FITS | 422 `UNSUPPORTED_DATA` (route); see §3.3 for the corruption sweep |
| repeated identical request | 2 upstream fetches (no cache). Records identical apart from `retrieved_at`; same PNG bytes. |
| 4 simultaneous distinct frames (2 detectors × 2 FOVs, ASGI) | upstream saw ≥ 2 in flight. Each answer follows its own token and equals the same request made alone; 4 distinct images. |
| env limits (`PERIGEE_FRAME_MAX_BYTES`, `_FRAME_BUDGET_S`, `_SEARCH_BUDGET_S`, connect/read timeouts) | reach `Settings` and the real httpx client (`follow_redirects=False`). Unparseable values fall back to the defaults instead of disabling a limit. |

**Concurrency limits.** Perigee configures **no** concurrency limit in the backend or the Worker.
Processor calls run through `run_in_threadpool`, which is bounded per process by anyio's default
limiter (**40 tokens**, measured). Vercel scales by instances. Both "configured concurrency
limit respected" items are therefore N/A, and this is stated rather than implied.

### 3.2 Measurements (`n6_measurements.json`; descriptive, small samples, one laptop, mocked upstream)

- **Cold** (fresh interpreter, 3 runs): import of `backend.main` + processor 0.29–0.43 s; first
  `/frame` 43–45 ms; second 38 ms; **peak RSS 127.6 MB**. A local process start is not a Vercel
  cold start.
- **Warm `/frame`** (10 each, retained cutouts, 6′): p50 30.6–40.8 ms. Clear near-IR ~37 ms,
  D6 ~40 ms, flagged ~33 ms, not-covered ~31 ms. One outlier max 66 ms.
- **Processor only, 10′ FOV**: peak Python allocation (tracemalloc) **12.95 MB**, ~114 ms under tracing.
- **Warm `/search`** over the full cached Eps Ind B SIA responses (754 KB DR1 + 278 KB QR3):
  p50 24.8 ms, 468 unique matches → 48 returned, 49.9 KB response.
- **Concurrency**, 4 distinct frames: sequential p50 167.7 ms vs simultaneous p50 122.9 ms
  (n = 5 each). There is partial overlap: numpy and astropy release the GIL only part of the time.
- **Sizes vs caps**: frame responses are 14–42 KB (cap 4,000,000 B). Image PNGs are 5.8–26.6 KB
  and flag PNGs 0.85–1.8 KB (cap 2 MiB). Raw cutouts are ~4.0 MB, almost all of it the fixed
  EPSF table, against a 24 MiB fetch cap.

### 3.3 Defect D1 (P1, fixed): a damaged WCS-WAVE table aborts the process

- **Found by** a truncation and corruption sweep of a retained cutout. When the last 2880-byte
  block (the WCS-WAVE table data) is zeroed, `astropy.wcs.WCS(header, fobj, key="W")` (astropy
  8.0.2 / wcslib) **aborts the interpreter with SIGABRT** (exit 134, no Python exception) in
  `backend/data/process.py` at the spectral-WCS step. Isolated with synthetic tables: any
  repeated value in a -TAB index vector (`X`/`Y` all zero, or `[5, 5]`) aborts. Zeroed or NaN
  `VALUES` and a strictly decreasing index are handled.
- **Impact:** on the live path this kills the Python function instead of returning a JSON
  envelope (the Worker then shows a generic 502), together with any other request in the same
  process. It needs a damaged file from the allowlisted archive (a partial or damaged transfer),
  so it cannot be triggered by a user-chosen URL. It is P1 because the failure is a process
  crash that the error contract cannot represent.
- **Fix** (smallest change): `_check_wave_table_index()` checks that every index column named
  by `PSi_2W` exists and is finite and strictly monotonic **before** wcslib sees it. A bad table
  raises `ValueError` into the existing "Wavelength unavailable: spectral WCS (key W) could not
  be evaluated" path. The frame is still produced from the intact IMAGE/FLAGS/VARIANCE, with
  `wavelength_um: null` and the note.
- **Failing-first regression:** `backend/tests/api/test_regression_wave_table_abort.py` runs the
  real `/frame` route in a child process (so a regression fails the test instead of killing
  pytest). Before the fix, 5 cases failed with `rc=-6`: x zero, y zero, both zero, x repeated,
  and the real retained cutout with the zeroed block. After the fix all 6 pass, including
  valid-table controls (increasing and decreasing).
- **No change for valid data:** all 183 retained cutouts give the same records before and after
  (scan diff empty). The live PNGs still equal the curated assets byte for byte.
  `PROCESSING_VERSION` was deliberately **not** bumped: no output changes for any input that
  previously completed.
- **Post-fix sweep:** each single 2880-byte block zeroed or 0xFF-filled (every non-EPSF block plus
  every 50th EPSF block; 152 variants) gives **0 crashes**. Results are either a typed
  `UnsupportedDataError` (422) or a frame with honest notes.

### 3.4 Missing overlay vs no adverse flags

- **Live:** with no FLAGS extension, the record has `flag_image: null`,
  `quality.status: "unknown"`, null valid/adverse counts and a "flag screen unavailable" note,
  never "clear". With FLAGS and nothing adverse, the overlay exists (fully transparent) and the
  status is "clear". With an adverse flag at the center, the overlay marks it and the status is
  "flagged" (`["HOT"]`). Checked through the route (synthetic).
- **Curated (Worker):** a failed overlay asset is a JSON 404 `ASSET_NOT_FOUND`, never a substitute
  image. Frames documents are served verbatim and keep their stored `quality.status`. Data
  invariant over every exported frames document: **no frame says "clear" without a flag overlay
  behind it.**
- **Frontend gap (Codex-owned, not changed here):** in `frontend/src/components/Plate.tsx` the
  `<img className="flag-overlay">` has no `onError`. If the overlay asset fails, it silently
  disappears while the "Show flagged pixels" toggle and the legend still render, which looks
  like "no adverse pixels". Suggested fix: on overlay error, show "Flag overlay could not be
  loaded", keep the record's `quality.status` text, and hide the legend. (P2, UI.)

### 3.5 Worker: fixed origin, bounds, curated fallback, build identity

- Source check (`cloudflare/src/app.js`): one constant origin
  (`https://perigee-liard.vercel.app`) plus three fixed paths. The query string, host, cookies and
  other headers are dropped. `redirect: "manual"`, and redirects are refused. The request body is
  capped at 64 KiB and the upstream body at 8 MiB. Timeout 70 s. Non-JSON or unparseable JSON
  becomes a 502 envelope. The existing B1/B3 tests in `cloudflare/test` still pass, unchanged.
- `qa/overnight-backend/worker_origin_failure.test.mjs` (10 tests) covers 8 origin failure modes:
  network error, hang (timeout), HTML 500, Vercel plain-text 500, "JSON" that is not JSON,
  redirect, 9 MiB body, and an origin 503 envelope (passed through). In every mode
  `/health`/`/search`/`/frame` return the documented envelope (502/504/503) with the request ID,
  and only the fixed origin is called. **All curated routes (presets, 2 cases, 5 frames docs + case
  variants, 952 assets) come back byte-exact with zero origin calls.** Every answer carries
  `X-Perigee-Worker` = the bundled `perigee-build.json` worker digest.
- **Real runtime check:** `wrangler@4.162.0 dev --local` ran on a **copy** of the Worker whose origin
  is a closed local port (`http://127.0.0.1:9`); repository source unchanged. The three live routes
  returned 502 `UPSTREAM_UNAVAILABLE` in 3–25 ms with the request ID echoed. 74/74 curated routes
  (all documents + a ~60-asset sample) were byte-exact. `/perigee-build.json` was served. The copy
  reported its own Worker digest `4718…6663`, not the repository's `4a40…3016`, which shows the
  identity header distinguishes modified Worker code. Script: `wrangler_dev_origin_down.py`.
- **Build identity:** `cloudflare/build.py` on `0917ccc` reproduced release digest
  `548e7202640872b3ea524061ac50a28d0be5d3b3a930048bf1ffac0b5b88024d`, the digest recorded for the
  deployed Worker (build inputs `frontend`, `backend/content`, `backend/platform` and `cloudflare`
  are unchanged since `fbb6647`). This branch changes none of those inputs, so the candidate
  Cloudflare bundle is identical. `backend/data/process.py` (D1) only changes the **Python
  origin**, which must be deployed separately; a Cloudflare deploy does not update it.

### 3.6 Fixed search radius and the 48 cap (source-verified)

- `backend/routes/_archive.py`: `SEARCH_RADIUS_DEG = 0.001` (3.6″), `POS=CIRCLE <ra!r> <dec!r> 0.001`,
  `MAXREC=2000`; `backend/models/search.py`: `LIMIT_MAX = 48`; `select_evenly` keeps first and
  last, evenly spaced in time. No pagination and no date filter.
- On the full real cached SIA responses for Eps Ind B and Barnard's Star at 2′ and 10′: identical
  SIA requests (`POS` with 0.001, `MAXREC 2000`) and identical returned frame keys at both FOVs;
  `ready`, `total_matches` = unique level-2 images (468 Eps Ind B, 368 Barnard); 48 returned,
  `truncated: true`, `selection: evenly_spaced_in_time`, equal to `select_evenly(merged, 48)`, with
  the earliest and latest kept, and the "Showing 48 of N" warning present. (The cached files were
  retrieved with a 0.02° cone; the mock serves them for any POS, which is fine for testing selection.)

## 4. Residual risks and limits

1. A thread that exceeds the processing budget is answered with 500 but **keeps running** (Python
   threads cannot be cancelled). This is bounded by anyio's 40-thread limiter per process.
   Processing is ~40 ms per frame, so this is unlikely in practice.
2. A cutout truncated **exactly at an HDU boundary** is valid FITS with fewer extensions. It is
   processed and labelled honestly (FLAGS or VARIANCE missing → `unknown`; WCS-WAVE missing →
   wavelength null with a note), not rejected as truncated. IRSA cutouts carry no
   CHECKSUM/DATASUM, so corruption inside a data unit (e.g. a zeroed IMAGE block) cannot be
   detected; TLS is the integrity control.
3. No concurrency limit is configured anywhere (backend or Worker). Behaviour under real
   simultaneous load on Vercel was not measured, and must not be load-tested against production.
4. Timings are local, mocked-upstream, small-sample figures, not capacity statements. Real IRSA
   latency dominates: the one live SIA call took 2.4 s.
5. Parity is proven for identical bytes. Against live IRSA the cutout is 1.5×FOV rather than the
   retained 0.10°, so the edges of rotated grids can differ from the curated assets.
6. Only one live archive call was made (SIA, no cutout). Whether the public origin runs the D1
   fix or the B4 wording is for the coordinator's origin check. This report makes no
   public-deployment claim.
7. The D1 fix guards the trigger found (non-monotonic -TAB index). Other wcslib aborts on
   different malformed headers cannot be ruled out. The bounded corruption sweep found none
   after the fix.

## 5. Final verification on the committed head

See the commit message and the hand-back for exact counts on the final commit; they are repeated here:

- `env -u PERIGEE_DATA_ROOT pytest backend -q` → **384 passed, 33 skipped**
  (baseline 0917ccc: 344 passed, 18 skipped)
- `PERIGEE_DATA_ROOT=… pytest backend -q` → **417 passed** (baseline: 362 passed)
- `pytest -q cloudflare/tests` → **16 passed**; `node --test cloudflare/test/*.test.mjs` → **22/22**
- `node --test qa/overnight-backend/worker_origin_failure.test.mjs` → **10/10**

## 6. Files

- `backend/data/process.py` — D1 fix (`_check_wave_table_index`, one call site)
- `backend/tests/api/test_regression_wave_table_abort.py` — D1 failing-first regression (6 tests)
- `backend/tests/api/test_route_parity.py` — N5 parity (10 synthetic + 12 retained-data tests)
- `backend/tests/api/test_route_resilience.py` — N6 resilience (25 + 2 retained-data tests)
- `qa/overnight-backend/worker_origin_failure.test.mjs` — Worker fault injection (10 tests)
- `qa/overnight-backend/wrangler_dev_origin_down.py` — workerd probe for the fault-injection copy
- `qa/overnight-backend/n5_parity_evidence.py` → `n5_parity_evidence.json`, `fixtures/request_identity_fixture.json`
- `qa/overnight-backend/n6_measure.py` → `n6_measurements.json`
- `qa/overnight-backend/live_sia_smoke.py` — the single live SIA smoke
- `qa/overnight-backend/corruption_sweep.py` — the bounded single-block corruption sweep (§3.3)
