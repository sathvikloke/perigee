# Overnight science/backend ledger (N1–N9)

- **Assignment:** `coordination/claude-overnight-science-backend.md` (copied unchanged; SHA-256 `53a603c077b04dac…`; source: Codex's `codex/overnight-backend-handoff` @ `da39ffd`).
- **Branch:** `claude/overnight-science-backend`, from `origin/main` @ `0ffff6f` (PR #48 merge; PRs #47 and #48 merged).
- **Started:** 2026-11-15 ~02:55 UTC by the coordinator Claude session.
- **Environment:** coordinator `.venv`: Python 3.12.16, astropy 8.0.2, numpy 2.5.4, pillow 13.0.0, fastapi 0.163.0; Node 26 locally, Node 22 in CI; Wrangler 4.162.0.
- **Inventory (verified):**
  - 183 raw cutouts under `research/build_data/raw`;
  - 183 preset frame records;
  - 6 case records, which are case-stretch copies of preset frames, not new observations.
- **Rules:** no `frontend/**` edits, no deploy, no merge to main; Codex owns UI and the final release.

## Status

| ID | Acceptance criterion (short) | Status | Evidence (files, commits) | Next action / blocker |
|---|---|---|---|---|
| N1 | Seven answer-key defects fixed; candidate reviewed; regenerates | not started | — | — |
| N2 | Stretch, flag, wavelength, positive-motion and information-removal controls reproducible | **done (reviewed)** | `science/reviews/overnight-controls/` (worker `45ee56b`, merged). Coordinator re-ran `run_controls.py` into a fresh directory: identical except `manifest.json` (timestamp/runtime). Independently checked: grey probes 1.0 MJy/sr → 156/174 per-frame, 159/159 shared; the flagged pixel's P→Q sky jump is **5.36″** (values 234.55/237.91 MJy/sr), recomputed from the raw FITS with the cutout WCS. Negative results recorded (3 strict field stars; R doesn't contain the detector pixel; Barnard proxy spread up to 2.0 px / 21°; Q/P physical median 0.971 with no cause established) | answer-key implications sent to the N1 worker |
| N3 | Selection, exclusion and unknown audit; negative registration control | **done (reviewed + defect fixed)** | `science/reviews/registration-audit/` (worker `e46c5bd`, merged; coordinator re-ran it with 0 diffs and 15 → 16 tests passing). **Defect fixed** (`8037100`): `check_acceptance` 'registration' read True for 2–5 px shifted-header fixtures. It now has an independent `astrometry` column (WCS-free regcheck): PASS 133 / UNKNOWN 56 / FAIL 0 of 189 (unique: 128/55), in the gate, which stays green. A failing-first test fails on the old script. fair_comparison C stays UNKNOWN (relative same-exposure check to A agrees to 0.15″; not independent). Barnard: marker, glow proxy and field-star residuals are separated | — |
| N4 | UI handoff with exact case/evidence fixtures and failure-state fixtures | in progress | `qa/ui-fixtures/make_fixtures.mjs` produces failure fixtures from the real Worker code (fault-injected assets): missing overlay (404 ASSET_NOT_FOUND), case unavailable (503), unknown case (404), live origin down (curated 200, proxied 502), no coverage (real record `2025W17_4B_0077_2_D1`), plus pointers to the existing partial/empty/expired/invalid examples | changed-FOV and stale-selection fixtures from the N5 worker; case and evidence fixtures from N1 |
| N5 | Route-to-processor parity; request-geometry identity tuple | not started | — | — |
| N6 | Faults/resources measured; origin state; release handoff | in progress | **Origin check (once, 04:00Z):** GitHub Vercel status on `main` `0ffff6f` = success (03:26Z). `GET perigee-liard…/api/v1/health` = ok, `token_signing: env`. One search (83.822, −5.391, limit 1) returns the **corrected B4 wording**, so the Python origin now runs code including PR #47 (the quota reset); it is no longer `058a2a6`. | worker measuring local faults; coordinator writes the release handoff |
| N7 | Admission validator exercised on the candidate | not started | — | needs N1 |
| N8 | Award evidence, claims registry, story | not started | — | after N1–N7 results |
| N9 | Integrated review, exact-head CI, PR, final handoff | not started | — | last |

## Workers

| Worker | Ownership (disjoint) | Branch | Status |
|---|---|---|---|
| N2 controls | `science/reviews/overnight-controls/**` | `claude/n2-controls` | **done**, `45ee56b`, merged and reviewed |
| N1+N7 case | `science/reviews/transfer-exercise/**`, `science/staging/**`, `tools/ingest/admit_case.py`, `backend/tests/data/test_admit_case.py` | `claude/n1-n7-case` | running |
| N3 audit | `science/reviews/registration-audit/**`, `science/reviews/acceptance/**` (negative control only) | `claude/n3-registration-audit` | **done**, `e46c5bd`, merged; acceptance fix by the coordinator |
| N5+N6 backend | `backend/**` (fixes only for demonstrated defects), new API/platform tests, `cloudflare/**` (defects only), `qa/overnight-backend/**` | `claude/n5-n6-backend` | running |
| Coordinator | ledger, `coordination/overnight-*.md`, N4 fixtures, integration | this branch | active |

## Resume block

- **Head:** see `git log -1`.
- **Next:** launch the workers, then the N6 origin check.
