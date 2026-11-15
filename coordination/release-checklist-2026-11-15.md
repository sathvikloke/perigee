# Perigee release and submission checklist

Prepared for Sathvik and the release coordinator on **15 November 2026**. This is a completion checklist, not evidence that the new working-tree changes are deployed or that the competition entry has been submitted.

## Deadline and event identity

**The Space Apps project submission cutoff is Sunday, 15 November 2026 at 11:59 p.m. in the Local Event's time zone.** For Perigee's Chicago event, that is **23:59 CST (UTC−06:00), or 05:59 UTC on Monday, 16 November**. The [official 2026 event page](https://www.spaceappschallenge.org/2026/) explicitly names this closing time; the [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/) applies the Local Event time zone. Do not calculate the deadline by adding 48 hours to the Saturday start.

The [2026 registration PDF](https://assets.spaceappschallenge.org/media/documents/2026_NASA_Space_Apps_Registration_Recruitment.pdf) independently confirms the **14–15 November 2026** edition. There is **no date or edition discrepancy** between those official sources and this workspace's November 2026 context.

The [Perigee team page](https://www.spaceappschallenge.org/2026/find-a-team/perigee/) identifies **Planet X and SPHEREx** and **Chicago, IL**, with virtual participation stated in the team's description. The [Chicago event page](https://www.spaceappschallenge.org/2026/local-events/chicago/) is the local schedule authority. **The Sunday pitch slot, any earlier local upload deadline, and the local talk duration remain unverified.** Earlier repository notes disagree on whether a five-minute talk was confirmed; treat that length as a rehearsal format until the organizer confirms it. Plan an early readiness buffer, not a presumed noon presentation.

Local judging and nomination are distinct from the platform cutoff. The [Judging & Awards Guide](https://www.spaceappschallenge.org/resources/judging-awards-guide/) describes selection of Global Nominees after the hackathon; December announcements are not an extension for the team's submission.

**Source verification:** the official event-page and recruitment-PDF text were returned by web search on 15 November. Direct fetches of the detailed guide, team and Chicago pages returned timeouts/502s (raw HTTP fetch returned 403). Their previously retrieved official page snapshots were inspected locally: the submission guide is dated 13 November 2026; the cached team record identifies Chicago and the challenge; the cached Chicago schedule array is empty. No present-day account registration, submitted state or newer local schedule was inferred from those snapshots. The coordinator separately checked the latest available organizer message and found no exact Sunday pitch slot. No private message text is stored here.

## Required completion gates

- [ ] **Integration:** all assigned code/content workers and the separate landing-page work finish; the coordinator reconciles their changes on the shared branch. Preserve unrelated edits. Record the exact final source revision.
- [ ] **Verification:** run the appropriate frontend tests, TypeScript/build, backend/content tests and release checks for the final combined change. Inspect the real desktop and narrow main journey, image/overlay failure recovery, saving, reopening, JSON export and print output. Earlier green runs cover only their recorded revisions.
- [ ] **Deployment:** the coordinator deploys the final approved build, records the Cloudflare release identity and Python-origin state, and repeats the logged-out release checks. Verify the social image and static metadata from the public URL after deployment.
- [ ] **Story and artifacts:** only after the assigned work and landing-page work finish, prepare the requested story-heavy video script/storyboard and the remaining day's schedule. Anchor the story in students and curious observers noticing an apparent change, checking dates/wavelengths/quality, and recording a supported conclusion with uncertainty. Keep the final video artifact within the applicable demo limit if selected as the official Project Demo.
- [ ] **Submission text:** reconcile the older [draft](../docs/SUBMISSION_DRAFT.md) with the final product. It still describes two guided investigations; the [latest release record](../qa/final-investigation/README.md) documents three. Replace categorical “bad pixel, not a change” wording with the accepted scientific limit: the flags make that pixel unreliable; they do not establish the cause. Do not present measured learning, calibrated brightness, measured motion or discoveries.
- [ ] **Team review:** Sathvik/Sagar settle personal attestations in [AI_USE.md](../docs/AI_USE.md), confirm the final team roster and same-event registration, and review the project page. These facts cannot be inferred from code or filled in by an agent.
- [ ] **Submit and confirm:** the team owner completes the official form and its required declarations, clicks **Submit for Judging** before 23:59 CST, and records the success banner/confirmation. “Save Progress,” public hosting, a finished deck and this checklist do not mean submitted. Aim to finish well before the hard cutoff and preserve time for link fixes.

## Submission format checks

The [official submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/) requires a public demo link: **at most seven slides including title/intro, or at most 30 seconds of video**. Use English for the submission and slides; a non-English video needs English subtitles. Show the project, experience and NASA-data use; include team identity and the selected challenge. Final-project/demo links must open without authentication. Complete the summary, detailed description, NASA data, other references and SI-use fields. Credit external resources, disclose SI assistance, watermark SI-generated images/video, and exclude minors' likenesses from submitted media. Verify every team member is accepted at the same event. Review the full guide before final submission.

## Artifact inventory

| Artifact | Location | Current status / remaining work |
|---|---|---|
| Public app / Final Project link | [perigee.lokesathvik.workers.dev](https://perigee.lokesathvik.workers.dev/) | Existing released app; final audit/landing changes need coordinator verification and deployment. |
| Public source | [GitHub repository](https://github.com/sathvikloke/perigee) | Recorded public source; ensure the submitted branch contains the final release and disclosures. |
| Official team/project page | [Perigee](https://www.spaceappschallenge.org/2026/find-a-team/perigee/) | Team exists in official saved page data; no submission confirmation inspected. |
| Challenge | [Planet X and SPHEREx](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/) | Official selected challenge; use this exact title in artifacts. |
| Seven-slide demo PDF | [Public PDF](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf), [repository copy](../frontend/public/demo/perigee-demo.pdf) | Existing seven-page deck; [deck record](../docs/presentation/DECK.md) reports render review and SHA-256 `ffab44ce1f9fe182d2b9f427ae186c30e18e2cfc7ff6ea24099ecbd8d05ca89e`. Reconcile older UI captures/science wording with the final story before submission. |
| Editable deck | Connected Spaces title **Perigee — NASA Space Apps demo** | Recorded in the deck notes; no direct editable URL is stored in the repository. |
| Recorded video | No published video link or finished video file found in the inspected presentation/coordination records | Requested storyboard/script remains a coordinator deliverable after all assigned work. Recording, editing, timing and public hosting remain necessary if video is chosen. |
| Existing longer talk/rehearsal | [Presentation handoff](../docs/presentation/README.md), [capture folder](../docs/presentation/rehearsal/) | Historical five-minute rehearsal and real captures; not a 30-second global demo video. Includes JSON/PDF evidence-card examples. |
| Project form draft | [SUBMISSION_DRAFT.md](../docs/SUBMISSION_DRAFT.md) | Draft only; needs the content reconciliation above and entry into the official form. |
| Scientific claim evidence | [Award evidence](overnight-award-evidence.md), [acceptance review](../science/reviews/acceptance/README.md), [third-case release](../qa/final-investigation/README.md) | Trace quantitative claims to the exact bounded checks; do not convert them into demonstrated classroom impact. |
| Social share preview | [1200 × 630 PNG](../frontend/public/social-preview.png), [renderer](generate-social-preview.py) | New local asset and metadata; must be included in final deployment. Code-rendered typographic brand graphic with AI code-assistance attribution in PNG metadata; no image-generation model or simulated sky imagery. |

## Metadata verification

`frontend/index.html` now contains matching document/OG/Twitter titles and descriptions, a canonical public homepage URL, `summary_large_image`, absolute HTTPS image URLs, image alt text, PNG MIME declaration and 1200 × 630 dimensions. The original font preload and favicon remain.

The PNG was rendered with the bundled Host Grotesk font and existing Perigee mark, then visually inspected. Static validation confirmed unique metadata keys, aligned title/description/alt values, the canonical/image URLs and actual PNG dimensions. The current graphic is **117,404 bytes**, with no visible tooling disclosure; accurate code-assistance attribution remains in its PNG metadata and the project's AI-use account. An isolated Vite production bundle in `/tmp/perigee-social-preview-build` passed before removal of the visible label. The coordinator's final combined typecheck/tests/build, copying of this regenerated PNG and public crawler fetch still remain. Metadata is shared across this client-routed app; it does not promise per-investigation server-rendered social previews.
