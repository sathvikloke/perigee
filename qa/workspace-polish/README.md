# Investigation workspace refinement

This pass keeps Perigee's black/citron identity and Host Grotesk typeface. It brings the observation images above the detailed workflow, replaces the full-width switcher with a compact header control, and gives notebook fields and metadata more readable sizing. All authored scientific questions remain available in context disclosures.

## Observed layout

On the same WISE 0855 investigation, the first image starts at 423px instead of 654px in a 1280×720 viewport, and at 475px instead of 757px in a 390×844 viewport. Body text increased from 14px to 16px; metadata increased from 12px to 13px. See `measurements.json` for the measured positions.

The notebook stacks below the comparison at 1100px; coordinate fields use four, two, then one column. Three guided investigation cards share a desktop row with aligned footers. At tablet widths each card has a preview beside its copy, and phone cards stack vertically.

## Verification

- Production frontend build and TypeScript check passed; 128 existing frontend tests passed.
- Cloudflare export parity: 16 tests passed. Worker routing: 22 tests passed.
- Inspected local UI at 320, 390, 820, 1024, 1280 and 1600px widths. No horizontal page overflow or broken loaded images was observed in the sampled views.
- Manually checked switcher navigation, keyboard open/Escape close, comparison selection, mobile observation controls, Blink/Pause, invalid coordinate feedback, authored question disclosures and preservation of saved investigation progress.
- Console warnings/errors were empty during the sampled checks.
- Independent artifact review found no release-blocking layout defect after phone caption separation and tablet stacking were refined.

This was a focused visual and interaction check, not a complete assistive-technology audit or a runtime PDF-print verification. Live release verification is performed after deployment against the generated build identity.

## Screenshots

- `desktop.jpg`: shortened investigation header and comparison/notebook hierarchy.
- `mobile.jpg`: compact phone introduction and observation controls.
- `tablet.jpg`: full-width comparison after the notebook breakpoint adjustment.
- `landing-cards.jpg`: final desktop investigation cards.
- `narrow.jpg`: long investigation title at 320px.
- `mobile-detail.jpg`: comparison caption separation and scientific warning.

Desktop/mobile overview captures precede the final caption spacing-only adjustment; the detailed phone and tablet captures show the final adjustment. These are development captures of real API content, not evidence of a production deployment.
