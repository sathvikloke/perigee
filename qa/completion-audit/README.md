# Completion audit evidence

Main at audit time: `9cb850bc2729b6ca45ceb356d6ad8099602d950b`.

See [the findings and ownership plan](../../coordination/completion-audit.md) and [Claude's assignment](../../coordination/backend-next-pass.md).

- `wrong-field.jpg` and `wrong-field.txt`: public-app reproduction after Orion at 2′, maximum 1, then the same position at 10′. Result heading is 10′; image remains 2′.
- `fresh-frame.json`: a fresh direct API search/frame request for the 10′ field. Same observation, correct 10′ registration. No frame token is retained.
- `case-fallback.txt`: local controlled 503 on the Epsilon Indi case-product list, while the catalog and general products remain available. No case error is presented; per-frame products appear with the generic stretch caveat.
- `overlay-failure.txt`: local controlled 404 on flag PNGs. The two failed images report zero natural width; the checked control and color keys remain.
- `mobile-barnard.jpg`: 320 CSS px layout check using the local overlay-failure server. Do not present this screenshot as a successful overlay demonstration.

The local failure server was an audit harness under `/tmp`, serving the existing built frontend and exported real catalog. It changed no application source or public deployment. Its failures were intentional. The Worker JSON/fetch failure cases were separately injected into `handle()` through its supported test dependencies.

Commands run from the repository root:

```sh
npm test --prefix frontend
npm run build --prefix frontend
PERIGEE_DATA_ROOT='/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data' /path/to/app-venv/bin/python -m pytest backend/tests -q
/path/to/app-venv/bin/python -m pytest cloudflare/tests/test_export_parity.py -q
node --test cloudflare/test/worker.test.mjs
```

Results: frontend 121 passed; build passed; backend 348 passed with raw data (330 passed/18 skipped without it); parity 7 passed; Worker 15 passed. FastAPI's test client emitted one Starlette/httpx deprecation warning; it did not fail the tests.

Measured placeholder contrast: foreground `#758098`, background `#fcfcfe`, 16 px text, ratio 3.869:1. Viewport measurements: narrow home and both cases used 320 CSS px with scroll width 320. The desktop cache-bug capture used a 1280 px viewport. These are browser layout checks, not physical-device or screen-reader testing.
