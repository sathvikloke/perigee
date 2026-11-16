# Perigee integration contract — version 1

This is the shared build contract for the six individualized coding prompts. It takes precedence over older architecture paragraphs that describe a persistent filesystem server or an in-memory job queue. The product is a responsive web app. Native iOS/Android development, app-store distribution, account registration, and a runtime language model are outside this sprint.

## Product and deployment decision

Use React, TypeScript, and Vite in `frontend/`. Use FastAPI, Python, Astropy, NumPy, and a small PNG encoder such as Pillow in `backend/`. Pick compatible supported package versions when implementation starts and record lockfiles; do not blindly copy the old Python 3.9 research environment into the production runtime. All application and processing implementation is new work in the event repository.

Vercel hosts the public web app and Python API. Prefer one Vercel Services deployment with two services and ordered rewrites: `/api/(.*)` goes to the Python service; the remaining paths go to the frontend. Services is currently Beta, so Suhrit must validate it with the first deployed shell. If it blocks progress for more than 30 minutes, use two Vercel projects with the same API contract and an explicit frontend API-base setting. Record that fallback once; do not let individual agents choose different hosting models.

The frontend always uses an API client module. Its default base is the same origin, with the stable prefix `/api/v1`. A fallback deployment may set a public API origin, which is not a secret. Do not hardcode a developer laptop, preview hostname, API token, or one person's local file path into production code.

The existing Vercel project is `perigee` in the `sathviklokes-projects` team. Project setup is complete, but no application deployment existed when these prompts were prepared. Suhrit should use the [deployment handoff](DEPLOYMENT.md) to locate and verify the project, Git settings and first deployment. Reuse that project instead of creating an unrelated duplicate.

## The execution model

An archive search returns bounded observation descriptors. The browser then requests individual processed frames with a concurrency limit of two. Each frame request downloads and processes one small service cutout, returns a small JSON result, and finishes. The UI can display completed frames while later requests are in flight. Progress belongs to this browser session; the first version does not promise a durable server-side job.

This replaces the earlier proposed `/api/jobs/:id` interface. Do not implement an in-memory queue, background thread that outlives the response, or filesystem database to preserve jobs across Vercel invocations. If processing one bounded frame cannot fit the measured runtime budget, report that evidence to Sathvik and Suhrit. A durable queue is a later coordinated architecture decision, not a hidden dependency that one agent adds independently.

Preselected investigation assets are small, verified products generated during the event and stored under `backend/content/presets/`. They may be bundled read-only with the backend if the package remains small. Full FITS downloads and archive mirrors stay outside Git and deployment bundles. Live results may be returned as compact PNG data URLs in JSON. A shared runtime cache is an optional acceleration; its absence must not change correctness.

## Repository ownership

| Owner | Primary files | Important boundary |
|---|---|---|
| Akshobya | `frontend/**` | Owns frontend package files, UI, API client, browser storage, exports, and browser tests |
| Aditya | `backend/main.py`, `backend/models/**`, `backend/routes/search.py`, `backend/routes/frames.py`, `backend/routes/health.py`, `backend/security/**`, `backend/tests/api/**`, backend dependency files | Owns API schemas and request orchestration; coordinates dependency additions |
| Suhrit | `backend/platform/**`, `backend/routes/catalog.py`, `backend/tests/platform/**`, `vercel.json`, `.github/workflows/**`, deployment documentation | Owns storage adapters, catalog/assets serving, deployment and operational checks |
| Sagar | `backend/data/**`, `backend/tests/data/**`, `tools/ingest/**`, `backend/content/presets/**` | Owns the scientific image processing implementation and verified generated outputs |
| Sathvik | `science/**`, `backend/content/cases/**`, `backend/content/targets.json`, demo/pitch documents, integration decisions | Owns scientific acceptance, authored investigation content and final product decisions |
| Neeraj | `qa/**`, QA findings and screenshot evidence | Optional support; no mandatory feature depends on his availability |

If a file is outside your area, propose the smallest change to its owner rather than silently taking it over. A necessary shared-interface fix can be coordinated in the assigned GitHub issue. Do not replace another person's package manifest, reformat their directory, or merge a broad rewrite because your local branch diverged. Use `codex/<name>-<workstream>` branches and focused pull requests.

## Data ownership

Only Sathvik and Sagar need the full local dataset. Everyone else may use small, clearly labeled development fixtures and the shared API. A fixture is not a NASA observation unless it has verified source provenance. Never display synthetic test imagery as real sky data in the public demo. The old scripts and generated starter assets were removed; do not look in Trash or other chats to recover implementation. Work from the retained source data, public documentation, and these specifications.

The five named presets are Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, and R Draconis. Preset IDs use `barnards_star`, `epsilon_indi_b`, `wise_0855`, `rw_aurigae`, and `r_draconis`. Curated case IDs use `fair_comparison` and `moving_neighbor`; `coverage_is_not_detection` is optional. Stable IDs are part of saved evidence and should not be renamed for cosmetic reasons.

## HTTP endpoints

| Method and path | Owner | Result |
|---|---|---|
| `GET /api/v1/health` | Aditya, deployed by Suhrit | Version, service state, and capabilities without secrets |
| `GET /api/v1/presets` | Suhrit | Five preset descriptors and case associations |
| `GET /api/v1/cases/{case_id}` | Suhrit serving Sathvik's content | Authored prompts, scientific context, allowed conclusions and evidence requirements |
| `GET /api/v1/presets/{preset_id}/frames` | Suhrit serving Sagar's products | Ordered curated frame records for an immediate investigation |
| `GET /api/v1/assets/{asset_id}` | Suhrit | An allowlisted, versioned small image asset; no arbitrary filesystem paths |
| `POST /api/v1/search` | Aditya using Sagar's data adapter | Query summary and bounded observation descriptors with frame tokens |
| `POST /api/v1/resolve` | API and frontend integration | Live SIMBAD object-name lookup with catalog epoch, source and explicit search center |
| `POST /api/v1/frame` | Aditya using Sagar's data adapter | One processed frame record plus compact intensity and optional flag images |

These are intended endpoints, not a claim that an API already exists. API changes require an update to this file, a concrete example, and agreement from the affected frontend/backend owners. The API must return JSON errors for API failures; the frontend SPA fallback must never turn a broken API route into a successful HTML response.

## Query request

`POST /api/v1/search` accepts `schema_version: 1`, finite `ra_deg`, finite `dec_deg`, `fov_arcmin` defaulting to 6, and `limit` defaulting to 24. For this sprint, support field sizes from 2 through 10 arcminutes and limits from 1 through 48. RA must be in `[0,360)` and declination in `[-90,90]`. Reject NaN, infinity, strings that only partly parse, and silent clipping. A UI may normalize exactly 360 degrees to 0 only if it visibly documents that normalization and sends the normalized value.

The frontend explicitly sends a default limit of **12** to bound initial loading; the API omission default remains 24 for existing clients. The coordinate form also accepts strict `HH:MM:SS` RA and signed `DD:MM:SS` Dec, converts them to decimal degrees before the API call, and rejects invalid minutes, seconds and ranges. A decimal RA is always degrees, never hours.

`POST /api/v1/resolve` accepts `{"schema_version":1,"name":"Barnard's Star"}` (one nonempty name, at most 80 characters). It requests SIMBAD through the fixed CDS-endorsed Harvard Sesame HTTPS endpoint; redirects are refused, the response is capped at 128 KiB, and the entire lookup has a 12-second deadline. No arbitrary resolver URL is accepted. `OBJECT_NOT_FOUND` (404) differs from an unavailable or timed-out resolver (503/504).

A successful result includes `name`, `catalog_position` (`ra_deg`, `dec_deg`, `epoch_jyear`), `search_center` (the same fields plus `kind`), `source`, `source_url`, `position_reference`, and `note`, alongside the usual schema/request IDs. For example, the live Barnard result preserves its J2000 catalog position (269.45207696°, 4.69336497°) while its search center is the validated 2026 finder prediction (269.4462585584787°, 4.768324486236583°). A curated finder center is used only when the resolved identity and catalog position agree with that target; other objects retain an explicitly labeled epoch-2000 catalog center. This lookup does not claim a detection or silently turn an arbitrary coordinate query into a preset. Live response examples are retained in `qa/audit-followups/search-resolver-live.json`.

Optional `collection_ids` must come from a server-maintained allowlist. Do not let a user provide an upstream URL, arbitrary collection expression, filesystem path, or executable query fragment. If the service initially supports DR1 and QR3 wide-survey collections only, report that scope explicitly. A zero result in that scope is not an all-mission absence claim. A selected coordinate must actually reach the archive; do not silently substitute the nearest preset.

The search response includes `schema_version`, `request_id`, `query`, `status`, `observations`, `returned_count`, `total_matches` when known, `truncated`, `warnings`, `collections_queried`, and `queried_at_utc`. Status is `ready`, `partial`, or `empty`; transport or upstream failure uses the error response. Partial means some useful results exist but a collection failed or a documented limit interrupted retrieval. Empty requires a successful query with no matching returned records, not a timeout. In the implemented API, `collections_failed` lists collections whose query failed, and `collections_capped` lists collections where the archive returned its record cap (SIA `MAXREC`, 2000); either makes the status `partial`, and a cap also sets `truncated: true` and `total_matches: null`. Returning an evenly spaced subset because of the caller's `limit` is not an interruption: the status stays `ready`, `truncated` is true and `total_matches` is known. Matching is a coverage search: an observation matches when its footprint contains the query position (a fixed 3.6-arcsecond radius), so `fov_arcmin` sets the cutout and display field but does not change which observations match. When more than `limit` match, the response is an evenly spaced-in-time sample that always includes the earliest and latest match; raising `limit` (up to 48) shows more. Version 1 has no date filter or pagination.

Observation descriptors contain stable `observation_id`, `collection_id`, `observed_at_utc`, `mjd`, `detector`, `source_url`, and `frame_token`. Values not provided by the archive remain null or omitted as specified by the schema; they must not be invented. Sort descriptors by numeric observation time with a stable ID tie breaker. Filesystem modification times and retrieval timestamps are not observation times.

Aditya signs the frame token server-side. It binds a descriptor to the normalized query, supported collection, expiry and token version. The secret stays in backend environment variables. Sagar supplies validated source metadata; the caller cannot replace an upstream URL inside a signed token. Suhrit supplies the secret through the platform, never through public frontend variables. Token expiry should allow a normal investigation session; an expired token produces a clear refresh action and preserves the user's notes.

## One-frame request and response

`POST /api/v1/frame` accepts `schema_version: 1` and a server-issued `frame_token`. The server verifies the token before fetching anything. It downloads only allowlisted archive resources, checks redirects and byte limits, and passes bytes plus normalized query metadata to the processor. A malformed token is a client error. An unavailable source is an upstream failure. Unsupported or corrupt FITS data is an explicit processing failure. These outcomes must remain distinct in logs and user-facing summaries.

The response includes a `FrameRecord`. Required identity fields are `frame_id`, `observation_id`, `collection_id`, `observed_at_utc`, `mjd`, and `source_url`. The wavelength fields are `wavelength_um` and `bandwidth_um`, each nullable, with a `wavelength_location` explanation identifying the target or query position. Do not label one sampled wavelength as the wavelength of every pixel in the image.

`image` contains `src`, `width`, `height`, and `media_type`. `src` is a small PNG data URL for live results or an allowlisted same-origin asset URL for curated frames. `flag_image` has the same shape or is null. The new code should target a 256 by 256 common display grid unless measured performance or input sampling warrants another documented size. Resampling does not create additional physical resolution; do not market the display pixel count as telescope resolution.

`registration` records center RA/Dec, field of view, angular scale, orientation and the display method. The fixed grid should be north up and east left where the chosen projection permits that convention. It must be identical for frames compared in a session. A predicted moving-source marker may change coordinates on that fixed grid; moving the entire grid with the source would suppress the visual motion being investigated.

`quality` includes `status` (`clear`, `flagged`, `not_covered`, or `unknown`), `covered`, `valid_aperture_pixels`, `adverse_aperture_pixels`, `flag_names`, and `notes`. Pixel counts may be null when unavailable; missing data is never encoded as a clean count of zero. A clear screen means the stated checks passed near the selected position. It is not a detection, calibrated flux, or astrometric validation certificate.

`display_scale` includes `mode` (`shared` or `per_frame`), `method`, and any numerical limits actually used. Curated comparisons should use a shared stretch when practical. A live sequence that uses per-frame auto-contrast must visibly state that brightness is not directly comparable. The interface must not imply that a changing white pixel necessarily means changing luminosity. Document background subtraction, interpolation and clipping when they are applied.

`marker` is null or contains pixel coordinates, `kind: catalog_prediction`, an epoch and a source explanation. Never return a marker labeled as a detection unless an independently tested detection algorithm exists and the team has explicitly approved that feature. `provenance` contains retrieval time, original URL, file hash where available, processing version and source acknowledgments. `limitations` is an array of concrete statements attached to the result, not hidden in a generic footer.

## Error and loading behavior

Use a common error envelope containing `schema_version`, `request_id`, and `error` with `code`, a short `message`, `retryable`, and optional non-sensitive details. Expected codes include `INVALID_COORDINATES`, `INVALID_FIELD_OF_VIEW`, `INVALID_FRAME_TOKEN`, `TOKEN_EXPIRED`, `UPSTREAM_UNAVAILABLE`, `UPSTREAM_TIMEOUT`, `UNSUPPORTED_DATA`, `PROCESSING_FAILED`, and `RATE_LIMITED`. Use meaningful HTTP statuses: 400/422 for invalid input, 404 for unknown preset/case/asset, 429 for rate limits, and 502/503/504 for appropriate upstream failures.

The UI distinguishes initial loading, metadata found, individual frame processing, partial results, genuinely empty query results, and failure. A failed frame does not reorder the remaining sequence or discard completed frames. Changing coordinates cancels or ignores stale requests by request identity. A response from an older query must not appear in the new query's viewer. Keep user-authored evidence notes intact when network calls fail.

Bound work in several places. The initial search has a small result limit. Browser frame concurrency is two. Upstream calls have connect/read timeouts and a maximum response size. A request has a soft processing budget below the deployed function's hard limit. An unsuccessful retry is reported; there is no unbounded loop. Do not create a hundred automatic calls because a slider moved quickly. Debounce search submission appropriately and avoid refetching a frame already available in the current session.

## Content and evidence contracts

A case contains a stable ID, title, target ID, short opening question, scientific background, ordered steps, selected observation IDs, source links, a supported-conclusion guide, and limitations. Sathvik authors the content; Suhrit serves it without changing scientific meaning; Akshobya turns steps into a usable experience. Keep wording short in the interface. The long scientific explanation belongs in a collapsible explanation or source link, not a wall of text before the first image.

The evidence card has `schema_version`, an ID generated locally, creation/update times, case ID when present, query coordinates, selected frame identities, dates/wavelengths/quality summaries, claim, observations, uncertainty, sources, and application version. Save it in browser local storage and export JSON. Printing is a separate rendering of the same evidence. Importing a saved file is optional and must validate its shape if implemented. Do not use browser storage for raw FITS, API secrets, or unbounded image histories.

Each newly selected frame also records optional `rendering`: the supplied `display_scale` and `registration` objects, image and flag-image references, resolved product URLs, and the actual archive cutout URL when supplied. These are available processing parameters and source references, not embedded FITS data or a complete rendering recipe. Older cards that lack this snapshot keep `rendering: null`; matching source hashes and method names cannot recover their original numerical display settings. A preview uses a current thumbnail only when its recorded source, processing and rendering metadata match.

After the learner opens the reference, optional `reference_evidence` preserves the case version, full conclusion guide, selected source identities, pinned review links and applicable WISE detector controls separately from the learner's notes. It remains absent before that action. Existing snapshots retain their original guide and values instead of silently adopting a revised case. The WISE 5.36-arcsecond value describes the same detector pixel mapped through two coordinate solutions; it is not a precision measurement of celestial motion.

Sharing a URL preserves coordinates, field of view and optional case ID. It does not automatically share private notes stored in one browser. Label the action accordingly. If a later shared-evidence service is introduced, it needs its own explicit contract and access behavior. Do not claim that a coordinate URL reproduces a person's written conclusion unless those fields are actually included in a tested export or sharing mechanism.

## Python handoff boundary

Sagar supplies archive-query and frame-processing functions under `backend/data/`, with typed plain inputs and outputs that Aditya can wrap. Network access should be separable from FITS transformation so unit checks can use tiny local fixtures. The processor accepts bytes and metadata rather than assuming a specific laptop path. Its output contains JSON-serializable metadata and image bytes or an agreed small encoding. It must not import the web application or mutate global request state.

Aditya validates HTTP input, verifies tokens, enforces budgets and maps known failures into the public envelope. Suhrit supplies cache/catalog/asset adapters with stable interfaces. Sathvik validates sample outputs against original headers and surrounding sources. Akshobya renders only documented fields. This separates science correctness, protocol correctness, deployment correctness and presentation correctness without requiring everyone to download the archive.

## Acceptance and integration gate

The first shared gate is one preset loaded from the deployed API into the actual frontend with its dates, quality explanation and evidence card. The second gate is a non-preset coordinate query that returns real archive descriptors and at least one processed frame or an honest documented empty/error response. Include a known-covered non-preset coordinate for the positive-path test so the gate cannot pass solely because every query fails gracefully.

Contract checks should cover missing wavelength, flagged central pixels, an uncovered source position, expired token, partial archive failure, stale frontend response, and source URL preservation. Scientific checks are separate from HTTP checks. A successful JSON parse is not a valid astronomical comparison. A beautiful screenshot is not proof that a live coordinate reached NASA's archive.

Record tested commit, environment, command, inputs, observed result and remaining limitations. Keep reports concise and actionable. A teammate should be able to reproduce a failing case without reconstructing a chat. If a contract change is necessary, update this file before asking other agents to adopt it and include an example of both the old and new behavior.

## Hosting references

The deployment owner should verify current platform details rather than rely on a model's old memory: [Vercel Services](https://vercel.com/docs/services), [Services routing](https://vercel.com/docs/services/routing), [FastAPI deployment](https://vercel.com/docs/frameworks/backend/fastapi), [Functions limits](https://vercel.com/docs/functions/limitations), and [Git integration](https://vercel.com/docs/git).
