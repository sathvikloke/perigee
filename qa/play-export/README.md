# Play the series and evidence export: worker 12

Branch `codex/parallel-12-play-export`, based on `claude/perigee-integration` at `b9717d6` (frontend A + Codex design A + worker 17 fixes).
Run on 2026-11-14 against the real stack: FastAPI in `PERIGEE_DEV_MODE=1` on :8070, Vite on :5198 with `PERIGEE_DEV_API=http://127.0.0.1:8070`.
The browser was headless Google Chrome driven by `playwright-core@1.49.1`, installed in a scratch folder rather than in `frontend/`.
The shared in-app browser pane was not used.

This covers judging finding 2 ("like a little video"), the in-app AI-use line and task 12 (evidence persistence and export).
These checks are practical, not a certification. No screen reader or physical phone was used.

## 1. Play over the series (judging finding 2)

A `▷ Play` / `Ⅱ Pause` toggle is the first control in the existing chronological stepper (`FrameViewer.tsx`). It appears both in case presets (Barnard's Star, Epsilon Indi B) and in non-case presets and live searches.

| Check | Result | Evidence |
|---|---|---|
| Plays in time order on the fixed grid | pass | Barnard's Star: `4/34 → 5 → 6 … 10/34` in 3.2 s. Every step is about 520 ms (about 2 fps), the same plate and grid, and the guide line through A stays fixed. See `play-run.log`. |
| Labels change with each frame | pass | Date, wavelength and quality chip change on each tick: 25 Aug 2025 2.0062 µm → 27 Aug 2025 4.0602 µm → 27 Aug 2025 1.3290 µm → …. The side panel (UTC, release, detector, frame ID) follows too. |
| Honest about stretch | pass | While playing, an amber notice reads "Each frame has its own contrast stretch, so brightness is not directly comparable." The full preset set is per-frame stretch, and this is the same wording as `compare.ts`. When the wavelengths in the series differ, a second line adds "The wavelength also changes from frame to frame; it is labeled on each one." The notice is hidden when not playing. |
| Starts only on click | pass | It is paused on load (`aria-pressed="false"`), including under reduced motion, and the counter did not move for 1.5 s. |
| Reduced motion | pass | Playback is slower: gaps of 1465 ms and 1560 ms (`PLAY_MS_REDUCED` = 1500). |
| One announcement | pass | During playback the live region changed once, to "Playing 34 frames in time order. Use Pause to stop." It does not announce each frame. |
| Stops on a hidden tab | pass | `visibilitychange` with `document.hidden` → paused, and the counter stays put. |
| Stops on print | pass | `beforeprint` → paused. The `.sequence` is not printed. |
| Stops on a breakpoint crossing | pass | 1280 → 540 px (crossing 560) → paused. Blink in `FrameViewer` stops on a breakpoint crossing too; before, only `CaseBench` did. |
| Stops on a manual step or a pair change | pass | ←/→, slider, Earlier/Later and "Frame A/C" all pause. On `wise_0855`, changing the blink pair `<select>` stops playback. |
| Blink and Play are exclusive | pass | `wise_0855`: Blink then Play gives `[blink false, play true]`; Play then Blink gives `[true, false]`. |
| Keyboard | pass | Space and Enter on the focused Play button toggle it. ArrowRight steps and pauses. |
| Fewer than 2 processed frames | pass (unit) | Play is `aria-disabled` (still focusable) and does nothing. Pending, loading and failed frames are skipped, never reordered. Frames that finish loading during a live search join the loop without restarting the timer. |
| Bounded loading | by design | Only the plate's current `<img>` and **one** `new Image()` warm-up for the next ready frame are requested. The series is never prefetched in bulk. |
| Touch targets and overflow | pass | Play is 88×44 at 390 and 76×44 at 320. `scrollWidth` equals the viewport at 320, 390, 768 and 1280. On phones, Play, Earlier and Later share one row and the scrubber and count share the next (`scripts/stepper.mjs`). |

Screenshots (Barnard's Star, playing):
- `play-barnard-1280.jpg`: frame 10/34, the notice, the guide line and the side details.
- `play-barnard-390.jpg`: the phone stepper layout and the notice.
- `play-barnard-390-frame1..3.jpg`: three consecutive played plates at 390, with the same grid and changing date and wavelength.

## 2. In-app AI-use line

The footer now ends with one line:

> Built with AI-assisted development (Claude Code, Codex). No AI runs in this app; all science checked against original NASA files.

- It links to `https://github.com/sathvikloke/perigee/blob/main/docs/AI_USE.md` (new tab, 44px target). See `footer-ai-1280.jpg` and `footer-ai-390.jpg`.
- **The link 404s until `docs/AI_USE.md` is merged to `main`.** It is being drafted on another branch.

## 3. Evidence card: save, reload, export a real card

**Steps:** Barnard's Star preset on the live API → write claim, observations and uncertainty → step to a non-case frame and attach it → reload → Export.

| Step | Result |
|---|---|
| Edit | "Saved on this device". `localStorage["perigee.evidence.v1"]` holds 1 card mapped to `api:preset:barnards_star`. |
| Reload | "Restored from this device". All three notes match exactly, and the attached list (A + C, plus 27 Aug 2025 · 1.3290 µm) is restored. |
| Export | The browser downloaded `perigee-evidence-moving_neighbor-2026-11-14-0d6c1181.json`, saved here as `barnards_star-evidence-card.json`. |
| URL afterwards | `?preset=barnards_star`. No note text. |

**Cross-check:** `scripts/crosscheck.py` compares every exported frame field with `GET /api/v1/presets/barnards_star/frames[?case_id=moving_neighbor]`. Result: **57 field checks, 0 mismatches** (`crosscheck.log`).

Exported excerpt (frame C; A and the extra frame have the same shape):

```json
{
  "schema_version": 1, "app_version": "0.1.0", "data_origin": "api",
  "case_id": "moving_neighbor", "preset_id": "barnards_star",
  "query": { "ra_deg": 269.4462585584787, "dec_deg": 4.768324486236583, "fov_arcmin": 6 },
  "frames": [ …, {
      "ref": "C",
      "frame_key": "2026W34_1A_0431_1_D3", "frame_id": "2026W34_1A_0431_1_D3",
      "observation_id": "2026W34_1A_0431_1", "detector": 3, "collection_id": "spherex_qr3",
      "observed_at_utc": "2026-08-19T04:57:42.053Z", "mjd": 61271.206736722,
      "wavelength_um": 2.0284358707774177, "bandwidth_um": 0.05017590956296267,
      "wavelength_location": "Spectral WCS (key W) sampled at the catalog-predicted position of Barnard's Star …",
      "quality_status": "flagged", "quality_flag_names": ["BLOOM", "OVERFLOW", "SUR_ERROR", "TRANSIENT"],
      "display_scale_mode": "shared",
      "source_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/2026W34_1A/l2b-v27-2026-243/3/level2_2026W34_1A_0431_1D3_spx_l2b-v27-2026-243.fits",
      "processing": { "processing_version": "perigee-processor-a/0.1.1", "pipeline_version": "l2b-v27-2026-243",
        "file_sha256": "ea3ecdd6…c032", "registration_method": "nearest_neighbour",
        "display_scale_method": "asinh", "marker_kind": "catalog_prediction" } } ],
  "claim": "Barnard's Star sits north of the guide line in C; the field stars stay put.",
  "observations": "A (25 Aug 2025) and C (19 Aug 2026): field stars land on the same pixels; …",
  "uncertainty": "A and C are at slightly different wavelengths and flagged near the target, …",
  "sources": [ IRSA SPHEREx, SIMBAD Barnard's star, Gaia (ESA), Space Apps challenge ]
}
```

Field by field:

| Required | In the export | Verified against |
|---|---|---|
| Frame IDs | `frame_key`, `frame_id`, `observation_id` | API FrameRecord, exact |
| Detector / release | `detector`, `collection_id` (`spherex_dr1` / `spherex_qr3`), and new `processing.pipeline_version` | API, exact (`pipeline_version` from `provenance.pipeline_version`) |
| UTC times | `observed_at_utc` (ISO, Z), `mjd` | API, exact |
| Wavelengths | `wavelength_um`, `bandwidth_um`, `wavelength_location` | API, exact (full precision, never inferred from the detector) |
| Flags | `quality_status`, `quality_flag_names` | API `quality`, exact |
| Source URLs | per-frame `source_url` (original IRSA FITS) plus card `sources` (case links) | API, exact |
| Processing | `processing.{processing_version, pipeline_version, file_sha256, registration_method, display_scale_method, marker_kind}`, `display_scale_mode` | API `provenance`, `registration`, `display_scale`, `marker`, exact |
| Claim / observations / uncertainty | the user's text, exact | the typed strings |
| case_id, query | `moving_neighbor`, preset query centre and FOV | case and preset JSON |
| No images | no `data:`, base64 or `/api/v1/assets` strings | checked in `crosscheck.log` |

## 4. Storage failure keeps notes

**Quota simulation** (`Storage.prototype.setItem` throws `QuotaExceededError` for `perigee*` keys, by init script):
- The status reads "Couldn’t save on this device · export to keep these notes". There was 1 debounced write attempt and no page errors.
- Leave in-app (home) and come back (history back): **all three notes are still there**, and the status still says it is not saved.
  - Before this change, returning re-read storage and would have shown an empty notebook.
- "My evidence" on home lists the draft as "moving_neighbor · not saved on this device; export to keep it".
- Export still works: `storage-failure-export.json` has the claim and both pair frames.
- See `storage-failure-notebook-1280.jpg`.

**Blocked storage** (the `window.localStorage` getter throws `SecurityError`): there are no page errors, notes stay on screen, and the status shows the same failure text.

**Within a tab only:** this protection does not survive a full reload, because nothing could be stored. The status line tells the learner to export.

## 5. Coordinate and share URLs never carry notes

- `routeToSearch` only writes `preset`, `view`, `ra`, `dec`, `fov`, `case` and `fixtures`.
- `parseRoute` ignores anything else, so `?claim=…` is dropped, not turned into a note. There are unit tests for both.
- After editing, saving, exporting and printing, `location.search` was still `?preset=barnards_star`.
- Home copy already says "Cards are saved only in this browser. Export one to keep or share it."

## Unit tests

- `frontend/tests/play-and-export.test.ts` adds 14 tests.
  - **Playback:** order, skip and wrap; under 2 ready frames; cadence; caveats; the single announcement; Play paused on first render; Play aria-disabled but focusable.
  - **Export:** every exported field, including processing; no image data; URLs never carry notes.
  - **Storage failure:**
    - `setItem` throwing a quota error keeps the session draft;
    - a throwing `localStorage` getter;
    - session-draft vs stored precedence;
    - unsaved drafts listed;
    - delete forgets the session copy.
- `npm test`: **56 passed** (42 before). `npm run build`: clean.

## Exact steps

```sh
~/Library/Python/3.9/bin/uv venv --python /Users/sathvikloke/.local/bin/python3.12 .venv
~/Library/Python/3.9/bin/uv pip install --python .venv/bin/python -r backend/requirements-dev.txt
PERIGEE_DEV_MODE=1 .venv/bin/python -m uvicorn backend.main:app --port 8070 &
(cd frontend && npm ci && PERIGEE_DEV_API=http://127.0.0.1:8070 npx vite --port 5198 --strictPort) &

mkdir -p /tmp/perigee-qa12 && cp qa/play-export/scripts/* /tmp/perigee-qa12/
(cd /tmp/perigee-qa12 && npm init -y >/dev/null && npm i playwright-core@1.49.1)
cd /tmp/perigee-qa12
OUT=<repo>/qa/play-export node play.mjs        # cadence, labels, announcement, stop rules, screenshots
OUT=<repo>/qa/play-export node evidence.mjs    # save/reload/export, quota, blocked storage, blink/play exclusivity
node stepper.mjs                               # stepper geometry at 320/390/768
curl -s "http://127.0.0.1:8070/api/v1/presets/barnards_star/frames?case_id=moving_neighbor" -o case.json
curl -s "http://127.0.0.1:8070/api/v1/presets/barnards_star/frames" -o all.json
python3 -I crosscheck.py <repo>/qa/play-export/barnards_star-evidence-card.json case.json all.json

cd <repo>/frontend && npm test && npm run build
```

## Limitations

- Playback loops. It shows whatever each frame is: different wavelengths, per-frame stretch and flag overlays (on by default for flagged frames; untick "Show flagged pixels" for a cleaner view). It is a visual aid, not a motion measurement.
- On a slow network the first pass through a series can show a frame before its PNG arrives. Only the next frame is warmed, by design. Curated preset assets are small static files.
- In-memory notes survive in-app navigation but not a full reload when storage is refused. The UI says to export.
- The AI-use link 404s until `docs/AI_USE.md` lands on `main`.
- A live coordinate search was not run in the browser for this pass, to avoid archive load. Play over live slots is covered by the skip/wrap unit tests and the ref-based timer.
