# API reliability and security review (worker 14)

Subject: the integrated API on `claude/perigee-integration` @ `8a49d77`. That is API A (`88e3772`) with the catalog routes (08) and processor A (05). This is a targeted review against named failure risks. It is not a certification. Each finding below was reproduced. The `test_review_api.py` tests fail on the base commit (11 of 12) and pass with the fixes. `test_r1_404_is_not_retried` guards the new retry, so it passes on both.

Run: `.venv/bin/python -m pytest backend/tests/api/test_review_api.py -q`

## Findings, ranked

| # | Severity | Status |
|---|----------|--------|
| R1 | High (reliability) | fixed |
| R2 | Medium | fixed |
| R3 | Medium | fixed |
| R4 | Low | fixed |
| R5 | Low | fixed |
| R6 | Low | fixed |
| R7 | Low | open (catalog owner) |
| D1–D3 | n/a | owner decisions |

### R1: no retry on IRSA's transient cutout 503s, so about 25% of frames fail on first load (High)
- **Reproduction (live):** I made 16 sequential cutout GETs through `bounded_get`, using the API's own `cutout_url_for` for Eps Ind A on 2026-11-14. 4 of them returned **HTTP 503 in 0.1 s**. The other 12 returned a ~4 MB FITS in 3.4–5.2 s. Script: an SIA search, then 8 cutouts, run twice.
  Test: `test_r1_transient_cutout_503_is_retried`, `test_r1_persistent_503_is_bounded_and_reports_attempts`.
- **Observed:** SIA search already retries IRSA's transient 502/503/504s, up to 5 times. `/frame` made one attempt and returned `502 UPSTREAM_UNAVAILABLE`. The frontend only offers a manual retry button, so roughly one frame in four showed an error.
- **Expected:** a bounded retry of fast transient failures. It must stay inside the existing fetch deadline and report the attempt count when it fails.
- **Fix (`routes/frames.py`):** `_fetch_with_retry` makes up to 3 attempts. It retries only on 502/503/504 or a connection reset/read error. It never retries a 404, a timeout, or a byte-cap failure. All attempts share the existing `frame_budget_s * 0.6` deadline (24 s), and it stops when less than 2 s remains. Backoff is 0.3 s and then 0.6 s. A failure includes `details.attempts`.
- **Budget check:** the worst case is a 24 s fetch plus processing in the remaining 16 s of the 40 s frame budget. That stays under `maxDuration` 60 even with a cold start. The cutout is ~4 MB whatever size is requested, so the 24 MB byte cap leaves 6× headroom. Live after the fix (`:8020`): 8 of 8 frames returned 200 in 3.9–7.1 s, with processing taking 31–86 ms.

### R2: validation error details were unbounded, so a 4 MB request produced a 17 MB error (Medium)
- **Reproduction:** `test_r2_validation_error_details_are_bounded`. With the server running, I sent a `/search` body of ~300k unknown keys (3.5 MB, under Vercel's 4.5 MB request limit):
  `python -c 'print("{"+",".join(f"\"k{i}\":0" for i in range(300000))+"}")' > /tmp/b.json; curl -s -o /dev/null -w '%{size_download}\n' -H 'content-type: application/json' --data-binary @/tmp/b.json localhost:8020/api/v1/search`
- **Observed (base):** a 4.3 MB body produced a **17.5 MB** `400` envelope, with one `details.fields` entry per key, in about 760 ms of CPU. On Vercel that exceeds the 4.5 MB response limit, so the platform returns its own non-JSON error. The endpoint also becomes a 4× amplification sink.
- **Expected:** a small JSON envelope.
- **Fix (`routes/_errors.py`):** `details.fields` keeps its first 20 entries and adds `fields_total`. After the fix the same request returns 1,096 bytes.
- **Request body cap (API B's 413 approach, which the coordinator asked about):** not ported. Vercel already caps request bodies at 4.5 MB. Measured at that size: a 4.4 MB token string takes 25 ms, 4.4 MB of whitespace takes 5 ms, and a 300k-element `collection_ids` takes 11 ms (422). The consequential part was the amplified response, which R2 fixes.

### R3: a corrupt `Content-Encoding` body escaped error classification and became INTERNAL_ERROR, which also dropped partial search results (Medium)
- **Reproduction:** `test_r3_corrupt_gzip_cutout_is_upstream_error_not_500`, `test_r3_corrupt_gzip_in_one_collection_keeps_partial_search`. The upstream answers `content-encoding: gzip` with a body that is not gzip, for example a proxy error page with the wrong label.
- **Observed:** `httpx.DecodingError` is a `RequestError` but not a `TransportError`, so `bounded_get` did not catch it. `/frame` returned `500 INTERNAL_ERROR`. In `/search`, when one collection hit it, the route's gather re-raised it as a programming error. That discarded the other collection's good results and returned 500 instead of `partial`.
- **Expected:** `UPSTREAM_UNAVAILABLE` for the frame, and `status: partial` for the search.
- **Fix (`security/upstream.py`):** catch `httpx.RequestError`, after `TimeoutException`.

### R4: the allowlist parser and the fetcher disagreed on control characters (Low)
- **Reproduction:** `test_r4_unsafe_characters_are_not_allowlisted`, `test_r4_token_with_control_char_source_is_rejected_before_fetch`.
- **Observed:** `urlsplit` silently drops tab, CR and LF, and strips leading spaces. So `is_allowed_source_url("https://irsa.ipac.caltech.edu/ibe/.../level2_\t...fits")` returned True. httpx then raised `InvalidURL` (not an `HTTPError`), which became `500 INTERNAL_ERROR`. The same gap applied to redirect `Location` values. The parser differential did not change the host, because every host trick I tried was rejected (see exclusions). It only turned a bad upstream value into a 500.
- **Expected:** reject before any fetch.
- **Fix:** `_has_unsafe_chars` rejects any character `<= 0x20` or `>= 0x7f` in both allowlist checks. Non-ASCII/IDN input was already rejected by the host comparison, and this check now rejects it explicitly as well.

### R5: the frame response could exceed Vercel's 4.5 MB response limit (Low)
- **Reproduction:** `test_r5_oversized_frame_response_is_a_json_error`. A processor returning two PNGs of 1.9 MB each (each under the 2 MB `MAX_PNG_BYTES`) produced a **5.07 MB `200`**.
- **Observed:** the per-image cap does not bound the base64 total. Vercel would replace the response with a non-JSON error. Processor A's real 256×256 frames are 15–24 KB, so the risk is latent today.
- **Fix (`routes/frames.py`):** `_json_within_budget` returns `500 PROCESSING_FAILED` (`reason: response_too_large`) if the serialized body exceeds 4,000,000 bytes.

### R6: the public dev secret was accepted as `PERIGEE_TOKEN_SECRET` in production (Low)
- **Reproduction:** `test_r6_dev_secret_refused_in_production`. Run `VERCEL_ENV=production PERIGEE_TOKEN_SECRET=<_DEV_SECRET from config.py> python -c 'from backend.security.config import load_settings; print(load_settings().token_secret_source)'`. The base prints `env`.
- **Observed:** the dev-mode fallback was refused in production, but the same publicly known string supplied through the env var was accepted. Anyone could then mint tokens. The impact is limited because `/frame` re-checks the source allowlist, but forged RA/Dec/FOV and identity strings would be accepted.
- **Fix (`security/config.py`):** in production that value leaves signing unconfigured, with `token_signing: "dev_secret_refused"` in `/health` and in the 503 details.

### R7: catalog error envelopes carry a different `request_id` from the `X-Request-ID` header (Low, not fixed)
- **Reproduction:** `curl -si -H 'X-Request-ID: abc-123' localhost:8020/api/v1/cases/nope_case`. The header is `abc-123`, but the body's `request_id` is a fresh UUID. API routes and the unknown-route 404 use the same id in both.
- **Why not fixed:** this only affects diagnostics. The fix means threading `Request` through four catalog routes (worker 08's file). Left for the catalog owner.

## Decisions for the API owner

- **D1: overflow status.** When IRSA returns `QUERY_STATUS=OVERFLOW` (MAXREC 2000), `/search` reports `status: ready` with `truncated: true` and `total_matches: null`. The contract says "partial means … a documented limit interrupted retrieval", which arguably covers this. Choose `ready` or `partial`. I did not change it.
- **D2: rate limiting.** `RATE_LIMITED` is defined but never emitted. API B uses a per-instance in-memory limiter. On Vercel, instances do not share memory, so it only catches a runaway loop that hits one warm instance. I did not port it, because the brief says no speculative infrastructure. If abuse protection matters for the judging window, a platform-level limit (Vercel Firewall rate limiting on `/api/v1/frame`) is the effective option.
- **D3: dev secret on Preview.** `PERIGEE_DEV_MODE=1` still enables the public dev secret on `VERCEL_ENV=preview`, and the existing test pins this behavior. That is safe only while Preview has no `PERIGEE_DEV_MODE` and keeps Vercel Authentication.

## Already handled well (no test added)

- Coordinates: NaN, ±Infinity, `1e999`, `-1e999`, `"12.5"`, `"12abc"`, booleans, null, arrays, RA 360/360.0/359.99999999999999999, Dec 90.0000000000001 and 400-digit integers all return 422 `INVALID_COORDINATES`, with no clipping. `-0.0` and `1e-400` are accepted as 0. `-0.0` is echoed as `-0.0`, which is harmless.
- Other inputs: `limit: 1.0`/`true` and `schema_version: 1.0` are rejected (strict). Duplicate JSON keys use the last value and are then validated. A 100k-deep nested body returns 400.
- Token tampering, wrong secret, signature swap, prefix/version change, expiry, and tampered-plus-expired returning INVALID: covered by `test_frame.py`. Comparison uses `hmac.compare_digest`.
- Replay across queries is not possible, because `/frame` takes only the token and the query comes from the signed payload.
- Token encoding: 3 alternative base64 spellings of the final signature character verify, because the spare bits are ignored. This is not consequential, because tokens are not used as server-side identifiers.
- SSRF host tricks: `irsa.ipac.caltech.edu.evil.com`, trailing dot, `:443`, userinfo `@`, `\@`, `#@`, `?@`, `%2e`, fullwidth dot, `http://`, `..` and `.%2e` are all rejected. The host and path are re-checked on every redirect hop, with at most 3 hops. Queries are allowed only on the server-built cutout URL.
- Byte cap: enforced on `Content-Length` and while streaming decoded bytes. The overall deadline is enforced with `asyncio.wait_for` and covers redirects.
- Search budget: collections run in parallel with a 25 s shared deadline, and retries stop when less than 2 s remains (at most 5 attempts).
- Search status: partial, empty and error semantics match the contract, including the case where one collection failed and the other was empty, which is an error.
- Unknown routes, wrong methods and unhandled exceptions all return a JSON envelope. `/health` and error details expose no secret values.
- Catalog: asset IDs are dictionary lookups behind a strict regex. `..`, `/`, `%2f` and `%2e%2e` return a JSON 404. Symlinks and files outside the root are never indexed, and each file is re-hashed when served.

## Limitations

- The live evidence is 16 cutout GETs plus 8 frames (one target, one afternoon). The 25% rate of transient 503s could be higher or lower at another time.
- I did not deploy to Vercel. The 4.5 MB request and response limits are Vercel's documented limits, not measured on a deployment.
- When the processor times out, its worker thread keeps running after the 500 is returned, because Python threads cannot be cancelled. This is noted only.
