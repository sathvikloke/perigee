# Processor comparison: integrated A vs Sagar's candidate (PR #19)

Worker 24, 2026-11-14. This is a comparison only. Neither candidate's branch was modified.

| | Branch @ commit | `processing_version` |
|---|---|---|
| **A** (integrated) | `origin/claude/perigee-integration` @ `6e855a2` (processor from worker 05 `9c9049a`, API A `88e3772`) | `perigee-processor-a/0.1.0` |
| **Sagar** | `origin/codex/sagar-data` @ `cb1f36b` (PR #19, single commit on `f2359c4`) | `perigee-data 0.1.0` |

Both were run on the same inputs:
- the 183 retained cutouts in `research/build_data` (read only);
- the same venv (CPython 3.12.16, with `backend/requirements-dev.txt` pins: astropy 8.0.2, numpy 2.5.4, pillow 13.0.0);
- the same case JSON (`origin/codex/sathvik-science`);
- the same Gaia controls.

## Recommendation: (c) keep A, and adopt specific pieces of Sagar's work

**The science is a tie.** Both pass the independent acceptance review on all 189 records, and both match Sathvik's audit on 183/183 frames. On identical inputs their numbers agree to about 1e-9 µm in wavelength and 0.005″ in marker position. Status and pixel counts match exactly.

**Integration is not a tie.** Sagar's products do not work with the layers that have already been built and tested against A:
- **Catalog.** Every image is dropped (0 of 366 image refs resolve), and both case listings return `missing`. The frontend would show plates with no image.
- **Live path.** One real archive URL form (`l2b_retry`) is rejected.
- **Merge.** Merging PR #19 as-is conflicts in 3 `backend/data` files and replaces A's tests. With both product trees present, it also hides every image in the default preset listings (see I-7).

Switching would mean either rewriting Sagar's output layout or changing the catalog and frontend, and then re-verifying layers 03, 07, 08 and 01. Science gains nothing in exchange.

**Adopt from Sagar:**
1. **`tools/ingest/fetch_manifest.py`.** It is stdlib-only and reads `research/build_data/manifest.json`, which is already on the integration branch. Any machine can then re-download all 183 cutouts and verify their hashes. Drop-in.
2. **The field-registration check.** Take `field_shift()` from `tools/ingest/check_registration.py` (FFT cross-correlation, with the target masked) and its injected-offset test.
   - Port it to read A's grid, which is `presets/<p>/case-<id>/` with nearest-neighbour resampling.
   - Today it imports Sagar's `data.grid` and `data.fits_io`, and writes into Sagar's `sets/` layout.
3. **Sagar's flag legend wording.** "Hatched pixels carry at least one adverse SPHEREx flag (informational SOURCE/FULLSAMPLE flags are not drawn)" could be added to A's `flag_image` as a `meaning` string.
   - Keep A's `legend`, which the frontend reads.
4. **Ideas to note, not code to merge.** Each is a product decision for the owners, not a defect in A:
   - a 4′ field that has no transparent corners;
   - bilinear display resampling;
   - the background offset;
   - `quality.status = "unknown"` when fewer than 10 usable pixels remain.

Sagar's audit claim checks out: running his `check_science_audit.py` gave 0 differences in 183 frames, and A gives 0 too.

## Side-by-side

| | **A (integrated)** | **Sagar (PR #19)** |
|---|---|---|
| Science acceptance, 189 records (cols 1–7 + case) | **189/189 PASS**, 0 FAIL; case_match 6/6 | **189/189 PASS**, 0 FAIL (with documented bridges); case_match 6/6 |
| PNG reconstruction from raw bytes | 100% exact, every frame (nearest) | 100% exact, every frame (bilinear, re-implemented from Sagar's stated rule) |
| Marker vs independent prediction | max 0.0007 display px | max 0.0068 display px (Sagar rounds to 0.01 px) |
| Gaia stars in PNG | 161 frames: median 0.45 px (0.63″), worst 2.01 px (2.8″) | 154 frames: median 0.35 px (0.33″), worst 2.26 px (2.1″) |
| Gaia UNKNOWN (no usable star) | 28 | 35 (smaller 4′ field) |
| Flag overlay reconstruction | 100% | 100% (alpha) |
| Literal wording check (`not photometry`, `not a detection`, `adds no resolution`) | PASS | **FAIL 189/189** literally; PASS semantically. Different phrasing; label carries "not a detection" |
| Sathvik audit (183 frames) | 0 diffs, max Δλ 3.3e-10 µm | 0 diffs, max Δλ 3.2e-9 µm |
| Grid | 6′, 256 px, 1.406″/px, nearest | **4′**, 256 px, 0.9375″/px, bilinear (finite neighbours) |
| Stretch | asinh, p1–p99.5, softening 10, no offset | median offset subtracted, low −2σ, high p99.9, softening 4σ |
| `pytest backend/tests` (integration tests) | **217 passed, 9 skipped** | data+presets swapped: **3 collection errors** (A's data tests import `FrameInput`, `ArchiveError`). Without `tests/data`: **179 passed, 1 failed**. With Sagar's `tests/data` and `tools/ingest`: **253 passed, 1 failed** (Sagar's 74/74 pass; API 121/121; platform 58/59) |
| `/presets` (port 8030 vs 8031) | 5 presets; both cases `frames_available: true` | 5 presets, counts 34/44/34/35/36; both cases **`frames_available: false`** |
| `/presets/epsilon_indi_b/frames` | `ready`, 44 frames, 88/88 asset URLs return 200 PNG | **`partial`**, 44 frames, **0 images** (88 refs dropped, 94 warnings) |
| `…?case_id=fair_comparison` | `ready`, 3 frames, 6/6 assets 200 | **`missing`**, 0 frames |
| Live `/search` 330.84, −56.786 | 200, 24 of 460 obs, 2.1 s | 200, 24 of 460 obs, 2.0 s (search is API A's, not the processor's) |
| Live 3 × `/frame` | 3/3 200, 4.1–4.9 s; `flag_image.legend` present | 3/3 200, 2.4–4.6 s; **no `legend`**. Same keys, same status, same wavelength |
| Offline live-path processing, 183 cutouts | 5.92 s, 32 ms/frame, 0 errors | 8.67 s, 47 ms/frame, **1 error**: `UnsupportedData` on `l2b_retry` URL |
| Full preset build (5 presets + 2 cases, 189 records) | 10.9 s; rebuild is **byte-identical** to the committed 574 files | 11.4 s; PNGs byte-identical, JSON differs in the last float digits |
| Product size | 574 files: 378 PNG (2.97 MB) + 196 JSON (2.15 MB) = **5.12 MB** | 389 files: 378 PNG (4.28 MB) + 10 JSON (1.08 MB) = **5.36 MB** |
| Frontend `npm ci && npm test` | 38/38 (fixtures from API A examples; processor-independent) | same 38/38. Sagar records also pass `normalizeFrameRecord` (6 case + 183 preset) |

### Six case frames, A vs Sagar

The numbers below are taken from the case sets (`case-*/` for A, `sets/*.json` for Sagar).
- **Marker** is shown in display px, and as the offset in arcseconds from the grid centre, so the two scales can be compared.
- **v/a** means valid/adverse aperture pixels.
- **mjd** is identical in all six rows (Δ = 0).
- The **grid centre** is identical in all six rows: both use the manifest query centre.

| frame_key | ref | Δλ (S−A) µm | status, v/a A → S | marker A px → S px | Δ marker ″ (S−A) | scale ″/px A → S | PNG bytes A → S |
|---|---|---|---|---|---|---|---|
| 2026W18_1A_0516_1_D3 | fair A | −6.2e-10 | clear 19/0 → clear 19/0 | (127.08,128.57) → (126.62,128.85) | (−0.002,−0.002) | 1.406 → 0.9375 | 24 842 → 23 887 |
| 2026W39_2A_0597_4_D3 | fair B | +6.9e-10 | clear 18/0 → clear 18/0 | (125.91,129.29) → (124.87,129.94) | (+0.004,+0.002) | 1.406 → 0.9375 | 22 448 → 23 928 |
| 2026W18_1A_0516_1_D6 | fair C | −4.3e-10 | clear 20/0 → clear 20/0 | (127.08,128.57) → (126.62,128.85) | (−0.002,−0.002) | 1.406 → 0.9375 | 26 576 → 25 562 |
| 2025W35_1A_0008_1_D3 | moving A | −1.5e-9 | flagged 0/19 → flagged 0/19 | (127.80,130.61) → (127.70,131.92) | (+0.003,+0.005) | 1.406 → 0.9375 | 7 490 → 15 994 |
| 2026W12_1A_0610_2_D3 | moving B | +1.5e-9 | flagged 0/20 → flagged 0/20 | (128.12,126.43) → (128.18,125.65) | (−0.001,−0.001) | 1.406 → 0.9375 | 5 425 → 15 589 |
| 2026W34_1A_0431_1_D3 | moving C | −1.5e-9 | flagged 0/19 → flagged 0/19 | (128.36,123.34) → (128.54,121.01) | (0.000,−0.001) | 1.406 → 0.9375 | 7 354 → 15 683 |

Flag names are identical in every row.
- A additionally carries `screened_pixels`, `nonfinite_aperture_pixels` and `flag_counts`. In the moving_neighbor frames, A's `nonfinite_aperture_pixels` is 3/3/2 for A/B/C; Sagar's records don't carry it.
- Moving-neighbor marker motion is the same on the sky: 5.89″/10.25″ for A versus 5.90″/10.26″ for Sagar. It shows as 4.19/7.29 display px in A and 6.29/10.94 px in Sagar.
- Stretch limits differ by design:
  - fair-comparison shared: A 0.116..1.178, Sagar −0.071..4.525 after offset;
  - moving-neighbor shared: A 0.170..32.7, Sagar −0.46..998.6.

  `visual_pairs.png` shows A on the left and Sagar on the right, for fair A (top) and moving A (bottom).

## Incompatibilities (exact field or path)

Integration blockers, against the catalog (08), API (03) and frontend (01) as integrated:

1. **Case sets are at the wrong path.**
   - Sagar writes `presets/<preset>/sets/<case_id>.json`.
   - The catalog (`backend/platform/catalog.py`, `CASE_SET_PREFIX = "case-"`, `_set_name`) serves `?case_id=` only from `presets/<preset>/case-<case_id>/`.
   - Result: `GET /api/v1/presets/epsilon_indi_b/frames?case_id=fair_comparison` → `status: "missing"`, 0 frames. The same happens for moving_neighbor, and `/presets` reports `cases[].frames_available: false`.
   - The frontend (`PresetInvestigation.tsx`) then falls back to the per-frame-stretch records in the default listing. A fair comparison would silently lose its shared stretch.
2. **Asset IDs have no extension.** Sagar's IDs look like `epsilon_indi_b.2026W18_1A_0516_1_D3.fair_comparison.image.v1`. The catalog's `ASSET_ID_RE` (`catalog_assets.py`) requires `\.(png|json)$`, so `is_valid_asset_id(...)` is `False`. Every `image.src` and `flag_image.src` (`/api/v1/assets/<id>`) is dropped as "not an allowlisted PNG": 0 of 366 refs survive.
3. **The manifest `assets` map has the wrong shape and location.**
   - Shape: in `presets/manifest.json`, `assets` maps `{id: {path, sha256, bytes, media_type}}`. The catalog only registers aliases from `{id: "<relative path>"}` string values, and skips other values silently.
   - Location: the manifest sits at the presets root, so the catalog indexes it under the `shared` group. `add_alias` would refuse it anyway ("alias target belongs to another preset").
   - Fixing only I-2 is therefore not enough.
4. **The live path rejects `l2b_retry` archive files.**
   - Sagar's `backend/data/archive.py` `_SOURCE_URL_RE` requires `/l2b-…/` and `_spx_l2b-…`.
   - `ObservationDescriptor.from_public_dict` (called by `process_frame_for_api`) raises `UnsupportedData` for a real DR products URL such as `…/qr3/level2/2026W38_1A/l2b_retry-v27-2026-262/6/level2_2026W38_1A_0162_1D6_spx_l2b_retry-v27-2026-262.fits`. That is 1 of the 183 retained frames.
   - Through API A this becomes `UNSUPPORTED_DATA` for a valid frame. A's processor does not re-validate the URL; the API already allowlists it.
   - Sagar's `build_presets.py` does not hit this, because it builds descriptors directly.
5. **No `flag_image.legend`.** Sagar sends `flag_image.meaning` (a string) and draws a hatched magenta overlay of RGBA (230,40,200, alpha 200/70).
   - The frontend's `Plate.tsx` `FlagLegend` reads `flag_image.legend` (`{name: [r,g,b,a]}`). With Sagar's records it shows "this frame's processor did not supply a colour key".
   - Sagar also draws no separate non-finite category (A: `non_finite` = yellow).
6. **Test suite.**
   - A's `backend/tests/data/{test_archive,test_process,test_real_frames}.py` import `FrameInput`, `ArchiveError` and `ProcessedFrame`, which are absent in Sagar's package. They give 3 collection errors.
   - Sagar's `backend/tests/data/` imports the package as top-level `data` (it puts `backend/` on `sys.path`) and imports `check_registration` from `tools/ingest/`. Both have to come along.
   - `backend/tests/platform/test_platform_catalog.py::test_bundled_generated_products_serve_cleanly` fails on I-2 and I-3.
7. **Merge hazard.**
   - `git merge-tree` of PR #19 into integration gives add/add conflicts in `backend/data/{__init__,archive,process}.py`.
   - The product trees do not collide by path, so both would coexist. The default listing then prefers Sagar's root `presets/<p>/frames.json` (set `""` sorts before `frames`): every preset has 0 images, while the case listings still come from A. This was checked with `CatalogStore` on a merged content root.
   - PR #19 is based on `f2359c4`, so its diff view also shows deletions of `science/reviews/**`, `vercel.json` and `prompts/parallel/**`. A 3-way merge keeps those files, but reviewers should not read the PR diff as the change set.

Contract and content differences (not blockers, but would need decisions):

8. **Field of view.** Sagar's curated presets use a 4′ field (`registration.fov_arcmin: 4.0`, 0.9375″/px). `backend/content/targets.json` says `default_fov_arcmin: 6`, and the live API (and Sagar's own live path) use 6′. A user comparing curated and live frames would see two different scales. In A, both are 6′ at 1.406″/px.
9. **Missing record fields.**
   - Absent in `quality`: `screened_pixels`, `nonfinite_aperture_pixels`, `flag_counts`.
   - Absent at record level: `schema_version`, `sampled_position`, `preset_id`, `case_id`.
   - Today's frontend reads none of these (checked against `normalizeQuality` and the components). The science review uses them, and `preset_id` is the catalog's cross-preset guard.
10. **`frame_id`.** Sagar uses `frm_<sha16>` (a hash of the key, grid and version). A uses `frame_id == frame_key`. Both satisfy the contract. Evidence cards store `frame_id`, so cards made against one processor won't match the other.
11. **Differences the review checker had to bridge.** Each is marked `BRIDGE` in `check_sagar_acceptance.py`:
    - B1: layout;
    - B2: bilinear reconstruction;
    - B3: offset plus Sagar's asinh form and limit rule;
    - B4: the missing quality fields;
    - B5: coverage at pixel edges (Sagar) versus pixel centres (A's checker). No frame differs under the two rules;
    - B6: no `sampled_position`;
    - B7: hatched overlay;
    - B8: limitation wording. The literal phrases are absent; Sagar's equivalents are "not for measuring brightness", "does not add telescope resolution" and the marker label "(not a detection)".
12. **`display_scale.low/high` meaning.** In Sagar's records these are after subtracting `background_offset`, so they are not raw MJy/sr limits as in A. The frontend shows only `mode` and `method`, so nothing in the UI breaks, but anyone reading the numbers needs the offset.

## How this was produced (reproduce)

```bash
git fetch origin && git checkout codex/parallel-24-processor-compare
~/Library/Python/3.9/bin/uv venv --python /Users/sathvikloke/.local/bin/python3.12 .venv
~/Library/Python/3.9/bin/uv pip install --python .venv/bin/python -r backend/requirements-dev.txt
DATA=".../research/build_data"; SAGAR=<scratch>/sagar   # git archive origin/codex/sagar-data | tar -x -C $SAGAR
# 1. science
.venv/bin/python science/reviews/acceptance/check_acceptance.py --data-root "$DATA" --all --out /tmp/acc_A.json
.venv/bin/python coordination/processor-compare/check_sagar_acceptance.py --data-root "$DATA" \
    --products $SAGAR/backend/content/presets --out /tmp/acc_S.json --all
# 2. API: copy of this branch with backend/data and backend/content/presets replaced by Sagar's
#    (then also backend/tests/data and tools/ingest/* for the second test run), then
PERIGEE_DEV_MODE=1 .venv/bin/python -m uvicorn backend.main:app --port 8030
.venv/bin/python coordination/processor-compare/exercise_api.py http://127.0.0.1:8030 api_sagar.json   # A on 8031
# 3. frontend: cd frontend && npm ci && npm test   (+ a temporary vitest file feeding both processors'
#    records through normalizeFrameRecord / normalizePresetFrames; not committed)
# 4. numbers
.venv/bin/python coordination/processor-compare/compare_numbers.py --a backend/content/presets \
    --sagar $SAGAR/backend/content/presets --out numbers.json
.venv/bin/python coordination/processor-compare/bench_live_path.py --data-root "$DATA" --out bench_A.json  # and in the swapped copy
.venv/bin/python coordination/processor-compare/time_build_a.py --data-root "$DATA" --out <empty dir>
(cd $SAGAR && python tools/ingest/build_presets.py --raw "$DATA/raw")   # after emptying its presets dir
(cd $SAGAR && python tools/ingest/check_science_audit.py --science <sathvik-science:science/audit/frames.json>)
.venv/bin/python coordination/processor-compare/audit_compare_a.py <same frames.json>
```

Files here:
- `acceptance_{A,sagar}_all.json`: matrix plus compact evidence for all 189 records each;
- `api_{A,sagar}.json`: HTTP exercise;
- `numbers.json`: six case frames plus sizes;
- `bench_live_path_{A,sagar}.json`: live path over 183 cutouts;
- `visual_pairs.png`;
- the scripts above.

## Limitations

- **Shared-library independence only.** The Sagar acceptance run reuses the reviewer's helpers unchanged, but its reconstruction and stretch were written from Sagar's *stated* method. A 100% match shows that the products are what the records say. It does not show that bilinear interpolation or the offset are the better display choices.
- **Same trust base as worker 15's review.** Both runs share its header WCS, SIMBAD astrometry and Gaia controls.
- **Live calls depend on IRSA.** IRSA answered 503 on some first-attempt `/frame` calls, retried up to 3 times (`attempts` in `api_*.json`). Live timings are dominated by IRSA, so they are not a processor benchmark; use `bench_live_path_*`.
- **No browser rendering.** The frontend check is limited to its unit tests plus the normalizers fed with real records. The UI was not rendered with Sagar's products, which would show empty plates anyway (I-2).
- **Integration cost not measured.** It was estimated from the incompatibilities, not by doing the port.
- **Small samples.** The `l2b_retry` rejection (I-4) was seen on 1 of 183 retained files. How often live search returns such files was not measured.
