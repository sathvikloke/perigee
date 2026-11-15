---
name: "Perigee"
description: "An orbital invitation to inspect the infrared sky and preserve evidence."
colors:
  paper: "#08090a"
  surface: "#121416"
  ink: "#f5f6f7"
  muted: "#a6acb2"
  line: "#2a2d30"
  line-strong: "#50565c"
  blue: "#d5f96e"
  blue-deep: "#c3e75e"
  blue-hover-line: "#a5bb6d"
  blue-hover-bg: "#20271a"
  cornflower: "#222a18"
  cornflower-line: "#62723d"
  lavender: "#14191b"
  lavender-line: "#313c40"
  lavender-ink: "#c6d8de"
  lime: "#24301e"
  green: "#c7e5aa"
  amber-bg: "#33291b"
  amber-ink: "#f3cc8d"
  error-bg: "#341e1b"
  error-ink: "#ffb7a8"
  field-bg: "#0c0f10"
  placeholder: "#9aa1aa"
  sky-hatch-a: "#1d2639"
  sky-hatch-b: "#3a4560"
  sky-label: "#e1e5ef"
  sky-label-bg: "#111827b3"
  marker: "#d3ed95"
  guide: "#8fd3ff"
  action-ink: "#11150b"
typography:
  display:
    fontFamily: "\"Host Grotesk\", ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "clamp(60px, 6.6vw, 96px)"
    fontWeight: 500
    lineHeight: 1.04
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "\"Host Grotesk\", ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "clamp(32px, 3.4vw, 46px)"
    fontWeight: 500
    lineHeight: 1.12
    letterSpacing: "-0.03em"
  investigation:
    fontFamily: "\"Host Grotesk\", ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "clamp(30px, 2.8vw, 40px)"
    fontWeight: 500
    lineHeight: 1.16
    letterSpacing: "-0.03em"
  section:
    fontFamily: "\"Host Grotesk\", ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "22px"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  body:
    fontFamily: "\"Host Grotesk\", ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "\"Host Grotesk\", ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "13px"
    lineHeight: 1.5
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: "max(0.92em, 12px)"
rounded:
  xs: "6px"
  sm: "10px"
  md: "16px"
  lg: "24px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.pill}"
    padding: "9px 22px"
  button-primary-hover:
    backgroundColor: "{colors.blue-deep}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "9px 13px"
  button-secondary-hover:
    backgroundColor: "{colors.blue-hover-bg}"
  button-link:
    backgroundColor: "transparent"
    textColor: "{colors.blue}"
    padding: "0"
  evidence-input:
    backgroundColor: "{colors.field-bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "12px"
    width: "100%"
  navigation:
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "8px 16px"
  quality-clear:
    backgroundColor: "{colors.lime}"
    textColor: "{colors.green}"
    rounded: "{rounded.xs}"
    padding: "4px 7px"
  quality-flagged:
    backgroundColor: "{colors.amber-bg}"
    textColor: "{colors.amber-ink}"
    rounded: "{rounded.xs}"
    padding: "4px 7px"
  notebook:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
  notebook-heading:
    backgroundColor: "{colors.lavender}"
    padding: "22px 20px"
  comparison-selected:
    backgroundColor: "{colors.cornflower}"
    textColor: "{colors.blue-deep}"
    rounded: "{rounded.sm}"
    padding: "6px 13px"
  brand-mark:
    textColor: "{colors.ink}"
    size: "34px"
---

# Design System: Perigee

## Overview

**Creative North Star: "The Orbital Observatory"**

A black sky, white typography and electric citron invite a learner into an investigation. The existing orbit mark is refined into a tilted ellipse, central ring and small orbital point. Host Grotesk connects the expansive, centered landing introduction to the quieter graphite workbench.

The landing surface uses decorative white stars and generous reading space. Working views concentrate on registered scientific images, nearby metadata and a reusable evidence notebook. This record describes the current React application, including its API and clearly labeled fixture modes; it does not describe the superseded light prototype or certify a deployment.

Source authority: [tokens](frontend/src/styles/tokens.css), [base components](frontend/src/styles/app.css), [orbital overrides](frontend/src/styles/orbital.css), [landing](frontend/src/components/Home.tsx), [star motion](frontend/src/components/OrbitField.tsx), [mark](frontend/src/components/BrandMark.tsx), and the [direction brief](coordination/orbital-ui-brief.md). The styles load in that order. Screenshots in `qa/orbital-ui/` provide visual context; current source governs subsequent review fixes. Product facts remain in [README.md](README.md) and the [integration contract](docs/INTEGRATION_CONTRACT.md).

**Key Characteristics:**

- Black and white identity with electric citron actions and selection.
- Self-hosted Host Grotesk with a large landing display and compact working hierarchy.
- Rounded graphite containers, image-led investigations and persistent evidence context.
- Decorative orbital motion on the landing page; deliberate user-controlled scientific playback in the bench.

## Colors

Near-black surfaces and white text establish the identity; electric citron identifies invitation, action and selection. The frontmatter retains actual CSS token names: `blue` is now citron, `cornflower` is an olive selection surface, and `lavender` is graphite notebook material. Those names do not authorize restoring the old colors.

### Primary

- **Electric citron** (`blue`) carries primary controls, links, focus and the highlighted hero line. `blue-deep` is its hover variant, with olive hover and selected-surface companions.
- **Action ink** is the dark text on filled primary buttons.

### Secondary

- **Quality green** pairs a dark green fill with pale green status text. **Amber** marks flagged data and comparison cautions; **error** colors distinguish failures. Status words accompany the color.
- Scientific hatching, pale image labels, prediction green and the cyan guide retain their evidence roles independently of the brand.

### Neutral

- **Black canvas** (`paper`), **graphite surface** (`surface`) and the darker field surface layer the work area. **White ink** and **muted gray** separate primary and supporting information.
- Fine gray dividers organize panels; the stronger line identifies editable fields. The notebook has a slightly cooler graphite heading and border.

**The Scientific Color Rule.** Keep quality states, coverage hatching, prediction markers and the guide visually distinct; the brand accent must not change what a scientific overlay means.

## Typography

**Display and body:** Host Grotesk, self-hosted at `/fonts/host-grotesk-latin.woff2`, with platform sans-serif fallbacks. The variable face declares weights 400–700 and uses `font-display: swap`. **Technical values:** the platform monospace stack; metadata rows also use tabular numerals.

The display is medium-weight, closely tracked and spacious in its surroundings. Most operational headings also use medium weight; semantic labels and scientific details carry the compact hierarchy. This is a role-based ramp rather than a fixed modular ratio.

- **Display:** centered landing question; narrows to `clamp(46px, 8.2vw, 62px)` below 760px and 42px below 360px.
- **Headline:** editorial landing sections. Investigation headings use their own smaller responsive role.
- **Section:** working section baseline; notebook headings adapt from 21px to 23px.
- **Body:** 16px operational text, with 14px supporting explanations. Landing descriptions use 17–21px; investigation-card descriptions use 16px. Supporting measures are bounded, including the 65ch introduction limit.
- **Label:** the reusable 13px metadata role; control text is 14px. Incidental landing captions are not a new type-scale step.
- **Inputs:** notebook text is 16px with a 1.55 line height at every breakpoint, with 24px between field groups.

**The Two Densities Rule.** Use the large display for the landing invitation; keep investigation headings, controls and metadata compact enough to inspect evidence together.

## Layout

The landing hero fills at least the viewport, keeps a calm centered reading column and uses stacked actions. Its top navigation floats over the scene. Continuation content has a 1200px maximum width: three image-led guided investigations, two compact open targets, a two-column evidence example, coordinate invitation and saved evidence. Guided cards share a footer baseline while their titles retain natural spacing. The evidence explanation and its h2 precede the example’s h3 in document order; desktop CSS places the example to the left without changing that reading order.

At 1050px and below, each guided card occupies a row with its preview beside its copy. At 760px and below, previews return above the copy, open targets and the evidence section stack, and the evidence explanation precedes its example. Landing gutters become 24px, then 18px below 360px. The 1500px adjustment enlarges the hero description.

Operational content retains the 1540px maximum with 40px desktop gutters; the top navigation follows the same outer alignment. The comparison/notebook grid uses `minmax(0, 2.25fr) minmax(310px, 1fr)` and a 24px gap. At 1100px the notebook follows the comparison. A “Record your evidence” / “Back to observations” anchor loop connects the separated areas; both destinations are focusable and the links preserve 44px targets. At 560px one full-width plate is selected with explicit observation controls and 12px comparison padding. The sequence viewer gains a metadata column at 1250px. At 1400px notebook padding expands to 24px.

The investigation header combines a compact target label, bounded investigation switcher, question and short orientation. Comparison images precede the detailed steps. The complete authored opening remains in the About disclosure; the notebook's full investigation question has its own disclosure. The Compare / Check / Explain strip sits with the steps, followed by progress and review controls. Coordinate fields use four columns on desktop, two at 1100px and one at 560px.

The reusable spacing scale runs from 4px to 32px. Larger landing section intervals are composition-specific. Ordinary controls have a 44px minimum target, primary actions 48px and the hero action 50px; inline text buttons extend their hit area without changing text layout. Print CSS restores light paper and semantic text, status, border and insight colors while retaining both selected plates, complete notes and provenance. This stylesheet behavior has not been verified through a runtime PDF print in this redesign pass.

## Elevation & Depth

Graphite fills, fine borders and tone changes provide depth. Cards do not use ambient lift shadows. The prediction ring has a thin shadow and the image compass has a text shadow solely to remain legible over observations. Stars sit behind a stable text column whose local star opacity is reduced without a visible panel.

**The Quiet Bench Rule.** Keep decorative perpetual motion off the investigation bench; image changes there follow explicit comparison or playback controls.

## Shapes

Large corners identify notebooks and major containers; medium corners frame image wells and disclosures; small corners identify operational fields and controls. Primary buttons and navigation use pills. Target cards use a related 20px silhouette, while compact target previews and the brand’s orbital elements are circular. The observed variation preserves useful density rather than making every element a pill.

## Components

### Buttons

Citron-filled primary buttons have dark text and deepen on hover. Secondary controls use graphite surfaces, olive hover fill and a stronger border. Inline link buttons use citron underlined text. Pressing enabled buttons moves them down 1px; color, border and transform feedback takes 160ms. Keyboard focus is a 3px citron outline with 3px offset. Disabled controls remain visibly disabled; reduced motion removes transitions.

### Chips and quality

Compact rounded chips pair text with status: green for a clear flag screen, amber for flagged data, neutral for unknown or uncovered. The target-type chip uses cool graphite. These states preserve their precise scientific meanings.

### Cards and notebook

Guided investigation cards pair real processed previews with a question, explanation and action context. Missing previews show a text fallback. Hatched pixels have no usable value and are explained below the cards. The notebook uses a cool graphite header, bordered white-on-dark form fields and attached-observation context; saved records can be reopened or exported from the landing continuation.

### Inputs and fields

Visible labels and hints precede dark fields with strong borders. Notebook textareas resize vertically and show character counts. Coordinate inputs and native selects use the same geometry; invalid coordinates gain a thicker error-colored border and a written error. Coordinate fields share four subgrid rows so labels, help, inputs and errors align across columns. Loading, empty, partial and failed results remain distinct.

### Navigation and comparison

White brand, muted links and a filled graphite evidence destination organize the top bar. Phone navigation uses shorter labels and removes the wide-only destination. The comparison selector uses explicit pressed states and a tinted olive selection; native disclosures expose quality, sources and processing detail without dominating the image plane.

### Orbit mark and starfield

The inline SVG mark combines a tilted ellipse, central ring and orbit point. The header point is citron; the hero wordmark is muted monochrome. Its proportions come from `BrandMark.tsx`, not a substitute icon.

The landing canvas contains decorative white points, not a sky map. Its center sits above the hero, so visible lower arcs travel leftward. A deterministic field of 1,000 candidate points is culled to the viewport; rendering caps pixel ratio at 2 and throttles drawing to roughly 30fps. A visible pause/resume control preserves phase. Reduced motion renders a static scene and labels the control “Motion reduced.” Offscreen, hidden-document and unmounted states stop work. The canvas is hidden from assistive technology and does not intercept input. Scientific Blink and Play remain separate, user-controlled interactions.

## Do's and Don'ts

### Do:

- **Do** preserve the fixed sky grid and keep dates, wavelength, quality and provenance associated with each frame.
- **Do** use the real source imagery for target previews and retain visible fixture labeling when that mode is active.
- **Do** keep a visible star pause control and honor reduced motion, offscreen state and document visibility.
- **Do** retain claim, observations and uncertainty with local-save status and export actions.

### Don't:

- **Don't** animate real scientific image data as part of the decorative orbital scene.
- **Don't** treat a catalog prediction, clear quality screen or coverage match as a detection.
- **Don't** apply the landing display scale or starfield to dense investigation controls.
- **Don't** promote tiny incidental landing captions or print provenance into the reusable type scale.
