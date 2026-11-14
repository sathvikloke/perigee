# My evidence: titles and reopen (QA-F3, F4)

Fixes F3 and F4 from the fresh-user QA (issue #6, `qa/fresh-pass/README.md` on `codex/neeraj-qa`).

## What changed

- **Titles.** Each saved card is titled for a person, not by its raw ID. A card's own `title` is used when it has one. Older cards get a title from the target list (`/api/v1/presets`) and the case content (`/api/v1/cases/<id>`), for example "Epsilon Indi B · Is this a fair comparison?". A coordinate search is titled by its position, for example "Coordinate search · RA 83.82°, Dec −5.39°". If none of that can be resolved, the raw ID is shown (`frontend/src/evidence/title.ts`).
- **Reopen.** Each row has a **Reopen** link before Export and Delete. Its accessible name includes the title, for example "Reopen Epsilon Indi B · Is this a fair comparison?". A preset card opens `?preset=<id>`. A coordinate card opens `?view=query&ra=…&dec=…&fov=…`, plus `&case=` when the card has a case. Development-fixture cards keep `&fixtures=1`. The link carries no notes. The route comes from the notebook context key the card is saved under, so the reopened notebook finds that same card. If the key is missing, the route is rebuilt from the card's own preset or query fields (`frontend/src/evidence/reopen.ts`).
- **F4.** Under the case pair's processing note: "The pair shares one stretch so the plates can be compared by eye; the timeline below gives each frame its own." It appears only for the case pair, and only when the pair's stretch is shared.

## Browser check (14 Nov 2026)

Setup: backend with `PERIGEE_DEV_MODE=1` on :8070, Vite dev server on :5270 proxied to it, live API, and localStorage cleared first. Test notes were written in Epsilon Indi B fair_comparison and Barnard's Star moving_neighbor. A live search ran at RA 83.82, Dec −5.39, limit 3, and IRSA answered on the first try. A synthetic card with its own `title` was also injected for WISE 0855.

| Check | Result | Screenshot |
|---|---|---|
| Home list titles: coordinate, Barnard, Epsilon, own-title | Pass: all human titles, no raw IDs | `01-home-list-1280.jpg` |
| Reopen reached by Tab, focus ring visible, name includes title | Pass: 3px cobalt outline with offset | `02-reopen-focus-1280.png` |
| Reopen Epsilon (Enter key) | Pass: `?preset=epsilon_indi_b`, EPS claim and observations restored | `03-reopened-epsilon-1280.jpg` |
| F4 sentence under case pair; timeline note unchanged | Pass | `04-f4-pair-stretch-note-1280.jpg` |
| Reload on reopened Epsilon page | Pass: same notes | n/a |
| Back to Home, then forward | Pass: list intact, notes restored after forward | n/a |
| Reopen Barnard (click) | Pass: BARNARD claim and uncertainty restored, observations empty as written | n/a |
| Reopen coordinate card | Pass: inputs 83.82 / −5.39 / 6, search reran, ORION notes restored | `05-reopened-coordinate-1280.jpg` |
| Reload on reopened coordinate page | Pass: same notes | n/a |
| Other cards untouched after all reopens | Pass: 4 cards, 4 contexts, claims unchanged | n/a |
| 390 px list | Pass: no horizontal overflow, Reopen 82×44 | `06-home-list-390.jpg` |
| 320 px list | Pass: no overflow, "RA"/"Dec" stay with values | `07-home-list-320.jpg` |
| 320 px reopen Epsilon | Pass: notes restored | `08-reopened-epsilon-notebook-320.jpg` |

## Follow-up fixes (same branch)

### Timeline overflow at 320 px

**Cause.** With the "Near this frame's wavelength" or "This frame's detector only" filter selected, the long option text (for example "Near 3.98 µm (within one band width)") set the `<select>`'s min-content width. `.sequence` and `.wave-filter` were grids with an implicit `auto` column, so that width stretched the whole timeline about 6 px past a 320 px screen. The sequence head, stepper, frame plate and side panel all overflowed with it.

**Fix.** Both grids now use `grid-template-columns: minmax(0, 1fr)` in `app.css`. Tokens and composition are unchanged, and at 1280 px the timeline keeps its two-column body.

**Sweep.** For every wavelength-filter option, step through every frame and check `scrollWidth <= innerWidth`:

| Page | 320 px | 390 px |
|---|---|---|
| Barnard's Star moving_neighbor | 41 states, 0 overflow | 41 states, 0 overflow |
| Epsilon Indi B fair_comparison | 55 states, 0 overflow (was 325 px with "near") | 55 states, 0 overflow |
| Live query RA 83.82, Dec −5.39 (24 results) | 30 states, 0 overflow | 30 states, 0 overflow |

Screenshots: `09-timeline-near-filter-320.jpg` (Epsilon), `10-query-timeline-near-filter-320.jpg`, `12-timeline-near-filter-390.jpg`.

### Focus after client-side navigation

**Cause.** `App.tsx` focused the `h1` once, in an effect keyed on the route. A preset renders "Loading curated frames…" first and mounts its heading later, so focus fell to `<body>`. This happened after clicking a target, Reopen, or the switcher, and on back/forward.

**Fix.** `frontend/src/lib/headingFocus.ts` focuses the heading immediately when it is already there. Otherwise a MutationObserver on `<main>` watches for the heading to mount, with no timeouts. It focuses the heading once and then disconnects. If the user moves focus to a control while the view is loading, the helper leaves it alone. Route changes clean the observer up. Unit tests: `frontend/tests/heading-focus.test.ts`.

**Browser check.** `document.activeElement` after each step:

| Step | Focus |
|---|---|
| Home → Barnard's Star (click) | `H1` "Follow a nearby moving star" |
| Back → Home | `H1` home heading |
| Forward → Barnard's Star | `H1` "Follow a nearby moving star" |
| My evidence → Reopen Epsilon Indi B | `H1` "Is this a fair comparison?" |
| Back, then forward | `H1` home heading, then `H1` "Is this a fair comparison?" |
| My evidence → Reopen coordinate card | `H1` "Which SPHEREx images cover this spot?" |
| Keyboard: Enter on "Reopen Barnard's Star · …" | `H1` "Follow a nearby moving star" (was `BODY` before the fix) |
| Reopen at 390 px, both presets | heading focused |

Screenshot: `11-reopen-heading-focus-390.jpg` shows the focus outline on the heading after a keyboard-driven reopen.

## Notes

- A reopened coordinate search uses the default result limit (24), because shared links have never carried the limit. The notebook key does not include the limit, so the notes still come back.
- While `/presets` is still loading on Home, an older card briefly shows its raw ID as its title, until the target names arrive.
