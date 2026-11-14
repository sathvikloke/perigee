# backend/data: SPHEREx archive search, cutouts and frame processing

Owner: Sagar (issue #2). Branch `codex/sagar-data`. This is the processor candidate
built in Sagar's session. It follows the integration board decisions 1–6 on
`codex/sathvik-science` and plugs into API candidate A (PR #12) unchanged.

Network code (`archive.py`) is separate from pure FITS processing (`process.py` and
helpers). Nothing here imports the web app or keeps global request state.

## Functions

```python
from backend.data import (SearchQuery, search_observations, fetch_cutout, process_frame,
                          fetch_and_process, process_frame_for_api, ObservationDescriptor,
                          FrameContext, CatalogTarget, DataError)

q = SearchQuery.validated(330.84, -56.786, fov_arcmin=6, limit=24)   # raises on bad input, never clips
res = search_observations(q)                # SearchResult; res.to_dict() is JSON
obs = res.observations[0]                   # ObservationDescriptor
frame = fetch_and_process(obs, q.ra_deg, q.dec_deg, q.fov_arcmin)    # FrameProduct
rec = frame.with_data_urls()                # FrameRecord dict with PNG data URLs filled in

# API hook (what PR #12 calls first): pure, dict in, dict out
out = process_frame_for_api(fits_bytes, meta)   # {"record", "image_png", "flag_png"}
```

Frame tokens: put `obs.public_dict()` and the query center/fov in the signed payload. On
`/frame`, rebuild with `ObservationDescriptor.from_public_dict(payload)`. That re-checks the
source URL against the IRSA allowlist and recomputes `frame_key`, so a tampered payload
can't redirect the fetch.

## Errors (all subclass `DataError`, `.to_dict()` gives code/message/retryable)

| Class | code | HTTP | retryable | When |
|---|---|---|---|---|
| InvalidCoordinates | INVALID_COORDINATES | 400 | no | RA/Dec missing, non-finite, out of range, not a number |
| InvalidFieldOfView | INVALID_FIELD_OF_VIEW | 400 | no | fov outside 2–10 arcmin |
| InvalidRequest | INVALID_REQUEST | 400 | no | limit outside 1–48, collection not allowlisted (API-A splits these into INVALID_LIMIT / INVALID_COLLECTION) |
| UpstreamUnavailable | UPSTREAM_UNAVAILABLE | 502 | yes (no for 4xx) | IRSA 5xx, HTML page instead of data, every collection failed |
| UpstreamTimeout | UPSTREAM_TIMEOUT | 504 | yes | IRSA too slow |
| UnsupportedData | UNSUPPORTED_DATA | 422 | no | not FITS, truncated, missing IMAGE/WCS, wrong file for the observation |
| ProcessingFailed | PROCESSING_FAILED | 500 | no | our bug on valid input (message never has a path or stack trace) |

"Position not covered" is **not** an error. It is `quality.status == "not_covered"`.

## Search behaviour

- IRSA SIA v2, collections `spherex_dr1` and `spherex_qr3`, searched in parallel. A record
  matches when its footprint touches an 18″ circle at the field center.
- IRSA's SIA answered about half of requests with a fast `502 Proxy Error` HTML page during
  the event (measured 2026-11-14). Search makes up to 4 attempts per collection within a
  25 s budget; 7 of 8 test positions came back complete and the 8th `partial`.
- `status`: `ready`, `empty` (successful query with no rows), or `partial` (one collection
  failed or the archive overflowed). If every collection fails, it raises. One failure plus
  zero rows also raises, because that is not "empty".
- More matches than `limit`: returns `limit` descriptors spread evenly over the whole date
  range, `truncated: true`, `total_matches` = the real count (`null` on archive overflow).
- Sorted by `mjd`, then `frame_key`. Descriptor time is SIA `t_min` (exposure start); the
  processed frame replaces it with mid-exposure time from the file header.

## FrameRecord meaning (for Akshobya)

Field names match `backend/models/frame.py` (PR #12). Extra fields are additive.

- **Identity**: `observation_id` is the archive ID (`2026W18_1A_0516_1`). One observation
  has up to 6 detector images, so the image identity is `frame_key` = `2026W18_1A_0516_1_D3`.
- **Time**: `observed_at_utc` / `mjd` are mid-exposure (`DATE-AVG`/`MJD-AVG`), `time_basis` says so.
- **Grid** (`registration`): TAN projection, north up, east left, centered on the query
  center (never on the moving target), 256×256 px. `grid_id` is equal for frames on the
  same grid. Pixel (0,0) is the top-left corner, with x right and y down. At 6′ one display
  pixel is 1.4″, while SPHEREx pixels are 6.15″, so the display is interpolated, not sharper.
- **Image**: grey + alpha PNG. Transparent means no data: outside the cutout, or a source
  pixel without a value such as a saturated star core. Missing data is never filled in.
- **Flag overlay**: hatched magenta where a pixel has an adverse SPHEREx flag. The hatching
  is a pattern, so the meaning doesn't depend on color.
- **Wavelength**: `wavelength_um`/`bandwidth_um` at one position: the catalog-predicted
  target for presets, the query center for live searches. `wavelength_location` says which.
  `null` when that position is off the image. It changes across every SPHEREx image.
- **Quality** at the same position (circle of 2.5 native pixels, ~19 pixels):
  `not_covered` = position off the image; `flagged` = any adverse flag or no-value pixel
  there; `unknown` = no flag mask, no variance map, or under 10 usable pixels; `clear` =
  none of those. Clear is a pixel screen, **not** a detection or a brightness measurement.
  `SOURCE` and `FULLSAMPLE` are informational, not problems.
- **Display scale**: `per_frame` means brightness is not comparable between frames
  (`comparable_brightness: false`). `shared` means one stretch for a comparison set; even then
  the brightness is a display, not calibrated photometry.
- **Marker**: only `kind: "catalog_prediction"`, labeled "Catalog prediction (not a
  detection)". It is never a measured position. It is `null` for live queries.

## Numbers measured

| What | Value |
|---|---|
| Process one frame (no network) | ~0.1 s |
| Download one cutout from IRSA | 3.5–10 s (~4 MB, mostly the PSF table) |
| Live search, both collections | 1.5–6 s |
| Frame JSON with data-URL PNGs | 40–65 KB |
| Runtime deps (numpy, astropy, pillow, pyerfa, pyyaml) | ~85 MB installed |

`requirements.txt` here lists what this package needs. PR #12's `backend/requirements.txt`
already pins compatible versions (astropy 8.0.2, numpy 2.5.4, pillow 13.0.0); its 121 API
tests pass with this package in place. `astropy.time` is kept off the frame path so
a serverless run never tries to download leap-second tables.

## Tests

```bash
python -m pytest backend/tests/data -q      # 74 tests, ~2 s, no network, no raw dataset needed
```

The fixtures are two real SPHEREx files trimmed to ~100 KB and one real SIA response cut
to 6 rows (see `backend/tests/data/fixtures/README.md`). Broken variants are built in code.
