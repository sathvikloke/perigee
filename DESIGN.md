---
name: Perigee
description: A classroom experiment bench for comparing astronomical evidence.
colors:
  paper: "#f6f7fb"
  surface: "#fff"
  ink: "#17213d"
  muted: "#59647a"
  line: "#dce1ee"
  blue: "#244de8"
  blue-deep: "#193bb9"
  cornflower: "#e8eeff"
  lavender: "#eeebfa"
  lime: "#eaf4cd"
  green: "#355319"
typography:
  display:
    fontFamily: 'ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "clamp(28px, 2.65vw, 38px)"
    fontWeight: 750
    lineHeight: 1.16
    letterSpacing: "-1.25px"
  headline:
    fontFamily: 'ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.45px"
  title:
    fontFamily: 'ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 650
    lineHeight: 1.5
  body:
    fontFamily: 'ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: 'ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "12px"
    lineHeight: 1.5
  eyebrow:
    fontFamily: 'ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "12px"
    fontWeight: 750
    lineHeight: 1.5
    letterSpacing: "1.25px"
rounded:
  lg: "24px"
  md: "16px"
  sm: "10px"
  tag: "6px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "9px 13px"
    width: "100%"
  button-primary-hover:
    backgroundColor: "{colors.blue-deep}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "9px 13px"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    padding: "9px 13px 9px 0"
  comparison-switch:
    backgroundColor: "{colors.paper}"
    padding: "3px"
  comparison-switch-selected:
    backgroundColor: "{colors.cornflower}"
    textColor: "{colors.blue-deep}"
    rounded: "{rounded.sm}"
    padding: "6px 13px"
  evidence-input:
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "12px"
    width: "100%"
  navigation-active:
    backgroundColor: "{colors.cornflower}"
    textColor: "{colors.blue-deep}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
  quality-tag:
    backgroundColor: "{colors.lime}"
    textColor: "{colors.green}"
    rounded: "{rounded.tag}"
    padding: "4px 7px"
  disclosure:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
  notebook:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
  notebook-heading:
    backgroundColor: "{colors.lavender}"
    padding: "22px 20px"
---

# Design System: Perigee

## Overview

**Creative North Star: "The Classroom Experiment Bench"**

The classroom experiment bench gives learners a calm place to compare observations and make their reasoning visible. Cool paper, rounded white containers and substantial navy headings surround the scientific imagery. Cobalt identifies actions and selection; a lavender notebook distinguishes writing from observation.

This system is extracted from the interactive local prototype in `design/prototype/`, not a live archive application. Registered sky plates and their adjacent metadata establish the evidence; interface decoration does not supply astronomical content. The prototype’s compact density supports both inspection and writing without hiding uncertainty.

**Key Characteristics:**

- Equal-scale, registered observation plates with nearby metadata.
- Rounded paper surfaces, flat depth and a lavender evidence notebook.
- Plain language, visible keyboard focus and readable scientific labels.

## Colors

Cool paper and navy provide the working surface; cobalt, lavender and lime distinguish actions, reasoning and qualified status.

### Primary

- **Cobalt** (`blue`) identifies the main evidence export, links, focus and key icons. **Deep cobalt** (`blue-deep`) strengthens hover and selected text. **Cornflower** carries selected controls and comparison explanations.

### Secondary

- **Lavender** identifies the notebook heading and contextual target tag.

### Tertiary

- **Lime** and **green** pair a quiet status fill with readable flag-screen text. The status wording remains essential; green alone does not establish a scientific conclusion.

### Neutral

- **Paper** is the page and inset-control background; **surface** is the white working container. **Ink** carries primary text, **muted** carries supporting labels, and **line** separates adjacent evidence.

**The Evidence Travels Together Rule.** Keep the image, date, wavelength, quality status and source associated when the selected observation changes.

## Typography

Display, body and metadata share the platform sans-serif stack in the frontmatter. Weight, size and spacing establish hierarchy without a separate decorative or monospace family. Date and wavelength rows use tabular numerals.

- **Display:** the investigation question; phone presentation uses 30px with a 1.1 line height and a short measure.
- **Headline:** section baseline; target and notebook headings adapt between 21px and 23px.
- **Title:** observation headings; responsive variants range from 13px on phones to 16px in the stacked tablet layout.
- **Body:** explanatory copy; dense supporting text commonly uses the label size.
- **Label:** metadata, hints, controls and statuses; weight follows its role rather than making all labels bold.
- **Eyebrow:** uppercase category labels. Phone spacing tightens slightly while preserving the label size.

**The Readable Metadata Rule.** Screen metadata stays at least 12px; notebook text entry becomes 16px at the stacked layout breakpoint.

## Layout

The prototype’s centered content has a 1540px maximum width with 36px desktop gutters. The investigation uses a two-column grid: `minmax(0, 2.25fr)` for comparison and `minmax(310px, 1fr)` for the notebook, separated by the large spacing step. Controls sit immediately above their plates. Two equally sized square images share a row and fixed sky registration.

At 1100px and below, gutters become 24px and the grid tightens. At 900px and below, the notebook follows the comparison in a single column and text entry grows. At 560px and below, gutters become 16px, pair controls span the width and explicit observation buttons select one full-size plate. The three-step strip condenses to Compare / Check / Explain, omitting repeated helpers, the duplicate breadcrumb and distance so the sky reaches the first viewport. The navigation retains the evidence destination; native source disclosure remains available in the content. At 1400px and above, notebook padding expands to the large spacing step.

The recurring spacing steps are 8, 16 and 24px; compact metadata and field groups also use 12px and 20px. Functional controls use a minimum 44px height, with a 48px primary action. These are minimums, not fixed heights. Print restores both plates and includes the selected provenance and full notes.

## Elevation & Depth

Containers are flat: white paper, tinted sections and fine borders provide separation without card shadows. The sky prediction marker uses a thin translucent shadow, and the compass uses a text shadow so they remain legible over image content. These are overlay treatments rather than elevation levels.

**The Paper Surface Rule.** Use borders and background changes for container depth; reserve image-overlay shadows for legibility.

## Shapes

Large rounded containers hold comparison and writing; medium corners frame sky wells and disclosures; small corners identify controls and fields. Compact tags use the tag radius. Numbered steps and prediction rings are circular. Fine borders organize paper surfaces. The square sky well clips the image, while hatched uncovered pixels remain visible as missing coverage.

## Components

### Buttons

Clear, rounded controls use the small radius and a minimum 44px height. The full-width cobalt export action has white text and deepens on hover. Secondary controls use white surfaces and a light blue hover fill; the print action is quiet text. Hover transitions take 160ms. Keyboard focus uses a 3px cobalt outline offset by 3px; reduced-motion mode removes transitions.

### Chips

Compact labels carry words as well as color. The lime flag-screen tag uses green text; the lavender target tag describes object type. These are informational labels, not controls or evidence of a detection.

### Cards / Containers

The white comparison container uses a border, large corners and medium padding. The notebook uses the same large silhouette with a lavender header and 20px body padding, increasing on wide screens. Native disclosures use medium corners and preserve keyboard operation.

### Inputs / Fields

Three stacked prompts collect claim, observations and uncertainty. A bold visible label precedes a separate hint and softly tinted textarea. Fields have a fine blue-gray border, small corners, 12px internal padding and vertical resizing. Desktop input starts at 12px; the stacked layout uses 16px. Required fields and whitespace checks use native validation. Visible status describes local saving, restored notes, unavailable storage and export results.

### Navigation

Rounded links use muted text; the current investigation uses cornflower with deep cobalt text. Hover adds paper fill and focus uses the shared outline. The compact phone header keeps the evidence link. The skip link appears on keyboard focus.

### Registered plates and comparison controls

A two-option segmented control exposes its selected pair with `aria-pressed`. A/B compares dates at nearly the same wavelength; A/C compares wavelengths at the same time. Switching updates the related metadata, source table, attached observations and explanatory text together. The second explanation has an amber contextual treatment; this is not a global alert palette.

Blink is explicitly started and paused, alternating one image plane every second (1.5 seconds with reduced motion). Changing pairs, changing the phone breakpoint, printing or hiding the document stops the timer. Predicted-position markers can be hidden. The reduced-motion setting also removes smooth scrolling. Notes persist locally; JSON export and print carry the selected evidence. No live coordinate-search component is implemented here.

## Do's and Don'ts

### Do:

- **Do** keep date and wavelength separate and visible beside each observation.
- **Do** preserve notes and selected evidence across comparison changes.
- **Do** use explicit pressed states, text status labels and visible focus.
- **Do** recompose to one manually selectable plate on narrow phones.

### Don't:

- **Don’t** use generated sky imagery as observational evidence.
- **Don’t** turn a catalog prediction or passed flag screen into a detection claim.
- **Don’t** reduce screen labels below 12px to fit the layout.
- **Don’t** describe this local prototype as live coordinate search.
