# Evidence (2026-11-14, branch codex/sagar-data)

| Check | Command | Result |
|---|---|---|
| Raw data reproducible from public URLs | `fetch_manifest.py` | 183/183 re-downloaded, all SHA-256 equal to the audit ledger |
| Unit tests (no network, no dataset) | `pytest backend/tests/data` | 74 passed |
| Same tests in a clean venv with only `backend/data/requirements.txt` | — | 74 passed |
| vs Sathvik's independent check (`science/audit/frames.json`) | `check_science_audit.py` | 183 frames: 0 differences in status, adverse counts, time; wavelength ≤ 3.2e-9 µm; predicted position 0.0″ |
| Case frames vs case JSON (board decision 6) | `check_cases.py` | 6/6 ok (fair_comparison A/B/C, moving_neighbor A/B/C) |
| Registration of case sets | `check_registration.py` | Field shift: Barnard A→B 0.35″, A→C 0.44″; Eps Ind B A→B 0.92″ (one native pixel is 6.15″). Method recovers injected 1.5–6″ offsets within 0.4″. Eps Ind B A↔C (different wavelength): target light center within 0.5–0.65″ of the marker in all three frames |
| vs processor-a (PR #11), same 183 files, 6′ grid | `compare_candidates.py` → `compare_processor_a.json` | frame_key, status, adverse and valid counts, time: all identical. Wavelength ≤ 3.2e-9 µm, marker ≤ 0.007 display px, image registration A vs B typically ≤ 0.1 px, coverage 0.886 both. Processing 70 vs 100 ms per frame; PNGs 15.7 vs 26.2 KB |
| Live gate 2 through API-A (PR #12) + this package | FastAPI TestClient on PR #12 with `backend/data` from this branch | Eps Ind A (330.84, −56.786): search 200 `ready`, 460 matches, 2.4 s → token → real cutout 3.7 s + processing 0.16 s → FrameRecord `2026W17_1B_0162_3_D1`, 25 KB. Tampered token → 400 INVALID_FRAME_TOKEN. PR #12's 121 tests pass |
| Live smoke | `live_smoke.py` → `live_smoke.json` | M13 (not a preset): `ready`, 448 matches, 3 frames processed. Official WISE 0855 coordinate: `ready`, 255 matches, 3 frames `clear` |
| IRSA reliability | 8 searches with retries | 7 `ready`, 1 `partial` (one collection still failing after 4 tries). Raw SIA: ~50% of requests got 502 |

Review images: `fair_comparison.png/.gif`, `moving_neighbor.png/.gif` (cyan circle = catalog
prediction; hatched = adverse flags; dark green = no data).
