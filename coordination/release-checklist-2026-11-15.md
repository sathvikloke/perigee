# Perigee release and submission checklist

Prepared for Sathvik and the release coordinator on **15 November 2026**. The application release is deployed and verified; the script and revised submission text are complete. Recording, team attestations and the competition submission remain open.

## Deadline and event identity

**The Space Apps project submission cutoff is Sunday, 15 November 2026 at 11:59 p.m. in the Local Event's time zone.** For Perigee's Chicago event, that is **23:59 CST (UTC−06:00), or 05:59 UTC on Monday, 16 November**. The [official 2026 event page](https://www.spaceappschallenge.org/2026/) explicitly names this closing time; the [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/) applies the Local Event time zone. Do not calculate the deadline by adding 48 hours to the Saturday start.

The [2026 registration PDF](https://assets.spaceappschallenge.org/media/documents/2026_NASA_Space_Apps_Registration_Recruitment.pdf) independently confirms the **14–15 November 2026** edition. There is **no date or edition discrepancy** between those official sources and this workspace's November 2026 context.

The [Perigee team page](https://www.spaceappschallenge.org/2026/find-a-team/perigee/) identifies **Planet X and SPHEREx** and **Chicago, IL**, with virtual participation stated in the team's description. The [Chicago event page](https://www.spaceappschallenge.org/2026/local-events/chicago/) is the local schedule authority. **The Sunday pitch slot, any earlier local upload deadline, and the local talk duration remain unverified.** Earlier repository notes disagree on whether a five-minute talk was confirmed; treat that length as a rehearsal format until the organizer confirms it. Plan an early readiness buffer, not a presumed noon presentation.

Local judging and nomination are distinct from the platform cutoff. The [Judging & Awards Guide](https://www.spaceappschallenge.org/resources/judging-awards-guide/) describes selection of Global Nominees after the hackathon; December announcements are not an extension for the team's submission.

**Source verification:** the official event-page and recruitment-PDF text were returned by web search on 15 November. Direct fetches of the detailed guide, team and Chicago pages returned timeouts/502s (raw HTTP fetch returned 403). Their previously retrieved official page snapshots were inspected locally: the submission guide is dated 13 November 2026; the cached team record identifies Chicago and the challenge; the cached Chicago schedule array is empty. No present-day account registration, submitted state or newer local schedule was inferred from those snapshots. The coordinator separately checked the latest available organizer message and found no exact Sunday pitch slot. No private message text is stored here.

## Required completion gates

- [x] **Integration:** all assigned app workers and the separate landing-page/winner-reference work finished. PR #54 merged as `4e247cf365300baf8f3df174ace2142a49479428`.
- [x] **Verification:** combined tests/build and desktop/narrow workflow, retry, persistence, JSON and Safari print checks passed within the bounds recorded in [audit verification](../qa/audit-followups/README.md). Physical-phone touch and full screen-reader testing remain outside this verification.
- [x] **Deployment:** Cloudflare version `7e8dfc44-b674-4f6a-ba1c-e4d0e848210c` is live; Vercel Python production is READY at the same Git revision. Logged-out edge/release checks passed 28/28 and 29/29. Public metadata/image and real browser name search were verified.
- [x] **Story and recording plan:** prepared the [29-second script, shot list, longer local rehearsal and day schedule](../docs/presentation/SUBMISSION_VIDEO.md) after release verification. Caption timing is included. Recording and hosting the final video are still required.
- [x] **Submission text:** the [draft](../docs/SUBMISSION_DRAFT.md) now covers three guided cases, current search and evidence behavior, and bounded scientific validation. The final hosted video URL and personal team attestations remain owner inputs.
- [ ] **Team review:** Sathvik/Sagar settle personal attestations in [AI_USE.md](../docs/AI_USE.md), confirm the final team roster and same-event registration, and review the project page. These facts cannot be inferred from code or filled in by an agent.
- [ ] **Submit and confirm:** the team owner completes the official form and its required declarations, clicks **Submit for Judging** before 23:59 CST, and records the success banner/confirmation. “Save Progress,” public hosting, a finished deck and this checklist do not mean submitted. Aim to finish well before the hard cutoff and preserve time for link fixes.

## Submission format checks

The [official submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/) requires a public demo link: **at most seven slides including title/intro, or at most 30 seconds of video**. Use English for the submission and slides; a non-English video needs English subtitles. Show the project, experience and NASA-data use; include team identity and the selected challenge. Final-project/demo links must open without authentication. Complete the summary, detailed description, NASA data, other references and SI-use fields. Credit external resources, disclose SI assistance, watermark SI-generated images/video, and exclude minors' likenesses from submitted media. Verify every team member is accepted at the same event. Review the full guide before final submission.

## Artifact inventory

| Artifact | Location | Current status / remaining work |
|---|---|---|
| Public app / Final Project link | [perigee.lokesathvik.workers.dev](https://perigee.lokesathvik.workers.dev/) | Final audit/landing release deployed and publicly verified; see the release record above. |
| Public source | [GitHub repository](https://github.com/sathvikloke/perigee) | Recorded public source; ensure the submitted branch contains the final release and disclosures. |
| Official team/project page | [Perigee](https://www.spaceappschallenge.org/2026/find-a-team/perigee/) | Team exists in official saved page data; no submission confirmation inspected. |
| Challenge | [Planet X and SPHEREx](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/) | Official selected challenge; use this exact title in artifacts. |
| Seven-slide demo PDF | [Public PDF](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf), [repository copy](../frontend/public/demo/perigee-demo.pdf) | Existing seven-page deck; [deck record](../docs/presentation/DECK.md) reports render review and SHA-256 `ffab44ce1f9fe182d2b9f427ae186c30e18e2cfc7ff6ea24099ecbd8d05ca89e`. Reconcile older UI captures/science wording with the final story before submission. |
| Editable deck | Connected Spaces title **Perigee — NASA Space Apps demo** | Recorded in the deck notes; no direct editable URL is stored in the repository. |
| Recorded video | No published video link or finished video file found in the inspected presentation/coordination records | Script/storyboard/captions are complete in `docs/presentation/SUBMISSION_VIDEO.md`; recording, editing, timing and public hosting remain necessary. |
| Existing longer talk/rehearsal | [Presentation handoff](../docs/presentation/README.md), [capture folder](../docs/presentation/rehearsal/) | Historical five-minute rehearsal and real captures; not a 30-second global demo video. Includes JSON/PDF evidence-card examples. |
| Project form draft | [SUBMISSION_DRAFT.md](../docs/SUBMISSION_DRAFT.md) | Reconciled with final release; needs the final media URL, accurate owner attestations and entry into the official form. |
| Scientific claim evidence | [Award evidence](overnight-award-evidence.md), [acceptance review](../science/reviews/acceptance/README.md), [third-case release](../qa/final-investigation/README.md) | Trace quantitative claims to the exact bounded checks; do not convert them into demonstrated classroom impact. |
| Social share preview | [1200 × 630 PNG](../frontend/public/social-preview.png), [renderer](generate-social-preview.py) | Included in the verified public deployment. Code-rendered typographic brand graphic with AI code-assistance attribution in PNG metadata; no image-generation model or simulated sky imagery. |

## Metadata verification

`frontend/index.html` now contains matching document/OG/Twitter titles and descriptions, a canonical public homepage URL, `summary_large_image`, absolute HTTPS image URLs, image alt text, PNG MIME declaration and 1200 × 630 dimensions. The original font preload and favicon remain.

The PNG was rendered with the bundled Host Grotesk font and existing Perigee mark, then visually inspected. Static validation confirmed unique metadata keys, aligned title/description/alt values, the canonical/image URLs and actual PNG dimensions. The current graphic is **117,404 bytes**, with no visible tooling disclosure; accurate code-assistance attribution remains in its PNG metadata and the project's AI-use account. An isolated Vite production bundle in `/tmp/perigee-social-preview-build` passed before removal of the visible label. The combined typecheck/tests/build passed. Public fetch returned the expected metadata and byte-identical image (HTTP 200, image/png). Metadata is shared across this client-routed app; it does not promise per-investigation server-rendered social previews.
