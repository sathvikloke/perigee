# Staged investigations and the case admission path (N7)

**Nothing in this folder is shipped.** `backend/content/**` is unchanged. A staged case moves into `backend/content/` only after science-owner approval and a reviewed frontend integration (owned by Codex).

This folder holds:

- **`wise_0855_quality_trap/`:** the candidate third investigation, "A dot that jumps". It is built from the reviewed transfer exercise (`science/reviews/transfer-exercise/`).
- **This README:** the admission process, the admission result and the accepted, repaired and rejected conditions.

The validator is `tools/ingest/admit_case.py`, with its tests in `backend/tests/data/test_admit_case.py`.

## The authoring and admission path

This is a repeatable authoring process for a person with the retained data. It is not a self-service authoring UI, an automatic source-discovery pipeline or a scheduled source of new lessons.

1. **Choose already-retained frames.** Every frame must already be a shipped preset record; no new raw data is downloaded.
2. **Run a science check that writes its numbers to a file,** for example `science/reviews/transfer-exercise/check_transfer.py`. It writes `results.json` and `answer_evidence.json`. Every number the case quotes then has a registry entry with a tolerance.
3. **Write `case.json` in the existing case schema.** No additive field was needed.
4. **Generate the case product set with the existing ingest tool:**
   ```sh
   .venv/bin/python -m tools.ingest.ingest case <case_id> --data-root "$DATA" \
       --targets backend/content/targets.json --case-file science/staging/<case_id>/case.json \
       --out science/staging/<case_id>/presets --report science/staging/<case_id>/ingest_report.json
   ```
5. **Link each conclusion to answer-evidence ids** in `evidence_map.json`. This is staging only and is not served.
6. **Run the admission check:**
   ```sh
   .venv/bin/python -m tools.ingest.admit_case science/staging/<case_id>/case.json \
       --products-root science/staging/<case_id>/presets \
       --evidence-map science/staging/<case_id>/evidence_map.json [--data-root "$DATA"]
   ```
   Exit 0 means admitted (no failing check). Warnings name what the tool could not verify.

### What `admit_case.py` checks

Each check returns pass, warn or fail with specific reasons.

| Check | What fails it |
|---|---|
| `structure` | a missing case field; an invalid case_id or target; a duplicate ref; an evidence ref that is not a frame; a step `check` path missing from the records |
| `frame_references` | a frame_key with no record in `<products>/<target>/case-<case_id>/`; a frame_key that is not `<observation_id>_D<detector>`; a record that belongs to another case or ref; a missing image or overlay asset |
| `provenance` | `source_url`, collection or SHA-256 differs from the record or from the shipped preset record; a non-https source; a manifest mismatch (with `--data-root`) |
| `metadata_agreement` | date, MJD (1e-8 d), wavelength or band width (1e-4 µm) or expected quality status differs from the record |
| `quoted_numbers` | a quoted wavelength (to its quoted precision), a date ("7 and 10 November 2025", "April 29", "2025-11-07") or an "N of M pixels" count matches no record. With an evidence registry, any unit-bearing number (arcsec, display/native px, days, %, band widths, MJy/sr, light-years) that matches no record-derived pair quantity or registry entry also fails. Without a registry, those numbers are listed as unverified warnings |
| `confounds` | a confound present in the data (time; wavelength more than half a band width apart; different stretches; a flagged frame) is never named in the questions or hints; different pipeline builds or collections are never mentioned |
| `display_claims` | a "share a stretch" claim whose frames have different `display_scale` limits; an "own stretch" claim for a frame that shares limits; a grey-level example that disagrees with the asinh stretch formula by more than 1; different stretches the learner is never told about; a claimed shared grid with different `grid_id`s |
| `quality_interpretation` | a quoted flag name that is not in the SPHEREx flag vocabulary seen in records; non-finite screened pixels that are never explained; a flagged frame whose flags are never named; a feature presented as proof of a specific physical cause ("is a cosmic ray", "flags prove …"), outside the not-supported list |
| `identity_and_prediction` | a marker that is not a `catalog_prediction`; a marker display requirement without "prediction"; a marker described as a detection or measurement (outside the not-supported list); the target asserted as identified when the evidence says `not_identified` |
| `answer_key` | an empty supported or not-supported list; a not-supported item without a reason; no resolvable evidence file. With an evidence map, any conclusion not mapped to existing answer-evidence ids also fails |
| `no_new_dependencies` | a frame that is not an already-retained or shipped cutout; a non-PNG/JSON or oversized product file; a secret-like string or signed URL; an opaque model dependency in the learner text or sources |
| `catalog_integration` | the backend `CatalogStore` cannot load the case or serves its frames as anything other than `ready` with resolvable assets. It runs in a temporary copy of the content root when the products are staged |

**Limits.** The text checks are deliberate heuristics, aimed at the specific failure modes N7 names. They are not a natural-language proof. For example, numbers written as words ("six months") are not checked. Without an evidence registry, the external values in a shipped case (for example "10.4 arcseconds per year" from Gaia) are reported as unverified, not verified. Per-conclusion evidence links can be checked only when an evidence map exists. The two shipped cases have case-level evidence files only.

## Admission results (2026-11-15)

Exact command outputs are reproduced by `pytest backend/tests/data/test_admit_case.py` and the commands above.

| Case | Verdict | Warnings (non-blocking) |
|---|---|---|
| `fair_comparison` (shipped) | **admit** | 5 external unit-bearing numbers not tied to records (12 light-years, 0.7″ Ba/Bb, 6.7′ to Eps Ind A, 0.65 px registration offset, 0.5″ parallax). Two `verification` references do not exist in this tree (`science/CASE_SELECTION.md`, `science/check_frames.py`) |
| `moving_neighbor` (shipped) | **admit** | 10 external numbers unverified (10.4″/yr Gaia proper motion, 6 light-years, …). The questions never literally ask about a "cause". Three `verification` references do not exist in this tree |
| `wise_0855_quality_trap` (staged) | **admit** | status is `staged_candidate` (not approved for shipping) |

For the staged case, all 30 quoted numbers and date mentions were matched under the strict registry, with zero unverified (report: `wise_0855_quality_trap/admission_report.json`). All three grey-level examples match the stretch formula. The checker also confirmed:

- stretch groups `[[A, B], [C]]`;
- one grid, `f448bdf044c35cf1`;
- all 16 conclusions mapped to evidence ids;
- the CatalogStore serves 3 frames with status `ready`.

The test suite also feeds deliberately broken copies to the validator. Each copy fails on the intended check:

| Broken copy | Check that fails |
|---|---|
| wrong frame_key | `frame_references` |
| wrong quoted wavelength (2.522 µm) | `quoted_numbers` |
| wrong quoted date (April 2026; 12 November 2025) | `quoted_numbers` |
| wrong frame wavelength | `metadata_agreement` |
| false "A, B and C share one stretch" | `display_claims` |
| wrong grey level | `display_claims` |
| missing not-supported list | `answer_key` |
| not-supported item without a reason | `answer_key` |
| an unmapped conclusion | `answer_key` |
| "the marker shows where … was detected" | `identity_and_prediction` |
| "Detected position" as the marker requirement | `identity_and_prediction` |
| "the dot … is WISE 0855" | `identity_and_prediction` |
| "it was a cosmic ray" | `quality_interpretation` |
| an unknown flag name | `quality_interpretation` |
| quality words scrubbed from a flagged case | `confounds` |
| a signed URL | `no_new_dependencies` |
| an unretained SHA-256 | `no_new_dependencies` and `provenance` |
| a missing product set | `frame_references` and `catalog_integration` |

## Accepted, repaired and rejected conditions

### Accepted

- **WISE 0855 P/Q/R (A/B/C) as a third investigation.** It exposes a trap the taught cases do not: a flagged detector pixel that *appears to move* between two matched-wavelength frames while the stars stay put. That is a convincing false positive, and its refusal can be traced to flags, morphology, detector position and pointing.
  - **Target-identity trap:** a catalogued field star sits near the prediction marker.
  - **Honest negative:** P/R cannot test WISE 0855's motion.

  All frames are already shipped and retained, and processor A reproduces their PNG bytes.
- **Shared stretch for A/B, own stretch for C (staging decision).** The existing ingest rule (`shared_groups_for_case`: same detector and Δλ below the band width) puts P and Q on one shared stretch when staged as a case. The case adopts that default:
  - The brightness trap in the guided case is A/B versus C. C has its own stretch, so grey 159 in A and B against 177 in C for 1.0 MJy/sr.
  - The unguided preset exercise keeps the per-frame "Q looks lighter" trap.

  This needs no additive schema field and no ingest change, and `admit_case.py` validates the shared and own claims and grey examples against the products. The rejected alternative is described below.

### Repaired during admission

- **"Absent from R" used as detector evidence.** R's cutout does not contain detector pixel (1709, 1364), as confirmed by the N2 controls (`origin/claude/n2-controls` @ `45ee56b`, `B_features.csv`). Absence from R is now only a statement about the sky.
- **Leading question.** "Does C's sky look a little lighter?" was false under the case stretch (background greys 19, 16, 19). It was replaced with a neutral question.
- **Imprecise wavelength.** "Extremely faint near 1.25 µm" in the background was replaced with the frame wavelengths (1.257 and 1.444 µm) plus a J-band reference.
- **Brightness explanation.** It now says that the per-frame stretch changes grey levels and that the shared stretch reverses the background order (N2). The small physical difference has no established cause, and "only the stretch" is listed as not supported.
- **A validator false positive, fixed in the validator.** The FITS extension name "FLAGS" in a limitation was read as a flag name. It was added to the non-flag allowlist (as were `IMAGE` and `VARIANCE`); the case text did not change.
- **The seven N1 answer-key defects:** see `science/reviews/transfer-exercise/README.md` → Second review pass.

### Rejected

- **Per-frame stretch for P/Q inside the guided case.** It would need either an additive field (for example `display_requirements.stretch_groups`) or a change to the ingest grouping rule. Both are outside this package's ownership. The shared default is also the fairer comparison. Not adopted.
- **R Draconis (kept from B5; no new evidence).** All 35 covered frames are saturated and flagged at the star (BLOOM, OVERFLOW, mostly non-finite pixels). The only defensible answer is "cannot tell". Its `confounds` and `quality_interpretation` conditions could be written, but the case would test nothing else.
- **RW Aurigae (kept from B5; no new evidence).** 32 of 35 frames are flagged at the target, with only 1 clear frame. There is no clean same-wavelength pair to anchor the reasoning.
- **Any claim that WISE 0855 is detected, absent or moving in these frames.** The answer evidence gives `target_identity.status = not_identified`, and the validator rejects text that asserts otherwise.

## Integration handoff for Codex (`wise_0855_quality_trap`)

**Additive schema field: none.** The case uses only fields already present in the shipped cases. `display_requirements.flag_overlay` is already used by `fair_comparison`; it is absent from `frontend/src/api/types.ts`, but extra fields are preserved. `status` is `staged_candidate` and must be changed only on approval.

**Files to copy when approved** (no regeneration needed; the ingest products regenerate byte-identically):

| From | To |
|---|---|
| `science/staging/wise_0855_quality_trap/case.json` | `backend/content/cases/wise_0855_quality_trap.json` |
| `science/staging/wise_0855_quality_trap/presets/wise_0855/case-wise_0855_quality_trap/` (3 PNG, 3 flags PNG, 3 JSON, `frames.json`) | `backend/content/presets/wise_0855/case-wise_0855_quality_trap/` |

- **`targets.json`:** optionally add `"wise_0855_quality_trap"` to `wise_0855.case_ids`. CatalogStore also discovers the case through `target_id`, and changing `targets.json` changes its content version.
- **After copying:** re-run `admit_case.py backend/content/cases/wise_0855_quality_trap.json` with no `--products-root`, and re-run the catalog and Cloudflare content builds.

**Frames and assets:**

| Ref | frame_key | Asset ids (`/api/v1/assets/…`) | Stretch | Quality at marker |
|---|---|---|---|---|
| A | `2025W45_2A_0278_1_D2` | `wise_0855.case-wise_0855_quality_trap.2025W45_2A_0278_1_D2.png`, `….flags.png` | shared A+B, asinh 0.2319–2.6719 MJy/sr | clear (0/20) |
| B | `2025W46_1A_0108_1_D2` | `wise_0855.case-wise_0855_quality_trap.2025W46_1A_0108_1_D2.png`, `….flags.png` | shared A+B | flagged PERSIST (2/19) |
| C | `2026W20_1A_0214_1_D2` | `wise_0855.case-wise_0855_quality_trap.2026W20_1A_0214_1_D2.png`, `….flags.png` | own, 0.2070–2.2294 MJy/sr; label "Brightness not directly comparable" | clear (0/19) |

Grid `f448bdf044c35cf1`, processor `perigee-processor-a/0.1.2`. The flag overlays are byte-identical to the shipped preset overlays. C's image PNG is byte-identical to the shipped preset PNG; A's and B's differ because of the shared stretch.

**UI requirements (frontend work, not done here):**

- **First frame:** the case opens on ref A (the existing `PresetInvestigation` behaviour). The default pair comes from `must_include_refs_any_of` `[A, B]`.
- **Flag overlay:** "Show flagged pixels" must be reachable for A, B and C in steps 2 and 3. The flagged dots are away from the marker, so the marker's quality chip alone does not reveal them. Use `flag_image.legend`. A missing overlay must not read as "no flags" (F3).
- **Marker:** label the marker "Catalog prediction (not a detection)". No guide line: the A→B shift is 0.04 display px and A→C is 2.9 px.
- **Stretch label:** C must carry a "Brightness not directly comparable" label. A and B share one stretch and must load the `case-wise_0855_quality_trap` products, never the per-frame preset products (F4).
- **Feature locations** (display px, for optional hint highlighting):
  - jumping dot A (114.9, 82.9) and B (117.9, 80.6);
  - A-only dot (32.4, 111.8);
  - dot near the marker about (132.4, 125.4);
  - marker about (127.1, 128.1) in A and B, (130.1, 127.8) in C.
- **Evidence card:** the per-frame fields as listed in `evidence_requirements.card_must_show_per_frame`. The learner's claim must stay distinguishable from `conclusion_guide`.

**Not verified here:** this case was not driven in a browser, and the live API does not serve it.
