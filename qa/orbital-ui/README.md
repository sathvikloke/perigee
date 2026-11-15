# Orbital UI verification

Frontend branch `codex/orbital-ui`, based on main `0ffff6f`; checked 2026-11-14 America/Chicago. Verified UI source: `5f729e5`. Public production was not changed by this UI pass.

Captures span the review iterations. Final hero/mobile landing, `investigation-desktop.jpg`, `notebook-mobile.jpg` and `comparison-mobile.jpg` establish the repaired layouts. The investigation full-page captures retain the earlier review state, before the compact workflow and notebook shortcuts; `case-failure.jpg` precedes removal of the redundant unavailable-frame message. These historical captures should not be treated as final-state baselines.

## Build and scope

- Production build passed; 13 Vitest files / 124 tests passed; `git diff --check` passed.
- Three new regression tests cover cutout request identity, bounded cache size and query-limit URL round trip.
- GitHub [backend and frontend/Cloudflare CI](https://github.com/sathvikloke/perigee/actions/runs/43678549747) and [deployment-contract check](https://github.com/sathvikloke/perigee/actions/runs/43678549855) passed at `5f729e5`. Backend raw-data tests retain the CI's documented skip when `PERIGEE_DATA_ROOT` is absent. Vercel's separate preview status remains blocked by the existing account build-rate limit.
- Impeccable static scan returned `[]` for `frontend/src`. This is source-scan coverage, not accessibility certification.
- Real-data browser walkthrough used `http://127.0.0.1:5184`, with `/api` proxied to the public Cloudflare app. No fixture data was used for the screenshots/exports.
- A temporary loopback-only proxy on port 8890 and separate dev origin 5185 injected failures into public read requests. Those servers were stopped after verification; no fault mechanism ships in product code.

## Observed checks

| Area | Evidence | Result |
|---|---|---|
| Hero and responsive layout | 390×844, 900×900, 1280×800, 1680×1000 captures and DOM width checks | No horizontal overflow in sampled landing layouts; two-line hierarchy and actions remain legible |
| Star animation | `hero-motion-a/b.jpg`, `hero-paused-a/b.jpg` at the same viewport | Running captures differ; paused captures are byte-identical. Source geometry places the orbit center above the hero, giving visible stars leftward travel |
| Motion accessibility | Source review of `OrbitField.tsx` | Reduced-motion preference draws a static field; pause/resume preserves phase; hidden/offscreen/unmounted state cancels rendering. OS reduced-motion was not toggled during this walkthrough |
| Landing previews | DOM `complete && naturalWidth > 0`, after scrolling lazy images into view | All seven real thumbnails loaded. Epsilon shows same observation date with 2.3232 / 4.9399 µm labels; Barnard shows both dates and wavelengths |
| Desktop comparison | 1280×800 entry screenshot | Target centers visible near y=770 and Blink control near y=470; compact setup strip retains context |
| Comparison controls | Desktop Blink / Pause, A+C → A+B; phone Observation B | Pair changes update dates/wavelengths and notebook attachment together; phone shows the selected observation |
| Phone notebook path | Record your evidence → notebook; Back to observations | Browser focus follows the anchor; settled notebook top ≈50px at 390px viewport. Avoids traversing the optional timeline to write notes |
| Saved evidence | Write all three fields → export → My evidence → reopen | Original notes restored. Header My evidence focuses the saved collection. Local test notes are clearly labeled UI verification |
| Curated export | `curated-evidence-export.json` | Two shared-scale source observations, dates, wavelengths, processing provenance, quality and limitations retained |
| Live query | One result, Barnard coordinates, field 2′ → 10′ | Same observation key returns a new cutout; reported native sample changes from x≈13.95 to x≈72.95 and displayed field updates to 10′ |
| Query export | `query-evidence-export.json` | One source observation, 10′ query context, `case_id: null`, `preset_id: null`; no inherited guided-case title |
| Query history | Home → browser Back | Coordinates, field=10 and limit=1 restored; notebook restored. Search field top positions aligned at the sampled desktop width |
| Form recovery | Incomplete notebook export | Native required-field validation focuses the missing field. Completing it allows download |
| Missing flags | Fault proxy returns 503 only for flag assets | Explicit warning and Retry flag overlay displayed; quality status retained; retry loads the overlay after fault removal |
| Missing case products | Fault proxy returns 503 only for case-frame endpoint | Zero comparison images; general sequence remains labeled with its own scale. No silent substitution. Try again recovers four comparison image layers and three loaded flag overlays with zero alerts |
| Placeholder readability | Relative-luminance calculation | `#9aa1aa` on `#0c0f10`: 7.38:1 |

## Design review

An independent reviewer inspected rendered artifacts before the direction rationale, then compared matched-scale Apollo/Sprint hero references. Repairs from review: added wavelength labels and an appropriate Epsilon pair; replaced repeated decorative branding with an example evidence record; compacted investigation entry; clarified pairwise blinking; added mobile notebook shortcuts. See `design-review.md` for the final disposition.

## Bounds

This verifies sampled layouts, real-data paths, two deliberate failure conditions and source-level motion handling. It is not a user study, full assistive-technology audit, cross-browser certification or measured learning outcome. Print colors were adapted and source-reviewed, but a new PDF export was not visually rendered during this pass. Backend overnight science changes remain a separate integration task. The reference screenshots contain only the supplied sites' first viewport.
