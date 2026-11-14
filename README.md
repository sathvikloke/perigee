# Perigee

**Guided investigations of the changing infrared sky.**

Perigee will help learners compare real NASA SPHEREx observations, understand whether a comparison is meaningful, and save a conclusion supported by evidence.

**Status:** documentation and research only. Application and processing code will be built from scratch during the November 14–15, 2026 hackathon.

## Start here

| Document | What it contains |
|---|---|
| [Full plan](docs/PLAN.md) | Final idea, human story, audiences, prior art, research findings, scope, architecture, schedule and pitch |
| [Team and schedule](docs/TEAM.md) | Updated ownership and checkpoints for five active builders plus support |
| [Build specification](docs/BUILD.md) | Required product behavior, proposed backend contract, acceptance checks and cut order |
| [Data guide](docs/DATA.md) | Who needs the data, what is downloaded, source links and scientific limits |
| [Research](docs/RESEARCH.md) | Data audit and competing-work findings |
| [Pitch](docs/PITCH.md) | Human story, judging evidence, seven-slide outline and local presentation |
| [Source index](docs/REFERENCES.md) | Official challenge, archive, scientific and competitor references |

## Weekend scope

1. Public RA/Dec input and chronological SPHEREx images.
2. Separate time and wavelength controls with quality/coverage context.
3. Five challenge presets.
4. Two complete investigations: Barnard's Star and Epsilon Indi B.
5. Saved evidence cards with observation IDs, sources, conclusions and limitations.

No runtime AI model or GPU is required. Spectra, precision photometry, measured proper motion, asteroid chemistry and accounts are outside the weekend scope.

## Ownership

| Person | Owns |
|---|---|
| Sathvik | Data analysis, scientific checks, case content and pitch |
| Sagar | Raw data retrieval, processing pipeline and final submission |
| Akshobya | Frontend and visual design |
| Aditya | Backend query API and jobs |
| Suhrit | Backend storage/cache, asset serving and deployment |
| Neeraj | Light testing, screenshots, links and submission support |

**Only Sathvik and Sagar need the full dataset.** Everyone else works against the agreed API contract and, once available, the shared backend. The large source files remain local and are excluded from Git.

## Timing

Start implementation Saturday, November 14, at 9 AM Chicago time. Aim for one complete flow by noon, live coordinates by 4 PM, core features by 10 PM, and presentation readiness Sunday morning. The exact local judging slot still needs to be checked; the global submission deadline is Sunday, November 15, at 11:59 PM Chicago time.

[Official challenge](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/) · [Team page](https://www.spaceappschallenge.org/2026/find-a-team/perigee/) · [Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/) · [Submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/)

## Repository contents

There is no frontend, backend, executable processing script, or generated demo asset in this repository yet. Research JSON files are observational records, not a working application. Original downloaded FITS and archive files remain on the data owners' machines.

Use branches and pull requests once implementation begins. Keep secrets, raw datasets, virtual environments and ZIP archives out of Git. Any final link submitted to judges must be accessible without sign-in; this repository is initially private.
