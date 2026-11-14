# tools/ingest: data tools (owner: Sagar)

All commands run from the repo root. The raw data stays outside the repo (e.g. `../perigee-data/raw`).

| Script | What it does |
|---|---|
| `fetch_manifest.py --out ../perigee-data/raw` | Re-download all 183 audited cutouts from IRSA and verify each against the ledger SHA-256 |
| `build_presets.py --raw ...` | Build `backend/content/presets/` (all five presets plus the two case sets) |
| `check_registration.py --raw ...` | Field-star registration check for the case sets |
| `check_cases.py --cases backend/content/cases` | Board decision 6: case frames vs the case JSON (wavelength to 1e-4 µm, date, quality) |
| `check_science_audit.py --science science/audit/frames.json` | All 183 frames vs Sathvik's independent science check |
| `compare_candidates.py --other <processor-a process.py> --raw ...` | Run another processor candidate on the same files and compare numbers |
| `make_previews.py` | Review images and blink GIFs for the case sets (`evidence/`) |
| `make_fixtures.py --raw ... --sia ...` | Rebuild the small real-data test fixtures |
| `live_smoke.py` | Bounded live run: search plus 3 frames at M13 and at the official WISE 0855 coordinate |

See `evidence/README.md` for the recorded results.
