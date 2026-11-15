# Landing verification — 15 November 2026

Implementation: isolated `codex/landing-satellite-motion`, base `bb65efa`. Local Vite app at http://127.0.0.1:5181/, using the live Perigee API read-only through its development proxy. This is not proof of a production deployment.

## Automated checks

Frontend test suite, TypeScript and production build pass; full logs are `tests.txt` and `build.txt`. Added tests cover authored preview pairs against real case JSON and the motion controller’s entrance/drift handoff, manual/visibility pause, replay/skip, and cleanup.

## Browser checks

- Desktop 1440×1000, laptop 1280×720, tablet 820×1180, phone 390×844 and narrow 320×740 inspected. Screenshots: `realistic-*.jpg`. No horizontal overflow at 390 or 320 pixels.
- At narrow sizes the primary action appears before the illustration; at desktop it remains beside the illustration. Nothing gates the start action.
- Pause changes to pressed Resume and disables replay. Resume restores controls. Replay changes to Skip entrance; Skip immediately restores Replay.
- Reduced-motion test harness loaded the real application with the media preference set before module initialization. Static artwork remains, Replay is absent, and disabled Motion reduced is visible. Evidence: `reduced-motion.jpg`. The temporary harness is not part of the app.
- Start investigating opens the live Barnard investigation with A+C selected. Evidence: `investigation-entry.jpg`. Returning Home restores landing.
- Landing card labels explicitly identify target and question. Epsilon previews show the authored A+B pair; ordering is independently covered by tests.
- Offscreen, hidden-document and disposal behavior verified with controller tests and source review; no claim of measured battery or frame-rate performance.

## Independent review

A separate review agent inspected the final artwork-in-page screenshot and found a major improvement in material realism: seams, foil, brackets, insulation and photovoltaic detail read as hardware. It also noted that the fixed-view cutout is still decorative; a future interactive data preview could connect the mission to the activity more directly. A bounded code review found no blocking lifecycle or accessibility defect and added controller tests.

## Limits

This is an AI illustration with a visible caption, not verified engineering geometry or a rotatable 3D model. Motion is a fixed-view approach and drift using browser transforms. No Three.js runtime remains. Reduced motion and controls were checked in the in-app Chromium browser; Safari/iOS device testing and integrated coordinator-branch validation remain with the coordinator. Existing investigation changes are outside this commit.
