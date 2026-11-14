"""Shared fixtures for the data-adapter tests. Run from the repo root: pytest backend/tests/data"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

FIXTURES = Path(__file__).parent / "fixtures"

# Values recorded for these exact observations by the original data audit
# (research/build_data/manifest.json), used as independent expectations.
EPSINDB_OBS = "2026W18_1A_0516_1"  # archive obs_id; frame_key adds "_D3"
EPSINDB_URL = "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2026W18_1A/l2b-v27-2026-244/3/level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits"
EPSINDB_CENTER = (331.0966687831005, -56.80064917516836)
EPSINDB_AUDIT = {"wavelength_um": 2.3231684949226565, "bandwidth_um": 0.057709446476132534, "x": 28.582179681539483, "y": 28.67359758570705, "aperture_pixels": 19}
BARNARD_OBS = "2025W34_2B_0557_4"
BARNARD_URL = "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W34_2B/l2b-v27-2026-229/2/level2_2025W34_2B_0557_4D2_spx_l2b-v27-2026-229.fits"
BARNARD_CENTER = (269.4462585584787, 4.768324486236583)


@pytest.fixture(scope="session")
def epsindb_bytes() -> bytes:
    return (FIXTURES / "epsindb_2026W18_1A_0516_1D3.fits.fixture").read_bytes()


@pytest.fixture(scope="session")
def barnard_bytes() -> bytes:
    return (FIXTURES / "barnard_2025W34_2B_0557_4D2.fits.fixture").read_bytes()


@pytest.fixture(scope="session")
def sia_bytes() -> bytes:
    return (FIXTURES / "sia_qr3_barnard_trimmed.xml").read_bytes()


def drop_extension(data: bytes, name: str) -> bytes:
    """Synthetic variant for tests: the same real file with one extension removed."""
    from astropy.io import fits

    with fits.open(io.BytesIO(data)) as hdul:
        keep = fits.HDUList([h.copy() for h in hdul if h.name != name])
        buf = io.BytesIO()
        keep.writeto(buf)
        return buf.getvalue()


@pytest.fixture
def epsindb_target():
    from data import CatalogTarget

    return CatalogTarget("epsilon_indi_b", "Epsilon Indi B", 331.04414658852124, -56.78284419511611, 2000.0, 3981.977, -2466.832, "SIMBAD (test)", 270.658, None)


@pytest.fixture
def barnard_target():
    from data import CatalogTarget

    return CatalogTarget("barnards_star", "Barnard's Star", 269.4520769586187, 4.69336496657667, 2000.0, -801.551, 10362.394, "SIMBAD (test)", 546.9759, -110.11)
