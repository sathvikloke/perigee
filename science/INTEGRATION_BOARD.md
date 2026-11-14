# Integration board

Maintained by Sathvik. Evidence only: a row is "done" when its behavior was exercised, not when it is planned.

**As of 2026-11-14 11:35 CST** (`origin/main` = `85c729f`; remote branches: `main`, `codex/team-master-prompts`)

## Actual state

| Gate / area | Owner | State | Evidence |
|---|---|---|---|
| Frontend app (`frontend/`) | Akshobya | Not started on any pushed branch | No `frontend/` on any remote branch |
| API (`backend/main.py`, routes) | Aditya | Not started on any pushed branch | No `backend/` code on remote |
| Platform + deploy (`vercel.json`, catalog/assets) | Suhrit | Vercel project exists; no app deployment | Commit `85c729f` message |
| Data adapter + presets (`backend/data/**`, `backend/content/presets/**`) | Sagar | Not started on any pushed branch | — |
| Targets content (`backend/content/targets.json`) | Sathvik | **Done, verified** | `science/CASE_SELECTION.md` |
| Case content (`backend/content/cases/*.json`) | Sathvik | **Authored, science-verified; not yet rendered in the app** | Same |
| Gate 1: one preset from the deployed API into the real frontend | All | Not met | — |
| Gate 2: non-preset coordinate → real archive → ≥1 processed frame | Aditya + Sagar | Not met; test coordinate chosen | Eps Ind A, 330.8400 −56.7860, 355 DR1 records |

## Decisions (binding for this sprint unless revised here)

1. **Frame identity is `frame_key = <observation_id>_D<detector>`.** One SPHEREx `observation_id` (e.g. `2026W18_1A_0516_1`) covers up to 6 detector images with different wavelengths, so `observation_id` alone is **not** unique per image. Add `detector` and `frame_key` to `FrameRecord` and observation descriptors. This is additive to the contract. Aditya to confirm.
2. **Observation time is mid-exposure.** `observed_at_utc` = `DATE-AVG`, `mjd` = `MJD-AVG` from the IMAGE header. If a descriptor comes from SIA before the file is read, use `t_min`, and the frame record replaces it with `MJD-AVG`. Sort by `mjd`, then `frame_key`.
3. **Quality status:**
   - `not_covered` is geometric only: the position is off the image.
   - Non-finite pixels at a covered position mean `flagged`.
   - Pixel counts are `null` when unknown, never 0.
   - `SOURCE` and `FULLSAMPLE` are informational.
4. **Wavelength is `null` when the position is off the image.** Never extrapolate the spectral WCS.
5. **Fixed grid:** north up, east left, centered on the preset `query_center`, identical across frames. Never recenter on the target.
6. **Case frames:** `fair_comparison` uses Eps Ind B A/B/C, and `moving_neighbor` uses Barnard A/B/C, with exact keys in the case JSON files. Sagar's processor output for these six frames must match the case JSON (wavelength to 1e-4 µm, same date, same quality status) before the case ships.
7. **The WISE 0855 challenge coordinate is tested separately** from the preset `query_center`. At FOV < 4.5′ the object falls outside the field.
8. **Cut order (from PLAN.md):** optional AI → third case → animation polish → overlays. The live coordinate path, two cases, provenance and the public link are not cut.

## Handoffs

**Sagar (data/processor)**
- Regenerate presets for the six case frames listed in `science/CASE_SELECTION.md`.
- Implement decisions 2–5. Two defects from the old audit logic are documented there; don't reproduce them.
- Ping me with your output for the six frames and I'll compare.
- Expect IRSA 502 HTML bodies with HTTP 502 (seen 11:30 CST). Validate the content type before parsing.

**Aditya (API)**
- Add `detector` + `frame_key` (decision 1).
- Map IRSA 502/HTML to `UPSTREAM_UNAVAILABLE`, and per-collection failure to `status: partial`.
- Use Eps Ind A (330.8400, −56.7860, fov 6) as the positive-path live test.

**Suhrit (platform)**
- Serve `backend/content/targets.json` as the source for `/api/v1/presets` and `backend/content/cases/{id}.json` for `/api/v1/cases/{id}` without rewording.
- Unknown case → 404 JSON.

**Akshobya (frontend)**
- The case JSON has `opening_question`, `summary`, `background.short` (first screen), `background.details` (collapsible), `steps[].prompt/hint/check`, `conclusion_guide`, `limitations` and `sources`. Render the copy as-is. Send me wording problems; don't rewrite.
- `display_requirements` asks for a shared stretch, a labeled catalog-prediction marker, and a fixed guide line for Barnard's Star.

**Neeraj (QA)**, once Gate 1 exists:
1. Fresh browser, public URL, no login.
2. Open each case. Do the dates, wavelengths and quality states match the case JSON?
3. Is the marker labeled a prediction?
4. Does a 2′ FOV query at the WISE challenge coordinate warn rather than claim absence?
5. Does an export contain `frame_key`s and source URLs?

## Open questions

- Exact Chicago local presentation slot. Plan for Sunday noon readiness.
- Whether to swap `fair_comparison` to the same-release DR1 pair (see `CASE_SELECTION.md`). Current choice: keep the DR1/QR3 pair and teach the release caveat.
