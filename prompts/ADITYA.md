# Aditya R: Perigee AI coding master prompt

Role: **Backend API and bounded request orchestration**

GitHub owner: **@adityaraut09**

Suggested branch: `codex/aditya-api`

Repository: https://github.com/sathvikloke/perigee

Prepared November 14, 2026. This is an implementation assignment for your coding agent. Read the current repository instructions and state before editing. The named human's latest instructions and the current integration contract govern your work. This document is intentionally long so the agent has the complete project context; its reference sections are not a demand to implement every workstream.

## Your assignment

You are the coding agent working with Aditya on Perigee's backend API. Your job is to turn explicit browser requests into bounded, traceable archive operations using Sagar's data adapter. The API must preserve the difference between invalid input, empty results, partial coverage, upstream failure and processing failure. A response that merely parses as JSON is not sufficient. The frontend needs stable meanings for every field so a learner never mistakes an operational problem for an astronomical finding.

Use FastAPI and typed models in the agreed backend structure. Inspect current files before scaffolding. Own the application entry point and the public request/response models, but keep scientific transformation in backend/data and platform/catalog behavior in Suhrit's modules. Make those boundaries easy to test independently. If a dependency requires a version change, coordinate it and commit the backend lockfile rather than leaving each teammate with a different environment.

The deployment model is stateless bounded requests. Search returns observation descriptors, and the browser requests one frame at a time with limited concurrency. Do not implement the earlier in-memory job queue proposal. Do not return a job identifier that only exists in one process or rely on a detached thread after the response. This choice keeps the first version compatible with Vercel without requiring a new database or durable queue.

You do not need the full raw dataset on your laptop. Use tiny synthetic fixtures for protocol tests and verified examples supplied by Sathvik or Sagar for integration. Keep synthetic examples clearly labeled. The live coordinate path still needs an intentional real archive smoke test. A backend that only knows five preset objects does not satisfy the assignment.

**Priority:** Make the public coordinate and frame APIs reliable, bounded, typed and scientifically traceable.

**You own:** backend/main.py, backend/models/**, backend/routes/search.py, backend/routes/frames.py, backend/routes/health.py, backend/security/**, backend/tests/api/** and backend dependency files.

**Coordinate before editing:** Do not take over frontend components, Sagar's scientific transform implementation, or Suhrit's deployment/storage modules. You coordinate shared backend dependencies and public schema changes.

**Your review perspective:** For this scenario, inspect validation, response schema, request budgets and error mapping. Implement the API boundary and reproducible protocol tests; coordinate scientific transformation with Sagar and deployed infrastructure behavior with Suhrit.

## Your ordered work packets

Work through the relevant packets as complete, verified slices. Inspect what teammates have already built. If a packet is complete, verify its boundary and continue; do not recreate it. The optional reference scenarios later in this document help diagnose risks and do not require dozens of new tests.

### 1. Define the typed public models

Implement the version-one query, descriptor, frame, quality, provenance and error models from the contract. Preserve units and nullability. Reject ambiguous values rather than coercing them into plausible defaults. Keep models independent of HTTP handlers where practical.

**Completion evidence:** Representative success, partial, empty and error payloads validate. Unknown wavelength and quality information survive serialization without becoming zero or an all-clear result. Share examples with Akshobya.

### 2. Create the FastAPI entry point

Wire the application, health route and modular routers without embedding scientific processing in main.py. Ensure API failures return JSON and a request identifier. Keep route prefixes consistent with the Vercel service receiving the original path.

**Completion evidence:** A direct request to /api/v1/health returns the expected JSON locally. Unknown API routes do not return frontend HTML. Suhrit can deploy the application entry point without renaming every route.

### 3. Validate coordinate queries

Enforce finite RA/Dec, field-of-view and result-limit bounds on the server. Use an allowlist for collections and reject arbitrary upstream URLs. Preserve normalized inputs in the response and make errors easy for the UI to display.

**Completion evidence:** Test poles, RA boundaries, missing fields, NaN-like input and oversized limits. Invalid requests do not reach the archive adapter, and valid requests retain the exact intended coordinate.

### 4. Integrate archive metadata search

Call Sagar's search adapter with a bounded query and map its outcomes to ready, partial or empty. Preserve collection scope, observation identity, dates and source URLs. Sort by observation time with a stable tie breaker.

**Completion evidence:** A known-covered non-preset coordinate returns real descriptors. One failed collection does not erase the other collection's results or masquerade as zero coverage.

### 5. Implement frame-token issuance

Sign a bounded descriptor and normalized query server-side with a version and expiry. Keep the signing secret in backend configuration. Validate the allowed archive source structure before issuing a token and before using it.

**Completion evidence:** Tampered, expired and malformed tokens fail before fetching any resource. A valid token can be replayed within its intended session window without depending on process-local state.

### 6. Implement one-frame processing orchestration

Verify the token, retrieve the bounded cutout through the data adapter, call the processor and serialize a compact frame record. Keep HTTP concerns outside the scientific transform. Enforce response-size and processing budgets.

**Completion evidence:** One real returned observation produces a traceable frame. Corrupt FITS, missing data and upstream timeout have distinct public errors. The response does not include raw FITS or secrets.

### 7. Make failure semantics consistent

Centralize known error mapping and request identifiers. Decide which failures are retryable and preserve useful non-sensitive details. Keep internal stack traces out of public responses while retaining enough diagnostics for the team.

**Completion evidence:** Akshobya can distinguish empty, partial, invalid and unavailable states without parsing prose. Tests cover an upstream HTML error page, 503, expired token and unsupported file.

### 8. Bound work and avoid duplicate storms

Coordinate timeout and retry policies with Sagar and the frontend. Limit response descriptors, per-frame work and upstream bytes. Do not stack unbounded retries across layers or let a slider trigger unlimited processing.

**Completion evidence:** Measure the upstream call count for one user action and one failure. An exhausted request terminates predictably, and already completed frontend frames remain useful.

### 9. Verify serverless behavior

Exercise a fresh application instance with no local cache or prior job state. Confirm dependency compatibility and the resolved Python entry point. Work with Suhrit on deployed route and cold-start smoke tests.

**Completion evidence:** The API works across separate invocations and does not assume a laptop filesystem. A successful local test is followed by a bounded deployed test of the same contract.

### 10. Publish the API handoff

Document implemented routes, model examples, error codes and exact test commands. Keep the contract current and the pull request focused. Coordinate any final schema differences before the frontend adopts them.

**Completion evidence:** Provide a real request/response example, known limitations and the tested commit. Do not close the issue until the frontend can consume at least one deployed preset and one live coordinate result.

## Your acceptance and handoff

The API is complete when a valid non-preset query reaches the archive, descriptors and individual frames preserve provenance, invalid inputs and token abuse are rejected, partial failures remain honest, and the deployed frontend can consume the contract without private backend knowledge.

Akshobya needs stable JSON examples and error meanings. Sagar needs the exact processor interface and budgets. Suhrit needs the entry point, environment variable names and deployment smoke commands. Sathvik needs the scientific fields and limitations preserved without reinterpretation.

## How to use the remaining reference

The integration contract defines shared interfaces and takes precedence over older architectural wording in the project plan. The project plan supplies the human story, bounded research findings, scientific scope, schedule and judging context. The operating guide explains how to carry out the assignment. The handoff recipes give concrete cross-team examples. The scenario library is a reference for relevant failure modes, not a mandatory exhaustive test suite.

All six teammates receive the same shared contract and reference facts, but the role, owned files, work packets and completion criteria above are individualized. Stay within that role unless the human explicitly reallocates work. Only Sathvik and Sagar need the full original dataset. No runtime AI model, model training or GPU is required. This is a responsive web app using Vercel, not a native mobile application.


---

Reference source: [docs/INTEGRATION_CONTRACT.md](https://github.com/sathvikloke/perigee/blob/main/docs/INTEGRATION_CONTRACT.md)

## Perigee integration contract — version 1

This is the shared build contract for the six individualized coding prompts. It takes precedence over older architecture paragraphs that describe a persistent filesystem server or an in-memory job queue. The product is a responsive web app. Native iOS/Android development, app-store distribution, account registration, and a runtime language model are outside this sprint.

### Product and deployment decision

Use React, TypeScript, and Vite in `frontend/`. Use FastAPI, Python, Astropy, NumPy, and a small PNG encoder such as Pillow in `backend/`. Pick compatible supported package versions when implementation starts and record lockfiles; do not blindly copy the old Python 3.9 research environment into the production runtime. All application and processing implementation is new work in the event repository.

Vercel hosts the public web app and Python API. Prefer one Vercel Services deployment with two services and ordered rewrites: `/api/(.*)` goes to the Python service; the remaining paths go to the frontend. Services is currently Beta, so Suhrit must validate it with the first deployed shell. If it blocks progress for more than 30 minutes, use two Vercel projects with the same API contract and an explicit frontend API-base setting. Record that fallback once; do not let individual agents choose different hosting models.

The frontend always uses an API client module. Its default base is the same origin, with the stable prefix `/api/v1`. A fallback deployment may set a public API origin, which is not a secret. Do not hardcode a developer laptop, preview hostname, API token, or one person's local file path into production code.

The existing Vercel project is `perigee` in the `sathviklokes-projects` team. Project setup is complete, but no application deployment existed when these prompts were prepared. Suhrit should use the [deployment handoff](https://github.com/sathvikloke/perigee/blob/main/docs/DEPLOYMENT.md) to locate and verify the project, Git settings and first deployment. Reuse that project instead of creating an unrelated duplicate.

### The execution model

An archive search returns bounded observation descriptors. The browser then requests individual processed frames with a concurrency limit of two. Each frame request downloads and processes one small service cutout, returns a small JSON result, and finishes. The UI can display completed frames while later requests are in flight. Progress belongs to this browser session; the first version does not promise a durable server-side job.

This replaces the earlier proposed `/api/jobs/:id` interface. Do not implement an in-memory queue, background thread that outlives the response, or filesystem database to preserve jobs across Vercel invocations. If processing one bounded frame cannot fit the measured runtime budget, report that evidence to Sathvik and Suhrit. A durable queue is a later coordinated architecture decision, not a hidden dependency that one agent adds independently.

Preselected investigation assets are small, verified products generated during the event and stored under `backend/content/presets/`. They may be bundled read-only with the backend if the package remains small. Full FITS downloads and archive mirrors stay outside Git and deployment bundles. Live results may be returned as compact PNG data URLs in JSON. A shared runtime cache is an optional acceleration; its absence must not change correctness.

### Repository ownership

| Owner | Primary files | Important boundary |
|---|---|---|
| Akshobya | `frontend/**` | Owns frontend package files, UI, API client, browser storage, exports, and browser tests |
| Aditya | `backend/main.py`, `backend/models/**`, `backend/routes/search.py`, `backend/routes/frames.py`, `backend/routes/health.py`, `backend/security/**`, `backend/tests/api/**`, backend dependency files | Owns API schemas and request orchestration; coordinates dependency additions |
| Suhrit | `backend/platform/**`, `backend/routes/catalog.py`, `backend/tests/platform/**`, `vercel.json`, `.github/workflows/**`, deployment documentation | Owns storage adapters, catalog/assets serving, deployment and operational checks |
| Sagar | `backend/data/**`, `backend/tests/data/**`, `tools/ingest/**`, `backend/content/presets/**` | Owns the scientific image processing implementation and verified generated outputs |
| Sathvik | `science/**`, `backend/content/cases/**`, `backend/content/targets.json`, demo/pitch documents, integration decisions | Owns scientific acceptance, authored investigation content and final product decisions |
| Neeraj | `qa/**`, QA findings and screenshot evidence | Optional support; no mandatory feature depends on his availability |

If a file is outside your area, propose the smallest change to its owner rather than silently taking it over. A necessary shared-interface fix can be coordinated in the assigned GitHub issue. Do not replace another person's package manifest, reformat their directory, or merge a broad rewrite because your local branch diverged. Use `codex/<name>-<workstream>` branches and focused pull requests.

### Data ownership

Only Sathvik and Sagar need the full local dataset. Everyone else may use small, clearly labeled development fixtures and the shared API. A fixture is not a NASA observation unless it has verified source provenance. Never display synthetic test imagery as real sky data in the public demo. The old scripts and generated starter assets were removed; do not look in Trash or other chats to recover implementation. Work from the retained source data, public documentation, and these specifications.

The five named presets are Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, and R Draconis. Preset IDs use `barnards_star`, `epsilon_indi_b`, `wise_0855`, `rw_aurigae`, and `r_draconis`. Curated case IDs use `fair_comparison` and `moving_neighbor`; `coverage_is_not_detection` is optional. Stable IDs are part of saved evidence and should not be renamed for cosmetic reasons.

### HTTP endpoints

| Method and path | Owner | Result |
|---|---|---|
| `GET /api/v1/health` | Aditya, deployed by Suhrit | Version, service state, and capabilities without secrets |
| `GET /api/v1/presets` | Suhrit | Five preset descriptors and case associations |
| `GET /api/v1/cases/{case_id}` | Suhrit serving Sathvik's content | Authored prompts, scientific context, allowed conclusions and evidence requirements |
| `GET /api/v1/presets/{preset_id}/frames` | Suhrit serving Sagar's products | Ordered curated frame records for an immediate investigation |
| `GET /api/v1/assets/{asset_id}` | Suhrit | An allowlisted, versioned small image asset; no arbitrary filesystem paths |
| `POST /api/v1/search` | Aditya using Sagar's data adapter | Query summary and bounded observation descriptors with frame tokens |
| `POST /api/v1/frame` | Aditya using Sagar's data adapter | One processed frame record plus compact intensity and optional flag images |

These are intended endpoints, not a claim that an API already exists. API changes require an update to this file, a concrete example, and agreement from the affected frontend/backend owners. The API must return JSON errors for API failures; the frontend SPA fallback must never turn a broken API route into a successful HTML response.

### Query request

`POST /api/v1/search` accepts `schema_version: 1`, finite `ra_deg`, finite `dec_deg`, `fov_arcmin` defaulting to 6, and `limit` defaulting to 24. For this sprint, support field sizes from 2 through 10 arcminutes and limits from 1 through 48. RA must be in `[0,360)` and declination in `[-90,90]`. Reject NaN, infinity, strings that only partly parse, and silent clipping. A UI may normalize exactly 360 degrees to 0 only if it visibly documents that normalization and sends the normalized value.

Optional `collection_ids` must come from a server-maintained allowlist. Do not let a user provide an upstream URL, arbitrary collection expression, filesystem path, or executable query fragment. If the service initially supports DR1 and QR3 wide-survey collections only, report that scope explicitly. A zero result in that scope is not an all-mission absence claim. A selected coordinate must actually reach the archive; do not silently substitute the nearest preset.

The search response includes `schema_version`, `request_id`, `query`, `status`, `observations`, `returned_count`, `total_matches` when known, `truncated`, `warnings`, `collections_queried`, and `queried_at_utc`. Status is `ready`, `partial`, or `empty`; transport or upstream failure uses the error response. Partial means some useful results exist but a collection failed or a documented limit interrupted retrieval. Empty requires a successful query with no matching returned records, not a timeout.

Observation descriptors contain stable `observation_id`, `collection_id`, `observed_at_utc`, `mjd`, `detector`, `source_url`, and `frame_token`. Values not provided by the archive remain null or omitted as specified by the schema; they must not be invented. Sort descriptors by numeric observation time with a stable ID tie breaker. Filesystem modification times and retrieval timestamps are not observation times.

Aditya signs the frame token server-side. It binds a descriptor to the normalized query, supported collection, expiry and token version. The secret stays in backend environment variables. Sagar supplies validated source metadata; the caller cannot replace an upstream URL inside a signed token. Suhrit supplies the secret through the platform, never through public frontend variables. Token expiry should allow a normal investigation session; an expired token produces a clear refresh action and preserves the user's notes.

### One-frame request and response

`POST /api/v1/frame` accepts `schema_version: 1` and a server-issued `frame_token`. The server verifies the token before fetching anything. It downloads only allowlisted archive resources, checks redirects and byte limits, and passes bytes plus normalized query metadata to the processor. A malformed token is a client error. An unavailable source is an upstream failure. Unsupported or corrupt FITS data is an explicit processing failure. These outcomes must remain distinct in logs and user-facing summaries.

The response includes a `FrameRecord`. Required identity fields are `frame_id`, `observation_id`, `collection_id`, `observed_at_utc`, `mjd`, and `source_url`. The wavelength fields are `wavelength_um` and `bandwidth_um`, each nullable, with a `wavelength_location` explanation identifying the target or query position. Do not label one sampled wavelength as the wavelength of every pixel in the image.

`image` contains `src`, `width`, `height`, and `media_type`. `src` is a small PNG data URL for live results or an allowlisted same-origin asset URL for curated frames. `flag_image` has the same shape or is null. The new code should target a 256 by 256 common display grid unless measured performance or input sampling warrants another documented size. Resampling does not create additional physical resolution; do not market the display pixel count as telescope resolution.

`registration` records center RA/Dec, field of view, angular scale, orientation and the display method. The fixed grid should be north up and east left where the chosen projection permits that convention. It must be identical for frames compared in a session. A predicted moving-source marker may change coordinates on that fixed grid; moving the entire grid with the source would suppress the visual motion being investigated.

`quality` includes `status` (`clear`, `flagged`, `not_covered`, or `unknown`), `covered`, `valid_aperture_pixels`, `adverse_aperture_pixels`, `flag_names`, and `notes`. Pixel counts may be null when unavailable; missing data is never encoded as a clean count of zero. A clear screen means the stated checks passed near the selected position. It is not a detection, calibrated flux, or astrometric validation certificate.

`display_scale` includes `mode` (`shared` or `per_frame`), `method`, and any numerical limits actually used. Curated comparisons should use a shared stretch when practical. A live sequence that uses per-frame auto-contrast must visibly state that brightness is not directly comparable. The interface must not imply that a changing white pixel necessarily means changing luminosity. Document background subtraction, interpolation and clipping when they are applied.

`marker` is null or contains pixel coordinates, `kind: catalog_prediction`, an epoch and a source explanation. Never return a marker labeled as a detection unless an independently tested detection algorithm exists and the team has explicitly approved that feature. `provenance` contains retrieval time, original URL, file hash where available, processing version and source acknowledgments. `limitations` is an array of concrete statements attached to the result, not hidden in a generic footer.

### Error and loading behavior

Use a common error envelope containing `schema_version`, `request_id`, and `error` with `code`, a short `message`, `retryable`, and optional non-sensitive details. Expected codes include `INVALID_COORDINATES`, `INVALID_FIELD_OF_VIEW`, `INVALID_FRAME_TOKEN`, `TOKEN_EXPIRED`, `UPSTREAM_UNAVAILABLE`, `UPSTREAM_TIMEOUT`, `UNSUPPORTED_DATA`, `PROCESSING_FAILED`, and `RATE_LIMITED`. Use meaningful HTTP statuses: 400/422 for invalid input, 404 for unknown preset/case/asset, 429 for rate limits, and 502/503/504 for appropriate upstream failures.

The UI distinguishes initial loading, metadata found, individual frame processing, partial results, genuinely empty query results, and failure. A failed frame does not reorder the remaining sequence or discard completed frames. Changing coordinates cancels or ignores stale requests by request identity. A response from an older query must not appear in the new query's viewer. Keep user-authored evidence notes intact when network calls fail.

Bound work in several places. The initial search has a small result limit. Browser frame concurrency is two. Upstream calls have connect/read timeouts and a maximum response size. A request has a soft processing budget below the deployed function's hard limit. An unsuccessful retry is reported; there is no unbounded loop. Do not create a hundred automatic calls because a slider moved quickly. Debounce search submission appropriately and avoid refetching a frame already available in the current session.

### Content and evidence contracts

A case contains a stable ID, title, target ID, short opening question, scientific background, ordered steps, selected observation IDs, source links, a supported-conclusion guide, and limitations. Sathvik authors the content; Suhrit serves it without changing scientific meaning; Akshobya turns steps into a usable experience. Keep wording short in the interface. The long scientific explanation belongs in a collapsible explanation or source link, not a wall of text before the first image.

The evidence card has `schema_version`, an ID generated locally, creation/update times, case ID when present, query coordinates, selected frame identities, dates/wavelengths/quality summaries, claim, observations, uncertainty, sources, and application version. Save it in browser local storage and export JSON. Printing is a separate rendering of the same evidence. Importing a saved file is optional and must validate its shape if implemented. Do not use browser storage for raw FITS, API secrets, or unbounded image histories.

Sharing a URL preserves coordinates, field of view and optional case ID. It does not automatically share private notes stored in one browser. Label the action accordingly. If a later shared-evidence service is introduced, it needs its own explicit contract and access behavior. Do not claim that a coordinate URL reproduces a person's written conclusion unless those fields are actually included in a tested export or sharing mechanism.

### Python handoff boundary

Sagar supplies archive-query and frame-processing functions under `backend/data/`, with typed plain inputs and outputs that Aditya can wrap. Network access should be separable from FITS transformation so unit checks can use tiny local fixtures. The processor accepts bytes and metadata rather than assuming a specific laptop path. Its output contains JSON-serializable metadata and image bytes or an agreed small encoding. It must not import the web application or mutate global request state.

Aditya validates HTTP input, verifies tokens, enforces budgets and maps known failures into the public envelope. Suhrit supplies cache/catalog/asset adapters with stable interfaces. Sathvik validates sample outputs against original headers and surrounding sources. Akshobya renders only documented fields. This separates science correctness, protocol correctness, deployment correctness and presentation correctness without requiring everyone to download the archive.

### Acceptance and integration gate

The first shared gate is one preset loaded from the deployed API into the actual frontend with its dates, quality explanation and evidence card. The second gate is a non-preset coordinate query that returns real archive descriptors and at least one processed frame or an honest documented empty/error response. Include a known-covered non-preset coordinate for the positive-path test so the gate cannot pass solely because every query fails gracefully.

Contract checks should cover missing wavelength, flagged central pixels, an uncovered source position, expired token, partial archive failure, stale frontend response, and source URL preservation. Scientific checks are separate from HTTP checks. A successful JSON parse is not a valid astronomical comparison. A beautiful screenshot is not proof that a live coordinate reached NASA's archive.

Record tested commit, environment, command, inputs, observed result and remaining limitations. Keep reports concise and actionable. A teammate should be able to reproduce a failing case without reconstructing a chat. If a contract change is necessary, update this file before asking other agents to adopt it and include an example of both the old and new behavior.

### Hosting references

The deployment owner should verify current platform details rather than rely on a model's old memory: [Vercel Services](https://vercel.com/docs/services), [Services routing](https://vercel.com/docs/services/routing), [FastAPI deployment](https://vercel.com/docs/frameworks/backend/fastapi), [Functions limits](https://vercel.com/docs/functions/limitations), and [Git integration](https://vercel.com/docs/git).


---

Reference source: [prompts/OPERATING_GUIDE.md](https://github.com/sathvikloke/perigee/blob/main/prompts/OPERATING_GUIDE.md)

## Operating guide for Perigee coding agents

### Read this as an implementation assignment

You are helping one named human teammate build Perigee during a two-day NASA Space Apps event. Your job is to deliver the concrete outputs in that person's brief, verify them, and hand them to the other owners in a form they can use. Do not stop after proposing a stack, describing your capabilities, or generating an attractive but disconnected mockup. Start by inspecting the current repository and your assigned issue, identify what already exists, and make the smallest useful implementation that advances your workstream.

This long document contains both instructions and reference material. The individual brief, current repository state, and integration contract determine your actions. The full project plan explains purpose and context. Read the role summary first, inspect the files that affect your task, then use the deeper reference sections as needed. You do not need to build every feature mentioned in background material. Respect the explicit ownership table and the difference between required work, optional improvements, and future aspirations.

The human remains responsible for decisions and can change priorities. When their latest message changes your assignment, incorporate that change while preserving relevant completed work. Do not reinterpret a quick status question as cancellation. Do not silently restart a project because your context was shortened. Maintain a short factual handoff note with the current branch, implemented behavior, tests, known issues, and next dependency. The note should help another person continue, not become a second competing specification.

### Establish the current state before editing

Inspect the working tree, branch, remotes, recent commits, and repository instructions. A teammate may already have merged a shell or a schema while this prompt was being written. Do not overwrite that work with a new scaffold. If the repository is still documentation-only, create only the portion you own. If a framework has already been chosen and works, follow it unless there is a concrete incompatibility with the agreed contract. A personal preference for another library is not sufficient reason to restart.

Identify the commands the repository actually exposes. A prompt may describe intended tests before those scripts exist. Do not claim a command passed if it was unavailable, silently skipped, or exited without exercising the behavior. When you add a needed script, make its purpose clear and keep it narrowly scoped. If dependency installation fails, preserve the error and diagnose the actual compatibility problem rather than switching runtimes repeatedly. Keep dependency changes in the package files owned by your workstream or coordinate them with the owner.

Use the repository's existing authentication for GitHub and Vercel when available. Never ask a teammate to paste credentials into a chat, commit environment values, or send secrets in email. A missing permission is a specific blocker to report with the exact action needed. It does not prevent you from developing against a local interface, writing a reproducible test case, or finishing independent parts of the assignment. Continue useful authorized work while waiting for access.

### Work in small complete slices

The first slice should cross a real boundary. For the frontend, that means a visible result from the actual API contract. For the API, it means a validated request producing an honest result using the data adapter. For processing, it means one original FITS cutout becoming a traceable display product. For deployment, it means a reachable service that returns the correct type of response. For science and content, it means one supported investigation with explicit evidence. For QA, it means a reproducible observation of the deployed product.

A slice is not complete because several files exist. It is complete when its input, processing, output and expected failure behavior have been exercised. Prefer one convincing vertical result over five unfinished abstractions. Once the slice works, generalize only the parts that are needed for the second target or the next required state. A two-day project rarely benefits from a universal plugin system, a configurable workflow language, or a new internal framework.

Keep the product visible throughout development. If you are building frontend behavior, open the actual page and inspect it. If you are building backend behavior, save a small request and response example that another person can replay. If you are handling data, inspect the output image alongside its metadata. If you are writing the pitch, use current screenshots and verified capabilities. Each workstream should leave evidence that the next owner can understand without trusting a verbal claim.

### Protect the shared contract

The API schema is the team's coordination mechanism. An independently reasonable field rename can break another person's progress. Before changing a public name, enum, route, unit or nullability rule, identify the affected consumer and propose the smallest compatible change. Include an example. If a change is additive and optional, explain its default. If it is breaking, coordinate both sides and record the contract revision. Do not quietly support two contradictory meanings under one field name.

Units belong in names and descriptions. Use degrees for API sky coordinates, arcminutes for field of view, micrometers for wavelength, and UTC for observation timestamps. Preserve numeric MJD when supplied by the archive. A display label can be friendlier, but it must not alter the underlying value. Separate observation time, retrieval time, processing time and local save time. These represent different events and should never be substituted for one another to make a timeline appear populated.

Null means unavailable or not established; it is not zero. This distinction matters for wavelength, quality counts, uncertainty and coverage. A missing flag mask cannot become a green badge. An unknown match count cannot become a promise that every observation was retrieved. When a field is optional, define how the consumer behaves without it. A robust interface remains understandable when the archive supplies less information than the most attractive demo example.

### Keep data lineage attached to the experience

Every displayed observation should retain its collection, observation identifier, source URL and date. Derived images should also record how they were produced. The public interface need not show every technical field at once, but the evidence export and source details should make the chain inspectable. If a frame is cached, say it is cached and retain the original observation time. A cached NASA observation is still real data; a synthetic image with a NASA-looking label is not.

Do not invent source records to satisfy a layout. Development fixtures should be visibly labeled and isolated from production content. If a test needs an unusual timestamp, missing wavelength, corrupt response or saturated mask, create a small synthetic fixture that is clearly a test. It should not become a featured observation by accident. Tests may exercise impossible combinations to check validation, but those combinations must never be presented as archive findings.

Preserve original bytes when performing scientific checks. Display products can be resampled, stretched or background-adjusted for readability, but those transformations change what a viewer can infer. The raw FITS remains the source for analysis. A PNG is useful for a browser; it is not automatically suitable for flux measurement. The application should help a learner understand that distinction without requiring them to read an image-processing textbook before they can begin.

### Scientific humility as concrete behavior

Perigee should be exciting because the user can inspect evidence, not because it makes stronger claims than the data support. A known moving star is a worthwhile investigation. A lesson about why two frames should be compared cautiously is worthwhile. A quality warning can be part of the discovery experience. Do not manufacture a new planet, a measured velocity, a chemical composition or a statistically significant brightness change to make the demo sound more impressive.

Several effects can create apparent differences between images: wavelength, point-spread function, sampling, background, blending, saturation, calibration, noise and coverage. The weekend app does not solve all of them. It exposes relevant metadata and guides a bounded visual investigation. A quality screen is one piece of evidence, not a universal truth score. Explain the actual check and its limitation. Avoid labels such as scientifically verified, confirmed discovery, or precise motion unless the team has performed and documented the corresponding analysis.

Known astronomical context and measured app output must remain separate. A reference may establish that Barnard's Star has high proper motion. That does not mean the app has measured its motion accurately. A catalog may predict an object's location at an epoch. That does not mean a bright pixel there is a validated detection. The content should distinguish what is known from external sources, what is visible in these observations, and what would require further analysis.

### Designing the learner's path

The first screen should make the next action obvious. A visitor should know that they can choose an investigation or enter coordinates. The app should explain the question before presenting a large control panel. Lead with an interesting object and a manageable task, then reveal technical details when they help the user decide what a comparison means. The goal is not to hide science; it is to put the right explanation next to the decision it supports.

The investigation should produce an artifact: a claim linked to specific observations and a statement of uncertainty. Avoid turning the experience into a passive slideshow followed by a generic quiz. The user should select evidence, notice an issue, and explain a conclusion. A learner can complete a useful investigation even if the conclusion is that these frames do not establish the proposed change. That is an authentic result when it follows from the evidence.

Do not require registration, a tutorial video, a hardware download, or a full dataset before the first result. A browser should be sufficient. The interface must work on a phone, but the primary comparison can be optimized for a laptop without pretending this is a native mobile application. On a small screen, stack panels, keep image controls reachable, and preserve the evidence flow. Do not shrink a desktop dashboard until every label becomes unreadable.

### Motion, animation and accessibility

Blinking is a tool for comparison, not a decorative effect. Provide explicit play and pause controls, a readable frame date, and a way to step one frame at a time. Respect reduced-motion preferences and do not start rapid animation without an understandable control. Avoid relying on color alone to distinguish good data, missing coverage and adverse flags. Labels and patterns should carry meaning even when a person cannot distinguish the chosen colors.

Keyboard users should be able to enter coordinates, select a case, move through frames, open quality details and save an evidence card. Maintain a visible focus indicator. Inputs need programmatic labels, and status changes need a useful text equivalent. Do not announce every animation frame through a live region; that would overwhelm a screen-reader user. Announce meaningful state changes such as search completion or an error, while leaving detailed frame information available on demand.

Long source URLs should not break the layout. Technical details can wrap or sit in an expandable panel. Buttons should describe actions, not implementation methods. Say what will be saved or shared. If a shared URL contains only coordinates, do not label it as sharing the entire investigation. When a browser blocks a download or storage operation, preserve the user's text and explain an alternative such as copying the evidence JSON.

### Serverless behavior and deployment discipline

The selected platform can run Python, but a serverless invocation is not a permanently running laptop. Treat local files as packaged read-only assets or temporary request scratch space. Never use a process-global dictionary as the only source of durable job state. Never return success and assume a detached thread will keep processing indefinitely. The bounded search-and-frame interface exists so the first implementation can finish useful work within individual requests.

Measure the small scientific path early. Importing a library successfully is not proof that it fits the deployed bundle or cold-start budget. Keep the package narrow: the browser does not need FITS files, and the deployed function does not need the full research directory, virtual environment, notebook cache, or hundreds of megabytes of sample data. Package only the code and small verified assets required for the running app. Record what the deployed build actually includes.

Vercel Services currently provides a way to ship the frontend and backend together, but it is Beta. Validate routing with the first shell. The API rewrite must precede the frontend catch-all, and the backend must handle the path it actually receives. A successful HTML page at an API URL is a routing failure, not a healthy API. If the fallback uses two Vercel projects, use a single documented API origin and test cross-origin behavior explicitly.

### Testing the risks that matter

Write tests for behavior that can fail in consequential ways: invalid coordinates, wrong ordering, mixed query responses, corrupted upstream data, token validation, quality-state confusion, missing sources and export corruption. Do not spend the sprint writing dozens of tests that merely repeat constants or implementation details. A test should protect an actual requirement or a failure already encountered. Prefer a few representative fixtures that cover different states over a large collection with no explained purpose.

Separate deterministic unit checks from integration checks that depend on NASA services. A network outage should not make every local test unusable. At the same time, a fully mocked suite is not evidence that the public coordinate path works. Keep at least one intentional live smoke test with a known-covered coordinate, bounded requests and recorded output. Run it when it can answer a real integration question, not repeatedly on every keystroke.

The final acceptance path should be tested on the deployed application in a fresh browser session. It must not rely on a developer's local files, an authenticated Vercel dashboard, cached browser state, or a hidden environment variable on one machine. Verify the same public URL that a judge will use. Record the commit and environment so a later deployment cannot silently invalidate the evidence. If a release changes after testing, rerun the affected path.

### Collaboration without blocking the team

Report blockers with an exact interface, file or permission. A useful message says which endpoint is unavailable, what payload you used, what response occurred, and which owner can resolve it. A vague message such as backend broken is not actionable. Include a temporary way to continue independent work, such as a local fixture matching the agreed schema. Do not let the temporary fixture become the final production path without an explicit decision.

When a teammate supplies a change, verify its behavior rather than assuming its label is accurate. A pull request called finished viewer may still lack no-coverage handling. A data file called clean may only have passed one flag screen. Review the relevant output and ask a precise question if necessary. Keep review focused on the shared requirement; avoid rewriting another person's style or expanding scope during integration.

Use issues as durable handoff points. Put the current result, next dependency and verification evidence where the named owner can find it. Do not dump an entire terminal transcript into an issue. Do not post secrets, personal inbox content or unrelated research. A concise status with a commit, command and example is more useful than a long chronological diary. Close an issue only when its acceptance criteria are satisfied or the team has explicitly changed its scope.

### Prioritization under the deadline

The application needs a real coordinate path, two coherent investigations, traceable observations, meaningful quality context, and a public working demo. Everything else competes with that core. Runtime AI, full spectra, automatic classifications, research-grade photometry, accounts, social feeds and elaborate visual effects are optional or deferred. A feature that sounds impressive but introduces a new untested service can reduce the chance of finishing the product.

If the current time is later than a planned checkpoint, do not blindly execute an outdated hourly schedule. Recalculate the remaining work and preserve the acceptance gates. The event began at 9 AM Chicago time on November 14, 2026; these prompts may be opened later. Start with the smallest end-to-end result immediately. The exact local presentation slot still needs confirmation, so aim for a stable demonstration well before Sunday afternoon.

Do not use the deadline as a reason to fabricate a test result, silently remove a required live query, or describe future functionality as complete. Cut optional scope openly. A small working application with clear limits is easier to evaluate than a broad interface whose main actions are placeholders. Keep the pitch aligned with what the current deployed build actually does. Planned expansion belongs in a clearly labeled future-work section.

### Finish with a reviewable handoff

Your final handoff should state what changed, why it matters to the user, how it was verified, and what remains. Include the branch or pull request, exact files that form the public interface, any configuration the next owner must supply, and one example input/output. Distinguish completed work from prepared work. If you created a deployment, include the actual URL, commit and status; if no deployment exists, say so.

Avoid vague assurances such as everything is production-ready. Say which flows were tested. If an integration test was blocked by an upstream outage, say which deterministic checks passed and which live path remains unverified. If a scientific claim is deliberately limited, carry that limit into the content and evidence export. The next teammate should not have to discover hidden caveats during the final rehearsal.

End your workstream by checking the repository for unintended files, large data, secrets and unrelated changes. Keep the commit focused. Preserve other people's work. Leave the issue in a state that accurately reflects progress. Your goal is to make the next person's job easier and bring the team closer to one understandable, functioning investigation—not merely to produce a large quantity of code.


---

Reference source: [docs/PLAN.md](https://github.com/sathvikloke/perigee/blob/main/docs/PLAN.md)

## Perigee project plan

Implementation starts from scratch during the November 14–15, 2026 event. This repository currently contains documentation and research records.

## The decision

Build **Perigee: guided investigations of the changing infrared sky** for the Planet X and SPHEREx challenge. The promise is: **Explore real NASA observations, make a comparison, and explain what the evidence supports.** Keep the public coordinate-and-time viewer at the center. Add two complete investigations and a saved evidence card around it. This is the final recommended scope for six people over November 14–15, 2026; it supersedes the earlier conditional Afterglow/outburst direction.

The first audience is motivated learners in astronomy clubs and classrooms, with teachers and club organizers helping them get started. The broader vision is a growing collection of investigations using new observations. A discovery engine, research-grade photometry service, and general astronomy chatbot are outside this weekend’s scope.

The team roster, challenge, relevant competitors, and archive methods have been reviewed, and the original NASA data is downloaded locally. The application has not been built or deployed. Start implementation from scratch on Saturday November 14 after the event begins. Scientific measurements and user demand have not been validated.

## The human reason to build it

**The human change we want is from following an explanation to making an evidence-based observation.** A curious learner should be able to ask whether something moved, inspect actual observations, notice why a comparison might mislead them, and explain their conclusion. That combines agency, the pleasure of finding something, and confidence in their own reasoning.

An illustrative journey—not a real user interview or testimonial: a student hears that a nearby star moves across the sky. They open Perigee, blink observations from different dates, compare the star with the surrounding field, check wavelengths and image flags, and write what they can support. They leave with an evidence card they can show their club or teacher. A later investigation asks a different question about a cooler object or an uncertain observation.

The scientific context is substantial: infrared observations help investigate cool objects and the material involved in stars and planets. SPHEREx has already produced brown-dwarf and interstellar-ice science. Perigee’s weekend contribution is making a small part of that observational process accessible; it is not claiming to discover a new planet or derive an asteroid’s composition from a few images. [NASA brown-dwarf results](https://www.nasa.gov/missions/spherex/nasas-spherex-telescope-sees-menagerie-of-brown-dwarfs/), [JPL interstellar-ice results](https://www.jpl.nasa.gov/news/interstellar-glaciers-nasas-spherex-maps-vast-galactic-ice-regions/).

| Audience | What they want | Product response | Reason to return |
|---|---|---|---|
| Motivated student or independent learner—primary | A real question they can investigate and a result they can explain | Short guided cases, real observations, clear evidence and uncertainty | Another case, a different object, revisiting a saved investigation |
| Teacher or astronomy-club organizer—initial adopter | A manageable activity with a clear learning outcome | A 10–15 minute case, discussion prompts, printable evidence card, no account required | New cohorts and different activities |
| Amateur astronomer—secondary | Convenient inspection and traceable data | Coordinate input, date/wavelength controls, quality context, archive links | Their own targets and later available epochs |
| Outreach educator or science communicator—secondary | An understandable example of how an astronomical conclusion is made | A shareable target view and an honest visual explanation | New events, classes, and demonstrations |
| Professional researcher—future collaborator | Reliable measurement, reproducibility, calibrated errors | Provenance is useful now; precision-analysis features require later validation | Do not promise a research workflow this weekend |

These motivations are product hypotheses informed by adjacent educational and citizen-science projects, not evidence that Perigee already has demand. Guided real-data learning already exists in Rubin’s education program, and classroom participation already exists on Zooniverse. There is no need to invent a new human motivation; the team needs to execute a useful SPHEREx experience. [Rubin education products](https://rubinobservatory.org/education/educators/program-guide/our-education-products), [Zooniverse education](https://www.zooniverse.org/get-involved/educate).

Repeat use should follow worthwhile new questions. Start with saved cases and a second investigation; later add a curated case library and revisits when new epochs become available. Avoid a daily-use or live-alert promise: archive ingestion and release schedules are not real-time. A successful single classroom session is also a legitimate benefit. No existing users or retention statistics are required by the judging criteria. [Archive access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/), [judging guide](https://www.spaceappschallenge.org/resources/judging-awards-guide/).

## What is distinct, and what already exists

| Closest existing work | What it already covers | Perigee’s contribution to demonstrate |
|---|---|---|
| IRSA’s SPHEREx interface and documentation | Archive access, images, flags, provenance, and spectrophotometry | A short, coherent investigation for a learner, ending in their own supported conclusion |
| SPXQuery and SPHEREx analysis packages | Programmatic retrieval and analysis workflows | A browser experience without requiring Python or archive expertise |
| SPHEREx timelapse and blink projects | Time browsing, image comparison; some also include masks, differences, curves, or exports | Put observation date, wavelength, quality, and the learner’s reasoning into the same guided flow |
| Driftnet and similar Planet X projects | Overlapping motion-review and evidence-report concepts | Do not claim evidence cards alone are new; demonstrate the complete educational interaction |
| Rubin and Zooniverse | Guided authentic-data education and public participation | Apply that approach carefully to SPHEREx’s particular time/wavelength/quality constraints |

References reviewed include [IRSA spectrophotometry](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html), [SPXQuery](https://spxquery.readthedocs.io/en/latest/), [SPHEREx timelapse](https://github.com/ShivenKhurana1/spherex-timelapse), [SPHEREx Blink](https://andrei25ciuta.github.io/SPHEREx/results.html), and [Driftnet](https://spherex-planet-x.vercel.app/about/). These comparisons are based on published interfaces, documentation, and selected code inspection, not a full performance benchmark of every project.

**Defensible contribution:** a focused educational workflow that helps a newcomer make and document a scientifically cautious comparison using real SPHEREx data. This is a proposed improvement in usability and learning, not an exclusive technical invention. The weekend must demonstrate that improvement. Do not claim “first SPHEREx citizen-science platform,” “first time viewer,” or “first evidence report.” NASA has also selected a SPHEREx-related citizen-science effort, Rogue Worlds. [NASA’s 2026 citizen-science selections](https://science.nasa.gov/get-involved/citizen-science/nasa-selects-19-new-citizen-science-proposals-in-2026/).

## The exact weekend product

The core journey is **choose a case or enter coordinates → inspect a chronological image sequence → check wavelength and quality → record a claim, evidence, and limitation → save or share the investigation**. A first-time visitor gets a clear starting question. An experienced visitor can go straight to coordinates.

| Priority | Deliverable | Completion condition |
|---|---|---|
| Required | Public RA/Dec viewer | A coordinate outside the five presets produces a real archive query and a chronological result or an honest empty/error state |
| Required | Time and wavelength controls | Time order uses observation dates; each frame shows its wavelength; changing wavelength is distinct from advancing time |
| Required | Five challenge presets | Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae, and R Draconis are accessible with correct labels and provenance |
| Required | Quality and coverage context | Missing coverage and flagged pixels are visible; a near wavelength match is not labeled a scientifically validated comparison |
| Required | Two complete investigations | Epsilon Indi B and Barnard’s Star have prompts, usable imagery, and a supported conclusion with limitations |
| Required | Evidence card | Records selected observations, dates, wavelengths, source links, learner claim, and uncertainty; saves locally and exports JSON or prints |
| Required | Share and failure handling | Target coordinates survive a URL; saved observations retain IDs; loading, partial results, no coverage, and archive errors are distinct |
| Optional after acceptance | Third investigation | WISE 0855 demonstrates why image coverage is not the same as detecting an object |
| Deferred | Quantitative science and platform features | Full spectra, calibrated light curves, proper-motion measurements, asteroid chemistry, ML classification, accounts, community feeds, and all-sky searches |

The challenge explicitly asks for a public website that accepts coordinates and shows time-ordered images. Spectra, image arithmetic, overlays, and other additions are optional. A preset-only story site would therefore leave the central requirement unfinished. [Official Planet X and SPHEREx challenge](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/).

### The two investigations

**1. Is this a fair comparison? — Epsilon Indi B.** Start with the candidate April 29 and September 27, 2026 observations identified in the research audit. Their audited predicted-source wavelengths are approximately 2.3232 and 2.3220 micrometers, and the selected central apertures passed the conservative flag screen. Regenerate their display products and verify these properties with the new processor before selecting them for the app. Let the learner examine dates, wavelength differences, and flags before making a statement. The supported finding is that this pair passes initial comparison checks; that does not establish a brightness change or measured motion.

**2. Follow a nearby moving star — Barnard’s Star.** Generate new display products from the retained original observations, blink them on the same sky grid, and compare the bright target with the surrounding field. Explain its known motion and distinguish a catalog-predicted marker from a measured centroid. Bright central pixels were flagged in the audited data, so verify and carry that limitation into the card. Do not report a new proper-motion value or precise brightness result.

A possible third case is **What does an empty-looking image tell us? — WISE 0855**. It would teach the distinction between coverage, visual appearance, and a statistically supported detection. An apparently empty preview alone does not prove that the object is absent or provide a calibrated upper limit. Author and implement this optional case during the event if the two core cases are complete.

## What the research and downloads actually establish

The decision pass reviewed the challenge and current judging/submission rules, the official descriptions of 30 global winners from 2023–2025, relevant competing viewers and educational workflows, SPHEREx archive/access/quality documentation, and the feasibility of the earlier outburst proposal. Winner descriptions show recurring combinations of a clear purpose, tangible experience, relevant science/data, and understandable presentation; they do not establish a causal winning formula. Losing entries and private judge scores were not available for a controlled comparison. [2023 winners](https://science.nasa.gov/directorates/smd/2023-nasa-international-space-apps-challenge-announces-10-global-winners/), [2024 winners](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-international-space-apps-challenge-announces-2024-global-winners/), [2025 winners](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).

**Downloaded source data:** 1,986 returned archive metadata records across five target positions, querying DR1 and QR3 wide-survey collections. From 188 selected cutout requests, 183 FITS files downloaded successfully; five requests returned HTTP 503 after retries. The original FITS files, archive metadata, source URLs/hashes, and official explanatory-supplement PDF remain local. Generated previews, frontend manifests, case files, preparation scripts, and the old starter ZIP have been removed. Build the application and processing pipeline from scratch during the event.

| Target | Saved FITS cutouts | Adequate central coverage | Central apertures passing the conservative screen |
|---|---:|---:|---:|
| Barnard’s Star | 34 | 34 | 0 |
| Epsilon Indi B | 44 | 43 | 29 |
| WISE 0855 | 34 | 34 | 21 |
| RW Aurigae | 35 | 33 | 1 |
| R Draconis | 36 | 35 | 0 |

The screen counts finite, sufficiently covered pixels without selected adverse flags near a catalog-predicted position. It is not a source-detection test or certified photometry. The bright-star flags and the earlier outburst data’s quality problems are reasons to keep quantitative scientific inference out of the critical path.

All 183 downloaded FITS files were structurally read and their SHA-256 hashes verified during the data audit. The audit also checked coordinate consistency and inspected candidate images. Those observations inform the research findings below, but the display pipeline and generated assets have been removed. A new implementation still needs its own validation; the audit does not establish calibrated fluxes or discovery performance.

Earlier work separately inspected 1,406 archive records, 1,544 NEOWISE rows, and 25 successful FITS downloads for three outburst-oriented targets. Published work already combines NEOWISE and SPHEREx in this area, while good photometry can require coadds, deblending, additional spectra, and stronger validation. The earlier files remain available, but they are not the weekend dependency. [Relevant outburst study](https://arxiv.org/abs/2602.07129), [NEOWISE quality documentation](https://irsa.ipac.caltech.edu/data/WISE/docs/release/NEOWISE/expsup/sec2_3.html).

This was a targeted feasibility audit, not a scan of all NASA data. It did not exhaust SPHEREx’s deep fields, all-sky positions, every wavelength/epoch pairing, or every competitor’s code. No PSF-matched photometry, measured proper motion, sensitivity-calibrated nondetection, prospective user study, or live application test has been completed. Further exhaustive archive exploration would not remove the immediate need to build and test the chosen interaction.

### Local handoff

Original source data is stored at **research/build_data/**. **Only Sathvik and Sagar need the full data download.** They own raw data processing, scientific checks, and the image/metadata outputs to be created during the event. Akshobya, Aditya, and Suhrit can develop against an agreed JSON contract, then use the shared backend; they do not need the full dataset locally. The repository contains research and planning documents, not a working application or reusable processing scripts. Keep raw FITS and virtual environments out of Git and the frontend bundle.

The source-data manifest records observation time, release, original URL, wavelength, coverage, flags, and file hashes from the audit. Preserve provenance in the eventual application. Design display previews as visualizations rather than flux measurements. Recheck coordinate handling in the new implementation: catalog epoch, proper motion, annual parallax, and binary motion are distinct considerations. Test the official WISE 0855 challenge coordinate separately from a predicted current position.

## Implementation and AI

**No AI model, model weights, GPU, or training dataset is required for this version.** Dates, wavelengths, coordinates, and flag decoding are deterministic. Use authored explanations and case-specific guidance for the demo.

If the complete core works by Saturday evening, an optional language-model helper could explain only the selected metadata and prewritten case material. It must link its sources and never infer an object’s composition, classify an apparent change as a discovery, or turn a missing measurement into a confident answer. This feature is the first thing to cut. There is no need to download a local model.

### Small architecture

Use the current [integration contract](https://github.com/sathvikloke/perigee/blob/main/docs/INTEGRATION_CONTRACT.md) for architecture and endpoint definitions. The selected product is a responsive React/TypeScript web app with a Python FastAPI backend hosted through Vercel. The contract replaces the earlier persistent-server/job-queue outline with bounded metadata searches and individual frame-processing requests. Vercel Services is the preferred single-project deployment and is currently Beta; Suhrit owns its early validation and the documented two-project fallback.

Align images to a fixed celestial grid so real motion remains visible. Do not center every frame on the predicted moving object and accidentally erase motion. Keep date and wavelength controls separate; the same detector does not guarantee the same wavelength. Display actual wavelength separation rather than inventing a universal comparison-confidence score. Do not use raw image subtraction as a proof of variability.

## Six people and a credible schedule

The live team page lists **Sagar Raut, Akshobya Rao, Aditya R, Neeraj Movva, Sathvik Loke, and Suhrit Bestavemula**. The assignments below reflect Sathvik’s updated direction: Sathvik and Sagar own all data work, Akshobya owns frontend, Aditya and Suhrit own backend, and Neeraj has a light support role outside the critical path. [Perigee team page](https://www.spaceappschallenge.org/2026/find-a-team/perigee/).

| Owner | Workstream | Concrete handoff |
|---|---|---|
| Sathvik Loke | Data analysis, scientific validation, investigation content and pitch | Own the full dataset with Sagar; select case frames, check alignment/wavelength/flags, write supported conclusions, and own the final story/slides |
| Sagar Raut | Data engineering and archive processing; final submission owner | Own the full dataset with Sathvik; retrieval, FITS-to-preview processing, manifests and callable data functions for the backend team |
| Akshobya Rao | Frontend and visual design | Coordinate form, five presets, viewer, timeline/wavelength controls, case screens, evidence card, local save/export/print and loading/error states |
| Aditya R | Backend query API and job orchestration | Input validation, search/job endpoints, progressive results, retries and integration with the data functions supplied by Sathvik and Sagar |
| Suhrit Bestavemula | Backend storage, content serving and deployment | Cache/storage integration, image/manifest/case endpoints, public deployment, health checks and backend integration checks |
| Neeraj Movva | Light testing and submission support | Fresh-browser checks, broken-link reports, screenshots and optional slide assembly; no required feature or deadline depends on his availability |

Plan for **five active builders**, with Neeraj providing optional support. At roughly 14–18 focused hours per active builder, budget about 70–90 person-hours total, including integration and presentation; do not count Neeraj’s availability toward required delivery. Akshobya is the single frontend owner, so Sathvik supplies finished case copy and conclusions, while Aditya and Suhrit deliver stable endpoints and data shapes. Sathvik owns the pitch/slides; Neeraj can help assemble them. In the first hour, Sathvik and Sagar agree the processing interface with Aditya and Suhrit, and all five agree the frontend manifest contract. The existing scope and milestones remain the ceiling; cut optional work early.

All times below are **Chicago time, CST**. The organizer email says the event starts Saturday November 14 at 9 AM. The local page says presentations are five minutes on Sunday, but neither the public schedule nor the retrieved final-details email gives the exact presentation slot. Be presentation-ready by Sunday noon, and move that earlier if the organizer supplies an earlier slot. The global submission deadline is Sunday November 15 at 11:59 PM local time. [Chicago event](https://www.spaceappschallenge.org/2026/local-events/chicago/), [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/).

| Time | Milestone | Gate |
|---|---|---|
| Saturday 9–10 AM | Agree API/manifest, divide files, create the first deployed shell | Every owner can run the same initial app |
| Saturday 10 AM–noon | One cached target works from selection to evidence card | First usable vertical slice is public |
| Saturday noon–4 PM | General RA/Dec query, progressive frames, dates/wavelengths/flags | A coordinate outside the presets reaches the archive and renders or reports an honest result |
| Saturday 4–7 PM | Two investigations, five presets, saving and export | Complete core journey works without manual database/file edits |
| Saturday 7–10 PM | Integration, failure states, first slides and narrated demo | Core feature freeze; cut optional work if any required gate is failing |
| Overnight | Rest and short handoff notes | Avoid making scientific or deployment fixes while exhausted |
| Sunday 8–10 AM | Acceptance checks and fixes | Public build, source attribution, data boundaries and evidence exports verified |
| Sunday 10 AM–noon | Rehearse local pitch, finish seven slides, capture backup demo | Presentation-ready; earlier organizer slot takes precedence |
| Sunday after local judging | Only critical fixes and final submission | Aim to submit by 8 PM, with buffer before the 11:59 PM hard deadline |

The critical path is **manifest/API agreement → one complete case → arbitrary coordinates → second case → verification → submission**. Sathvik prepares case copy and presentation content while Akshobya builds the screens. Aditya and Suhrit split the backend work against the same contract. If the live-query gate fails Saturday afternoon, both backend owners pair with Sagar to resolve it and drop optional features. Cached presets help reliability but do not substitute for the challenge’s coordinate requirement.

## Acceptance, risks, and cut order

Acceptance should test user-visible behavior: enter an unseen valid coordinate; verify the displayed frames are in observation-time order; inspect all five presets; distinguish out-of-coverage from HTTP failure; change wavelength without pretending time advanced; inspect a flagged example; save and reopen an evidence card; verify exported observation IDs and source URLs; and open the public deployment in a fresh browser without the developer’s credentials. Check phone, laptop, and presentation layouts, keyboard operation, and a pause control for blinking.

For scientific checks, trace the selected case frames back to raw metadata, verify fixed-grid registration against surrounding sources, keep predicted markers explicitly labeled, and confirm that no UI text claims a measured discovery, flux change, or composition that the pipeline has not established. A clean central flag screen is not a certificate of scientific validity.

If time permits, ask someone who has not built the app to complete one case and explain what they learned and what remains uncertain. This is a small usability check, not a requirement for recruited users or a statistically credible impact study. A recorded complete flow and a reproducible evidence card are already useful demonstration evidence.

| Risk | Already observed or plausible failure | Response |
|---|---|---|
| Archive reliability | Five selected downloads returned HTTP 503 after retries | Prepared cache, bounded retries, partial results and explicit unavailable status |
| Scientific overclaim | Bright targets are flagged; wavelength, background, PSF and coverage vary | Explain limits; defer calibrated measurements; show actual metadata |
| Live-query scope | A polished preset experience can hide an unfinished requirement | Make a new coordinate the Saturday acceptance gate |
| Integration | Parallel frontend, backend and data work diverges | One manifest contract, early deployed slice, shared fixture data |
| Presentation timing | Exact Sunday local slot is not published in the checked sources | Ready by noon or earlier if instructed; retain a backup demo |
| Excess features | AI, spectra, accounts and custom infrastructure consume the weekend | Cut them before cutting the viewer, evidence flow or verification |

Cut optional AI first, then the third investigation, elaborate animation, optional catalog overlays, and visual extras. Preserve actual NASA data, general coordinate input, chronological viewing, essential wavelength/quality context, the two completed investigations, attribution, and the public submission.

## Story and judging evidence

Suggested opening: **“Imagine hearing that a nearby star is moving across the sky. With Perigee, you can open real NASA observations, compare them yourself, and explain what you found. We guide you through the checks that make that comparison meaningful—because the exciting part of science is learning how to tell what the evidence actually says.”** This is a pitch framing, not a claim that a usability study has already proved the effect.

| Criterion | What the team can show by Sunday |
|---|---|
| Impact | A specific learner and teacher use case, a complete activity, and a clear learning outcome |
| Creativity | The integrated comparison-to-evidence interaction and a candid explanation of how it improves on related tools |
| Validity | Real downloaded observations, provenance, metadata checks, and visible limits on inference |
| Relevance | Public RA/Dec input and chronological SPHEREx imagery satisfying the challenge |
| Presentation | One understandable human journey, a working demonstration, and a realistic expansion path |

The official rubric uses Impact, Creativity, Validity, Relevance, and Presentation. Existing users are not a prerequisite. A good pitch helps explain the project, but the working artifact, scientific coherence, and submission also matter. These criteria support the plan; they cannot guarantee a win. [Judging and awards guide](https://www.spaceappschallenge.org/resources/judging-awards-guide/).

Use seven slides for the global demo: **1** team and promise; **2** the learner’s question; **3** real coordinate/time viewer; **4** wavelength and quality checks; **5** the completed evidence card; **6** comparison with existing tools and realistic future use; **7** what works, sources, limitations, and team. The guide allows seven slides including the title or a video of at most 30 seconds. Prepare a separate five-minute spoken version for Chicago’s local presentation. [Submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/).

Five-minute local outline: 0:00–0:40 human question; 0:40–1:10 why SPHEREx data makes the investigation possible; 1:10–3:10 live journey through one case, with the second case briefly visible; 3:10–3:50 what is distinctive and who benefits; 3:50–4:30 what is working and the limits; 4:30–5:00 expansion and closing. Avoid spending the opening explaining the software stack.

Submission checklist: confirm the public app and project links work; include NASA/SPHEREx and CDS/SIMBAD acknowledgments and the appropriate release citations; distinguish cached observations from live queries; describe built features rather than planned ones; follow the official project submission requirements. [Project submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/).

Build the application and processing code from scratch after the event starts on Saturday November 14. The first milestone is one complete investigation with a coordinate viewer; keep the current role assignments and two-day checkpoints.


---

Reference source: [prompts/HANDOFF_RECIPES.md](https://github.com/sathvikloke/perigee/blob/main/prompts/HANDOFF_RECIPES.md)

## Concrete handoff recipes

These recipes describe how the six workstreams connect. They are examples of reviewable work, not a second feature backlog and not a claim that these artifacts already exist. Use the recipes relevant to your role. Keep one authoritative implementation of each interface. An owner can simplify an internal design as long as the observable contract and scientific meaning remain intact.

### Recipe 1: make the first cross-team example small

Start with one curated frame, one case, and one observable user action. Sagar supplies a freshly generated image and its metadata. Sathvik identifies the question that image can support. Suhrit serves the catalog and asset through the intended routes. Aditya ensures the shared model can represent the record without silently dropping fields. Akshobya renders the image, date, wavelength, quality state and source link, then lets the learner select it as evidence. Neeraj may inspect the resulting public flow after it exists.

The handoff should include the exact observation identifier, case identifier, asset identifier, and processing version. It should also include the expected quality state and any intentionally unavailable fields. If the supplied record has no verified bandwidth, retain null. If the image uses per-frame stretching, the record and interface should say so. One small record that survives every boundary accurately is more useful than a large directory of unexplained images.

Place the development example where its owner can maintain it. Do not copy six slightly different versions into unrelated packages. If a frontend fixture is temporarily needed, derive it from the agreed model and identify it as a development fixture. Once the real endpoint works, test that endpoint and remove any production fallback that could silently hide its failure.

### Recipe 2: agree a record through an example, not a label

An issue saying the frame model is finished is insufficient for integration. Provide a compact example with actual field names, units and representative values. Include a successful record, a record with unknown wavelength, and an error envelope only if those examples resolve a real consumer question. Use clearly fictional identifiers in synthetic examples. Never attach a real observation identifier to invented scientific values merely to make a fixture look realistic.

The receiving owner should read the example and describe the resulting behavior. For example, an unknown wavelength should produce an unavailable label and should not pass a numeric wavelength filter accidentally. A quality record with unknown counts should not render an all-clear badge. A partial metadata search should preserve useful observations and show that the searched scope was incomplete. This brief consumer review catches meaning errors that a JSON schema alone may miss.

Once the shape is agreed, put the type or model in its owned directory and link it from the issue. Record a schema version in serialized evidence. Versioning is useful only if it reflects a real compatibility boundary; do not create a migration framework before there is a second version. Additive optional fields should have documented fallback behavior. A changed unit or renamed stable identifier requires coordinated changes to saved content and consumers.

### Recipe 3: trace one displayed pixel region back to a source

For one representative output, record the original archive URL, collection, observation ID, retrieval timestamp and file hash. Identify the FITS extensions used for intensity, wavelength, flags and uncertainty where available. Describe which coordinate was sampled for wavelength and which aperture was examined for the displayed quality summary. Preserve enough information that Sathvik can reproduce the check without guessing which downloaded file produced the image.

The processing note should distinguish source pixel coordinates from output display coordinates. A target can land between pixels, outside a valid region, or near an edge. Interpolation may alter the output appearance, and a resampled flag image needs a method appropriate for categorical information. Do not smooth a bit mask as though it were an intensity field and then interpret fractional values as official flags. Record the actual chosen method and its limitations.

This trace does not need to be a polished notebook or an automated report generator. A short reproducible command, a small metadata record and an inspected image can be enough. Its purpose is to catch a coordinate, extension, unit or transformation mistake before the same mistake is replicated across every preset. Expand verification when a new data format or processing branch introduces a distinct risk.

### Recipe 4: test the public coordinate path independently

Choose a valid coordinate that is not one of the five preset centers and has a reasonable prospect of covered observations. Document why it was selected. Submit it through the same form and API a visitor will use. Inspect the normalized query returned by the backend, then confirm that the archive request used that coordinate. A successful response from a nearby hardcoded preset is a failure of this requirement even if the displayed sky looks plausible.

Record whether the result is complete, truncated, partial or empty. If the source returns many matches and the application limits them, preserve that scope in the user-facing result. Do not invent a total match count when the archive response does not supply one. If one collection fails, distinguish that failure from a complete search of all supported collections. If every upstream call fails, show an error rather than an empty universe.

Then process a small number of returned frames through the deployed API. Confirm chronological ordering by observation time rather than completion order. Check that changing the query while a slow frame is pending prevents the old result from appearing in the new view. This single integration exercise covers a consequential public requirement; it should not become an uncontrolled download of all available observations.

### Recipe 5: preserve a learner's work across failure

A learner may write a claim before all requested frames finish. Treat that text as their work. A failed frame, token expiry, route navigation or temporary archive outage should not erase it. Keep evidence selections tied to stable observation identifiers, and make the relationship visible when some selected data cannot currently be reloaded. A retry should recover the missing network result without silently resetting the entire investigation.

Local persistence should have a bounded, versioned shape. Save text, query parameters and observation references; avoid retaining an unlimited collection of image data URLs. If browser storage is unavailable or full, keep the current in-memory text and offer a practical export or copy action. Do not report that an investigation was saved unless the storage write actually succeeded. A failed save should be understandable without developer tools.

For an export check, create a short claim containing punctuation and line breaks, select two observations, and include an uncertainty statement. Export the card, inspect the downloaded JSON, and verify that the text, IDs, dates, wavelengths and source links survived. Check the print view separately because CSS can hide useful context. The exported artifact should remain understandable after the browser tab is closed.

### Recipe 6: rehearse the scientific explanation

Ask a teammate to explain the difference between observation date and wavelength while looking at the actual viewer. Then ask what a flagged aperture means and what it does not mean. If they infer that every changing pixel is a changing star, the interface or case copy needs improvement. If they think a catalog marker is a measured detection, fix the label and nearby explanation before adding another visualization.

For the fair-comparison case, the desired outcome is a reasoned statement about whether initial checks support comparing the selected frames. It is not a guaranteed brightness-change claim. For Barnard's Star, externally established motion provides context, while the displayed frames and their flags determine what this particular comparison can show. If the expected visual effect is not clear in the regenerated products, rewrite the activity around the evidence that is actually visible.

Keep the explanation short enough to use during a live demonstration. The learner should encounter the important constraint at the decision point, not only in a source document. Additional technical detail can be expandable. A concise limitation attached to a specific observation is more useful than a generic warning repeated everywhere. The objective is informed interpretation, not making every screen feel like a legal notice.

### Recipe 7: make a deployment check reproducible

Record the Vercel project, deployment URL, commit and environment. First check the frontend document and a direct deep link. Then request the health endpoint and inspect both content type and body. An HTTP success containing the frontend HTML at an API route is a routing defect. Check a catalog route and a small asset route before attempting the more expensive live processing path.

The next check should cross the scientific boundary: submit a bounded search and process one resulting frame. This establishes whether the deployed Python package contains the required libraries, can reach the upstream service, can use temporary files correctly and can return a suitably small result. Measure actual elapsed time and response size. Do not infer deployed behavior from a successful local import or a dashboard reporting that a build completed.

Open the judge-facing URL in a session without team credentials. Confirm that deployment protection is configured appropriately for that intended audience. Do not disable protections on unrelated projects. If two-project hosting is used, record the frontend API origin and test cross-origin requests from the actual production frontend. A development server proxy can conceal a production CORS problem, so it is not a substitute for this check.

### Recipe 8: report a failure so the right owner can act

A useful report includes the user action, expected result, actual result, relevant query or case ID, deployment or commit, and a short reproduction. Add a screenshot for a visual defect and a sanitized response for an API defect. Avoid dumping full logs or raw files when a few lines show the problem. Remove tokens and personal notes before sharing diagnostic material.

Route the report by the failed boundary. A correctly returned unknown wavelength displayed as zero belongs to the frontend. An archive failure converted to empty belongs to API orchestration. A misregistered image with correct query metadata belongs to processing. A JSON route intercepted by the SPA belongs to deployment routing. Incorrect case interpretation belongs to science content. Ownership may change after diagnosis; start with evidence rather than blame.

State whether the defect blocks the core demonstration, affects a required secondary path, or is optional polish. The first category gets immediate coordination. The second gets a clear owner and checkpoint. The third can be deferred when the deadline is close. A report is resolved when the original reproduction succeeds against the intended build, not merely when a code change has been pushed.

### Recipe 9: prepare one trustworthy release handoff

Before rehearsal, identify the exact build that the team will present. Freeze optional additions while checking the required journey. Keep a concise list of known limitations and a fallback using the verified curated observations. The fallback must remain labeled as curated or cached; it must not masquerade as a successful live query when the archive is unavailable. Show both the working capability and the actual current state honestly.

The presentation should use screenshots and a demonstration from that build. A feature visible only on a developer branch should not appear as a released capability. If a later change fixes a blocking issue, repeat the affected checks and update the deployment reference. Preserve the last known working deployment until the replacement has been verified. Avoid a broad last-minute dependency upgrade without a concrete need.

The final handoff is brief: what works, where it is available, what was tested, what remains, and who owns the next action. Include source acknowledgments and the correct submission links. Sagar and Sathvik should coordinate the actual submission, with a second person checking links and content. A complete application can still be difficult to judge if the submitted URL requires login or the project description describes an older build.


---

## Scenario reference for Aditya R

Use these scenarios selectively when implementing or reviewing your owned boundaries. They describe possible failures, not evidence that those failures have occurred in Perigee. Some are relevant to another owner; route those findings instead of taking over their implementation. Do not add fifty-eight tests merely because fifty-eight scenarios are listed. Choose checks that protect actual requirements, distinct failure modes or defects you encountered.

For your role: For this scenario, inspect validation, response schema, request budgets and error mapping. Implement the API boundary and reproducible protocol tests; coordinate scientific transformation with Sagar and deployed infrastructure behavior with Suhrit.


### Scenario 1: Empty coordinate submission

**Situation:** A visitor opens the coordinate form and presses search without entering a position, or leaves one coordinate blank while entering the other. Whitespace and placeholder text are not observations.

**Expected behavior:** Reject the incomplete query before an archive call. Keep the entered value, identify the missing field, and show a concise correction. The backend independently rejects missing or nonfinite values. Never substitute a preset, zero degrees, or the last user's query.

**Why it matters:** The public coordinate requirement is only meaningful when the requested position is the position actually searched. Silent defaults can create convincing but unrelated astronomy results.

### Scenario 2: Coordinate boundaries and units

**Situation:** A user enters RA 359.999 degrees, declination near a pole, a negative RA, 360 degrees, or sexagesimal text into a decimal-only field. Different clients may parse these values differently.

**Expected behavior:** Apply one documented boundary policy and preserve the normalized coordinates in the response. Reject unsupported formatting rather than partially parsing it. If the UI supports sexagesimal conversion, test it separately and show the resulting decimal values before submission.

**Why it matters:** A unit mistake can move the query to a completely different sky field while still producing plausible images, making it harder to notice than an obvious crash.

### Scenario 3: Unreasonable field size

**Situation:** A caller requests an enormous field, a negative field size, zero, a string, or a tiny value outside the supported range. The request might arrive directly at the API rather than through the UI.

**Expected behavior:** Enforce the contract's finite field-of-view bounds on the server and communicate them in the form. Do not start a huge download and hope the function finishes. Preserve a clear validation error and avoid creating cache entries for invalid requests.

**Why it matters:** Field size affects cost, runtime, coverage and display geometry. A bounded scientific service must protect both the user's interpretation and the archive from accidental unbounded work.

### Scenario 4: Known-covered non-preset query

**Situation:** The team tests a coordinate that is not one of the five presets but is known to have archive coverage. The frontend must use the general coordinate workflow.

**Expected behavior:** Retrieve actual archive metadata and process at least one genuine returned observation. Record the normalized input, collection, observation identifier and source URL. A preset fallback, mocked response, or generic error page does not satisfy this positive-path check.

**Why it matters:** The challenge asks for coordinate-based exploration. A beautiful preset tour can conceal an unfinished central requirement unless this distinct path is exercised deliberately.

### Scenario 5: Successful empty search

**Situation:** The archive responds successfully but returns no matching observations in the specific collections and footprint queried. Other releases or collection types may still contain coverage.

**Expected behavior:** Return an explicit empty result with the query scope and retrieval time. Offer an understandable next action such as changing coordinates or reviewing supported collections. Do not say the object does not exist or NASA has never observed the position.

**Why it matters:** An empty search result describes the query and its scope. It is not evidence of physical absence or a complete statement about every telescope and archive.

### Scenario 6: One collection unavailable

**Situation:** A search queries two supported collections. One returns useful records, while the other times out or reports an upstream failure.

**Expected behavior:** Preserve successful results and mark the search partial. List the collection that could not be checked and distinguish its failure from zero matches. Sort the available descriptors normally and allow the learner to continue with the stated limitation.

**Why it matters:** Discarding all useful records makes the app fragile, while hiding the failed collection falsely suggests complete coverage. Partial results need both utility and an honest boundary.

### Scenario 7: Archive returns an HTML error page

**Situation:** An upstream URL responds with status 200 but contains an HTML maintenance page rather than a VOTable or FITS file. Network status alone appears successful.

**Expected behavior:** Validate response type and structure before parsing it as scientific data. Return a meaningful upstream or unsupported-data error, preserve a request identifier, and avoid exposing a long HTML page to the user. Do not manufacture an empty table to recover.

**Why it matters:** Operational success and scientific validity are different. A superficially successful HTTP request can still contain no usable observation and must not silently enter the data pipeline.

### Scenario 8: Intermittent HTTP 503

**Situation:** A selected FITS cutout request returns HTTP 503, perhaps after other frames from the same target loaded successfully. Earlier research encountered this exact class of failure.

**Expected behavior:** Use bounded retries within the request budget, then return a retryable failure for that frame. Keep completed frames and their chronological order. Explain that the archive is unavailable for this request rather than interpreting the failure as missing sky coverage.

**Why it matters:** A service outage must not become an astronomical conclusion. The user should retain useful evidence and understand which part of the sequence is incomplete.

### Scenario 9: Frame processing exceeds its budget

**Situation:** A request downloads slowly or spends too long transforming an image. The deployed function has a hard duration limit and the browser may disconnect first.

**Expected behavior:** Stop cleanly before the hard limit when possible, return a useful timeout response, and preserve already completed work in the browser. Measure the failing stage. Reduce bounded work or fix the cause; do not introduce a detached background thread that is assumed to survive.

**Why it matters:** A pending spinner is not durable processing. The application needs a clear operational contract when a single frame cannot finish within the supported request budget.

### Scenario 10: Corrupt or unsupported FITS

**Situation:** A downloaded file is truncated, missing a required extension, contains an unsupported structure, or fails a meaningful FITS integrity check.

**Expected behavior:** Reject the specific frame with an actionable processing code. Preserve source identity for diagnosis without exposing private paths or stack traces. Verify that the next valid frame can still load. Do not fabricate a blank image labeled as a valid observation.

**Why it matters:** A placeholder can be visually indistinguishable from a genuine empty field. Unsupported data must remain explicit so a user cannot mistake a software failure for evidence.

### Scenario 11: Missing wavelength metadata

**Situation:** A valid-looking image lacks a trustworthy wavelength value at the requested position, or the spectral coordinate calculation fails.

**Expected behavior:** Represent wavelength as unknown and explain the missing check. Keep the image available for appropriately limited inspection if safe, but do not substitute detector center wavelength and imply precision. The evidence card should retain the unknown state.

**Why it matters:** SPHEREx comparisons depend on both time and wavelength. Filling a missing value with a plausible number creates false confidence exactly where the learner needs context.

### Scenario 12: Same detector different wavelength

**Situation:** Two observations share a detector identifier but sample different wavelengths at the relevant position. A naive interface groups them as interchangeable.

**Expected behavior:** Display the actual sampled wavelengths and their separation. Keep the time control distinct from wavelength filtering. Do not call the pair a controlled brightness comparison merely because the detector number matches. Carry this limitation into the case explanation.

**Why it matters:** Detector labels are convenient metadata, but they do not by themselves establish equivalent spectral sampling. The product's educational value depends on making this distinction understandable.

### Scenario 13: Flagged bright central source

**Situation:** A bright target has overflow, blooming, saturation-related or other adverse flags near the selected position. The surrounding field can still be visually informative.

**Expected behavior:** Show the affected quality state and explain what it limits. Preserve useful visual inspection without reporting precise photometry or measured motion from those pixels. Keep the flag overlay aligned with the intensity image and distinguish informational flags from adverse ones.

**Why it matters:** Bright targets can make a compelling demo while also being poor measurement inputs. The correct response is a bounded investigation with visible limitations.

### Scenario 14: No pixels in the target aperture

**Situation:** A query intersects an image footprint, but the predicted target position lies outside the actual usable cutout or has no finite aperture pixels.

**Expected behavior:** Report not covered or unknown as appropriate. Never interpret zero inspected pixels as zero bad pixels and therefore clean data. Check coverage before evaluating aperture statistics and ensure the frontend does not display a green quality badge.

**Why it matters:** This is a subtle numerical failure: an empty set can accidentally pass a naive all-clear test. The data model must distinguish absent evidence from reassuring evidence.

### Scenario 15: Missing variance or mask information

**Situation:** The intensity image can be displayed, but variance or quality information is missing, invalid or not interpretable by the implemented pipeline.

**Expected behavior:** Keep the missing information explicit and prevent a clean quality classification. Explain the limited basis of the preview. Do not invent an uncertainty estimate or infer detection significance from display intensity alone. Tests should verify null handling end to end.

**Why it matters:** Scientific uncertainty cannot be reconstructed by a confident label. A useful viewer may still show the image while being clear about the checks it cannot perform.

### Scenario 16: Frame registration mismatch

**Situation:** Two images appear to shift because their display grids differ in orientation, angular scale, center or projection, rather than because the source moved.

**Expected behavior:** Verify the common celestial grid against surrounding field sources and stored registration metadata. Fix the display transformation before interpreting motion. Show the chosen orientation and field size consistently. Do not align by resizing image rectangles alone.

**Why it matters:** The central visual effect of the app can be caused by its own rendering pipeline. Registration checks protect the distinction between sky motion and software-induced movement.

### Scenario 17: Target-centered motion erased

**Situation:** A processor recenters each observation on a catalog-predicted moving target. The target stays fixed while the rest of the field appears to move.

**Expected behavior:** Use a fixed sky grid for the comparison and move only the predicted marker as appropriate. Document the reference center and epoch. Check the surrounding sources as controls. Do not claim a target's apparent stability demonstrates lack of proper motion.

**Why it matters:** A well-intentioned centering step can remove the very signal the investigation is supposed to help users inspect, so coordinate conventions must be explicit.

### Scenario 18: Catalog marker mistaken for detection

**Situation:** A marker is drawn at a propagated catalog position, but a user or pitch slide describes it as the app's measured object location.

**Expected behavior:** Label it catalog prediction, retain the source and epoch, and keep it visually distinct from any measured centroid. Correct content and exports that imply detection. Do not add a detection label without an approved and independently checked algorithm.

**Why it matters:** Predictions and measurements answer different questions. The app must not turn a useful navigation aid into a scientific result through ambiguous wording.

### Scenario 19: High proper motion and epoch mismatch

**Situation:** A nearby object has moved significantly since its catalog reference epoch. A preset coordinate, official challenge coordinate and predicted current position differ.

**Expected behavior:** Preserve the coordinate's origin and epoch, test each intended input deliberately, and explain finder predictions. Do not silently rewrite a user-supplied position. Check whether the chosen field includes the expected location while keeping the underlying coordinate model's limits.

**Why it matters:** A source can be missed or mislabeled even when every API request succeeds. Position provenance matters as much as image provenance for nearby moving objects.

### Scenario 20: Per-frame contrast changes

**Situation:** Two frames are stretched independently, making one source appear brighter despite the display transformation changing between frames.

**Expected behavior:** Record the scaling mode and show a clear brightness-comparison limitation. Prefer a shared stretch for curated pairs where feasible. Keep raw values separate from display values. Do not report variability from the visual effect of auto-contrast.

**Why it matters:** Image enhancement helps visibility but can manufacture apparent change. The viewer should make its display choices understandable instead of silently inviting a physical interpretation.

### Scenario 21: Noisy or empty-looking WISE view

**Situation:** A preview near WISE 0855 contains little obvious signal at the predicted position, while the queried image does cover that location.

**Expected behavior:** Explain coverage versus detection and avoid a calibrated nondetection claim. A quiet-looking PNG alone does not provide a sensitivity limit. Keep wavelength and quality context visible and use the example as a reasoning exercise if selected.

**Why it matters:** The absence of an obvious visual feature is not the same as a statistically established absence. This case helps learners understand why astronomy uses quantitative methods.

### Scenario 22: Crowded or blended source

**Situation:** Several sources overlap within the display resolution or aperture. The target marker sits near multiple bright pixels.

**Expected behavior:** Identify blending as a limitation and avoid assigning all visible intensity to one object. Keep the case's question within what the display supports. Do not silently add deblending or classification machinery that has not been validated in the sprint.

**Why it matters:** A clear interface cannot make an ambiguous measurement unambiguous. The appropriate product behavior is to preserve context and avoid false specificity.

### Scenario 23: Observation time and retrieval time confused

**Situation:** A newly downloaded file has a recent filesystem timestamp, while the observation itself was taken months earlier. A timeline is built from the wrong date.

**Expected behavior:** Sort and label by archive observation time. Preserve retrieval time separately in provenance. Validate timezone conversion and a stable tie breaker for equal times. Do not make an old observation appear newly acquired because it was fetched today.

**Why it matters:** The experience promises a view through time. Using the wrong timestamp undermines that promise even if the images and source links are otherwise correct.

### Scenario 24: Out-of-order concurrent responses

**Situation:** The browser requests several frames in parallel, and a later observation finishes processing before an earlier one.

**Expected behavior:** Place each result into its predetermined observation slot and keep the chronological sequence stable. Show pending or failed slots distinctly. Do not append frames solely in completion order or start playback while dates jump unpredictably.

**Why it matters:** Network timing is unrelated to astronomical chronology. The UI must preserve the scientific ordering while still benefiting from progressive loading.

### Scenario 25: Stale results after a new search

**Situation:** A user submits one coordinate and quickly changes to another. Responses from the first request arrive after the second query is active.

**Expected behavior:** Cancel or ignore stale work using request identity, and keep each frame associated with its query. Do not overwrite the new viewer, source details or evidence card with old results. Preserve deliberate notes without mixing observation sets.

**Why it matters:** This race can create a believable but incorrect relationship between coordinates and images. It is a data-integrity problem as well as a frontend state-management problem.

### Scenario 26: Expired frame token

**Situation:** A learner leaves a session open long enough for its signed frame token to expire, then requests another frame.

**Expected behavior:** Return a clear expiration response and offer a metadata refresh. Preserve the learner's notes and already loaded evidence. Do not accept an expired token silently or expose signing details. A refresh should not unexpectedly change the selected coordinate.

**Why it matters:** Security and usability should cooperate: a bounded token can protect the service without making a normal interruption destroy the investigation.

### Scenario 27: Tampered frame token or URL

**Situation:** A caller changes a signed descriptor, attempts to substitute an arbitrary URL, or sends a token with a malformed payload.

**Expected behavior:** Reject the request before network access. Validate signature, expiry, version and allowed source structure. Do not follow attacker-chosen redirects to internal or unrelated hosts. Log a bounded diagnostic without printing secrets or the full private environment.

**Why it matters:** The frame endpoint should process known archive resources, not become a general-purpose URL fetcher. This boundary is important even in a short public hackathon demo.

### Scenario 28: Cache miss on a fresh invocation

**Situation:** A second serverless instance handles a request without the files or in-memory objects that a first instance had created.

**Expected behavior:** Recompute bounded work or use the supported shared cache/packaged asset path. The request must remain correct without instance affinity. Do not interpret a local cache miss as missing scientific coverage or require the same process to stay alive.

**Why it matters:** Serverless scaling makes process-local assumptions unreliable. Caching may accelerate the application, but it must not secretly be the only source of truth.

### Scenario 29: Bundled preset asset missing

**Situation:** The preset manifest references an image that was not included in the deployed build, or the asset identifier does not resolve.

**Expected behavior:** Return a real missing-asset error and show a recoverable state. Check manifest-to-file integrity during the build or release verification. Do not substitute an unrelated image. Preserve the observation identity so the data owner can repair the package.

**Why it matters:** A local demo can work while production silently lacks its images. Asset integrity must be verified in the deployed environment, not only on the data owner's laptop.

### Scenario 30: Live frame response too large

**Situation:** A processor returns raw FITS bytes, an oversized image, or a large collection of base64 payloads in a single function response.

**Expected behavior:** Return only the bounded display product and metadata required by the contract. Enforce dimensions and byte limits. Split work into individual frame requests or use an approved asset path. Do not raise every limit without measuring the actual output.

**Why it matters:** The browser needs a usable visualization, not the entire scientific archive. Payload discipline improves reliability and keeps a public service within its platform constraints.

### Scenario 31: Cold start and heavy dependency import

**Situation:** The first deployed request after inactivity is slower than local tests because scientific dependencies load and the function starts cold.

**Expected behavior:** Measure the cold path, keep dependencies narrow, and show a meaningful loading state. Avoid packaging the local virtual environment or raw dataset. Test a fresh deployment rather than assuming a warm developer session represents user experience.

**Why it matters:** The first interaction often determines whether a judge or learner continues. A cold-start delay should be understood and bounded rather than mistaken for an unexplained broken app.

### Scenario 32: API route returns frontend HTML

**Situation:** A rewrite sends an API request into the SPA catch-all. The HTTP status is 200, but the body is the application's index page.

**Expected behavior:** Fix route order or service path handling. Verify content type and JSON structure in the API client and smoke tests. Test the deployed path with a direct request. Do not treat any 200 response as proof the backend is healthy.

**Why it matters:** Frontend and backend can each work independently while their shared deployment is misrouted. This is a high-value early integration check.

### Scenario 33: Deep-link refresh fails

**Situation:** A user opens or refreshes a saved investigation URL directly instead of navigating from the home page. The host returns 404 or loses query state.

**Expected behavior:** Configure the frontend route fallback correctly without intercepting API routes. Restore the supported coordinate and case parameters from the URL. Validate malformed parameters and retain a clear default path. Test both navigation and a fresh direct load.

**Why it matters:** A shareable link is part of the product promise. It must work for someone arriving from an email or slide, not only inside an already running session.

### Scenario 34: Judge encounters deployment protection

**Situation:** The final URL works for a team member logged into Vercel but asks an unauthenticated visitor to sign in or request access.

**Expected behavior:** Test in a fresh browser and verify the intended public production route. Configure access deliberately for this public project without exposing unrelated resources. Do not send judges a dashboard URL or a temporary private preview as the final project.

**Why it matters:** A working private deployment is not an accessible submission. Access behavior must be checked from the viewer's perspective before the team records its final links.

### Scenario 35: Phone-sized comparison layout

**Situation:** A learner opens the app on a narrow screen and the desktop viewer, controls or evidence form overflow horizontally.

**Expected behavior:** Stack panels and preserve the core sequence of actions. Keep controls reachable and labels readable. Do not hide scientific limitations simply to fit the screen. Verify touch interaction and that the image remains large enough to inspect meaningfully.

**Why it matters:** The product is a responsive web app. Mobile support means usable browser behavior, not a tiny desktop screenshot or a separate native application.

### Scenario 36: Keyboard and screen-reader path

**Situation:** A visitor navigates without a mouse or uses assistive technology to understand inputs and state changes.

**Expected behavior:** Provide labels, visible focus, logical order and accessible controls for selecting frames and saving evidence. Announce meaningful loading/error changes without reading every blink frame aloud. Test the actual interaction rather than relying on visual appearance.

**Why it matters:** The investigation should not require one particular input device. Accessibility checks often expose unclear controls and state transitions that affect many users.

### Scenario 37: Animation and reduced motion

**Situation:** Blink playback starts rapidly, continues without an obvious pause, or ignores a reduced-motion preference.

**Expected behavior:** Provide explicit play, pause and single-step controls, respect reduced-motion settings, and keep dates readable. Avoid using animation as the only way to compare frames. Preserve a static side-by-side or stepped alternative where feasible.

**Why it matters:** Blinking is a scientific viewing aid. It should help comparison without creating discomfort or preventing a user from inspecting one observation carefully.

### Scenario 38: Local storage unavailable or full

**Situation:** A browser blocks local storage, reaches its quota, or runs in a mode where persistence is limited. The learner has already written a conclusion.

**Expected behavior:** Catch the storage failure and preserve the in-memory text. Offer export or copying as a fallback. Do not claim the card was saved when it was not. Avoid storing large image payloads in a way that quickly exhausts the quota.

**Why it matters:** The user's reasoning is the valuable artifact. A storage problem should not erase it or create a false sense that it will survive closing the page.

### Scenario 39: Evidence export loses provenance

**Situation:** The exported JSON or printed card contains the user's claim but omits observation IDs, wavelengths, limitations or original source links.

**Expected behavior:** Define one evidence model and render both saved and exported forms from it. Verify the exported file can be read independently and still identifies the supporting observations. Do not generate a polished report that cannot be traced back to data.

**Why it matters:** An evidence card is meaningful because another person can inspect its basis. Losing provenance turns it into an unsupported statement with decorative images.

### Scenario 40: Coordinate link mistaken for shared notes

**Situation:** A share button copies a URL containing coordinates and a case ID, while the user's written notes remain only in their browser.

**Expected behavior:** Label the action as sharing the view or target. Explain that notes require an evidence export unless a real sharing service exists. Test what a second browser actually receives. Do not promise that local storage is shared across devices.

**Why it matters:** The distinction between a view and a completed investigation is easy to miss. Accurate sharing language prevents lost work and misleading demonstrations.

### Scenario 41: Print view hides the limitation

**Situation:** A printed evidence card looks clean but omits the warning about flags, wavelength mismatch or per-frame contrast that was visible on screen.

**Expected behavior:** Carry limitations and sources into the print rendering, with legible dates and observation identities. Remove navigation clutter rather than scientific context. Inspect a real print preview or exported PDF page before calling the feature complete.

**Why it matters:** The export may be the artifact a teacher or judge reads later. It must preserve the meaning of the investigation, including its boundaries.

### Scenario 42: Fixture leaks into production

**Situation:** A mock adapter or synthetic image used during frontend development remains enabled in the deployed app and is labeled as NASA data.

**Expected behavior:** Make fixture mode explicit and ensure the production configuration uses verified sources. Add a release check that detects mock labels or placeholder URLs. If a live service is unavailable, show that limitation instead of silently switching to fabricated results.

**Why it matters:** A believable demo is not enough; the evidence must be real. Development convenience must not blur the distinction between a test scenario and an astronomical observation.

### Scenario 43: Public error exposes a secret or local path

**Situation:** An exception response contains environment values, a signing key, a personal filesystem path, or an unfiltered stack trace.

**Expected behavior:** Return a bounded public error with a request ID and keep useful diagnostics in appropriate logs without secrets. Verify the frontend does not render raw server exception text. Check configuration names without printing their values.

**Why it matters:** A hackathon app still runs on real accounts and infrastructure. Useful debugging information can be provided without exposing credentials or unrelated personal details.

### Scenario 44: Unbounded automatic retries

**Situation:** A browser, API layer and archive adapter each retry failures independently, multiplying requests after a temporary outage.

**Expected behavior:** Define one coordinated retry policy with bounded attempts, backoff and a total budget. Surface a clear retry action after exhaustion. Avoid retrying invalid input or unsupported data. Measure how many upstream calls one user action actually generates.

**Why it matters:** Several individually reasonable retries can combine into an accidental request storm. Coordination protects the archive, the deployment and the user's understanding of progress.

### Scenario 45: Case content and selected frames disagree

**Situation:** A case explanation names dates, wavelengths or quality conditions that no longer match the frames included in the current deployed preset.

**Expected behavior:** Validate content references against the exact bundled manifest and update the explanation or select the intended observations. Do not leave an old conclusion attached to a new image pair. Record the content and processing version together.

**Why it matters:** The scientific story is only as trustworthy as its connection to the displayed evidence. Small dataset changes can invalidate otherwise well-written instructions.

### Scenario 46: Source link fails or points to the wrong release

**Situation:** An evidence card links to a generic homepage, an inaccessible local file, or a different collection than the displayed observation.

**Expected behavior:** Use the original public source URL and release identity. Test representative links from a fresh browser. Keep a human-readable source label without losing the precise reference. Do not replace a broken scientific citation with an unrelated convenient URL.

**Why it matters:** Traceability is a concrete behavior, not a list of impressive institutions. The link should support the specific observation or claim it accompanies.

### Scenario 47: Novelty claim exceeds the comparison

**Situation:** Pitch copy says Perigee is the first SPHEREx viewer, first citizen-science platform, or a new discovery method despite overlapping existing work.

**Expected behavior:** Describe the actual contribution: a coherent guided comparison and evidence workflow for learners. Cite relevant predecessors and show the specific improvement in the running demo. Do not use an unsupported first-ever claim to make the project sound stronger.

**Why it matters:** A candid, demonstrated contribution is more defensible than a broad novelty assertion that a judge can disprove with a familiar tool.

### Scenario 48: Optional feature threatens the core

**Situation:** An agent starts adding a chatbot, accounts, full spectra, advanced animation or a new service while live coordinate search or evidence saving is unfinished.

**Expected behavior:** Stop optional expansion, identify the missing required gate, and redirect effort to the smallest complete path. Preserve useful work without making it a dependency. Record the feature as future work only if it remains relevant.

**Why it matters:** The weekend is constrained by integration and verification time. More features do not compensate for a broken central interaction or an inaccessible final submission.

### Scenario 49: Another teammate changes a shared interface

**Situation:** A merged branch changes a route, field name, enum or dependency while another owner is developing against the previous contract.

**Expected behavior:** Inspect the actual diff, coordinate the intended contract, and update producers and consumers together. Prefer a compatible transition when practical. Do not overwrite the other branch or maintain contradictory local assumptions in separate prompts.

**Why it matters:** Parallel work succeeds through explicit interfaces. Integration failures often arise from small unannounced changes rather than from difficult algorithms.

### Scenario 50: Deadline arrives with incomplete work

**Situation:** The team has a mostly working app but several optional items and one important defect remain before local judging or global submission.

**Expected behavior:** Prioritize the required user flow and a truthful demo, cut optional scope, verify public access, and report the remaining limitation plainly. Preserve a tested deployment and a backup demonstration. Do not claim untested features are complete.

**Why it matters:** A clear, stable artifact with honest limits is easier to judge and use than a last-minute collection of partially connected features.

### Scenario 51: User closes and revisits an investigation

**Situation:** A learner saves a card, leaves the page and returns later. Available archive results or application versions may have changed.

**Expected behavior:** Restore the saved claim and its original observation identities. Distinguish saved evidence from a refreshed live search, and offer deliberate re-querying. Do not silently replace the supporting frames while keeping the old conclusion.

**Why it matters:** Repeat use should preserve the integrity of earlier reasoning. A later dataset update is a new opportunity to investigate, not a reason to rewrite past evidence invisibly.

### Scenario 52: Different package versions break a teammate

**Situation:** A dependency update works on one machine but changes the API, supported Python version, image output or frontend build on another.

**Expected behavior:** Use compatible runtime versions and committed lockfiles where appropriate. Coordinate shared backend dependencies with Aditya and frontend dependencies with Akshobya. Reproduce the failing command before changing more packages. Do not commit a local virtual environment.

**Why it matters:** A predictable environment saves more time than speculative upgrades. The team needs a reproducible build that survives a clean checkout and deployment.

### Scenario 53: Case quality screen treated as universal validation

**Situation:** A UI badge or pitch slide describes a frame that passed a narrow central-pixel screen as fully scientifically valid.

**Expected behavior:** Name the actual screen and preserve its limits. Check surrounding pixels, coordinate assumptions and display transformations separately where relevant. Remove any confidence percentage without a defined validated interpretation. Keep the learner's conclusion appropriately bounded.

**Why it matters:** A simple check can be useful without being universal. Scientific language should describe what was tested, not turn one passing condition into a blanket endorsement.

### Scenario 54: Preset and live query differ in provenance

**Situation:** A curated preset loads instantly from bundled assets while a live coordinate query processes current archive responses. The UI presents them as identical acquisition paths.

**Expected behavior:** Keep both useful, but show whether the result is curated/cached or freshly queried and preserve observation dates in either case. Do not imply a live archive request occurred when a preset was loaded. Use the same evidence schema for both.

**Why it matters:** Reliability and transparency can coexist. A cached demonstration is legitimate when its source and retrieval path are clear and the separate live requirement is also implemented.

### Scenario 55: Data upload becomes an accidental public archive

**Situation:** A deployment or Git commit includes raw FITS collections, a virtual environment, private notes, or unrelated local files because an agent staged an entire directory.

**Expected behavior:** Review the staged file list and deployed bundle, keep only intended source and small verified assets, and respect ignore rules. Preserve large original data locally with the two data owners. Do not upload personal inbox content or credentials.

**Why it matters:** The project needs traceable access to selected observations, not a wholesale copy of a laptop. A deliberate artifact boundary improves both privacy and deployment reliability.

### Scenario 56: A shared branch contains unrelated user work

**Situation:** An agent opens the repository and finds edits or commits made by someone else while its own task was idle.

**Expected behavior:** Inspect and preserve those changes. Work on a focused branch or isolated checkout, and resolve overlaps with the owner. Do not reset, force-push, delete untracked files or recreate the repository to get a clean-looking state.

**Why it matters:** The repository is a shared workspace. Protecting existing work is part of completing the assignment, even when that work makes the local state less convenient.

### Scenario 57: A claimed success lacks observable evidence

**Situation:** A teammate reports that an endpoint, image comparison or export works, but provides only a screenshot or a passing test name without the relevant input and environment.

**Expected behavior:** Request or produce a reproducible check with the commit, input, command, output and limitation. Use the actual deployed path for integration claims. Avoid repeated broad testing once the relevant evidence is sufficient.

**Why it matters:** Evidence should match the claim. A screenshot can establish layout, while an HTTP trace can establish routing; neither alone proves scientific validity or an entire user journey.

### Scenario 58: Public browser starts with no prior state

**Situation:** A first-time visitor opens the final URL without a saved account, browser cache, local files or the team's authenticated services.

**Expected behavior:** Make a curated investigation available through the public app and verify its source details, controls and evidence flow. Ensure live query errors are honest and that no developer-only setup is required. Test with a fresh session rather than a familiar tab.

**Why it matters:** The judge and intended learner encounter the product from the outside. The final experience must stand on its own without the development team's hidden context.


## Start now

Inspect the repository and your assigned issue. Identify the earliest incomplete packet in your role and implement the smallest useful slice. Keep the human updated with concrete findings and dependencies. Finish with verified behavior, a focused commit or pull request, and the handoff described above. Do not end after merely summarizing this prompt.
