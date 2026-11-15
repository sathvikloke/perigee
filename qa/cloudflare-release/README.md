# Cloudflare public release verification

## Backend hardening release — 2026-11-15, 03:24 UTC

PR [#47](https://github.com/sathvikloke/perigee/pull/47) is merged and its Cloudflare changes are deployed publicly. Worker version: `4031abf8-c0fb-4689-8205-3211ea0c673c`. Source: `fbb664749a8c31a13cb02cb42ceb2fdeb2ae83bb`, built from a clean tree. No frontend application code or curated content changed in this release.

- Release digest: `548e7202640872b3ea524061ac50a28d0be5d3b3a930048bf1ffac0b5b88024d`.
- Worker digest: `4a4073ba9fd628fc3ea2ef85601819165fce8de938234c9e13dde31e18fa3016`, verified from the running Worker's `X-Perigee-Worker` header as well as the published identity.
- Before deployment: frontend build and catalog export completed; 16 Cloudflare Python tests and 22 Worker tests passed. A separate review run passed 52 release-identity/smoke tests, including rejection of mismatched Worker code.
- Public [static/route smoke](backend-47-edge-smoke.txt): **26/26**, including exact catalog/asset bytes, PDF, JavaScript and running Worker identity.
- Public [release smoke against the expected build](backend-47-identity-smoke.txt): **29/29**, including logged-out access, source/content/Worker identity, a live search (377 matches, 2.6 s) and one processed PNG (10,642 bytes, 2.6 s). Timings describe this run only.
- The deck remains 2,369,713 bytes with SHA-256 `ffab44ce1f9fe182d2b9f427ae186c30e18e2cfc7ff6ea24099ecbd8d05ca89e`.

Cloudflare now serves the safer error handling and verifiable release identity. Live search, processing and health still use the existing Vercel Python deployment. PR #47's corrected search-sampling warning is merged but **not deployed to that Python origin** because Vercel's build quota blocked the latest build. Successful live smoke verifies the running API, not that Python source update.

This release does not resolve the frontend behavior findings in [PR #46](https://github.com/sathvikloke/perigee/pull/46). Those belong in the forthcoming UI work. The draft transfer exercise is not shipped or learner-tested. No competition submission has been made.

## Earlier hosting migration — 2026-11-15, 01:14–01:18 UTC

Verified on 2026-11-15, approximately 01:14–01:18 UTC, without authentication.

- App: https://perigee.lokesathvik.workers.dev
- PDF: https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf
- Worker version: `979e0619-e17e-4471-bce1-1144129f7a33`
- Deployed source: `fd7933d85ea518aa11fb34918c8d6fbe1de9e6a5`
- Catalog content: `targets-2026-11-15a`, including the WISE 0855 source correction.
- PDF: 7 pages, 2,369,713 bytes, SHA-256 `ffab44ce1f9fe182d2b9f427ae186c30e18e2cfc7ff6ea24099ecbd8d05ca89e`.

## Automated checks

The final bundle passed `npm run build`, 7 Python export-parity tests, 15 Worker tests and Wrangler dry-run before deployment. The export contains five presets, two cases, two case-specific frame sets and 952 asset IDs (574 canonical files and 378 aliases). Every exported asset was compared byte-for-byte with the Python catalog.

The deployed [release smoke](release-smoke.txt) passed **20/20**: public access, SPA routes, health, catalog, PNG decoding, JSON errors, live Orion search (377 matches, 1.8 s) and one processed frame (valid 10,642-byte PNG, 3.5 s). Timings describe this run only. Search, frame and health use the existing Vercel Python API through the fixed-origin proxy.

The first static/route smoke was **21/23** ([original output](initial-static-smoke.txt)). Both differences were traced to Cloudflare's edge, not changed data:

- Compressed JSON receives a weak ETag (`W/` prefix). The decompressed content still matches its SHA-256 exactly; an identity-encoded request preserves the strong ETag. This matches [Cloudflare's ETag behavior](https://developers.cloudflare.com/cache/reference/etag-headers/).
- The exact path `/api/v1/assets/x%00.png` is rejected by Cloudflare with HTTP 400 HTML before the Worker runs. The response has `server: cloudflare` and no application request ID. This exception applies only to that malformed-path probe; normal unknown API routes and traversal probes still produce JSON 404s.

The smoke harness now has an explicit `--cloudflare-edge` mode for these narrow expectations. The deployed run passed **24/24**, including the encoded-NUL rejection as its own check, exact PDF and JS bytes, all ten catalog documents, three asset types, remaining route parity and blocked internal manifest paths. Local Worker tests retain the original FastAPI expectations. No production code was changed to make these checks pass.

Reproduce after building and generating route expectations as described in [CLOUDFLARE.md](../../docs/CLOUDFLARE.md):

```sh
python cloudflare/tests/smoke_local.py --base https://perigee.lokesathvik.workers.dev --cloudflare-edge
python -m backend.platform.smoke --base https://perigee.lokesathvik.workers.dev
```

A separate [GitHub Actions run](https://github.com/sathvikloke/perigee/actions/runs/43662439693) also passed 20/20 at 01:18 UTC against the Cloudflare URL. It returned 377 search matches (1.6 s) and a valid frame (2.9 s). The repository homepage and `PERIGEE_PUBLIC_URL` now point to Cloudflare.

## Browser check

A fresh Cloudflare browser origin had no saved notes. The following were checked in the in-app browser:

- Open Epsilon Indi B and load the actual A/B images.
- Switch to A/C; dates/wavelength labels and explanation update.
- Turn on flagged pixels; overlays and legend appear.
- Write synthetic QA notes, return home, reopen the saved card; all three fields restore and the app says “Restored from this device”.
- Download [the actual JSON evidence card](evidence-card.json), containing A/B frame provenance and the entered claim, observations and uncertainty.
- All three visible science images report loaded; no console errors were recorded.

![Public investigation and restored notebook](investigation.jpg)

This was a hosting migration check, not a repeat of every earlier accessibility or science check. The earlier [production journey](../production-journey/README.md) retains that evidence. Physical-phone and screen-reader tests remain unperformed.

Cloudflare serves the frontend and curated content independently of the live archive/API. Live searches still depend on Vercel and IRSA. Browser notes on the old Vercel origin do not migrate to Cloudflare automatically. Nothing has been submitted to the competition.
