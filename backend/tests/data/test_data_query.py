"""Input rules from docs/INTEGRATION_CONTRACT.md "Query request"."""
import math

import pytest

from data import InvalidCoordinates, InvalidFieldOfView, InvalidRequest, SearchQuery


def test_defaults_and_normalised_values():
    q = SearchQuery.validated(10.5, -20)
    assert (q.ra_deg, q.dec_deg, q.fov_arcmin, q.limit) == (10.5, -20.0, 6.0, 24)
    assert q.collection_ids == ("spherex_dr1", "spherex_qr3")


@pytest.mark.parametrize("ra", [360.0, -0.001, math.nan, math.inf, "12", None, True])
def test_bad_ra_rejected_not_clipped(ra):
    with pytest.raises(InvalidCoordinates):
        SearchQuery.validated(ra, 0)


@pytest.mark.parametrize("dec", [90.0001, -91, math.nan, "4.7abc"])
def test_bad_dec_rejected(dec):
    with pytest.raises(InvalidCoordinates):
        SearchQuery.validated(10, dec)


def test_boundaries_accepted():
    assert SearchQuery.validated(0, -90).dec_deg == -90
    assert SearchQuery.validated(359.999, 90).ra_deg == 359.999


@pytest.mark.parametrize("fov", [1.99, 10.01, 0, -5, math.nan, "6"])
def test_field_of_view_bounds(fov):
    with pytest.raises(InvalidFieldOfView):
        SearchQuery.validated(10, 10, fov_arcmin=fov)


@pytest.mark.parametrize("limit", [0, 49, 2.5, True])
def test_limit_bounds(limit):
    with pytest.raises(InvalidRequest):
        SearchQuery.validated(10, 10, limit=limit)


def test_collections_come_from_allowlist():
    assert SearchQuery.validated(10, 10, collection_ids=["spherex_qr3"]).collection_ids == ("spherex_qr3",)
    for bad in (["spherex_qr3", "https://evil.example/x"], [], ["SELECT *"]):
        with pytest.raises(InvalidRequest):
            SearchQuery.validated(10, 10, collection_ids=bad)
