# Perigee completion audit

Audited on 14 November 2026 in America/Chicago, against main `9cb850bc2729` and the public Cloudflare app. **The core application works, but it is not ready to call fully finished.** This pass found scientific-display and navigation defects that the passing test suite did not cover. The first priority is correcting those defects, then making release checks trustworthy and demonstrating the educational contribution.

Sathvik's current ownership decision: Claude implements backend/platform work. Codex audits the frontend and waits for Sathvik's specific frontend instructions. No frontend or backend application source was changed during this audit. [Claude's complete assignment](backend-next-pass.md) contains the backend acceptance criteria.

**New comparison evidence:** Suhrit's 7:48 p.m. email identifies [SPHEREx Explorer](https://spherex-explorer.vercel.app/). Direct inspection of its live [methods](https://spherex-explorer.vercel.app/about) and [loaded cases](https://spherex-explorer.vercel.app/discover) shows more overlap than the email suggests: it already describes quality masking, saturation caveats, wavelength-aware comparisons, and authored cases with evidence and limitations. Their numerical results have not been independently reproduced in this audit. Educational cases or quality awareness alone are therefore insufficient novelty claims. The narrower distinction to verify is learner-authored, revisable, source-linked reasoning that an educator can review, followed by an unfamiliar transfer task. Perigee has evidence cards; demonstrated learning gains remain pending. Claude has been assigned this additional comparison.

## Current evidence

### Neeraj's later QA report, triaged against this release

Neeraj's email, sent 14 November at 7:07 p.m. Chicago time, includes a 390×844 browser-emulation report and screenshots. It reports successful pair switching, playback, notebook persistence and export. It explicitly excludes a physical phone, screen reader, timed rehearsal and production live search. His deployment reference is older than the current Cloudflare release, so use the observations with that boundary.

- The old Vercel deck URL returning HTML is superseded by the verified Cloudflare PDF; keep using the Cloudflare app/deck links.
- His reported “19 and 20 versus the script's 19 and 18” is **not a confirmed A+B defect**. Current Cloudflare case JSON and local case records give A=19, B=18, C=20 valid aperture pixels. The 19/20 combination corresponds to A+C. Rehearse with the pair named explicitly; do not change A+B's figures to match another pair.
- Empty cards after merely opening a case are reported, not independently reproduced here. The code does save a draft when a comparison pair is selected, even without text. Check fresh storage and distinguish opening a case from switching its pair before changing persistence semantics.
- Barnard's duplicate “Different dates” labels and “Blink the three frames” instruction are supported by the current source. Clarify the time intervals and distinguish two-frame comparison from three-frame timeline playback during the frontend/content pass.
- Flag abbreviations are printed without individual definitions. The existing background does explain saturation and OVERFLOW/BLOOM, so do not say there is no explanation anywhere. Add concise, scientifically accurate meanings near the codes when frontend work resumes.
- Neeraj offers to rehearse. His suggested simpler script is useful, but preserve scientific qualifiers: a **median** registration residual is not a maximum bound on every star; a screen with no adverse flags does not prove that all pixels are good. Keep catalog predictions separate from measured positions.

| Check rerun in this audit | Result |
| --- | --- |
| Backend pytest with the local FITS dataset | 348 passed |
| Backend pytest without the raw-data environment variable | 330 passed, 18 correctly skipped |
| Frontend Vitest | 121 passed |
| Frontend TypeScript and production build | Passed; JavaScript 102.17 kB gzip, CSS 6.61 kB gzip |
| Cloudflare Worker tests | 15 passed |
| Cloudflare export parity | 7 passed |
| Public app and live query | Working; Orion returned 377 matches |
| Fresh direct frame request for a 10′ field | Correct 10′ grid; independently isolates the cache problem to the frontend |
| Public seven-slide PDF | 2,369,713 bytes; SHA-256 `ffab44ce1f9fe182d2b9f427ae186c30e18e2cfc7ff6ea24099ecbd8d05ca89e` |
| Controlled case-product outage | Guided bench silently substituted general-sequence products |
| Controlled overlay-image outage | Failed images had `naturalWidth: 0`; checked toggle and legend remained without an error |
| Narrow layout | Home and both guided cases inspected at 320 CSS px; no horizontal overflow in those inspected views |

This is a scoped audit, not a full security, accessibility, performance or astronomy certification. Existing independent science reviews cover 189 bundled records and separate Gaia registration checks; this pass reran the available 348-test suite, not every independent science-review script. Physical devices, a screen reader, cold mobile performance and unfamiliar human users remain untested in this pass.

## Frontend findings awaiting Sathvik's instructions

### F1 — P1 — A second search can display the wrong sky cutout

**Confirmed on the public app.** Search RA `83.82208`, Dec `-5.39111`, FOV `2`, maximum results `1`. After it loads, change only FOV to `10` and search again. The results heading and URL say 10′ while the image still says 2′. The reused observation is `2025W36_2B_0338_1_D1`. A fresh direct API call returns a correct 10′ registration.

`frontend/src/components/QueryInvestigation.tsx:93` keys the session cache only by API mode and `frame_key`. Neither query geometry nor release/source identity is included. Both the initial slot lookup and `loadFrame()` use that key. This can affect the image, sampled wavelength, quality and saved evidence after a position or field-size change.

**Required result:** include normalized RA, Dec, FOV and source/release identity in cache identity, and use the same identity at every read/write/retry. An identical request may reuse a frame; a different cutout must not. Add an interaction regression for two successive searches and verify image registration, notebook context and export. Preserve correct stale-request cancellation.

Evidence: [screenshot](../qa/completion-audit/wrong-field.jpg), [DOM record](../qa/completion-audit/wrong-field.txt), [fresh backend frame](../qa/completion-audit/fresh-frame.json).

### F2 — P1 — Navigation can change a query URL without changing the shown investigation

**Confirmed on the public app.** After a completed search, click the main “Search coordinates” link. The URL becomes `?view=query`, but the previous coordinates, results and notebook remain. The app therefore displays an investigation whose address no longer reproduces it.

`App.tsx` keeps `QueryInvestigation` mounted with a key based only on API mode; its initial inputs and auto-search effect are mount-only. Same-view route changes are not reconciled. Merely adding every query value to the component key would risk remounting when a successful search updates its own URL.

**Required result:** distinguish external navigation/back/forward from a successful search's own URL update. The address, form, shown results and notes must agree; preserve drafts and prevent duplicated searches. Include shared-link reopen and browser-history cases. Also decide whether result limit belongs in the URL: currently a one-result link reloads with the default 24.

### F3 — P1 — A missing quality overlay is visually indistinguishable from a loaded overlay with no visible flags

**Reproduced with a local server returning 404 for flag PNGs while serving the real images and metadata.** `Plate.tsx:103` has no overlay load/error state. “Show flagged pixels” stays checked and the color key stays visible even when both overlay images fail. A learner following the bad-pixel investigation cannot tell that the quality layer is unavailable. The numerical quality summary remains valid; the failure is the unannounced visual layer.

**Required result:** separately track science-image and mask loading/failure, show a specific unavailable state, and offer recovery without losing notes or swapping observations. A failed mask must not be presented as evidence that no flagged pixels exist. Keep numerical quality status separate from overlay availability. Test one failed mask, both failed masks and recovery.

Evidence: [failed overlay DOM and image state](../qa/completion-audit/overlay-failure.txt).

### F4 — P2 — Guided products silently fall back to different display processing

**Reproduced with a local 503 for the case-specific frame list.** `PresetInvestigation.tsx:42` swallows the error, and line 112 substitutes same-ID frames from the general sequence. In Epsilon Indi A+B this changes shared-stretch products to individually stretched products without saying the case download failed or offering retry. The generic per-frame stretch caveat does appear, so the app is not wholly hiding the difference; it still silently changes the authored exercise.

**Required result:** retain free exploration, but explicitly mark the guided products unavailable and offer a retry. Do not silently substitute a scientifically different rendering. Preserve text already entered. Decide deliberately whether to disable the guided comparison or present an explicitly labeled degraded version.

Evidence: [fallback DOM](../qa/completion-audit/case-fallback.txt).

### F5 — P2 — My evidence has two destinations and leaves keyboard focus behind

**Confirmed on the public app.** On an investigation, “My evidence” scrolls to the current notebook, not the saved-card list. Focus remains on the header link. On the home page it means the saved collection. `App.tsx:66` also uses a fixed 50 ms delay for one navigation path.

**Required result:** give the saved collection and current notebook distinct, consistent destinations; move keyboard focus to the intended section after it mounts. Preserve modifier-key/new-tab behavior for genuine links. Test from home, both investigation types and a loading/error view.

### F6 — P2 — A required comparison frame offers a remove action that cannot remove it

**Reproduced locally.** In the guided A+B case, the sequence's “Attached to notebook · remove” button remains pressed after activation. `FrameViewer.tsx:474` presents a toggle, but `PresetInvestigation` automatically reattaches the active pair to `exportCard`.

**Required result:** identify frames attached by the active comparison as required, or make removal work consistently across the notebook and export. Do not offer an operation that is immediately undone by derived state. Keep optional extra observations independently removable.

### F7 — P1 — Notebook placeholders do not meet minimum text contrast

Computed foreground `rgb(117,128,152)` on `rgb(252,252,254)` is **3.869:1** at a 16 px normal font. The token is `--placeholder: #758098` in `styles/tokens.css:45`. The 4.5:1 criterion includes placeholder text. See [W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

**Required result:** adjust the placeholder token to at least 4.5:1 on the actual input surfaces, preserving the chosen visual system. Recheck computed colors and mobile rendering. Labels and hints already exist; preserve them.

### F8 — P2 — A new sky search can retain an unrelated guided-case identity

**Code-confirmed path; not exercised as a complete saved-card journey in this pass.** “Search the archive here” carries the preset's `caseId`. Subsequent successful searches keep `route.caseId` (`App.tsx:196`), while `QueryInvestigation.tsx:253` assigns it to new cards even when the user moves to another part of the sky. Saved titles can consequently imply that an unrelated coordinate card is still the original case.

**Required result:** define case context as a property of the appropriate investigation, not every later search in the same component. Clear or explicitly relabel it when the query no longer belongs to the case. Test the saved title and exported `case_id`, while preserving the original case's draft.

## Backend and platform work for Claude

| ID | Priority | Remaining work | Evidence and completion condition |
| --- | --- | --- | --- |
| B1 | P2 | Validate and classify unusable Worker catalog/proxy bodies and rejected asset reads | Three controlled failures reproduced: HTTP 200 HTML mislabeled JSON, an uncaught binding error, and invalid upstream JSON passed through. Fix with bounded validation and existing error envelopes; keep successful bytes and parity unchanged. |
| B2 | P1 | Put relevant unit and Cloudflare checks into CI | `deploy-check.yml` omits Cloudflare from PR paths and does not run the test suites above. Cloudflare-only changes must run export/parity/Worker checks, and normal relevant PRs must run unit tests without secrets or live archive calls. |
| B3 | P2 | Identify the static build actually served and verify expected release identity | Cloudflare build info is outside public assets; health is the older Vercel service. A green Vercel-triggered smoke is not proof of a Cloudflare redeploy. Compare static source/content identities and report the backend separately. |
| B4 | P2 | Correct guidance about reducing the archive search | `search.py:160` says smaller FOV returns fewer matches, but `_archive.py` searches a fixed-radius query center. The two live searches returned the same 377 matches. Correct the guidance; do not add an unplanned search protocol. |
| B5 | Contribution work | Produce an evidence-based adjacent-tool comparison and a draft transfer exercise | Primary sources, reproducible observations and explicit limits. Keep a new exercise out of production until scientific review and frontend direction. No invented human outcomes. |

The full implementation prompt, preserved behavior and acceptance checks are in [backend-next-pass.md](backend-next-pass.md). Source fixes and deployed fixes must be reported separately while Vercel builds are quota-limited.

Aditya independently verified the current API, token rejection, non-preset search and browser retry. He has **no new PR**. His [verification](https://github.com/sathvikloke/perigee/issues/4#issuecomment-6887141847) and [processor compatibility notes](https://github.com/sathvikloke/perigee/pull/19#issuecomment-6887382417) support preserving processor A. His deck/source-label blocker describes Vercel before the primary Cloudflare release and is no longer a blocker for the submitted Cloudflare links.

## Contribution and presentation work

Technical complexity is already substantial enough for a focused hackathon project. More complexity alone will not close the impact, novelty or story gaps.

1. **Define the contribution precisely.** A learner can make and explain a cautious claim using time, wavelength, quality and traceable source files in one guided workflow. Existing blinking/registration tools are the baseline, not inventions to claim. Compare the closest SPHEREx tools directly, not only IRSA and Backyard Worlds.
2. **Make the human outcome observable.** Have two unfamiliar people state an initial interpretation, complete a guided case, then attempt a different pair without coaching. Record where they got stuck, whether they distinguished date from wavelength, and whether they treated a prediction or flag-screen pass as a detection. This is a useful small usability check, not proof of broad educational effectiveness.
3. **Prepare one reason to return.** An independent transfer exercise or a teacher-assigned new question is a meaningful second use. A saved notebook alone does not establish repeat motivation. Claude can prepare a scientifically reviewed candidate; its presentation waits for frontend instructions.
4. **Rehearse the story around a decision.** Show an apparent change, let the audience form an interpretation, reveal the relevant quality/wavelength evidence, then show a learner's reasoned conclusion. Keep the vivid Barnard motion example and the Epsilon Indi comparison lesson. Do not claim a newly detected object or measured motion.
5. **Align the pitch with the final release.** The deck exists and is public. After fixes, make its screenshots, URLs, feature claims and the project description match the exact build. Existing text that implies every frame was individually Gaia-validated needs narrowing: independent FITS re-derivation and separate field-star registration checks are different evidence.

The previous five examples are 2025 **category winners across challenges**, not five SPHEREx winners: SpaceGenes+ (Science), Resonant Exoplanets (Data), SkySense (Technology), A Solar Tale (Storytelling), and Henry's Farm Adventures (Art and Technology). Their [official awards](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/) establish the distinctions, not a numerical ranking or a guarantee that Perigee matches them. A strong comparator has a clear audience, an understandable benefit, a working demonstration and an evidence-supported contribution. Perigee's scientific care is a strength; user benefit and differentiation need the concrete demonstrations above.

## Submission and final release gates

- **Team:** settle the existing personal facts in `docs/AI_USE.md` and submission draft accurately. Do not invent attestations or describe agent checks as human review.
- **Team:** confirm team registration, the Local Event presentation slot and the actual submission deadline; submit the project and verify the submitted links. Preparing a draft is not submitting it.
- **Claude/platform:** supply tested backend changes and exact release provenance; account for Vercel quota honestly. Do not interpret every push or green CI result as a deployment.
- **Codex, after frontend instructions:** fix F1–F8, add meaningful interaction regressions, and test the combined release at desktop/narrow widths with keyboard navigation, notes persistence, export and the new failure paths.
- **Team:** one real phone and one screen-reader pass, then a logged-out run from the links entered in the competition form. Capture any remaining limitation instead of declaring complete accessibility.
- **Release owner:** preserve the current working deployment until the replacement passes. Verify the app, curated cases, fresh non-preset query/frame, deck MIME/hash and exact expected build. Check source labels on the primary app.

## Defer unless a demonstrated need changes the priority

- New discovery algorithms, calibrated photometry, numerical motion measurement, spectra, accounts, a mobile-native rewrite and additional AI models.
- Full NASA-archive downloads or a processor replacement. Existing verified observations are sufficient for the current cases.
- JSON import, cross-device notes, multiple attempts per target, new teacher management screens, and more cases beyond one validated transfer candidate. These may help repeat use, but require product decisions; current local persistence is not cloud sync.
- A global rate limiter/cache/queue redesign. There is currently no global application limiter; that was an explicit D2 decision. Assess a real platform rule before wider promotion if needed, including direct Vercel access. Do not pretend a per-process counter is global protection.
- Closing old candidate PRs and pruning branches. These do not block the working demo and should not be confused with merging their content.

## Design audit summary

The interface has a coherent product-specific system: paired sky plates, explicit observation metadata, quality controls and an evidence notebook. Preserve that structure and the navy/cobalt/lavender tokens. The integrity problem is several state/failure paths, not a need for a redesign.

Provisional technical scores using the Impeccable audit scale: accessibility **2/4**, performance **3/4**, responsive behavior **3/4**, theming **4/4** within the intentional light theme, implementation integrity **2/4**; **14/20**. This is a scoped engineering/design assessment, not a Space Apps judging score or a WCAG conformance claim. No new dark mode is required. The static detector returned no findings on `frontend/src`; it did not catch the verified runtime defects or the measured placeholder contrast and cannot establish a clean bill of health.

There are **12 technical findings: five P1 and seven P2**, no observed site-wide P0 outage, plus contribution and team release tasks. Recommended frontend sequence after instructions: Impeccable harden for F1–F4/F8, clarify for F5–F6, colorize for F7, then polish. Add onboarding changes only after Sathvik chooses the presentation direction. Repeat the affected interaction checks and audit after fixes.

Keep the working strengths: genuine NASA data, explicit scientific limits, controlled processing budgets, signed frame requests, preserved drafts during archive failure, deterministic playback/filter controls, no-login curated cases, and a public deck. They make this a credible project worth improving; they do not erase the reproduced defects.
