# Audit follow-up verification

Working record for the November 15 usability and release pass. A source change is not treated as a verified production fix.

## Acceptance scope

- Archive search: bounded transient retries, two concurrent frame requests, completed-frame cache, first usable frame selected, default 12 results, meaningful loading and completion states, readable errors, cancellation without stale updates.
- Accessible search: object-name resolution, decimal or sexagesimal coordinates, prominent example, optional advanced settings.
- Guided investigation: immediate instruction, purpose-based comparison labels, steady playback geometry, deliberate flags, mobile comparison, one clear sequence from observation through checks to recording.
- Notebook: required-pair recovery, observation before conclusion, visibly disabled unavailable actions, reference scroll/focus, no empty JSON export, saved notes retained.
- Scientific meaning: selected-pair stretch claims checked against both records; hatching includes unusable covered pixels; quality, wavelength and source limitations remain available.
- Navigation and presentation: investigations anchor, accessible case names, preview/default pair parity, calmer landing copy, social metadata, accurate disclosure link label.
- Responsive and print: desktop, 390 px and 320 px checks; readable source information; Safari PDF with backgrounds disabled preserves meaningful colors and hatching.
- Release: reviewed landing-worker integration, frontend/backend/edge checks, clean source identity, public deployment, live name/search/frame path, no misleading completion claim.

## Observed checks before final integration

- Search button visibly changes to “Searching…”; processing then shows “Loading images…” and an actual completed-frame count. A two-frame example finishes with the busy state removed and “Frame processing finished: 2 frames ready.” Screenshots: `search-running.jpg`, `search-finished.jpg`.
- Investigations navigation from an investigation reaches `/#investigations` and focuses the investigations heading.
- Safari private-window PDF, “Print backgrounds” unchecked: image hatching and both flag swatches remain visible. All three pages inspected. Evidence: `perigee-print-no-backgrounds.pdf` and rendered PNGs. The export used an empty test notebook to isolate visual preservation; this does not verify a completed evidence card.
- Print comparison-heading alignment was refined after that export and needs checking in the final export.

## Integrated local results

- Frontend: 186 tests passed, TypeScript and production build passed. Backend: 428 passed, 33 raw-data-dependent tests skipped. Cloudflare export parity/identity: 16 passed; Worker: 24 passed.
- Live local name search: Barnard's Star resolves to the verified 2026 finder center and all 12 returned frames became ready. The resolver's live Barnard/Epsilon/Vega checks are recorded in `search-resolver-live.json`.
- Controlled recovery: an isolated local gateway injected a retryable 502 for image 1 and delayed its retry. Image 2 became the selected usable image while image 1 recovered. A clean repeat completed both images with one search, three frame requests and one injected failure (`recovery-verification.json`). An earlier run also recovered from a genuine second 502 from the local API. These bounded checks do not establish an upstream reliability percentage.
- The recovery check exposed hash-only navigation restarting a search. App history handling now ignores hash-only changes. Clicking “View first ready image” and attaching an observation did not start another search in the clean repeat.
- Fresh 390 px Epsilon investigation completed through all three checks, required-pair recovery, notes, reference focus/scroll and JSON download. Download contained two observations and the typed notes. Existing saved WISE notes and reviewed steps were retained.
- First guidance is above the image (428 px in the initial 390 px capture), instead of below the comparison. Optional full-frame exploration is after the notebook and collapsed. The final pass further condensed comparison detail.
- At 360 px, both WISE playback layers have identical image top and height after reserving consistent metadata rows. At 320 px there is no horizontal overflow and source details read as labeled records (`sources-320.jpg`). Touch gesture direction/cancellation is unit-tested; physical-device touch behavior was not exercised.
- Final Safari export (`perigee-final-print.pdf`) keeps image tops aligned. The earlier backgrounds-off export verifies hatching and flag colors. These print checks use an empty local test notebook; populated-note serialization was verified in JSON.
- Landing worker commit `77c8add` integrated as `9bdf567`; its independent responsive, motion/reduced-motion and preview-pair evidence remains in `qa/landing-motion/VERIFICATION.md`.

Production release identity and public checks will be added after deployment.
