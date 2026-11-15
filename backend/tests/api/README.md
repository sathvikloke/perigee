# API protocol tests and example payloads

```sh
~/Library/Python/3.9/bin/uv venv --python 3.12 .venv     # once
~/Library/Python/3.9/bin/uv pip install --python .venv/bin/python -r backend/requirements-dev.txt
.venv/bin/python -m pytest backend/tests/api -q          # no network
PERIGEE_DEV_MODE=1 .venv/bin/uvicorn backend.main:app --port 8000
PERIGEE_DEV_MODE=1 .venv/bin/python -m backend.tests.api.live_search_check   # real IRSA search
PERIGEE_DEV_MODE=1 .venv/bin/python -m backend.tests.api.live_frame_check    # real cutout fetch + probe
PERIGEE_DEV_MODE=1 .venv/bin/python -m backend.tests.api.make_examples [--live]
```

`PERIGEE_DEV_MODE=1` enables a fixed development signing secret. It is ignored when
`VERCEL_ENV=production` or `PERIGEE_ENV=production`. Deployments set
`PERIGEE_TOKEN_SECRET` (at least 32 bytes).

## Example labels (`examples/`)

- `*.live.json`: produced by this API from the real NASA/IPAC IRSA archive. The tokens are
  signed with the development secret and expire after 6 hours, so they only illustrate the shape.
  `frame_response.live.json` is a real end-to-end frame for Eps Ind A (RA 330.84, Dec -56.786,
  FOV 6 arcmin). The real token was verified, the real cutout was fetched from IRSA and processed
  by processor-a (`backend/data/process.py` from `origin/codex/parallel-05-processor-a` @ 9c9049a,
  temporarily copied in and not committed here).
- `*.fixture.json`: produced through the real routes with fixture archive or processor
  stand-ins. These are not NASA results. `frame_response.fixture.json` copies identity, date,
  wavelength and quality from the science-verified `fair_comparison` frame A, but its image
  is a synthetic 16x16 placeholder and `provenance.data_origin` is `"fixture"`.
- `error.*.json`: real error envelopes from the routes.

## Error codes added to the contract list

`INVALID_LIMIT`, `INVALID_COLLECTION`, `INVALID_REQUEST` (malformed JSON or an unknown
field), `UNSUPPORTED_SCHEMA_VERSION`, `PROCESSOR_UNAVAILABLE` (503: `backend.data.process_frame`
is not installed), `SERVICE_MISCONFIGURED` (503: no signing secret), `NOT_FOUND`,
`METHOD_NOT_ALLOWED` and `INTERNAL_ERROR`. The HTTP status for `TOKEN_EXPIRED` is 400, and
`details.action` is `"refresh_search"`.
