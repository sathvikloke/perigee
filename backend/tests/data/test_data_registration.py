"""The registration check used for the curated sets recovers known offsets."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from conftest import EPSINDB_CENTER

from data.fits_io import open_cutout
from data.grid import GridSpec, resample_bilinear, source_pixel_coords

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "ingest"))
from check_registration import field_shift  # noqa: E402


@pytest.mark.parametrize("dra_arcsec,ddec_arcsec", [(0, 6), (4, -3), (1.5, 0)])
def test_injected_grid_offset_is_recovered(epsindb_bytes, dra_arcsec, ddec_arcsec):
    cut = open_cutout(epsindb_bytes)
    ra, dec = EPSINDB_CENTER
    g0 = GridSpec(ra, dec, 4, 256)
    g1 = GridSpec(ra + dra_arcsec / 3600 / np.cos(np.radians(dec)), dec + ddec_arcsec / 3600, 4, 256)
    ims = [resample_bilinear(cut.image, *source_pixel_coords(g, cut.wcs)) for g in (g0, g1)]
    yy, xx = np.mgrid[0:256, 0:256]
    dx, dy, _ = field_shift(ims[0], ims[1], (xx - 128) ** 2 + (yy - 128) ** 2 > 53**2)
    scale = g0.scale_arcsec_per_px
    assert dx * scale == pytest.approx(-dra_arcsec, abs=0.5)
    assert dy * scale == pytest.approx(-ddec_arcsec, abs=0.5)


def test_display_coordinates_put_north_up_east_left():
    g = GridSpec(100.0, 10.0, 4.0, 256)
    cx, cy = g.to_display_xy(100.0, 10.0)
    nx, ny = g.to_display_xy(100.0, 10.0 + 60 / 3600)  # 1 arcmin north
    ex, ey = g.to_display_xy(100.0 + 60 / 3600 / np.cos(np.radians(10)), 10.0)  # 1 arcmin east
    assert (cx, cy) == pytest.approx((128, 128))
    assert ny < cy and nx == pytest.approx(cx, abs=0.05)  # north is up (smaller y)
    assert ex < cx and ey == pytest.approx(cy, abs=0.05)  # east is left


def test_curated_sets_were_checked():
    """Every committed comparison set has a registration report under one native pixel."""
    root = Path(__file__).resolve().parents[2] / "content" / "presets"
    index = json.loads((root / "manifest.json").read_text())
    sets = [s for p in index["presets"] for s in p["comparison_sets"]]
    assert sets
    for s in sets:
        rep = json.loads((root / s["path"]).with_suffix(".registration.json").read_text())
        checked = [p for p in rep["pairs"] if p.get("field_shift_px") is not None]
        assert checked and all(p["field_shift_arcsec"] < 6.15 / 2 for p in checked)
