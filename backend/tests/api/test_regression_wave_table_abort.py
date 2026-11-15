"""Regression (N6): a WCS-WAVE lookup table whose index vector is not strictly
monotonic (e.g. a zeroed table data block, [0, 0, ...]) made astropy 8.0.2 /
wcslib abort the whole Python process (SIGABRT) inside ``WCS(..., key="W")``.

On the live path that kills the serverless function instead of returning a JSON
envelope (and any other request sharing the process). The processor must reject
such a table *before* wcslib sees it and report the wavelength as unavailable,
exactly like any other unusable spectral WCS.

The route call runs in a child process, so a regression shows up as a failed
assertion on the child's exit status instead of killing pytest.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
import synthetic as syn  # noqa: E402

DATA_ROOT = os.environ.get("PERIGEE_DATA_ROOT")
RAW_REL = "raw/epsilon_indi_b/level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits"

# Child: POST /api/v1/frame through the real route + processor A, upstream = the file.
CHILD = r"""
import json, sys
from dataclasses import replace
import httpx
from fastapi.testclient import TestClient
from backend.main import app
from backend.routes import _adapters
from backend.routes._adapters import resolve_services
from backend.tests.api.conftest import Harness
from backend.tests.api.test_frame import make_token

data = open(sys.argv[1], "rb").read()
obs, det, ra, dec = sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
h = Harness()
h.processor, _ = _adapters.processor_a_adapter()
h.settings = replace(h.settings, frame_fetch_max_bytes=24 * 2**20, frame_budget_s=40.0)
h.fetch_handler = lambda req: httpx.Response(200, content=data, headers={"content-type": "application/fits"})
app.dependency_overrides[resolve_services] = h.services
client = TestClient(app, raise_server_exceptions=False)
url = ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/x/l2b-v27-2026-244/%d/"
       "level2_%sD%d_spx_l2b-v27-2026-244.fits" % (det, obs, det))
tok = make_token(ra_deg=ra, dec_deg=dec, observation_id=obs, detector=det, frame_key="%s_D%d" % (obs, det),
                 source_url=url)
r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": tok})
print(json.dumps({"status": r.status_code, "body": r.json()}))
"""


def run_route_in_child(tmp_path: Path, data: bytes, obs: str, det: int, ra: float, dec: float) -> dict:
    p = tmp_path / "cutout.fits"
    p.write_bytes(data)
    r = subprocess.run(
        [sys.executable, "-c", CHILD, str(p), obs, str(det), repr(ra), repr(dec)],
        cwd=REPO, capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, f"child process died (rc={r.returncode}); stderr tail: {r.stderr[-400:]}"
    return json.loads(r.stdout.strip().splitlines()[-1])


def with_wave_index(raw: bytes, x=None, y=None) -> bytes:
    with fits.open(io.BytesIO(raw)) as h:
        hl = fits.HDUList([hdu.copy() for hdu in h])
    t = hl["WCS-WAVE"].data
    if x is not None:
        t["X"][...] = x
    if y is not None:
        t["Y"][...] = y
    buf = io.BytesIO()
    hl.writeto(buf)
    return buf.getvalue()


def assert_wavelength_unavailable_not_crash(out: dict) -> None:
    assert out["status"] == 200, out
    f = out["body"]["frame"]
    assert f["wavelength_um"] is None and f["bandwidth_um"] is None
    assert any(n.startswith("Wavelength unavailable") for n in f["quality"]["notes"]), f["quality"]["notes"]
    # The rest of the frame is still produced from the intact IMAGE/FLAGS/VARIANCE data.
    assert f["quality"]["status"] in ("clear", "flagged")
    assert f["image"]["src"].startswith("data:image/png;base64,")


@pytest.mark.parametrize(
    "x,y",
    [(0, None), (None, 0), (0, 0), (np.array([5, 5], dtype=np.int32), None)],
    ids=["x_zero", "y_zero", "both_zero", "x_repeated"],
)
def test_non_monotonic_wave_index_does_not_abort_the_process(tmp_path, x, y):
    raw = with_wave_index(syn.make_fits(), x=x, y=y)
    ra, dec = syn.CENTER
    out = run_route_in_child(tmp_path, raw, "2099W01_1A_0001_1", 3, ra, dec)
    assert_wavelength_unavailable_not_crash(out)


def test_valid_wave_tables_are_unaffected(tmp_path):
    ra, dec = syn.CENTER
    out = run_route_in_child(tmp_path, syn.make_fits(), "2099W01_1A_0001_1", 3, ra, dec)
    assert out["status"] == 200
    assert out["body"]["frame"]["wavelength_um"] == pytest.approx(syn.wavelength_at_native(29.5), abs=1e-6)
    # A strictly decreasing index is valid for wcslib and must keep working.
    out = run_route_in_child(
        tmp_path, with_wave_index(syn.make_fits(), x=np.array([2049, 1], dtype=np.int32)), "2099W01_1A_0001_1", 3, ra, dec
    )
    assert out["status"] == 200 and out["body"]["frame"]["wavelength_um"] is not None


@pytest.mark.skipif(not DATA_ROOT or not (Path(DATA_ROOT) / RAW_REL).is_file(), reason="needs PERIGEE_DATA_ROOT")
def test_retained_cutout_with_zeroed_wave_table_block(tmp_path):
    """The original finding: the real Eps Ind B cutout with its last 2880-byte block (the
    WCS-WAVE table data) zeroed, as a damaged transfer could leave it."""
    raw = (Path(DATA_ROOT) / RAW_REL).read_bytes()
    damaged = raw[:-2880] + b"\0" * 2880
    out = run_route_in_child(tmp_path, damaged, "2026W18_1A_0516_1", 3, 331.0966687831005, -56.80064917516836)
    assert_wavelength_unavailable_not_crash(out)
