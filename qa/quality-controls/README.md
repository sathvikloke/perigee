# Wavelength, quality and comparison controls: worker 13

Branch `codex/parallel-13-quality-controls`, based on `claude/perigee-integration` at `bdeaa2a`.
Run on 2026-11-14 against the real stack: FastAPI in `PERIGEE_DEV_MODE=1` on :8090, Vite on :5200 with `PERIGEE_DEV_API=http://127.0.0.1:8090`.
The browser was headless Google Chrome driven by `playwright-core@1.49.1`, installed in a scratch folder rather than in `frontend/`.
No live IRSA calls were made. The shared in-app browser pane was not used.

These checks are practical, not a certification. No screen reader or physical phone was used.

## 1. Wavelength filter for stepping and Play

The full Barnard's Star series has 34 frames across 0.80–4.73 µm.
Consecutive frames jump between wavelengths, for example 2.0062 → 4.0602 → 1.3290 µm.
Played unfiltered, brightness and appearance change for reasons unrelated to motion.

The chronological stepper (`FrameViewer.tsx`) now has one native select, **Wavelengths to step and play**:

| Option | Rule | Source of truth |
|---|---|---|
| All wavelengths (default) | every frame | — |
| Near X µm (within one band width) | \|λ − X\| ≤ the frame's **own** `bandwidth_um`; X is the current frame's `wavelength_um`, frozen when chosen | `wavelength_um`, `bandwidth_um` |
| Detector N only | same `detector` field as the current frame | the record's `detector` field; the summary reports the real λ range of the kept frames |

The rules for what the filter keeps and how it is described:
- **Excluded frames are counted.** These are frames with a null wavelength (for example, position off the image), frames with no band width, and frames not loaded yet or failed. They are counted on their own lines and never treated as zero.
- **No inferred wavelengths.** No wavelength is inferred from a detector number or label.
- **Shared controls.** Earlier/Later, ←/→, Home/End, the slider and Play all respect the filter.
- **Time order stays.** Time and wavelength stay separately labelled on the plate.
- **Visible count.** The summary reads like "3 of 34 frames near 2.01 µm, each within its own band width (2.0062–2.0284 µm)".
- **Jumping outside the filter.** A case-frame jump to a frame outside the filter is allowed. The UI then says "Frame #N is outside this filter", and Earlier/Later move to the nearest kept frame.
- **Reset.** A new search or preset resets the filter to all wavelengths.

### Barnard's Star numbers (real products, `GET /api/v1/presets/barnards_star/frames`)

| Filter, centred on case frame A (`2025W35_1A_0008_1_D3`, 2.0062 µm, bw 0.0497) | Frames kept |
|---|---|
| Near 2.01 µm, each within its own band width | **3 of 34**: A 2.0062, B 2.0123, C 2.0284 µm (25 Aug 2025, 19 Mar 2026, 19 Aug 2026) |
| Detector 3 only | 6 of 34, 1.6698–2.0284 µm |
| (not offered) Detectors 1–3 "SWIR" group | 18 of 34, 0.8041–2.0284 µm |
| Frames with no wavelength at the target | 0 |

- **Why near-band keeps 3.** Three frames is a short loop, but they are exactly the three case frames, and they span a year at nearly the same wavelength. That is the cleanest "little video" of Barnard's Star moving north past fixed field stars, so the near-band filter is the primary option.
- **The coarser option.** It is per detector, not the 1–3 / 4–6 split. The SWIR group still spans a factor of 2.5 in wavelength (0.80–2.03 µm), so brightness would keep jumping. One detector spans 1.67–2.03 µm here, and the summary states that range.
- **Epsilon Indi B for comparison.** Case A is 2.3232 µm. The near filter keeps 3 of 44 frames, 2.3220–2.3760 µm. One frame (`2025W17_4B_0077_2_D1`, not covered) has no wavelength at the target and is listed as left out.

### Play on filtered Barnard frames

From `filter-run.log` (`scripts/filter.mjs`):

| Check | 1280 | 390 |
|---|---|---|
| Frames visited in 3.4 s | A → B → C → A → B → C → A, about 500 ms each | same |
| Labels per frame | 25 Aug 2025 · 2.0062 µm → 19 Mar 2026 · 2.0123 µm → 19 Aug 2026 · 2.0284 µm; "Flagged near target" each time | same |
| Counter | `1 / 3`, `2 / 3`, `3 / 3` | same |
| Live region (once) | "Playing 3 frames near 2.01 µm in time order. Use Pause to stop." | same |
| Caveat while playing | "Each frame has its own contrast stretch, so brightness is not directly comparable." The wavelength-change line is dropped, because the filter summary already gives the range. | same |
| Horizontal overflow | `scrollWidth` 1280 | `scrollWidth` 390 |
| Select target | 259×44 | 259×44 |

Screenshots: [`play-filtered-barnard-1280.jpg`](play-filtered-barnard-1280.jpg) and [`play-filtered-barnard-390.jpg`](play-filtered-barnard-390.jpg) (playing, frame B, guide line through A, flag legend).

## 2. Failed and not-loaded frames in the slider and blink picker

`FrameViewer.tsx` now marks a frame without an image instead of hiding it.

**Slider:**
- The slider's spoken value reads "#3 · 1 Jun 2026 · failed to load".
- The visible counter next to it reads "3 / 5 · failed to load".
- On the plate, "Wavelength pending" becomes "Wavelength unknown (not loaded)" for a failed frame.

**Blink pair picker:**
- Options read "#3 · 1 Jun 2026 · failed to load". Other states read "not loaded yet", "loading" and "not loaded (stopped)" (the last is for a frame superseded by a newer search).
- Ready frames show their wavelength ("#5 · 27 Sep 2026 · 2.32 µm"), so a like-for-like pair is easy to pick.
- Failed options are **no longer disabled**. Choosing one keeps Blink disabled and explains why: "#3 has no image (failed to load). Retry it from the stepper, or choose another frame to blink."

**How this was checked:**
- **In the browser:** the development fixture's simulated 502 frame (`?view=query&…&fixtures=1`), with the fixture banner on. See [`failed-frame-marked-390.jpg`](failed-frame-marked-390.jpg) and [`blink-picker-failed-390.jpg`](blink-picker-failed-390.jpg).
- **Fault proxy not used:** replaying `qa/loading-recovery/fault_proxy.py` needs a recorded IRSA search, and there was no cache on this machine. Recording one would mean live IRSA calls.
- **Unit tests:** the live-search states (pending, failed, superseded) are pinned by unit tests that render the component.

## 3. Quality states (390 px, reached by keyboard)

From `quality-run.log` (`scripts/quality.mjs`). Each state was reached with the keyboard: a Frame A button plus Enter, or Home/→ in the stepper. "Quality details" was opened with Enter on its `<summary>`. Every state had `scrollWidth` equal to the viewport.

| State | Real example | Plate chip | Explanation (beside the plate) | Quality details |
|---|---|---|---|---|
| clear | Epsilon Indi B case A `2026W18_1A_0516_1_D3` | ✓ Flag screen passed | "No problem flags were found in a small circle around the predicted position… This is not a detection and not a brightness measurement." | covered yes · usable 19 · problem 0 · flags none reported |
| flagged | Barnard's Star case A `2025W35_1A_0008_1_D3` | Flagged near target | "Problem flags or missing pixels were found near the predicted position. You can look, but brightness and exact position here are not reliable." | covered yes · usable 0 · problem 19 · BLOOM, OVERFLOW, SUR_ERROR, TRANSIENT · 3 of 19 non-finite |
| not_covered | Epsilon Indi B `2025W17_4B_0077_2_D1` (frame #1, Home) | Position just off image | "The predicted position is just outside this image… That is not evidence the object is absent." Wavelength: "Not available — the position is off this image". | covered no · usable/problem **not available** · flags **not checked (the position is off this image)** |
| unknown | **None in the real products.** Development fixture `FIXTURE_UNKNOWN_QUALITY_D2`, with the fixture banner and the plate note "Development fixture — not NASA data." | Flag screen not run | "The flag screen was not run or could not be completed for this frame, so its quality is unknown. Treat it as unchecked, not as clear." | covered/usable/problem **not available** · flags **not checked** |

Screenshots: [`quality-clear-390.jpg`](quality-clear-390.jpg), [`quality-flagged-390.jpg`](quality-flagged-390.jpg), [`quality-not-covered-390.jpg`](quality-not-covered-390.jpg), [`quality-unknown-fixture-390.jpg`](quality-unknown-fixture-390.jpg).

Text fixes made here:
- **Problem flags for unscreened frames.** Unknown and not-covered frames used to show "none reported", which reads as a clean result. They now say "not checked". The fix is in `FrameDetails` and the case bench quality panel, through `formatFlagNames`.
- **Unknown explanation.** It now says it is "not as clear".
- **Missing counts.** Unknown counts stay "not available", never 0.
- **Marker label.** Every marker remains "Catalog prediction, not a detection".

## 4. Keyboard path

From `keyboard-run.log` (1280) and `keyboard-run-390.log` (390); both gave the same results.

1. Focus **Frame A** → Enter → "Case frame A", 4 / 34.
2. Shift+Tab ×4 (Later, slider, Earlier… up to the select) → the **Wavelengths to step and play** select, with a 3px solid focus outline.
3. Type **N** (type-ahead on the closed native select) → "Near 2.01 µm", counter `1 / 3`. Spoken: "Frame 1 of 3 near 2.01 µm (4 of 34 in all)…".
4. Shift+Tab to **▷ Play** → Space → playing, announced once ("Playing 3 frames near 2.01 µm…") → Space → paused.
5. → B (2/3), → C (3/3), → stays on C, ← B, Home A, End C. All stay inside the filter.
6. Slider ← → B. Its value reads "#19 · B · 19 Mar 2026 · 2.01 µm".
7. On the select, type **A** → back to all wavelengths. The position is kept (19 / 34).

macOS Chrome opens a popup on ArrowDown for a closed select, which a headless browser cannot drive. Type-ahead is the keyboard path verified here. Space/↓ then Enter in the native popup is standard platform behaviour.

## Unit tests

`frontend/tests/quality-controls.test.ts` adds 15 tests:
- **Barnard regression:** the real 34 Barnard λ/bandwidth/detector values give near-A = [A, B, C] and detector 3 = 6.
- **Play under the filter:** order and wrap, plus starting from outside the filter.
- **Stepping:** step-within and slider position.
- **Copy:** the announcement and caveat wording.
- **Band width:** each frame's own band width is used.
- **Exclusion counts:** null wavelength, no band width and not loaded are counted, and none is treated as zero.
- **Status tags:** blink-picker option text, with no disabled options; the counter tag and spoken value; "Wavelength unknown (not loaded)".
- **Filter select:** rendered, with a disabled near option and its reason when the frame has no wavelength.
- **Quality text:** four distinct chips, labels and explanations; "not checked" flags.
- **Unknown fixture:** labelled `_fixture`, with nulls kept, and reachable through the fixture search.

`npm test`: **86 passed** (71 before). `npm run build`: clean.

## Exact steps

```sh
~/Library/Python/3.9/bin/uv venv --python /Users/sathvikloke/.local/bin/python3.12 .venv
~/Library/Python/3.9/bin/uv pip install --python .venv/bin/python -r backend/requirements-dev.txt
PERIGEE_DEV_MODE=1 .venv/bin/python -m uvicorn backend.main:app --port 8090 &
(cd frontend && npm ci && PERIGEE_DEV_API=http://127.0.0.1:8090 npx vite --port 5200 --strictPort) &

mkdir -p <scratch>/qa13 && cp qa/quality-controls/scripts/*.mjs <scratch>/qa13/
(cd <scratch>/qa13 && npm init -y >/dev/null && npm i playwright-core@1.49.1)
cd <scratch>/qa13
OUT=<repo>/qa/quality-controls node filter.mjs      > <repo>/qa/quality-controls/filter-run.log
node keyboard.mjs                                    > <repo>/qa/quality-controls/keyboard-run.log
W=390 node keyboard.mjs                              > <repo>/qa/quality-controls/keyboard-run-390.log
OUT=<repo>/qa/quality-controls node quality.mjs     > <repo>/qa/quality-controls/quality-run.log

cd <repo>/frontend && npm test && npm run build
```

## Limitations

- **The near-band filter keeps only 3 Barnard frames.** That is honest and enough for the motion loop, but it is short.
  - The per-frame contrast stretch still changes brightness between frames, and the playing caveat says so.
  - The case bench's A/B/C use a shared stretch; the full-series stepper does not.
- **The near filter's centre is frozen when chosen.** To re-centre, pick "All wavelengths", step to another frame, and choose "Near" again.
- **"Same detector" is a coarse grouping.** One detector still spans about 0.36 µm in this series, and the caveat states the spread.
- **No visual tick marks on the slider track.** Failed frames show in the counter, the spoken value and the picker, not as coloured marks on the native range input.
- **No real "unknown" quality example exists.** The fixture is the only demonstration, and it is bannered.
- **Not exercised against a live faulting search.** Failed-frame marking was checked with the fixture's simulated failure and unit tests only, for the fault-proxy reason in §2.
- **Element screenshots hide the fixed skip link** with a screenshot-only style. Tall captures otherwise draw it mid-image. It is not a page defect.
- **Not tested on Vercel.**
