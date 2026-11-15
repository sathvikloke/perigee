# Cartoon opening and hero motion

The user rejected the realistic-looking spacecraft and motion that felt absent. Their selected reference is a cartoon satellite with dark ink contours, blue panels and simple cel shading. They asked for a thick white outside contour on black and, separately, a cartoon rocket or asteroid flying left before the hero appears. A later clarification requires the rocket exhaust to move independently.

The implementation keeps the app's black, white and citron identity and the scientific workbench. The satellite and rocket are authored raster cartoons supplied by the coordinator, not geometry assembled in code, cropped photographs or observational data. The decorative telescope is labeled as a space-telescope AI illustration rather than an engineering-accurate SPHEREx model.

## Motion contract

| Moment | Visible behavior | Controls and fallback |
|---|---|---|
| First homepage load | Black scene, left-facing cartoon rocket enters from the right and flies left in 1.45 seconds. A matching black cover moves left from 0.65 to 2.05 seconds, revealing the real hero from right to left. | Skip intro and Escape finish immediately. Deep links and ordinary returns to Home skip the opening. Replay intro is explicit. |
| Exhaust | Separate flame art varies its length and thickness on a 190 ms cycle, with three small trailing embers. | Removed with the opening; reduced motion bypasses it entirely. |
| Hero arrival | Title mask, supporting copy and primary action settle while the cover leaves. The cartoon telescope translates and rotates into its final position. | The final readable layout is the default when the opening is skipped or unavailable. |
| Hero at rest | Telescope floats 22 px and rolls three degrees over 6.8 seconds; starfield continues its leftward arc. The action arrow responds to hover/focus. | Pause animation stops telescope and stars. No pause preference is persisted. Hidden/offscreen motion pauses. |
| Investigations | Cards rise in a short sequence while their actual preview pairs reveal through horizontal shutters. Hover/focus lifts the actionable card and moves its arrow. | Observational pixels are not transformed relative to each other. Content stays visible if IntersectionObserver or animation is unavailable. |
| Evidence and exploration | An evidence sheet settles into place, its uncertainty appears next, and the archive invitation draws its top rule. | Each section enters once. Viewport departure, keyboard/pointer interaction, a hidden tab, printing and reduced motion settle active section effects to the readable static layout. |

No percentage or loading claim accompanies the decorative opening. The two intro images must load before flight starts; if unavailable after 1.2 seconds, the page opens. A 2.25-second fail-safe after the animation starts prevents an overlay remaining indefinitely. A hidden document settles to the page, rather than leaving a returning visitor stuck behind a paused opening. Native modal-dialog semantics keep keyboard focus out of the covered page; closing restores access and focuses the hero heading without scrolling.

The motion controller uses the browser's existing Web Animations API. Flame and hero text use CSS animation. No animation framework, WebGL renderer or procedural spacecraft dependency was added.

Clean transparent illustrations receive a white contour through an SVG alpha filter: threshold alpha at 0.5, dilate the resulting silhouette, flood white and merge the unchanged source artwork over it. This avoids amplifying almost-transparent edge speckles. The satellite contour is 14 display pixels; the smaller rocket and exhaust use 7 and 4 pixels respectively. SVG is only the border filter, not a replacement illustration.

The served artwork uses three 1254 × 1254 lossless WebP files (`perigee-{satellite,rocket,flame}-cartoon.webp`). Sharp converted the PNGs with `lossless: true, effort: 6`; decoded comparisons found zero alpha differences and zero visible color differences. Combined artwork transfer size fell from 1,733,927 to 1,034,180 bytes (40.4% smaller). Detailed source/output checksums are in [ASSET.md](ASSET.md).

## References and research bounds

The separate motion researcher inspected the text/catalog of [Awwwards' Igloo case study](https://www.awwwards.com/igloo-inc-case-study.html), [Motion's curtain documentation](https://motion.dev/docs/curtains) and the [MotionSites Aetheris hero example](https://motionsites.ai/?prompt=aetheris-voyage-hero). The useful translation is one continuous intro-to-page reveal. The researcher did not observe those animations playing, and no paid curtain library was used.

Implementation consulted [MDN's Web Animations API guide](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API/Using_the_Web_Animations_API), the existing controller source and the installed Bloody Coconut motion-direction/motion-system guidance plus Impeccable's animate and craft-floor playbooks. The explicit cartoon and pre-hero brief governs this focused replacement; no unrelated visual-world exploration was performed.

## Verification

All 215 frontend tests passed across 22 files, including the intro/observatory lifecycle tests and 12 landing-section lifecycle tests. Checks cover first-load eligibility (including legacy `ra`/`dec` deep links), timed reveal, skip, missing finish events, visibility changes, cancellation, stale callbacks, observatory pause/replay, section departure, keyboard/pointer interaction, reduced motion, printing and cleanup. TypeScript and Vite production build passed with the lossless WebP assets and integrated motion. These checks establish lifecycle policy, not visual quality or frame-rate performance.

The coordinator reported browser verification at 1280 × 800: the cartoon rocket crosses left, its separate flame stays attached and changes shape/length, and the satellite's white contour is visible. Desktop and 390 px mobile had no horizontal overflow; Escape and pause/resume worked. This child did not perform that browser inspection. Root also checked Replay, Escape, pause/resume, the guided-step progress rail, and the notebook reference reveal on a 390 px viewport. No console warnings or errors appeared in that journey. Reduced-motion behavior was covered by controller tests; an operating-system preference walkthrough was not performed. Production verification is recorded separately after deployment.
