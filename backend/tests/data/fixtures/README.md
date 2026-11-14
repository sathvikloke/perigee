# Data-adapter test fixtures

All files here come from real NASA/IRSA SPHEREx archive products unless marked synthetic.
Regenerate with `tools/ingest/make_fixtures.py`.

| File | Source | Change from original |
|---|---|---|
| `epsindb_2026W18_1A_0516_1D3.fits.fixture` | DR1 Level 2 cutout, Epsilon Indi B field, 2026-04-29, detector 3 (`research/build_data/manifest.json`, sha256 of original listed there) | EPSF and ZODI extensions removed; IMAGE, FLAGS, VARIANCE, WCS-WAVE untouched |
| `barnard_2025W34_2B_0557_4D2.fits.fixture` | DR1 Level 2 cutout, Barnard's Star field, 2025-08-24, detector 2 | same trimming |
| `sia_qr3_barnard_trimmed.xml` | IRSA SIA v2 response, `spherex_qr3`, circle around Barnard's Star, fetched 2026-11-14 | only the first 6 of 124 rows kept |

The extension is `.fits.fixture` because `*.fits` is git-ignored for the raw dataset.
Tests that need broken or missing data build those variants in code (see `conftest.py`) and
never present them as real observations.
