# Perigee

**Guided investigations of the changing infrared sky.**

Perigee lets a learner compare real NASA SPHEREx images of the same patch of sky, check whether the comparison is fair, and save a conclusion backed by the evidence.

- **Compare:** two observations of one RA/Dec, registered to the same sky grid, side by side or blinked, with every frame in date order.
- **Check:** date, wavelength at the target's position, and image-quality flags travel with each image, so a difference caused by wavelength or a bad pixel is not mistaken for change over time.
- **Record:** the learner writes a claim, observations and uncertainty into an evidence card that lists the frame IDs, wavelengths, quality status and archive links needed to check it.

Built for the NASA Space Apps 2026 challenge [Planet X and SPHEREx](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/).

## Try Perigee

**[Open the public web app](https://perigee-liard.vercel.app)** — no login required. Start with **Epsilon Indi B** to investigate a fair comparison, or **Barnard's Star** to follow a nearby moving star.

Verified release on `main`: **`ef29890`**, published 2026-11-15. The [production smoke check](https://github.com/sathvikloke/perigee/actions/runs/43658316997) passed **20/20** without login, including a live non-preset archive search and processed image. Preview deployments remain protected. See [deployment details](docs/DEPLOYMENT.md).

Working features:

- Five challenge targets with bundled observations: Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis.
- Two guided investigations, with date/wavelength comparisons, predicted positions, and quality overlays.
- Live coordinate search through NASA/IPAC IRSA, with bounded cutouts processed on request.
- Evidence notebooks saved in the browser; reopen, JSON export, and print/save PDF.
- A [rehearsed demo package](docs/presentation/README.md) with screenshots, an exported evidence card and a visually checked three-page PDF.

Release-candidate checks: **348 backend tests** with raw data (**330 passed / 18 skipped** without it), **121 frontend tests**, a passing build, a 183-frame audit with no stale records, and **189/189** records passing independent re-derivation from original FITS files ([science review](science/reviews/acceptance/README.md)). These are code/data checks, separate from the hosted smoke run.

Known limits: live searches depend on IRSA availability; curated investigations use bundled products. Notes remain on the current device unless exported. No photometry, measured proper motion, or discovery claim is produced. Local browser checks covered 320/390 px and keyboard use; physical-phone and screen-reader testing have not been performed. The [public browser pass](qa/public-release/README.md) verified comparison switching, quality overlays, notebook saving/reopen and a real JSON export separately from the HTTP smoke check.

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
| [Deployment](docs/DEPLOYMENT.md) | Vercel Services configuration and verified public release |
| [Pitch](docs/PITCH.md) and [pitch draft](docs/presentation/README.md) | Story, seven-slide outline and five-minute demo script |
| [Source index](docs/REFERENCES.md) | Challenge, archive, scientific and competitor references |
| [Dispatch log](coordination/claude-dispatch.md) | Which agent tasks ran, what was selected and integrated, and open decisions |

Scope: a responsive web app for desktop and mobile browsers, hosted on Vercel. No runtime AI model or GPU. Spectra, photometry (brightness measurement), measured proper motion, asteroid chemistry and accounts are out of scope.

The global submission deadline is Sunday, November 15, 2026, at 11:59 PM Chicago time.

[Official challenge](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/) · [Team page](https://www.spaceappschallenge.org/2026/find-a-team/perigee/) · [Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/) · [Submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/)

Keep secrets, raw datasets, virtual environments and ZIP archives out of Git. Original FITS files stay on the data owners' machines.
