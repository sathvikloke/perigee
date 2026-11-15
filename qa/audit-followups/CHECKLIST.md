# Audit completion checklist

Reconciled on 15 November 2026 against the user's two pasted usability audits, the attached 12:48 a.m. audit, and the requested copy/motion changes. This separates application fixes from recording/submission tasks and from verification limits. The initial usability release is PR #54; the final invalid-link recovery action is the subsequent audit-completion change.

## First pasted audit

| Item | Implementation | Evidence |
|---|---|---|
| Transient frame 502s | Two bounded automatic retries with backoff/jitter; two concurrent frame requests; completed-frame cache. This addresses recovery, not NASA availability. | `frameRecovery.ts`, `frameCache.ts`; injected-failure check in `recovery-verification.json`. |
| Slow search and failed first image | Frontend defaults to 12; first ready frame selected while other frames load. User selection then takes precedence. | `QueryInvestigation.tsx`; real public search finished 12/12. |
| Raw errors | Human-readable errors and retrying/loading messages replace API codes in the user interface. | `common.tsx`, `FrameViewer.tsx`. |
| Investigations navigation | Correct `/#investigations` destination, scroll and heading focus. | Public browser verified. |
| “Blink the three frames” | Instructions refer to playing each pair, with the relevant A+B/A+C checks preserved. | `moving_neighbor.json`, `PresetInvestigation.tsx`. |
| Hidden A+C requirement | Explicit required-pair explanation and one-click recovery preserve notes. The scientific completion requirement remains. | All three case requirements tested; fresh Epsilon browser flow. |
| Disabled reference looks enabled | Disabled action is gray; enabled primary action remains citron. | Existing styles and 390 px reference check. |
| Reference appears below fold | Newly revealed reference scrolls into view and receives focus; reduced motion is respected. | `Notebook.tsx`; completed fresh browser journey. |
| Identical pair labels | Actual intervals or comparison purpose shown, e.g. 7 months / 1 year for Barnard. | `CaseBench.tsx`; public view. |
| Slider begins at 4/34 without explanation | Optional explorer starts at authored image A, explicitly labeled **Investigation image A**, and shows its actual chronological position. It is now collapsed after the notebook. | `PresetInvestigation.tsx`, `FrameViewer.tsx`. |
| Blink shrinks or jumps | Stable stacked image geometry; desktop reference image stays visible. Metadata rows reserve equal height on phones. | Equal WISE image bounds at 360 px, local playback checks. |
| Flags dominate by default | Overlays start off; quality status and a plain explanation remain visible. | `CaseBench.tsx`, `FrameViewer.tsx`; rendering tests. |
| Object names and sexagesimal input | Name-first search with SIMBAD/Sesame resolution; strict decimal or HH:MM:SS/degree:minute:second coordinates. | Resolver and coordinate tests; live Barnard, Epsilon and Vega checks. |
| Epsilon preview mismatch | Home preview uses A+B, matching the default case. Saved user work may intentionally restore another pair. | `landingPreview.ts`; authored-pair tests. |
| Phone comparison | Horizontal swipe plus explicit image buttons and playback; vertical scrolling is protected from accidental swipes. | Gesture logic tests and narrow browser inspection; physical touch remains untested. |
| Case button accessible names | Target and question are included in each accessible button name. | `Home.tsx`; public accessibility tree. |
| Social preview | OG/Twitter title, description and 1200 × 630 PNG published and byte-checked. | `README.md` public release record. |
| Footer label | Link reads **AI use disclosure** and opens the actual disclosure document. | Public browser verified. |
| Empty JSON download | Download disabled until observations and required note fields are present. | `Notebook.tsx`; export/completion tests. |

## Second pasted usability audit

| Concern | Implemented response |
|---|---|
| Guidance arrives late | Immediate case/pair-specific **Notice** instruction above the images. |
| A conclusion is requested before observation | **What did you notice?** comes first, with a sentence starter; explanation and uncertainty follow. |
| Controls describe structure instead of purpose | Date/wavelength pair labels, **Earlier/Later observation**, and **Play comparison**. A/B/C remain as useful source references. |
| Scientific language overwhelms | Plain explanation of what can still be learned; detailed processing and terminology are expandable. Essential quality/measurement limits remain visible. |
| Phone flow requires excessive travel | One active guided check at a time; checks lead to the notebook; optional full archive is collapsed after it; focus/scroll connects each step. |
| Search feels expert-only | Prominent example, object-name entry, optional coordinate mode and collapsed advanced controls. |

## Attached scientific and presentation audit

| Finding | Implemented response |
|---|---|
| False shared-stretch statement for WISE/Epsilon A+C | Compatibility is derived from both records and their mapping parameters; separate stretches cannot establish a brightness change. |
| Inaccurate hatching description | Visible text, alt text and quality explanations include missing coverage and saturated/non-finite pixels; hatching does not mean dark sky. |
| Missing immediate instruction/flag key | Immediate **Notice** instruction; legend beside the enabled overlay control. |
| Stale accessible search status | Status uses queued/loading/ready/error counts and announces actual completion. |
| Fragmented 320 px provenance | Narrow layout uses labeled observation records with readable wrapping. |
| Safari PDF drops legend swatches | Print colors are preserved for scientific images and legend swatches; backgrounds-off PDF inspected. |
| Optional direct recovery from invalid investigation link | **Choose an investigation** action now opens the investigation list, scrolls and focuses its heading. Local behavior verified before deployment. |

## Copy, motion and visual requests

| Request | Implemented response |
|---|---|
| Remove the three screenshot callouts | Removed “A new view of the familiar,” “An invitation to look closer,” the “NASA SPHEREx observations · No account needed” line and “Explore the targets.” |
| Less dramatic but purposeful copy | Shorter hero/investigation introductions, clear verbs and observation-first notebook prompts. Black/citron and Host Grotesk retained. |
| Meaningful landing motion | SPHEREx-inspired illustrated entrance and restrained drift, moving starfield, pause/replay/skip and reduced-motion state. Side chat completed and changes integrated. |
| Visible animation after Search | Button changes to **Searching…**, animated search indicator and scan; processing shows actual completed count/progress and finishes honestly. |
| Professional spacing and sizing | Responsive typography, consistent controls, stable playback dimensions and narrow provenance layout; checked at desktop and narrow sizes. |
| Winner comparison | Separate 50-winner visual study completed. It informed the design/story; it is not a guarantee of award competitiveness. |

## Submission tasks and verification limits

| Item | Status |
|---|---|
| Story with a clear audience and outcome | Prepared: students/teachers/curious observers; notice → check → explain with traceable evidence. |
| Short video demonstrating the complete idea | Script, six-shot plan and 29-second captions prepared in `docs/presentation/SUBMISSION_VIDEO.md`. **Final recording, edit and upload are not complete.** |
| Project-page text | Updated for three cases and bounded science claims. **Final media URL and accurate owner attestations remain inputs.** |
| Competition entry submitted before deadline | **Not confirmed submitted.** User confirmed 11:59 p.m. Local Event time; Chicago is CST. |
| Physical-device swipe and full screen-reader audit | Not performed. Browser layout/keyboard/focus and gesture logic were checked; those checks do not substitute for physical-device or full assistive-technology testing. |
| Populated PDF after final style change | Earlier audit verified a populated PDF. Final style check used an empty test notebook; populated JSON was checked separately. No claim of a fresh populated-PDF run on the final build. |
| Raw-data-dependent backend checks | 33 skipped in the final test environment; the recorded 428 passing tests exclude them. |
| Future upstream reliability or classroom impact | Not established. Recovery was exercised and a live 12-frame run succeeded; no invented uptime, user-learning or retention claims. |

See [verification record](README.md) for test counts, screenshots, deployment identity and the bounds of each check.
