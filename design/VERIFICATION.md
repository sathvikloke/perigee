# UI reference verification — 14 November 2026

## Implemented and observed

- Browser-rendered desktop and 390px phone layouts; 320px width measured without horizontal document overflow.
- A/B → A/C updates the displayed image, date, wavelength, release, selected evidence and explanatory text together. Corrected A's label to “Shorter wavelength” in the same-time comparison.
- Phone A/B controls show the corresponding complete plate; blink exposes an explicit Pause control. No autoplay on load.
- Claim, observations and uncertainty survive a browser reload. Test notes were cleared through the UI afterward.
- JSON download succeeded; the downloaded file was read independently. It contains the three test notes, selected A/B frame IDs, detector/release, original source URLs, retained-file hashes and processing. Test download is local, not committed as real evidence.
- The prototype uses three newly rendered real FITS previews. Generated comp starfields are not used. Source-file SHA-256 values match the independent science records.
- JavaScript syntax check passed with `node --check design/prototype/app.js`.

## Review and repairs

An independent, context-free reviewer first received desktop/mobile renders, then the selected comp and direction contract. It identified small scientific captions, the A/C “Earlier” label, and incomplete print provenance. All three were repaired: screen type now has a 12px minimum, phone textareas use 16px, plate headings wrap, comparison labels follow the selected pair, and a dedicated print section carries selected observation IDs, exact source URLs, release/detector, wavelength, timestamps, source hashes and processing. Print notes use expanded text instead of a clipped textarea. Whitespace-only export notes also receive validation.

Phone orientation content was condensed after the narrow-view check: the three step names remain while their repeated helper text is omitted, bringing the actual comparison earlier. Full guidance remains adjacent to the comparison and notebook.

## Scanner scope

Installed Impeccable 4.0.2 preflight found all required parsers. The independent bad/good fixture check passed with real `parse-document` coverage (Node v26.13.0). The one initial scan of `design/prototype/index.html` exited 2 and is retained in `detector-findings.json`. Its primary useful findings were undersized labels and body text; these drove the size repair. Its all-caps finding refers to the short investigation breadcrumb, not body prose. Initial findings are not presented as a clean final scan or an accessibility certificate. Actual post-repair mobile computed styles confirmed 12px quality text and 16px inputs.

## Limits

This verifies the UI reference, not Claude's integrated frontend or Vercel deployment. Live requests, archive failures, all five presets and the second case need their own end-to-end checks in that app. Full keyboard/screen-reader testing, performance measurements, browser-storage failure injection and the operating-system PDF output were not completed here. Print source/notes support is implemented and source-reviewed; a saved PDF was not visually verified. No claim of WCAG conformance or user research results is made.
