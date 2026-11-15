# Perigee overnight assignment: finish the science and backend evidence

Prepared by Codex for the existing **Perigee parallel implementation coordination** Claude Code session, on the night of November 14–15, 2026, America/Chicago.

## 1. The assignment and the completion rule

Sathvik is the only human working tonight. He has authorized a sustained implementation session and wants you to finish all remaining compute experiments and backend work before the final UI pass and submission. Codex owns the UI and final integration. This is an execution assignment, not a request for a proposal, another list of recommendations, or a research-only answer.

**Continue working until every mandatory package below has a documented, evidence-backed disposition and every feasible backend/science fix is implemented and verified.** Do not stop after planning, launching workers, producing their summaries, opening a draft PR, passing an initial test run, or completing only the easy packages. Independently review worker outputs, fix the defects you find, run the relevant checks against the integrated commit, update the handoff, and continue to the next unfinished package. A worker finishing is not the coordinator finishing.

If an external service, missing authorization, irrecoverable environment failure, or usage limit genuinely blocks one item, record the exact failing operation and the remaining dependency, try a reasonable alternative, and continue all independent work. Never fabricate a successful experiment, hide a failing check, label incomplete work complete, defeat platform limits, or repeatedly retry a known quota failure. A blocker is an honest residual dependency, not permission to abandon the rest. At a context boundary, preserve and resume from the durable state described below. Stop only when the scoped work is finished or all remaining work is genuinely blocked after alternatives are exhausted. Do not keep running redundant experiments merely to consume the night.

**There is no requirement to recruit users, get adoption, interview teachers, conduct a human study, or demonstrate measured learning gains.** This is a hackathon judged on a prototype and its potential. Do not make Sathvik or Sagar participation a prerequisite for your computational work. We still need a credible beneficiary, a useful task, a convincing demonstration, and accurate claims. You may demonstrate that the system exposes a confound or preserves evidence; you may not translate that into an unmeasured claim that people learn faster or make fewer mistakes.

The deliverable is a technically complete, reviewed backend/science candidate plus a precise UI integration handoff. It is not a guarantee of a global award. “Award-level” is our quality target, not a measurable pass/fail label or a reason to inflate results.

## 2. Product purpose and the contribution we are trying to make concrete

Perigee is a web application for investigating real SPHEREx observations. The primary user is a curious student or newcomer trying to understand whether a visible difference between sky images is evidence of change. A teacher or outreach facilitator is a plausible adopter. An expert can inspect the provenance, but this is not an expert-grade discovery or astrometric measurement pipeline.

The human story: someone sees a dot jump and wants to know whether they found something. A sky viewer can show the dots. Perigee should help them ask a better question, inspect dates, wavelengths, display scaling and pixel quality, distinguish observation from catalog prediction, revise a claim, and leave with a short evidence card that another person can inspect. The satisfying outcome can be a supported qualitative change or a justified refusal to claim a discovery. Both are real scientific reasoning.

Our narrow contribution is the **complete, source-linked investigation and reasoning record**, grounded in reviewed examples and usable on another comparison. Blinking images, aligning frames, wavelength labels, quality masks, shared stretch, authored cases, and export buttons individually are not new. Do not claim them as unique. Do not claim discovery of Planet X, measured proper motion, validated photometry, a detection limit, or a novel AI model. No runtime AI model is needed to finish this assignment.

Potential repeat use should be tangible: an initial guided investigation, a second investigation exposing a different trap, an unfamiliar comparison to investigate independently, and a saved or exported record that can be revisited or compared with a later record. A teacher could use multiple cases or compare reasoning across activities; we do not need to build a classroom management SaaS or prove adoption tonight.

The flagship demo should connect: **a real moving-neighbor example → a convincing false-positive example → a revised, traceable claim.** The second example must not be an unsupported gotcha. The claims and answer key have to survive scrutiny.

## 3. Research basis: what the recent global winners suggest

The reviewed 2025 category winners are comparators across challenges, not “previous SPHEREx winners.” Their project pages describe their own implementations and intended benefits; their numerical or scientific performance claims were not independently reproduced by us. We cannot infer judges' private reasoning or derive a deterministic winning formula.

Official announcement:
https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/

| Reviewed winner | Relevant pattern from its project description | Gap Perigee must close |
| --- | --- | --- |
| SpaceGenes+ — Best Use of Science | A focused scientific question, a NASA dataset, and a clearly described intended research use. | Make our scientific question, controls, and supported conclusion as concrete; test limitations rather than hide them. |
| Resonant Exoplanets — Best Use of Data | A described chain from astronomical input through analysis to an interpretable report. Its ambitious accuracy claims remain that team's claims. | Make our much narrower chain complete and reproducible: source data → comparison → checks → claim and evidence. Do not imitate unverified performance language. |
| SkySense — Best Use of Technology | A recognizable recurring decision for a named audience, with the tool integrated into that task. | Show why someone would open another investigation and what they can do with the resulting record. More technologies are not the goal. |
| A Solar Tale — Best Storytelling | A clear audience and an understandable narrative built around a scientific subject. | Supply accurate, brief story beats that make the scientific stakes understandable in seconds. A complicated backend alone cannot do this. |
| Zumorroda-X / Henry's Farm Adventures — Best Use of Art and Technology | Learner actions embedded in a human story, with NASA data connected to those actions. | Give the learner meaningful decisions and consequences for the claim; support a complete activity rather than a passive gallery. |

Team project sources, reviewed earlier by Codex:

- https://www.spaceappschallenge.org/2025/find-a-team/spacegenes/?tab=project
- https://www.spaceappschallenge.org/2025/find-a-team/resonant-exoplanets/?tab=project
- https://www.spaceappschallenge.org/2025/find-a-team/twisters/?tab=project
- https://www.spaceappschallenge.org/2025/find-a-team/hercode-space/?tab=project
- https://www.spaceappschallenge.org/2025/find-a-team/zumorroda-x/?tab=project

Codex retrieved the actual project JSON, beyond the HTML shells, at `/tmp/perigee-winner-benchmark/0-project.json` through `4-project.json`, in the same order as the table. Use these if you need the full descriptions. Do not depend on those temporary files for the final reproducible artifact. Summarize relevant facts and cite sources; do not copy entire project descriptions into our repo. The B5 comparison's account of what its own worker inspected remains accurate, but now include the additional Codex evidence with its distinct inspection scope.

Judging uses Impact, Creativity, Validity, Relevance and Presentation. The useful inference is: a clear audience and purpose, an interesting contribution, credible NASA-data use, a complete demonstration, and a comprehensible story reinforce one another. Existing customers and feature count are not our gates. These are our interpretations, not NASA promises of an award.

Official guides and challenge, already retrieved this evening:

- https://www.spaceappschallenge.org/resources/judging-awards-guide/
- https://www.spaceappschallenge.org/resources/project-submission-guide/
- https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/

Their cached text is under `/tmp/perigee-global-readiness/`. Preserve challenge relevance. A global nominee, finalist and global award are different stages, across challenges. Do not describe any of those as guaranteed. Do not widen this assignment into another exhaustive winner search.

Closest existing tools are in `science/reviews/contribution/README.md`. SPHEREx Explorer already has authored cases, wavelength checks, masks, shared scaling, cautions, a tour and a game. Codex previously rendered its home/About/Discover/tour/play surfaces; your B5 worker separately read the shipped bundle and API. The absence of a particular reasoning-record feature in the inspected surfaces is a bounded observation, not proof it exists nowhere. Other comparators include spherex-timelapse, SPHEREx Blink and Driftnet. Do not use their unreplicated published metrics to score ourselves or claim superiority.

## 4. Current baseline: do not restart or undo completed work

Repository: https://github.com/sathvikloke/perigee

Your existing coordinator worktree:
`/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/.claude/worktrees/perigee-parallel-coord-4aa087`

Last inspected state: clean `claude/backend-next-pass` at `7e776b0bd956bf6bacf00123e8c9383ff07305a4`. PR #47 has since been merged. PR #48, recording the verified release, is also merged. Last fetched `origin/main` is `0ffff6f1756537a086796aff785506fa1e22604e`. Fetch and inspect again; these are starting facts, not permission to overwrite newer work.

Codex's separate worktree, read-only to you:
`/Users/sathvikloke/Documents/ChatGPT/perigee-release-verification`

This prompt is stored there at `coordination/claude-overnight-science-backend.md`, on `codex/overnight-backend-handoff`. Read this entire file before starting. Copy it into your new branch or reference its immutable Git version, and create your own durable progress file. Do not edit Codex's working tree.

Raw data already available, read-only:
`/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data`

The manifest is `manifest.json` in that directory. There are 183 retained cutouts and 189 processed records when the six authored case variants are included. Verify this inventory before quoting it. Do not count duplicates as independent observations. The coordinator `.venv/bin/python` already has the working scientific dependencies. Reuse the environment if valid; record versions and use the repo dependency specifications. Do not commit the venv or raw FITS.

Shipped presets: `barnards_star`, `epsilon_indi_b`, `wise_0855`, `rw_aurigae`, `r_draconis`. Shipped investigations: `moving_neighbor`, `fair_comparison`. Processor A remains the integration baseline in `backend/data/process.py`. Old candidate PRs are not automatically new work; do not blindly merge #9, #14, #15, #16, #18 or #19.

Public app: https://perigee.lokesathvik.workers.dev

Cloudflare Worker `perigee`, last verified version `4031abf8-c0fb-4689-8205-3211ea0c673c`, serves the UI, curated catalog and assets. It was deployed from clean source `fbb664749a8c31a13cb02cb42ceb2fdeb2ae83bb` with release digest `548e7202640872b3ea524061ac50a28d0be5d3b3a930048bf1ffac0b5b88024d`. Live search/frame/health proxy to https://perigee-liard.vercel.app. That Python origin last ran `058a2a621199f8bc281b6efbcb4e4b87eca4127d`. Its build quota previously prevented the later Python warning-copy fix from deploying. Inspect current state once; do not assume the quota never resets or pretend a Cloudflare deploy updates Python.

The current release passed Codex's expected-build smoke 29/29 and Cloudflare route smoke 26/26. Selected independent checks passed 52 backend-related tests, 16 Cloudflare Python tests and 22 Worker tests. Your earlier full backend run reported 362 passes with raw data. These are historical observations on their stated revisions, not your new run's results. Preserve that distinction.

Read these existing artifacts first, selectively but substantively:

- `docs/INTEGRATION_CONTRACT.md`, `docs/DEPLOYMENT.md`, `docs/CLOUDFLARE.md`
- `qa/backend-next-pass/README.md`, `qa/cloudflare-release/README.md`
- `science/reviews/acceptance/README.md` and `check_acceptance.py`
- `science/reviews/barnard/`, `science/reviews/epsilon/`, `science/reviews/targets/`
- `science/reviews/transfer-exercise/` and `science/reviews/contribution/`
- `coordination/processor-compare/README.md`
- `docs/PITCH.md`, `docs/SUBMISSION_DRAFT.md`, `docs/presentation/README.md`
- The old full audit: `git show origin/codex/completion-audit:coordination/completion-audit.md`, PR #46. Its B1–B5 backend findings have now been addressed; its suggestion to require human validation is superseded by this assignment.

B1 already hardened Worker errors and malformed payloads. B2 established CI. B3 established served-content and running-Worker identity, including a real old-Worker mismatch reproduction. B4 corrected search wording in source. B5 produced the contribution comparison and draft transfer exercise. Build on this, do not relabel it as new overnight progress.

## 5. Ownership, integration and operating rules

1. Inspect status, branches and active workers first. Start a fresh backend/science branch from current `origin/main` in your own worktree, preserving any uncommitted work. Use a clear branch such as `claude/overnight-science-backend`. Never force-push shared main or reset another worker's changes.
2. **Do not edit `frontend/**`**, UI styles/components, the shipped presentation PDF, or the user-facing site design. Codex owns those. You may read frontend code to establish contracts and report defects. Place candidate content, fixtures and integration specifications under backend/science/qa/coordination paths.
3. Keep the existing `/api/v1` behavior and required fields compatible. Do not change token security, source semantics, coordinate conventions, quality meanings or display defaults to make a test pass. Additive data must have explicit validation and not silently change the existing case experience.
4. You are authorized to delegate this assignment to parallel Claude workers with distinct file ownership. Suggested lanes: science controls; astrometric audit; backend parity/faults; content/contribution handoff. You are the integration owner. Avoid multiple workers editing shared models, build config or the same report. Use bounded local concurrency; begin at two CPU-heavy processes and increase only if memory/CPU remains healthy. More agents are not themselves progress.
5. Cache and reuse local inputs. Start with the retained data and cached Gaia catalogs. Download only a small, specifically justified missing input if a mandatory test requires it; record source, query, retrieval time, size and hash. No full-archive crawl, huge ML training run, paid upgrade or new dependency stack is needed.
6. Keep secrets out of logs, fixtures, PRs and prompts. Use existing configured credentials through normal tooling. Do not change account access, authentication protections, plans or billing.
7. Do not deploy Cloudflare or merge into main while Codex is preparing UI integration; that could overwrite concurrent frontend changes. Prepare a tested release candidate and a backend-origin deployment plan. The user has authorized eventual public deployment, but final shared-release integration is owned by Codex. Explicitly distinguish “implemented and verified locally/CI” from “running publicly.”
8. Do not email teammates, submit the competition project, edit external team claims, or invent anyone's attestation. No teammate response is required to finish your scoped technical work.
9. Prefer deterministic scripts, small inspectable outputs, meaningful tests and direct review. A new test should exercise a failure, scientific invariant or external contract, not merely restate the implementation.
10. Keep a durable ledger at `coordination/overnight-status.md`: package, acceptance criterion, status, file/commit evidence, next action and residual blocker. Update at meaningful milestones. Before context compaction, write a concise resume block with branch, head, active workers, commands in progress, next package and unresolved failures. Resume rather than asking Sathvik to repeat the task.

## 6. Gap map and mandatory work packages

Every row must be closed with evidence or a specific unresolved blocker. Frontend-owned parts must be handed off with actionable inputs, not marked implemented by you.

| ID | Gap affecting award readiness | Your required outcome |
| --- | --- | --- |
| N1 | The unfamiliar exercise still contains scientifically overbroad answers. | Corrected, checked answer key and admission decision for a third investigation. |
| N2 | The value of the comparison controls is described more than demonstrated. | Reproducible counterexample experiments with exact inputs, outputs and bounded conclusions. |
| N3 | Registration evidence has selection limits; predicted motion can be confused with measurement. | Transparent coverage and sensitivity audit, with accurate small science summaries. |
| N4 | A complete reasoning record is our proposed distinction, but needs a precise transferable contract. | Validated candidate investigation and evidence examples ready for Codex to integrate. |
| N5 | Retained-data acceptance does not establish parity of the full live processing path. | Bounded route-to-processor parity checks across geometry and quality cases. |
| N6 | Judge-facing reliability depends on failure behavior, resource bounds and mixed deployments. | Measured local resilience checks, targeted fixes and an exact release-origin plan. |
| N7 | Repeat use and additional investigations need an achievable content process. | A small validated case-authoring/admission path, exercised on the candidate. |
| N8 | Contribution, benefit and evidence are spread across documents and can overclaim. | A concise claims registry, winner-gap closure table and pitch-ready evidence handoff. |
| N9 | New work can be “done” in isolation but fail when integrated. | Reviewed PR with exact-head checks, reproduced artifacts and complete final handoff. |

### N1 — Correct and finish the unfamiliar comparison

Start from `science/reviews/transfer-exercise/`. Its WISE 0855 P/Q/R frames are real retained frames:

- P: `2025W45_2A_0278_1_D2`
- Q: `2025W46_1A_0108_1_D2`
- R: `2026W20_1A_0214_1_D2`

Their hashes, wavelengths, flags and processor reproduction were checked in B5. Reuse that evidence unless new changes require rerunning it. Fix these remaining reasoning defects:

1. “Which pair differs only in time?” is false: P/Q also differ in quality, per-frame scaling, pipeline build and pointing. Ask which pair has closely matched target wavelength for investigating a temporal difference, and state the remaining controls.
2. “Nothing in these images shows the sky changing” and “neither is in the sky” are too broad. Limit the answer to the inspected features: the flags, native-pixel behavior and controls do not justify identifying those features as new or moving astronomical sources. Do not claim an exhaustive absence of all change.
3. A TRANSIENT flag is not proof of a unique physical cause. Show the exact flag meanings and measured morphology without claiming a cosmic ray or any other mechanism that was not independently established.
4. Different wavelengths do not universally prohibit astrometry, and a displacement below a native pixel is not universally unmeasurable. P/R does not establish WISE 0855 motion here because the target is not securely detected/identified in these frames and no suitable astrometric fit is performed. Wavelength, PSF, sensitivity, sampling and quality require consideration; do not teach a false universal rule.
5. The dot near the marker is positionally associated with a catalog source; that does not prove its identity. The marker is a catalog prediction, not an image detection.
6. Showing that the same input radiance receives different grey levels proves a display effect. It does not prove that every observed frame-wide brightness difference has only that cause.
7. Keep “expected below sensitivity” as a sourced expectation, not a measured non-detection or an upper limit. Do not calculate a detection limit unless the noise/PSF/selection assumptions actually support one.

Rewrite the reference answer, rubric and explanatory text consistently. Remove stale “Sathvik and Sagar must test this” completion gates. Keep the distinction between computational review and learner outcomes. The answer key is an inspectable scientific interpretation, not a claim of human validation.

Create machine-readable evidence for each answer: exact frame keys, relevant metadata/flag values, feature coordinates and units, calculation or image reference, supported conclusion and explicit limit. Prepare a candidate case in a staging folder, not an automatically shipped third case. Prefer the existing case schema wherever it fits. Document any truly necessary additive field for Codex.

Acceptance: every answer can be traced to a reproducible observation or a named external source; all seven wording defects are resolved; the three frames regenerate consistently; a second review pass actively looks for unsupported conclusions. If the candidate fails the science admission criteria, repair it using local data or produce an evidence-based rejection plus the best valid bounded alternative. Do not force an invalid “success.”

### N2 — Run controlled experiments that make the contribution visible

Produce a small experiment suite, for example under `science/reviews/overnight-controls/`, with one command, a manifest, JSON/CSV results and a few legible plots/contact sheets. State the question and expected invariant before inspecting the final result. Keep source frames immutable; derived views must be labeled as derived.

Required controls:

**A. Stretch control.** For P/Q, compare the shipped per-frame stretch with a common, explicitly specified stretch using the same units and finite-value treatment. Recompute the illustrative 1.0 and 2.0 MJy/sr grey-level probes and any useful bounded additional levels. Show that one physical input maps differently under independent stretches and identically under a shared mapping, within documented rounding. Provide actual paired images and parameters. This is a rendering test, not photometry or measured variability. Do not invent “false-positive reduction” percentages.

**B. Flagged-feature control.** Reproduce the P/Q feature associated with detector pixel (1709, 1364), accounting for cutout origin conventions. Locate it on native detector and common sky coordinates, inspect raw values and flag bits, and compare its apparent shift with surrounding usable field sources. The earlier report found approximately 5.3 arcsec of apparent displacement while stars remain approximately aligned. Recalculate; do not hard-code agreement with that number. Repeat the overlay/coordinate mapping check for the P-only flagged feature. Show how the evidence changes a defensible interpretation without asserting the unknown physical cause.

**C. Wavelength control.** For the shipped Epsilon Indi A/B/C case and P/Q/R, calculate time differences, target wavelengths, bandwidths, detector and pipeline identifiers. Make an unambiguous table showing which variables differ. Epsilon's C is approximately simultaneous with A but at a different wavelength; verify exact values. Quantify matching relative to the relevant band widths, stating which normalization is used. Do not universalize a chosen teaching threshold into a scientific law.

**D. Positive visual control.** Use the Barnard case to show an example consistent with genuine qualitative motion relative to background stars, while retaining saturated-core warnings and separate catalog prediction. Compare the available visual proxies and describe sensitivity to window/method rather than selecting the best-looking estimate. This establishes that the workflow does not reduce every result to “artifact.”

**E. Information-removal demonstration.** Assemble the same examples as images alone, then with wavelength/scale/quality/provenance information restored. Define exactly which question can and cannot be answered from each representation. This is an information-availability/traceability comparison, not a human trial, an AI benchmark, or proof that users improve. A compact evidence matrix is preferable to an arbitrary numerical score.

Keep source selection transparent. These are deliberately chosen teaching counterexamples, not a representative survey of all SPHEREx observations. Record negative results and failure cases. No p-values or confidence intervals on handpicked examples unless a legitimate sampling model warrants them. Use physical and display units separately. If a result is a deterministic mapping, report tolerance rather than fake statistical confidence.

Acceptance: another developer with the retained data can reproduce the tables and illustrations; each figure states the precise supported lesson; the results improve the demo or answer key; no outcome is described as measured learning, discovery performance or population-wide reliability.

### N3 — Tighten astrometric and registration validity

The old acceptance review reports 189/189 records passing reconstruction/provenance checks, 161 frames with usable Gaia centroid checks, median offset around 0.45 display px, and no Gaia SNR-qualified control for `fair_comparison` C. Its absolute check keeps stars within one native pixel of Gaia before computing residuals. Shared Astropy/WCSLIB usage also limits independence.

Audit this honestly rather than replacing the result with a more flattering headline:

- Count unique raw observations separately from case copies and list frames without an independent star-based check.
- Report candidate catalog stars, attempted measurements, quality/SNR/morphology exclusions, association exclusions and retained matches per frame. Make selection conditions visible.
- Report residual distributions, median and useful quantiles with sample counts, detector/quality strata and units. A median over preselected matches is not a global accuracy bound.
- Run a bounded sensitivity analysis of matching/selection parameters and report ambiguous associations. Where feasible, define measurement eligibility using quality/SNR before applying the positional association filter. Do not pretend arbitrary widened matching produces secure identifications.
- Add a deliberate registration-offset negative control to the validator using a derived test fixture. Demonstrate that the check notices the offset or loses valid matches instead of silently passing only the easy survivors. Keep this separate from real observation results.
- Retain `unknown` when independent validation is unavailable. For fair-comparison C, investigate whether an already available appropriate reference or a valid relative control can strengthen the statement. Do not waste the night downloading catalogs or relabel header-WCS reconstruction as independent astrometric validation.
- For Barnard, separate the independently propagated marker, a visual saturated-glow proxy and surrounding-star residuals. Preserve that annual parallax is not modeled and the saturated core precludes precision astrometry here.

Do not replace processor A or redesign calibration absent a demonstrated correctness bug. If the audit exposes one, isolate it, establish a regression case and fix the smallest responsible code path. Explain effects on existing assets and regenerate only affected products with a before/after manifest.

Acceptance: a concise validity report states exactly what was tested, what was excluded, what is unknown and how a deliberately wrong registration is caught. It must not claim that all 189 products have an independent Gaia validation.

### N4 — Make the investigation and evidence record ready for UI integration

Read the existing case, FrameRecord, notebook/export structures and API contract. Do not create a parallel incompatible notebook service, account system or database.

Prepare a compact handoff at `coordination/overnight-ui-handoff.md` with validated fixtures outside `frontend/`:

- The candidate third investigation: exact frame references, proposed sequence, prompt copy, hints, supported/unsupported conclusions, answer key and required source/quality display states.
- A sample evidence record with a clearly labeled **illustrative learner claim**, its supporting observations, uncertainty, selected pair, metadata provenance and source identifiers. Never present it as feedback from a real participant.
- An example initial claim and revised claim, showing what observation justifies the revision. Separate author text from computed facts. Preserve the user's own words and make exported conclusions distinguishable from the reference answer.
- A reproducibility check that frame references, source hashes, dates, wavelengths, units, quality and display-scale descriptions agree with the referenced records. If the current export format cannot express an important provenance distinction, give Codex a small compatible addition and migration/fallback rules rather than silently changing the schema.
- A precise distinction between curated and live source, asset missing and quality flagged, selected comparison and unrelated stored cards, record draft and completed claim, and catalog prediction and image measurement.
- An investigation completion contract. Completion means the user has made the intended observations and recorded a bounded claim; a PNG loading or a notebook existing is not the same thing. Do not add backend grading of free text or make an LLM judge the user.

For a second visit, describe the supported flow using existing primitives: reopen a prior record, choose another reviewed case or independently selected comparison, and save/export a separate record. A future classroom workflow can be a clearly labeled possibility; do not claim a shipped teacher dashboard.

Supply fixtures for failure states that Codex can use in UI checks: missing overlay; case data unavailable; partial search; no coverage; token expired; stale/mismatched frame selection; changed field of view for the same frame. Reuse existing fixtures where adequate. No duplicate mock server framework is necessary.

Acceptance: Codex can implement the UI from exact data and instructions without asking you to rediscover frame identities, reconstruct the answer key or infer endpoint semantics. Identify which outcomes still require UI work; do not mark them complete yourself.

### N5 — Exercise the full live backend path, including request identity

Use the existing API test harness and injectable archive/processor seams. The retained-data reconstruction test alone does not prove that live route inputs produce the intended pixels and metadata.

Required coverage, reusing existing tests where they already prove it:

- Trace a representative request from search result through signed frame token, frame processing and returned image/metadata. Compare results with a direct processing call for the **same raw bytes, coordinates, FOV, grid and processing parameters**. Explain expected differences from authored shared-stretch case copies.
- For the same observation ID, test at least two allowed FOVs and shifted coordinates. Ensure backend caching and asset identity cannot return the old geometry. The known frontend cache bug is separate; prove the backend contract and supply a fixture for the UI fix.
- Cover representative near-IR and longer-wavelength inputs, adverse flags/non-finite pixels and a geometric no-coverage input from retained data. Exercise coordinate edge handling through existing fixtures rather than making many archive requests.
- Check that timestamps, wavelength at target, quality sampling, common-grid identity, image dimensions, data provenance and overlay alignment remain consistent across the route boundary.
- Use one small bounded live archive smoke for external integration if available. Prefer cached/offline fixtures for the matrix. An external service outage is a reported live-check limitation, not a reason to fail deterministic checks or spoof a passing live run.
- Confirm invalid/expired/tampered tokens, request IDs and upstream errors retain their documented status and payload behavior. Fix newly discovered gaps; do not weaken validation to ease local runs.

Record raw-input hashes, normalized request parameters, relevant runtime versions, observed output hashes and allowed tolerances. Do not expect byte equality across intentionally different stretches or processing versions without establishing the preconditions.

Acceptance: a route-level parity report with actual runs and regression coverage for any defect found, plus the exact request identity tuple Codex should use for client caching. The public origin may still be on older Python code; report that independently from candidate correctness.

### N6 — Finish resilience, performance and release-origin readiness

Inspect existing tests before adding more. Reuse completed B1–B4 coverage and focus on remaining end-to-end uncertainty.

Use local mocked/cached upstreams for bounded concurrency and fault experiments. Never load-test NASA or the public production service. Test the smallest realistic matrix that establishes behavior: normal, timeout, malformed/oversized response, partial collection success, invalid/truncated FITS, repeated same request, and a few simultaneous distinct requests. Confirm configured timeout, byte/memory and concurrency limits are actually respected where applicable. Track peak memory and wall time if practical. Separate cold and warm observations; label small-sample percentiles as descriptive, not capacity guarantees.

Important contracts:

- Partial search remains partial; an unavailable archive does not become a false empty successful result.
- Fixed search radius is 3.6 arcsec (`POS=CIRCLE RA DEC .001`); image FOV changes the cutout, not the archive discovery cone. The result cap is 48 with temporal sampling; it is not pagination or an exhaustive time search. Verify source rather than assuming these constraints changed.
- Untrusted upstream responses cannot become arbitrary proxy destinations or expose credentials. Retain the existing fixed-origin proxy boundary and response-size/time bounds.
- Curated routes and assets remain usable when the live origin fails. Demonstrate this locally with fault injection, not by disrupting the public origin.
- A missing overlay is distinguishable from no adverse flags. Do not synthesize a “clear” quality assessment when an asset fails.
- Builds must retain a verifiable Worker identity and served-content identity. Do not replace expected-build checks with a weak homepage-200 test.

Check the Vercel quota/deployment state once through available tooling. Determine whether B4's warning correction is live. If a deployment is now possible, prepare the exact candidate revision and deployment steps for Codex; do not silently publish a competing frontend build. If still blocked, record the smallest remaining source-vs-production difference and its user impact. Do not migrate the Python stack to an untested platform just to eliminate a minor wording gap.

Produce `coordination/overnight-release-handoff.md`: candidate commit, backend origin status, old/new behavior, pending deployment steps, required secrets by **name only**, smoke commands, compatibility with current UI, rollback reference and whether public release still differs. Keep existing correct architecture and release documentation intact.

Acceptance: any discovered P0/P1 backend correctness defect is fixed and verified; bounded resilience evidence is recorded; unsupported production claims are absent; final integration can deploy without guessing which components are live.

### N7 — Demonstrate a feasible way to add another investigation

This closes the repeat-use/content-depth gap without bloating the product. Reuse the existing schema and processor. Create a small authoring template and validator or extend an existing validator. It should check:

- Every frame reference exists and source/provenance fields resolve.
- Dates/wavelengths/units and any quoted numbers agree with computed records.
- The claimed learning question fits the available data and states confounds.
- Required shared-grid/shared-stretch assumptions are actually true, or the case explicitly treats their absence as part of the task.
- Quality and non-finite-pixel interpretation are supported; target identity and catalog predictions are labeled correctly.
- The answer key contains supported and unsupported conclusions and evidence references.
- No new raw data, secrets or opaque model dependency is required for the demo.

Exercise the process on N1's candidate. Document accepted, repaired and rejected conditions. R Draconis and RW Aurigae were previously poor candidates because of saturation/flagging and lack of a clean useful pair; preserve those negative findings unless new evidence changes them. One additional scientifically sound investigation is more valuable than numerous weak cases.

Do not promise an automatic source-discovery pipeline, recurring new data ingestion or scheduled new lessons unless implemented. Distinguish a repeatable authoring process from a shipped self-service authoring UI.

Acceptance: the candidate passes an inspectable admission checklist and automated structural checks, or has an explicit evidence-backed rejection with a valid alternative. Codex receives exact assets and integration requirements. The case remains staged until the frontend integration is reviewed.

### N8 — Consolidate the contribution, story and claims

Create `coordination/overnight-award-evidence.md`, short enough to read in a few minutes, backed by the detailed artifacts. This is the bridge between backend work and the pitch.

Include:

1. One sentence naming the audience, their task and the resulting benefit as potential where appropriate.
2. One sentence stating the narrow contribution, without “first,” “unique,” or universal superiority claims.
3. The five-winner gap table above, updated with concrete closure evidence and remaining UI work. Do not grade us with invented judge scores or claim parity because our test count is larger.
4. A claims registry: claim, status (`observed`, `computed`, `interpretation`, `proposed`), supporting file/command/source, important limitation, and safe short pitch wording.
5. Three strongest demonstrations with exact frame IDs, visible event, action, supported conclusion and required caveat. Keep caveats comprehensible rather than burying the story under internal implementation details.
6. A 30-second narrative draft and a seven-slide evidence outline compatible with existing submission guidance. These are inputs for Codex and Sathvik, not edits to the final deck. Tie a concrete human motivation to the real data and the completed evidence card.
7. What the prototype demonstrably does today, what awaits UI integration, and what is future potential. No fabricated users, testimonials, adoption, measured learning gains or award probabilities.
8. A clear statement of what NASA/SPHEREx data contributes that a generic toy animation cannot: real observation changes and confounds, mission quality metadata, and traceable frames a reviewer can inspect.

Keep the current contribution comparison accurate, incorporating the additional source inspection scope if needed. Do not spend the night searching for a perfect claim of novelty. A defensible combination serving a clear task can be the contribution even when component features already exist.

Acceptance: every quantitative pitch claim resolves to an artifact; every promised function is either implemented or explicitly future work; no requirement for real users has slipped back in; the story has an actual outcome rather than a list of features.

### N9 — Integrate, review, verify and deliver

Before declaring completion:

1. Integrate all accepted worker changes in your branch. Resolve overlap deliberately. Review actual diffs and regenerated results, not just worker messages.
2. Verify changed science scripts from a clean output directory or explicit output path, with documented environment and input manifest. Ensure generated differences are explained and no stale result file is cited as a new run.
3. Run the relevant backend and Cloudflare tests, then required repository CI on the integrated head. Run frontend typecheck/tests/build only as compatibility verification; do not edit frontend to mask failures. Distinguish a pre-existing or concurrent UI failure from a backend regression with evidence.
4. Reconcile any changed content with catalog export and integrity checks. Confirm no raw FITS, caches, secrets, giant logs, venvs or unintended generated bundles entered Git.
5. Do one adversarial scientific review pass: challenge source identification, motion-vs-prediction, wavelength assumptions, quality interpretation, sampling bias and overbroad conclusions. Repair findings and rerun the affected checks.
6. Do one integration review pass: wrong request identity, stale assets, missing overlays, partial failures, source-vs-deployed mismatch and backward compatibility. Fix backend issues; provide precise frontend residuals.
7. Open or update one coherent PR, or a small justified stack with explicit order, against current main. Use a concrete description of changed behavior, scientific results and validation. Record exact head and CI links. Do not call an opened PR “deployed.”
8. Update the durable ledger with all N1–N9 outcomes. Mandatory unfinished work remains visible. “Out of scope” needs a reason grounded in ownership or scientific invalidity, not convenience.
9. Deliver a final handoff that starts with what changed, the three strongest new results, the PR/head, actual test outcomes and exact remaining actions for Codex. Link the UI handoff, release handoff and award evidence document.

The current known frontend findings belong in the handoff but are **not yours to implement**:

- F1: cache key omits coordinates/FOV/release; same frame ID can show old geometry.
- F2: URL/history changes can leave old results/notes; result limit is not fully serialized.
- F3: overlay image failure can leave a misleading enabled legend.
- F4: failed authored-case load silently falls back to different stretch semantics.
- F5: notebook current-record versus collection state and timer-driven focus behavior.
- F6: removing a required comparison member immediately reattaches it.
- F7: placeholder contrast below the required target.
- F8: unrelated searches retain case identity in notebook/export labels.
- Additional copy/accessibility checks: Barnard date labels and two-frame/three-frame wording; flag glossary; accurate draft status; phone and keyboard/screen-reader behavior.

Codex will address these and the visual redesign. Flag any newly discovered frontend issue with a minimal reproduction and correct expected behavior, without making parallel UI edits.

## 7. Practical sequencing for the night

Start with baseline inspection and the durable checklist, then begin N1/N2 science and N5/N6 backend checks in parallel where available. N3 can run beside them with bounded compute. N4/N7 use the corrected scientific results; N8 should be written from actual outputs, not optimistic placeholders. N9 is mandatory integration work, not optional polish.

Prioritize scientific correctness and backend defects before adding content depth. Once those are sound, finish the candidate, reproducibility assets and pitch evidence. If a check already has strong current evidence, cite and verify its applicability rather than rerunning an expensive sweep without reason. Conversely, do not use yesterday's green run to cover changed code.

An overnight time budget is a reason to make efficient choices, not to skip mandatory verification or launch open-ended searches. Use bounded experiments with a clear question and stopping condition. No model training, giant archive download, replacement architecture, speculative automatic Planet X detector or elaborate authentication system is needed.

Useful existing commands and entry points; inspect flags before running:

```sh
.venv/bin/python science/reviews/transfer-exercise/check_transfer.py --data-root "/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data"
.venv/bin/python science/reviews/acceptance/check_acceptance.py --help
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m pytest cloudflare/tests -q
node --test cloudflare/test/*.test.mjs
npm run build --prefix frontend
.venv/bin/python cloudflare/build.py
.venv/bin/python -m backend.platform.smoke --help
```

The actual smoke after final shared deployment must compare against its expected build:

```sh
python cloudflare/tests/smoke_local.py --base https://perigee.lokesathvik.workers.dev --cloudflare-edge
python -m backend.platform.smoke --base https://perigee.lokesathvik.workers.dev --expect-build cloudflare/build/build-info.json
```

Do not run the expected-build public check against an un-deployed local candidate and then misdiagnose the intentional mismatch. Verify local candidate identity locally; final deployment smoke belongs to Codex's coordinated release.

## 8. Final completion checklist

- [ ] New work starts from the current integrated baseline, with other work preserved.
- [ ] N1 answer-key defects repaired and the candidate scientifically reviewed.
- [ ] N2 controls executed and reproducible, with actual figures/tables and bounded interpretations.
- [ ] N3 selection limits, unknown cases and a negative registration control documented.
- [ ] N4 exact case/evidence fixtures and UI integration contract delivered.
- [ ] N5 route-level parity and request-geometry identity established.
- [ ] N6 relevant backend faults/resource limits checked, defects fixed, origin status accurately recorded.
- [ ] N7 case admission process exercised without inventing unsupported cases.
- [ ] N8 contribution/story/claims artifact grounded in results, with no human-user requirement.
- [ ] N9 integrated review, relevant tests and exact-head CI complete; PR and handoff ready.
- [ ] No frontend changes, unintended deployment, invented measurements or hidden failures.
- [ ] Every unresolved dependency names its concrete cause and smallest next action.

**Start now by reading the entire assignment, recording the actual baseline and creating the durable ledger. Then execute. Do not return only a plan or ask Sathvik which package to do next. Keep going through the remaining feasible work until this checklist is genuinely satisfied.**
