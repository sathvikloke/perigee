# Use of AI (Super Intelligence) in Perigee

**DRAFT for Sagar (submission owner) and Sathvik.** The initial implementation account was written on 2026-11-14 against `claude/perigee-integration` @ `5b4c9c7`; the release and validation account was updated on 15 November. Commit counts below describe that historical integration snapshot, not every later commit. Items marked **[TO CONFIRM]** require accurate team input before submission.

The Space Apps [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/) requires teams to "clearly indicate where and how SI tools were utilized". For code and data, the rule is: "Must acknowledge SI generation in descriptive text and metadata." For images and videos: "Must include a visible watermark to indicate SI generation." The guide also says SI "should not be used to (come up with your idea of how to solve the challenge)".

## Short statement (for the submission form and slides)

> Perigee was built with AI assistance. The team directed Claude Code and OpenAI Codex work on research, implementation, tests, review code, UI design, release coordination and presentation drafting. Processing consistency was checked using a separate code path and original FITS files; an independent Gaia-based alignment check reports both passed and inconclusive frames. The app itself runs no AI model: dates, wavelengths, positions and quality flags are computed deterministically from archive data. OpenAI image generation produced the visibly labeled decorative landing illustration. **[TO CONFIRM: accurately describe how the idea arose and any additional AI tools used; do not assert exclusive human authorship unless true.]**

## Which AI tools were used, and for what

### Claude Code (Anthropic), Claude Opus 5.5

Claude Code agents did most of the implementation and review work.

- **Evidence in Git.** On `claude/perigee-integration` @ `5b4c9c7`, **51 of 56 commits** carry the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. This trailer is the commit-level metadata acknowledgment. The 5 commits without it are the initial planning, prompt and task-pack commits (see "Planning documents and prompts" below).
- **How it ran.** A coordinator Claude Code session launched background workers, each in its own git worktree and branch (`codex/parallel-NN-*`, draft PRs #9–#24). It compared their results and merged selected candidates into `claude/perigee-integration`. The log is in [`coordination/claude-dispatch.md`](../coordination/claude-dispatch.md). The task prompts are in [`prompts/parallel/`](../prompts/parallel/README.md).
- **Duplicate candidates were built on purpose and one was chosen.** Frontend A and B, API A and B, and processor A and B were each built independently. The A versions were kept as the base, and specific pieces of B were ported in. The dispatch log records the reasons.
- **What the agents wrote:**
  - the React frontend;
  - the FastAPI backend (search, frame, catalog and asset routes);
  - the SPHEREx FITS processor (`backend/data/`) and the processed preset products;
  - the Vercel Services configuration;
  - the ingest and audit tools (`tools/ingest/`);
  - the backend and frontend test suites.
- **Reviews, also by agents:**
  - an API reliability and security review with fixes (worker 14);
  - an independent science acceptance review (worker 15) and a Barnard's Star case review (worker 10);
  - a comparison of processor A with Sagar's PR #19 (task 24);
  - a judging critique (worker 21);
  - the pitch and demo-script draft (worker 20);
  - this README and disclosure (worker 22).
- **Science content.** The target list and the two case files came from the science branch `codex/sathvik-science` (PR #8). Its three commits also carry the Claude trailer. That covers the targets, the case text and the science-check scripts.

### Codex (OpenAI)

Codex set the UI design direction. The dispatch log and the task pack both say "Codex owns UI design".

- **What Codex produced** (branch `codex/ui-design-and-parallel-tasks`, commit `46002f3`):
  - `DESIGN.md` and `PRODUCT.md`;
  - `design/HANDOFF.md`;
  - an HTML/CSS/JS reference prototype.
- **How it was used.** Claude frontend workers ported the selected design ("design A") into `frontend/`. `design/HANDOFF.md` records that choosing between the three compositions was "delegated by the user to Codex".
- **Generated images.** The same commit has three AI-generated UI composition mockups, `.impeccable/mocks/perigee-{a,b,c}.png`. Their prompts are in `design/IMAGE_PROMPTS.md`. The mockups were for exploring layouts only, and the prompts asked for placeholder star fields labelled "Design preview". They are **not** part of the integrated app.
  - If any mockup appears in the slides or video, it needs a visible "AI-generated" watermark.
  - **[TO CONFIRM: which image-generation tool made them.]**
- The three small star images in the design prototype are real SPHEREx data, rendered from FITS. They are not generated images.

### Agent skills (instruction packs for the coding agents)

Frontend workers had to follow the Bloody Coconut and Impeccable design skills (`prompts/README.md`, `prompts/parallel/README.md`). These are written instructions for the agents, not models. They are listed here because they shaped AI-generated UI code.

### Planning documents and prompts

These cover the 5 commits without a Claude trailer:
- `docs/` plan, research, build, data and team files (`0d14605`);
- the individualized master prompts in `prompts/` (`6990cc1`, PR #7 from `codex/team-master-prompts`);
- the sprint brief and the 24-task parallel pack (`f2359c4`, `fa92766`).

`prompts/README.md` describes the master prompts as "Individual AI coding prompts" of about 18,000 words each, written for coding agents.

- Codex drafted planning and task prompts under the user's direction, and prepared the 15 November submission script and revised project text. **[TO CONFIRM: any additional human-authored portions or other tools used outside this conversation.]**

### Sagar's data pipeline (PR #19, `codex/sagar-data`)

Its single commit `cb1f36b` has no AI trailer. One file from it was adopted: `tools/ingest/fetch_manifest.py`.

- **[TO CONFIRM by Sagar: whether AI tools were used for this work, and which.]**

### Other tools

- **[TO CONFIRM: any chatbot or AI use outside this repository]**, for example research questions, slide text, voice-over, or images or video in the demo. Each use needs the same disclosure, and images and video need a visible watermark.

## How the team directed and reviewed the work

Confirmed from the repository:

- **The task prompts set the rules.** The prompts committed by Sathvik fixed the scope, the integration contract, file ownership and the acceptance gates. They also set rules such as:
  - label any development fixture visibly, so it is never mistaken for archive data;
  - never present a catalog prediction as a detection;
  - do no photometry (brightness measurement).
- **Scientific-meaning decisions went to Sathvik and were not made by agents.** The dispatch log lists five science escalations for him. The revised Barnard's Star (PR #22) and Epsilon Indi B (PR #31) case texts were merged only after Sathvik accepted them on 2026-11-14 (`2a4273a`, `98fae22`).
- **API review items D1–D3 were settled as implementation choices within the written contract** and are documented in `backend/tests/api/REVIEW.md`. Deployment protection and any rate-limit rule stay owner decisions.
- **Agents may not change deployment protection, secrets or production promotion.** These are owner actions in `docs/DEPLOYMENT.md`.
- **The human data owner's work was compared, not overwritten.** Sagar's processor (PR #19) was compared with processor A using the same acceptance checker and tests. Specific pieces were then adopted with attribution: the manifest re-download script, the field-registration check and the stricter "unknown" quality rule (processor A 0.1.2).
- **Initial candidates worked in isolation.** The initial coordinator build used separate branches and draft PRs. The 15 November Codex audit also used agents with assigned file ownership in a shared checkout, followed by integration tests and independent review. The separate landing agent supplied an isolated commit for integration.

Not confirmed from the repository:
- **[TO CONFIRM: which team members read or tested which merged code, and whether anyone besides Sathvik approved merges.]** The candidates were selected and merged by the coordinator Claude session, under Sathvik's authorization. The log does not record line-by-line human review, so do not claim it unless it happened.
- **[TO CONFIRM: the idea's origin.]** The guide says SI should not be used to come up with the solution idea. The repository's first commit (`0d14605`, "Document Perigee concept…") does not show who or what produced the concept. State plainly how the idea arose.

## No runtime AI

The deployed app contains no AI model and calls no AI service.

- `backend/requirements.txt` lists only FastAPI, Starlette, Pydantic, httpx, anyio, Astropy, NumPy, Pillow and certifi.
- `frontend/package.json` depends only on React.
- A search of `backend/`, `frontend/src/` and `tools/` finds no model or AI-API library.
- Wavelengths, dates, registration, quality flags and the catalog marker are computed deterministically from FITS headers and pixels, SIMBAD positions and proper motions.
- The case explanations are fixed text written in advance. They are not generated at run time.

## Landing illustration

The landing-page spacecraft illustration was generated with OpenAI image generation using NASA/JPL-Caltech SPHEREx hardware photographs as visual references. It is visibly labeled “AI illustration” in the landing figure. It is decorative artwork, not a mission photograph, engineering model, live spacecraft position or scientific observation. The image's prompt and reference provenance are recorded in `qa/landing-motion/ASSET.md`. No generated imagery is used as an observation in an investigation.

## How scientific claims were checked

- **Historical processing acceptance sweep.** The sweep re-derived 189 records (183 frames plus 6 case copies) from the original FITS bytes through a separate code path (`science/reviews/acceptance/`). The 189/189 processing-consistency result is scoped to that sweep, not a claim that every later generated case copy received independent astrometric validation. The checks covered:
  - sky registration through the header TAN-SIP WCS;
  - wavelength from the `WCS-WAVE` table, by two independent methods;
  - time from `DATE-AVG` and `MJD-AVG`;
  - quality flags from the `MSKN` bit definitions;
  - coverage;
  - display stretch;
  - provenance, including the sha256 of each raw file.
- **Processing consistency is distinct from independent alignment.** The 189/189 result above does not validate the astrometry of every frame. The independent Gaia-based check returned 133 PASS, 56 UNKNOWN and 0 FAIL across those records, or 128 PASS and 55 UNKNOWN across the 183 unique cutouts. UNKNOWN means too few usable stars. The earlier 0.45-display-pixel median describes the stars that survived its association check, not all-frame accuracy. See the correction in `science/reviews/acceptance/README.md` and the independent `science/reviews/registration-audit/README.md`.
- **The Barnard's Star imagery was checked separately** (`science/reviews/barnard/`). The predicted marker moves about 7 display px (about 10″) from frame A to C. Six Gaia field stars stay within 0.77 px.
- **These checks were written by AI agents too.** Their independence comes from separate code and the original data, not from human authorship. **[TO CONFIRM: any spot checks Sathvik or Sagar did by hand, e.g. the science branch's own independent checks.]**
- **Barnard's Star case text corrected.** An earlier version gave the wrong expected motion ("about 2 display pixels"). The shipped text now says about 4 display px from A to B and about 7 (about 10″) from A to C on the 6′ grid, matching the review above.

## Where the acknowledgment appears ("descriptive text and metadata")

| Place | Status |
|---|---|
| `README.md`, "Use of AI" section | Added in this change |
| This file, `docs/AI_USE.md` | Added in this change |
| Commit metadata: `Co-Authored-By: Claude Opus 5.5` trailers | Present on 51 of 56 integration commits |
| App footer | **AI use disclosure** links to this account in the public release. |
| Submission form "Use of SI" answer and the final slide | **Sagar and Sathvik.** Use the short statement above once the [TO CONFIRM] items are settled. |
| Any AI-generated image or video in the demo | **Must be visibly watermarked.** |
