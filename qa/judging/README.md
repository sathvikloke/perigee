# Independent judging critique (parallel worker 21)

Reviewer: parallel worker 21, 2026-11-14, against `claude/perigee-integration` @ `46debe0`. This is a review only. No product code, content or pitch file was changed.

What was exercised:
- The local build: `PERIGEE_DEV_MODE=1 uvicorn backend.main:app --port 8060` with `vite --port 5197` proxied to it, at a 1280×800 viewport.
- The pitch draft's demo path: home, Epsilon Indi B A+B / A+C, Barnard's Star A+C with the guide line, and one live coordinate search loaded from the URL.
- Anonymous `curl` checks of the public Vercel URLs.

Live IRSA use was 1 `/search` and 9 `/frame` calls. I left the page early to stop the rest of the 24-frame queue.

## Rubric sources (official, fetched 2026-11-14)

- **Judging criteria:** https://www.spaceappschallenge.org/resources/judging-awards-guide/
  - Each criterion is scored 1–5: Impact, Creativity, Validity, Relevance, Presentation.
  - For Presentation, the guide says "Judges evaluate the demo and full project".
- **Submission rules:** https://www.spaceappschallenge.org/resources/project-submission-guide/
  - The project link must not require "a password, permission, or registration".
  - Without access there is no score: "If judges can’t access your project, it can’t be evaluated".
  - The demo is 7 slides or a video of 30 s or less. The "majority of judges’ evaluation will be based on your project submission".
  - Super Intelligence (SI) use must be indicated: "Code and data: Must acknowledge SI generation in descriptive text and metadata."
- **Challenge:** https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/. The page is JS-rendered, so the text was read from its embedded page data.
  - The objective is to display a series of images of an RA/Dec patch "like a little video, making it easy to spot moving objects".
  - It asks teams to test on Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis.
  - The considerations include coordinates in the URL, contamination-flag metadata, Gaia/WISE overlays, adding or subtracting epochs, a choosable field of view, and spectra.

## Score estimate (reviewer's judgment, 1–5)

| Criterion | Est. | One-line rationale |
|---|---|---|
| Impact | 3 | It is a careful learning tool for students and clubs, with a reusable evidence card. Its reach is asserted, not shown, and the pitch rightly makes no discovery or user claims, which caps the score. |
| Creativity | 3 | Keeping date, wavelength, quality and the learner's own reasoning on one "fair comparison" bench is a real twist. But SPHEREx blink and timelapse viewers already exist (SPHEREx Blink, spherex-timelapse and Driftnet are listed in `docs/RESEARCH.md`), and slide 5 compares only against IRSA and Backyard Worlds. |
| Validity | 4 | The science is the strongest part. It passes 189/189 independent re-derivations from FITS, Gaia DR3 stars land at a median 0.45 display px, and the honest failure and "not a detection" states hold up in the UI. Points are lost because nothing runs at a public URL yet and the phone layout is still in progress. |
| Relevance | 3 | It uses real IRSA SPHEREx data and has all five challenge targets, any RA/Dec, URL coordinates (`?view=query&ra=…&dec=…` auto-searches) and flag metadata. However, there is no "little video" playback, and the motion target is held out of the live demo (finding 2). |
| Presentation | 3 | The UI is clean and the narration is scrupulously honest. Against that, there is no link a judge can open, the repo README still says "documentation and research only", and the 5-minute script spends its headline on a question whose answer is "can't tell". |

## Three ranked findings

### 1. No judge can open the project: production is behind Vercel Authentication and the production branch has no app

**Evidence:**
- `curl -s -o /dev/null -w "%{http_code} %{redirect_url}" https://perigee-sathviklokes-projects.vercel.app/` returns `302 https://vercel.com/sso-api?...`, a login wall.
- `git ls-tree --name-only origin/main` returns only `.gitignore README.md docs prompts research`. The production branch in `docs/DEPLOYMENT.md` is `main`, which has no frontend or backend.
- Every integration preview also 302s to Vercel SSO (`coordination/claude-dispatch.md`, entry 07; the pitch draft §3, "Public deployment: Not verified").
- `https://perigee.vercel.app/` returns 200, but it serves an unrelated app: its bundle contains "co-pilot", "telemetry" and "Scan ingest for anomalies" strings. Do not submit that URL.

**Why it costs points:**
- Under the submission guide, an inaccessible project "can’t be evaluated", and global judges score mainly from the submitted project link. That puts **every criterion** at risk, not just one.
- It hurts **Validity** directly ("potential to function in real-world applications" is unproven while no public instance exists).
- It hurts **Presentation** ("judges evaluate the demo and full project").

**Owner:** Suhrit (deployment), with Sathvik for the Vercel project settings and the `main` promotion. Neeraj does the logged-out check.

**Fix within the sprint (about 1–2 h):**
1. Promote `claude/perigee-integration` to `main` once regression worker 23 is green.
2. In Vercel Project Settings → Deployment Protection, turn Vercel Authentication off for production. Previews can stay protected, which keeps decision D3 safe.
3. Set `PERIGEE_TOKEN_SECRET` for Production. Do not set `PERIGEE_DEV_MODE`.
4. Verify in a logged-out private window:
   - `/api/v1/health` reports `token_signing` other than `dev_fallback`;
   - one preset loads;
   - one live search returns frames within the 60 s `maxDuration`.
5. Capture shot S9 and put the URL in the README and the submission.

### 2. The demo and build undersell the challenge's core ask: see motion in a series "like a little video"

**Evidence:**
- **The challenge.** The objective is a series shown "like a little video, making it easy to spot moving objects", tested on Barnard's Star first.
- **The pitch.** `docs/presentation/README.md` opens and demos with "Did Epsilon Indi B change between April and September?". Its scripted answer is "I can't tell whether it changed in brightness". Barnard's Star is kept "out of the live demo" pending PR #22.
- **The Barnard view.** In the running app, the Barnard view already shows the motion clearly: A↔C with the guide line, the glow visibly north of the line in C (`qa/judging/03-barnard-AC-guide-line-1280.jpg`).
- **The PR #22 text is not on screen.** The wrong "about 2 display pixels at 5 arcsec/pixel" sentence lives only in `display_requirements.marker` in `backend/content/cases/moving_neighbor.json`. I expanded every `<details>` and searched `document.body.innerText`: "2 display pixels" does **not** appear in the UI. The text blocker for a live Barnard demo is therefore not user-visible.
- **No playback.** Neither viewer can play the whole series:
  - `grep -n "play\|setInterval" frontend/src/components/*.tsx` finds only two-frame blink timers (`CaseBench.tsx:56`, `FrameViewer.tsx:61`).
  - "All 44 frames in time order" and the live results (`04-live-search-wise0855-url-1280.jpg`) are manual ←/→ steppers.

**Why it costs points:**
- **Relevance:** the challenge's stated objective is to spot moving objects, and the headline case is a change question the app explicitly cannot answer.
- **Impact and Presentation:** the vivid, true result (the fastest-moving star visibly shifting against fixed Gaia-checked field stars) appears only on slide 6. The live 2:15 is spent on a fair-but-null comparison.

**Owner:** Sathvik (pitch order and the PR #22 decision). Akshobya owns the optional play control.

**Fix within the sprint:**
1. Sathvik accepts or edits PR #22 (`b4fcc8c`). This is a JSON text change; the imagery already passed review 10.
2. Reorder the live demo to open on Barnard A↔C:
   - blink, with the guide line on;
   - watch the field stars, then the star;
   - then go to Epsilon Indi A+B / A+C as the "but is the comparison fair?" twist.
   - The time is roughly neutral: swap 1:05–1:40.
3. Optionally, Akshobya adds a "▷ Play" toggle to the existing chronological stepper in `FrameViewer.tsx`. It advances `onIndexChange` over ready frames at about 2 fps, reusing the blink timer, pause and reduced-motion rules. It should carry the existing per-frame stretch caveat. This is about 1 h with a vitest. It is not a new feature concept; it is the challenge's literal objective on a control that already exists.

### 3. The repo, submission and demo surfaces a judge actually reads are stale, and the required SI disclosure is missing

**Evidence:**
- **The repo README contradicts the build.** `README.md` on `claude/perigee-integration` (and on `main`) still says:
  - line 7: "**Status:** documentation and research only";
  - line 60: "There is no frontend, backend, executable processing script, or generated demo asset in this repository yet".
- **No SI disclosure text.** The project was built largely by parallel Claude/Codex agents (46 commits carry `Co-Authored-By: Claude`). But `grep -rn -i -E "assisted|claude|codex|generated with|\bAI\b" frontend/src` finds only internal code comments: no user- or judge-facing SI statement.
- **Disclosure is optional in the draft.** The pitch draft treats disclosure as an open option ("whether to name the parallel AI-assisted build", decision 6).
- **No global-judging demo is planned.** The submission demo seen by global judges is 7 slides or 30 s of video. The draft plans the 5-minute local talk in detail, but has no 30-second video or slide-only version that stands without narration.

**Why it costs points:**
- **Presentation:** a judge who follows the repo link reads that nothing exists.
- **Validity:** the README contradicts the working build.
- **Compliance and Creativity:** the submission guide requires SI generation to be acknowledged "in descriptive text and metadata". Judges "evaluate originality, intent, and execution based on the SI-assisted elements you include and identify". An undisclosed AI-built codebase is a credibility risk that a short honest note removes.

**Owner:** Sagar (final submission owner), with Sathvik (pitch and story). Neeraj assembles the slides.

**Fix within the sprint (about 1–2 h):**
- Rewrite the README's top 20 lines with:
  - what Perigee does;
  - the public URL (after finding 1);
  - local run commands;
  - NASA data used (IRSA SPHEREx DR1/QR3, plus Gaia DR3 for checks);
  - credits;
  - a plain SI statement: the team chose the idea and owns the science checks, AI coding agents generated much of the code under review, and there is no runtime AI.
- Add one SI line to the app footer or "Observation sources & processing" panel.
- Make the 7-slide deck self-explanatory without narration, since global judges read it cold. Put the S2 Barnard/Epsilon frames and the public URL on the slides.

## Not findings (checked and fine)

- Live search from the URL works: `?view=query&ra=133.795&dec=-7.2452`, the challenge's WISE 0855 position. It returned 24 of 258 matches in DR1+QR3, the first frames were ready in about 15 s, and it showed status counts honestly.
- Marker, flag and stretch caveats are consistent across the case and query views.
- The science acceptance and Barnard imagery reviews are thorough and support the pitch's numbers.

## Limitations of this review

- **Scores are estimates.** They are one reviewer's estimate against the published rubric descriptions. No judge input or past scoresheets were available.
- **Not exercised:**
  - the phone layout (worker 17 is still running);
  - evidence export file contents, print, and "Check your claim against the case guide";
  - IRSA failure states;
  - the full 24-frame queue (stopped after 9 frames to limit IRSA load).
- **Deployment not tested.** No deployed build was available to test. The serverless timing of `/frame` on Vercel is unverified.
- **How the challenge text was read.** The challenge page was blocked in the built-in browser and returned only a shell to `WebFetch`, so it was read from the page's embedded data downloaded with `curl`.

Screenshots in this folder:
- `01-home-1280.jpg`: home
- `02-epsindi-fair-comparison-1280.jpg`: Epsilon Indi B case, first viewport
- `03-barnard-AC-guide-line-1280.jpg`: Barnard A/C with the guide line and flag overlay
- `04-live-search-wise0855-url-1280.jpg`: URL-driven live search
