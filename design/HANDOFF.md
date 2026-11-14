# Perigee UI handoff

Owner: Codex. Implementation: Claude worker 01 / Akshobya, supported by workers 12, 13, 17, 18. Follow Bloody Coconut and its Impeccable orchestration for all frontend work. This reference implements one complete investigation; the integration contract still governs the live app.

## Selected direction

For learners comparing real astronomical observations, use a rounded classroom experiment bench: two large sky plates beside a persistent evidence notebook. The image, date, wavelength and quality travel together. This communicates curiosity and scientific care while preserving a fixed sky grid and explicit uncertainty.

Selected comp: `.impeccable/mocks/perigee-a.png`. Selection delegated by the user to Codex. B's left rail reduces the comparison area; C separates writing from the image and contains incorrect preset labels. These are exploration artifacts, not scientific evidence.

THESIS: Help a learner decide whether a comparison is fair before making a claim.
OWN-WORLD: Classroom experiment bench, cool paper, deep navy text, cobalt actions, cornflower selection, lavender notebook and small lime check signals.
STORY: Compare the dates and wavelengths → examine quality → record what the evidence supports.
FIRST VIEWPORT: Compact wordmark header; investigation question; a 3-step strip; two equally weighted observation plates occupying roughly two thirds of the work area; notebook alongside. Controls sit immediately above the plates, metadata and sources immediately below.
FORM: concept seed `40e4fb15`, grounded candidate 6. Soft 24px main corners, 16px image wells, 10px controls; substantial sans-serif heading; compact, readable scientific labels. No decorative space scene.

## Recognition-critical relationships

- Keep the two plates equal in scale and registered to the same sky grid. Do not turn the opening into a marketing hero.
- Keep the notebook visually distinct and visible with the image on desktop. Preserve claim, observations and uncertainty through every view change.
- Keep date and wavelength separately labeled for every frame. Do not infer wavelength from detector number.
- The primary action saves an evidence card, not a discovery claim. Export contains selected frame IDs, detector, release, source URLs, processing and user notes.
- At 900px and below, put the notebook after the comparison. At 560px and below, use one plate with explicit A/B (or A/C) controls; never squeeze two illegible postage stamps side by side.
- Native controls, visible keyboard focus and text status labels remain part of the design. All functional touch targets at least 44px.

## Concrete reference

`design/prototype/index.html`, `styles.css` and `app.js` define the implemented target. Serve the folder over HTTP. It is a local interaction reference, not the integrated live archive app. Port the layout and tokens into React; do not add the static prototype as a second application route.

Its three PNGs are freshly rendered from retained original FITS files using the new science registration check. Provenance is in `design/prototype/assets/provenance.json`. No generated starfield is used. Transparent pixels mean outside the retained cutout. A/B use the same stretch and grid. Markers are catalog predictions. Final API output must be checked against these reference semantics, not substituted solely because a PNG looks similar.

## Corrections to the generated comp

Use 3 workflow steps, not 4. Correct A/B wavelengths are 2.3232 and 2.3220 µm; C is 4.9399 µm at A's time. Replace the comp's generic “Good” with a precise flag-screen status. No account icon or official NASA product claim. “No flags near the predicted position” does not establish detection, brightness change or measured motion. Generated mock imagery and its incorrect metadata must never reach the app.

## Interaction and failure contract

Switching A/B to A/C changes the image, date, wavelength, source and explanation together. Blink alternates a single fixed image plane at a deliberate cadence and exposes Pause; reduced-motion users start paused. Leaving blink stops its timer. A/B remain available manually. Quality details use a native disclosure. Notes autosave locally with visible status and survive refresh. Export and print show the same selected evidence.

The integrated live coordinate form must implement the existing input bounds, loading, partial, empty, failed and retry states. Preserve the last valid image and notes when a request fails; state that the old image is still displayed. Do not label archive/network failure “no observations.” Missing quality is unknown, never clear. Display processing/coverage failures adjacent to the affected plate. Keep errors factual and give one useful next action.

The static reference intentionally has no pretend live search or working target list. The functional app must retain all five presets, both cases and public coordinates from the contract; extend this design language to those controls.

## Vault and reference translation

The substantive Obsidian vault is `Documents/Codex/2026-11-13/rand/outputs/3d-design-research/vault`. Selected UI lessons informed adjacent controls and consequences, distinct spatial hierarchy, persistent interaction state and mobile recomposition. The Downloads vault has only a default welcome note. Neither vault was edited.

Observed IRSA SPHEREx visualization documentation supports keeping image metadata close while reducing primary toolbar complexity. The Backyard Worlds landing page demonstrates a concrete human question and explicit availability status; its classifier was out of data during inspection, so no classifier behavior is claimed as observed.

Reference URLs: https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/visualization.html and https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9 .
