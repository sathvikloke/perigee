# Mobile and keyboard QA: worker 17

Branch `codex/parallel-17-mobile-accessibility`, based on `claude/perigee-integration` at `41d8b42` (frontend A).
Run on 2026-11-14 against the real stack: FastAPI in `PERIGEE_DEV_MODE=1` on :8040 and Vite on :5195 with `PERIGEE_DEV_API=http://127.0.0.1:8040`.
The browser was headless Google Chrome, driven by `playwright-core@1.49.1`. Axe used `axe-core@4.10.2`.
Both packages were installed in a scratch folder, not in `frontend/`, so nothing is added to the bundle or to `package.json`.

These checks are a practical subset. They are **not** an accessibility certification. No screen reader, physical phone or forced-colors test was run.

## Check matrix

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Sky in the first phone screen at 390×844 | **fixed** | The first plate's image moved from 735px to 653px (Epsilon Indi B) and to 658px (Barnard's Star). Visible sky grew from 109px to 191px. The step strip, question, target and pair choice all stay. `before-phone-390.png` and `after-phone-390.jpg` |
| 2 | Touch targets ≥44px at 320 and 390 (details open) | **fixed** | Before, these were under 44px: brand link (29px), three "Hint" summaries (32px), provenance FITS links (15px), the frame-details FITS link, the footer archive link (19px), "Search the archive here" (18px) and the fixture button. After, every control measures ≥44px. Two inline text buttons keep an 18px box but get a 44px `::after` hit area, confirmed with `getComputedStyle(el,'::after').height`. Checkbox labels were already 44px. |
| 3 | "Search  coordinates" double space | **fixed** | The accessible name is now "Search coordinates" on desktop and "Search" on phones (one text node per breakpoint). |
| 4 | Horizontal overflow at 320, 390, 768 and 1280 | **fixed** (320) / pass | Before, 320px had `scrollWidth` 332, caused by the step strip widening the bench grid. After, `scrollWidth` equals the viewport at every width, on all three presets and the query route. |
| 5 | Long IRSA URLs and frame IDs | **fixed** | On phones the provenance table wraps long frame IDs and FITS links instead of scrolling sideways. Frame-details values already used `overflow-wrap:anywhere`. In print, full source URLs and SHA-256 values wrap. See `after-phone-320-sources-open.jpg` and `after-phone-390-sources-open.jpg`. |
| 6 | Keyboard path: preset → case → A+B/A+C → blink → stepper → quality `<details>` → notebook → export → print | pass | 37 tab stops at 1280 with no trap. Order: skip link, brand, nav, switcher, archive link, A+B, A+C, (phone: Observation A, Observation B), Blink, checkboxes, hints, background, quality, sources, Earlier, slider, Later, checkboxes, Frame A/C/B, attach, frame details, 3 notebook fields, Export, Print, guide, footer. |
| 7 | Focus visible | pass | Every tab stop showed a 3px solid cobalt outline (`after-desktop-1280-focus-blink.jpg`). |
| 8 | Stepper arrow keys and focus retention | **fixed** | ←/→/Home/End step frames (35→44→43→1 of 44). Before, pressing End or reaching either end disabled the focused button, which dropped focus to `<body>`. After, `aria-disabled` keeps focus on the button and pressing it at the end does nothing. |
| 9 | Live regions do not chatter | **fixed** | Case blink: 0 live-region mutations in 3.5 s. Sequence blink (`wise_0855`): 1 mutation, a single "Blinking two frames" message. Before (from reading the code), the announcement was built from the current index, so it changed every 1–1.5 s while blinking. |
| 10 | Reduced motion | pass | With `reducedMotion: "reduce"`, blink starts paused (`aria-pressed="false"`, no `.plates.blinking`), `scroll-behavior` is `auto` and transitions are `0s`. Blink is never auto-started for any user. Covered by the unit test `frontend/tests/motion-and-controls.test.ts`. |
| 11 | Coordinate inputs: labels and error association | pass (+1 fix) | All four inputs have `<label for>` and a help text through `aria-describedby`. Submitting RA=400 sets `aria-invalid="true"`, adds the error to `aria-describedby` ("Right ascension must be at least 0 and less than 360 degrees.") and moves focus to RA. **Fixed:** Declination no longer sets `inputMode="decimal"`, because the iOS decimal keypad has no minus sign. See `after-phone-390-query-error.jpg`. |
| 12 | Print / save PDF of the evidence card | pass (+1 fix) | Under print emulation, the page shows both plates and the notes (including multi-line notes and a long URL). The provenance shows frame IDs, observation ID, detector, release, UTC time, wavelength, flag screen, the full source URL, processing version, grid, stretch and SHA-256. **Fixed:** the "Search the archive here" button no longer prints. See `print-preview-1280.jpg` and `print-evidence.pdf`. |
| 13 | axe-core (wcag2a/aa, 21a/aa, 22aa) | pass | 0 violations on home @1280, `epsilon_indi_b` @1280 and @390, `barnards_star` @390 and `wise_0855` @1280 (all with details open), and query with an invalid input @390. The items axe could not decide were contrast on decorative `aria-hidden` glyphs, text over the sky image (the compass and the "6 arcmin field" chip) and textareas partly off-screen. |
| 14 | Hint summaries distinguishable | **fixed** | The three "Hint" summaries now have the accessible names "Hint for step 1", "Hint for step 2" and "Hint for step 3". The visible text is unchanged. |
| 15 | 320px first screen | open (by design) | At 320×700 the blink button wraps below A/B and the question takes more lines. The first plate starts at 827px (Epsilon Indi B) or 747px (Barnard's Star). The page is usable and does not overflow, but the sky does not reach the first screen. |
| 16 | Compass "N↑ E←" over a bright sky | open | It relies on a text shadow over variable pixels. Axe cannot decide this, and it was not measured. It is `aria-hidden`, and the orientation also appears in text ("north up, east left"). |

## Before → after (390×844, Epsilon Indi B)

- Before: switcher, then question, steps, target, a full-width pair control, a **full-width Blink row**, the A/B row and then the plate (image at 735px).
- After: the same content, with **Observation A | Observation B | ▷ Blink pair in one row**. The top bar is 60px instead of 68px and the switcher is 52px instead of 57px. The step strip is 40px, which is fine because it is not interactive. Image at 653px.
  This matches Codex's reference `design/screenshots/mobile.jpg`, where the image starts at about 645px.

## Exact steps

```sh
# stack
~/Library/Python/3.9/bin/uv venv --python /Users/sathvikloke/.local/bin/python3.12 .venv
~/Library/Python/3.9/bin/uv pip install --python .venv/bin/python -r backend/requirements-dev.txt
PERIGEE_DEV_MODE=1 .venv/bin/python -m uvicorn backend.main:app --port 8040 &
(cd frontend && npm ci && PERIGEE_DEV_API=http://127.0.0.1:8040 npx vite --port 5195 --strictPort) &

# QA tooling outside the repo (nothing added to frontend/)
mkdir -p /tmp/perigee-qa && cp qa/mobile/scripts/*.mjs /tmp/perigee-qa/
(cd /tmp/perigee-qa && npm init -y >/dev/null && npm i playwright-core@1.49.1 axe-core@4.10.2)

cd /tmp/perigee-qa
ROUTES="?preset=epsilon_indi_b,?preset=barnards_star,?preset=wise_0855" WIDTHS=320,390,768,1280 node probe.mjs   # sky top, targets, overflow
OPEN=1 ROUTES="?preset=epsilon_indi_b" WIDTHS=320,390 node probe.mjs                                             # with all <details> open
W=1280 TABS=70 node keyboard.mjs        # tab order, focus outline, stepper focus, live-region mutations
RM=1 W=390 TABS=16 node keyboard.mjs    # reduced motion + phone order
ROUTE="?preset=wise_0855" TABS=1 node keyboard.mjs   # sequence-blink live region
node query.mjs                          # coordinate labels / aria-describedby / error focus at 320 and 390
OUT=. node print.mjs                    # print emulation content checks + PDF
INCOMPLETE=1 node axe.mjs               # axe-core pass
OUT=<repo>/qa/mobile node shots.mjs     # regenerate the screenshots in this folder

# unit tests and build
cd frontend && npm test && npm run build
```

The scripts use the system Chrome at `/Applications/Google Chrome.app`. The shared in-app browser pane had reached its tab limit because other workers' tabs were open, so it was not used and no other session's tab was touched.
