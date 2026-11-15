# Team and schedule

Execution priority: follow the [short two-day sprint brief](SPRINT_BRIEF.md); use this document as reference.

The six team members are **Sagar Raut, Akshobya Rao, Aditya Raut, Neeraj Movva, Sathvik Loke, and Suhrit Bestavemula**. The assignments below reflect Sathvik’s updated direction: Sathvik and Sagar own all data work, Akshobya owns frontend, Aditya and Suhrit own backend, and Neeraj has a light support role outside the critical path. [Perigee team page](https://www.spaceappschallenge.org/2026/find-a-team/perigee/).

| Owner | Workstream | Concrete handoff |
|---|---|---|
| Sathvik Loke | Data analysis, scientific validation, investigation content and pitch | Own the full dataset with Sagar; select case frames, check alignment/wavelength/flags, write supported conclusions, and own the final story/slides |
| Sagar Raut | Data engineering and archive processing; final submission owner | Own the full dataset with Sathvik; retrieval, FITS-to-preview processing, manifests and callable data functions for the backend team |
| Akshobya Rao | Frontend and visual design | Coordinate form, five presets, viewer, timeline/wavelength controls, case screens, evidence card, local save/export/print and loading/error states |
| Aditya Raut | Backend query API and bounded frame requests | Input validation, search/frame endpoints, progressive results, bounded retries and integration with the data functions supplied by Sathvik and Sagar |
| Suhrit Bestavemula | Backend storage, content serving and deployment | Cache/storage integration, image/manifest/case endpoints, public deployment, health checks and backend integration checks |
| Neeraj Movva | Light testing and submission support | Fresh-browser checks, broken-link reports, screenshots and optional slide assembly; no required feature or deadline depends on his availability |

Plan for **five active builders**, with Neeraj providing optional support. At roughly 14–18 focused hours per active builder, budget about 70–90 person-hours total, including integration and presentation; do not count Neeraj’s availability toward required delivery. Akshobya is the single frontend owner, so Sathvik supplies finished case copy and conclusions, while Aditya and Suhrit deliver stable endpoints and data shapes. Sathvik owns the pitch/slides; Neeraj can help assemble them. In the first hour, Sathvik and Sagar agree the processing interface with Aditya and Suhrit, and all five agree the frontend manifest contract. The existing scope and milestones remain the ceiling; cut optional work early.

All times below are **Chicago time, CST**. These are the original build milestones; use the [15 November recording and submission schedule](presentation/SUBMISSION_VIDEO.md#sunday-schedule-in-chicago-time) for the remaining day. The organizer information gives Saturday November 14 at 9 AM as the start. Sunday's exact local pitch slot, talk duration and any earlier upload cutoff remain unverified; earlier five-minute/noon notes were rehearsal assumptions. The global platform deadline is Sunday November 15 at 11:59 PM CST. [Chicago event](https://www.spaceappschallenge.org/2026/local-events/chicago/), [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/).

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
