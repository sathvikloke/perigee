# Perigee

**Guided investigations of the changing infrared sky.**

Perigee lets a learner compare real NASA SPHEREx images of the same patch of sky, check whether the comparison is fair, and save a conclusion backed by the evidence.

- **Compare:** two observations of one RA/Dec, registered to the same sky grid, side by side or blinked, with every frame in date order.
- **Check:** date, wavelength at the target's position, and image-quality flags travel with each image, so a difference caused by wavelength or a bad pixel is not mistaken for change over time.
- **Record:** the learner writes a claim, observations and uncertainty into an evidence card that lists the frame IDs, wavelengths, quality status and archive links needed to check it.

Built for the NASA Space Apps 2026 challenge [Planet X and SPHEREx](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/).

## Status (verified locally, 2026-11-14)

Working on a laptop (Vite frontend proxied to the FastAPI backend), using real archive data:

- Five challenge presets with real frame counts: Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis.
- Two guided cases: Epsilon Indi B ("is this a fair comparison?") and Barnard's Star (a moving neighbour).
- Live coordinate search for any RA/Dec through NASA/IPAC IRSA, with real cutouts processed on request. Coordinates in the URL start a search.
- Evidence card saved in the browser, with JSON export.
- Tests (commit `a416c9e`, `qa/regression/run.sh`): backend **299 passed** with raw data (282 passed / 17 skipped without); frontend **121** (vitest); 183-frame audit and 189-record science acceptance pass; live check 6/6 against IRSA.
- Science acceptance: **189/189** processed records pass an independent re-derivation from the original FITS files ([review](science/reviews/acceptance/README.md)).

**Not yet verified:**

- **Public URL: TBD (pending production promotion).** The hosted Preview builds and starts: an authenticated check of deployment `bc03f40` returned the app HTML, `/api/v1/health` JSON and the case endpoint. Live search and frames there are off until `PERIGEE_TOKEN_SECRET` is set. Logged-out visitors are redirected to Vercel login, so judge access is not verified. See [deployment notes](docs/DEPLOYMENT.md).
- This GitHub repository is currently private. A judge-facing link must open without sign-in.
- Phone and keyboard checks were done locally in headless Chrome (390 and 320 px, axe-core 0 violations); no physical phone or screen reader. Print was checked in print preview. An exported evidence card was inspected by the regression check (`qa/regression/README.md`, N5). "Check your claim against the case guide" was exercised in the fresh-user pass (`qa/fresh-pass`, issue #6).

## Run locally

Requires Python 3.12 and Node.js. From the repository root:

```sh
# Backend (FastAPI), port 8000
python3.12 -m venv .venv          # or: uv venv --python 3.12 .venv
.venv/bin/pip install -r backend/requirements-dev.txt
PERIGEE_DEV_MODE=1 .venv/bin/uvicorn backend.main:app --port 8000

# Frontend (Vite), in a second terminal; /api is proxied to 127.0.0.1:8000
cd frontend
npm ci
npm run dev
```

Open the URL Vite prints (default http://localhost:5173). `PERIGEE_DEV_MODE=1` enables a fixed development signing secret for frame tokens; it is refused in production, where `PERIGEE_TOKEN_SECRET` must be set. Run the backend from the repository root (`backend.main:app`), not from inside `backend/`. To use a different backend port, set `PERIGEE_DEV_API` before `npm run dev`.

Tests: `.venv/bin/python -m pytest backend -q` and `cd frontend && npm test`.

## Data used

- **NASA SPHEREx Level 2 spectral images** (DR1 and QR3) from [NASA/IPAC IRSA](https://irsa.ipac.caltech.edu/Missions/spherex.html): searched and cut out live, or pre-processed for the presets. See the [IRSA SPHEREx data access guide](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) and [DR1 overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html). Raw FITS files are not committed.
- **[SIMBAD](https://simbad.cds.unistra.fr/)** (CDS, via the Sesame resolver; the case source links use CDS's official CfA Harvard mirror while the Strasbourg site is offline): target positions and proper motions, used for the catalog-prediction marker (labelled "not a detection").
- **[ESA Gaia DR3](https://www.cosmos.esa.int/web/gaia/dr3)**: field-star positions used to check image registration (median offset 0.45 display px).

More detail: [data guide](docs/DATA.md) and [source index](docs/REFERENCES.md).

## Repository map

| Path | Contents |
|---|---|
| `frontend/` | React + TypeScript + Vite app: presets, case bench, frame viewer, live query, evidence notebook |
| `backend/` | FastAPI app (`backend.main:app`): `/api/v1` search, frame, catalog and asset routes; FITS processor (`backend/data/`); bundled presets and case content (`backend/content/`) |
| `science/` | Independent science reviews: [acceptance](science/reviews/acceptance/README.md) and [Barnard's Star case](science/reviews/barnard/README.md) |
| `tools/ingest/` | Command-line tools to fetch archive data, rebuild presets and audit products |
| `docs/` | Plan, build spec, data guide, integration contract, deployment, team, [pitch draft](docs/presentation/README.md) and [AI-use disclosure](docs/AI_USE.md) |
| `qa/` | [Judging critique](qa/judging/README.md) and screenshots |
| `prompts/`, `coordination/` | The AI coding-agent task prompts and the log of how they were run and integrated |

## Credits

Team roles, from [docs/TEAM.md](docs/TEAM.md):

| Person | Role |
|---|---|
| Sathvik Loke | Data analysis, scientific validation, investigation content and pitch |
| Sagar Raut | Data engineering and archive processing; final submission owner |
| Akshobya Rao | Frontend and visual design |
| Aditya R | Backend query API and bounded frame requests |
| Suhrit Bestavemula | Backend storage, content serving and deployment |
| Neeraj Movva | Testing, screenshots and submission support |

Data: NASA/IPAC Infrared Science Archive and the SPHEREx mission; CDS/SIMBAD; ESA Gaia.

## Use of AI

Much of this code, its tests and its review documents were written by AI coding agents (Claude Code workers in parallel, with Codex setting the UI design direction), under the team's direction and with decisions that change scientific meaning left to the team. The app itself runs no AI model; full details are in [docs/AI_USE.md](docs/AI_USE.md).

---

## Project documents

Read the [short two-day sprint brief](docs/SPRINT_BRIEF.md) first. The [integration contract](docs/INTEGRATION_CONTRACT.md) is the shared technical source of truth. Individual coding prompts are indexed in [prompts/README.md](prompts/README.md), and the parallel task pack in [prompts/parallel/README.md](prompts/parallel/README.md).

| Document | What it contains |
|---|---|
| [Full plan](docs/PLAN.md) | Idea, human story, audiences, prior art, research findings, scope, architecture, schedule and pitch |
| [Team and schedule](docs/TEAM.md) | Ownership and checkpoints |
| [Build specification](docs/BUILD.md) | Required product behavior, backend contract, acceptance checks and cut order |
| [Data guide](docs/DATA.md) | What is downloaded, source links and scientific limits |
| [Research](docs/RESEARCH.md) | Data audit and competing-work findings |
| [Deployment](docs/DEPLOYMENT.md) | Vercel Services configuration and open access decisions |
| [Pitch](docs/PITCH.md) and [pitch draft](docs/presentation/README.md) | Story, seven-slide outline and five-minute demo script |
| [Source index](docs/REFERENCES.md) | Challenge, archive, scientific and competitor references |
| [Dispatch log](coordination/claude-dispatch.md) | Which agent tasks ran, what was selected and integrated, and open decisions |

Scope: a responsive web app for desktop and mobile browsers, hosted on Vercel. No runtime AI model or GPU. Spectra, photometry (brightness measurement), measured proper motion, asteroid chemistry and accounts are out of scope.

The global submission deadline is Sunday, November 15, 2026, at 11:59 PM Chicago time.

[Official challenge](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/) · [Team page](https://www.spaceappschallenge.org/2026/find-a-team/perigee/) · [Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/) · [Submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/)

Keep secrets, raw datasets, virtual environments and ZIP archives out of Git. Original FITS files stay on the data owners' machines.
