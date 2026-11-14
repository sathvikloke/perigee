# science/

Sathvik's scientific validation workspace. These tools are independent checks, not the app's processing pipeline (`backend/data/**`, owned by Sagar).

| File | Purpose |
|---|---|
| `INTEGRATION_BOARD.md` | Current verified state, binding decisions and per-owner handoffs |
| `CASE_SELECTION.md` | Why each case frame was chosen and how it was verified |
| `check_frames.py` | Re-derives time, predicted position, wavelength and flag screen for every retained FITS file. Writes `audit/frames.json`. |
| `check_registration.py` | Reprojects a case's frames to one fixed north-up grid and checks control-star stability. Writes `audit/registration_<case>.json` and `.png`. |
| `audit/` | Small JSON/PNG outputs: no FITS, no image arrays |

Requires the local dataset in `research/build_data/` (only Sathvik and Sagar have it) and the research venv with astropy, numpy, scipy and matplotlib.

A `clear` screen means no problem flags in a small circle around a catalog-predicted position. It is not a detection, calibrated photometry or astrometric validation.
