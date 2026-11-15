# Third investigation release verification

## Scope

The learner opens WISE 0855 from the home page, compares the admitted A/B/C images, reviews six steps, writes a claim with observations and uncertainty, saves it locally, compares it with a separately labelled reference, and can export/reopen the evidence card. Existing free-exploration notes for this target retain their own context and reopen route.

The science content and ten case assets were promoted from `science/staging/wise_0855_quality_trap`. Learner-facing science copy is unchanged. A and B use their admitted shared stretch; C explicitly warns that brightness is not directly comparable. No reference guide line is added. The marker remains a catalog prediction rather than a detection.

## Validation before release

- Case admission with retained raw data: all 12 gates passed.
- Backend and registration audit: 456 passed, with raw-data tests enabled. Existing Astropy/NumPy warnings are recorded in the run output.
- Frontend: 128 tests passed; TypeScript and production build passed.
- Cloudflare export parity: 16 passed, including all 12 catalog documents and 968 assets.
- Worker: 22 passed, including the newly admitted case routes.
- Saved-card regression: old WISE free-exploration notes and the new guided card have separate keys; routes round-trip to the original notes.
- Completion regression: a draft or reference click alone is insufficient; required images, all reviewed steps, claim, observations, uncertainty and successful local save are required. Completion is not automatic grading.
- Once a reference is opened, normal autosaving does not hide it during revision. Learner text is never replaced by reference text.

## Browser evidence

Local app on port 5186 with the current FastAPI app on port 8052, using real bundled NASA data:

- Home lists three guided investigations and two open explorations.
- A/B blink, A/C selection, flag overlays and the C contrast warning worked.
- Saved six reviewed steps and three original text fields; reference was initially gated and then appeared separately.
- JSON download completed, then My evidence reopened the card with checked steps, text and revealed reference intact.
- At 390 × 844, document width equals viewport width; no broken images. Browser error/warning log was empty.
- [Desktop arrival](desktop.jpg), [mobile arrival](mobile.jpg), [mobile comparison](mobile-comparison.jpg).

An independent finish reviewer inspected these renders first and then the integration source. They identified the reference/autosave flicker, which was fixed and regression-tested, and found no remaining release blocker. They did not independently control the browser.

## Design decision

Retain the current black, white and citron visual system. The highest-value follow-up is to make the observation images visible sooner by tightening the opening context. The evidence workspace and completion flow deserve priority over another visual redesign. This review does not establish award competitiveness or full accessibility conformance.

Production identity and smoke results are recorded after deployment in `docs/DEPLOYMENT.md`.
