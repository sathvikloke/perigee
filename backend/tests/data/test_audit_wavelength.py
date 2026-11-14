"""audit_all's committed-vs-rebuilt wavelength comparison (PR #35 review).

The tolerance (1e-9 um) must absorb cross-platform float noise, still catch a
real change, and never let NaN/inf or a null mismatch pass as equal.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.ingest.audit_all import WAVELENGTH_TOL_UM, wavelength_differs  # noqa: E402

LAMBDA = 2.3231697654321  # a typical SPHEREx wavelength in um


def test_cross_platform_float_noise_passes():
    # Sagar measured up to ~3e-15 relative between macOS arm64 and Linux x86-64.
    for rel in (1e-16, 3e-15, 1e-13):
        assert not wavelength_differs(LAMBDA, LAMBDA * (1 + rel)), rel
    assert not wavelength_differs(LAMBDA, LAMBDA + 0.9 * WAVELENGTH_TOL_UM)
    assert not wavelength_differs(LAMBDA, LAMBDA)
    assert not wavelength_differs(2, 2.0)  # an int in JSON is still a number


def test_real_changes_are_reported():
    assert wavelength_differs(LAMBDA, LAMBDA + 1e-6)
    assert wavelength_differs(LAMBDA, LAMBDA - 1e-6)
    assert wavelength_differs(LAMBDA, LAMBDA + 2 * WAVELENGTH_TOL_UM)
    assert wavelength_differs(LAMBDA, 4.94)


def test_null_handling():
    assert not wavelength_differs(None, None)  # off-image in both: no wavelength
    assert wavelength_differs(None, LAMBDA)
    assert wavelength_differs(LAMBDA, None)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, "2.32", True, [2.32], {"v": 2.32}])
def test_non_finite_or_invalid_never_equal(bad):
    # abs(nan - x) > tol is False, so a naive check would call NaN "equal".
    assert wavelength_differs(bad, LAMBDA)
    assert wavelength_differs(LAMBDA, bad)
    assert wavelength_differs(bad, bad)
    assert wavelength_differs(bad, None)
