"""Offline checks for backend/data/archive.py (injected transport; no network)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.data.archive import (  # noqa: E402
    ArchiveError,
    cutout_url,
    fetch_cutout,
    is_allowed_url,
    parse_sia_votable,
    search_spherex,
    sia_url,
)

GOOD = "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2026W18_1A/l2b-v27-2026-244/3/level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits"

VOTABLE = b"""<?xml version="1.0" encoding="utf-8"?>
<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
 <RESOURCE type="results"><TABLE>
  <FIELD name="obs_id" datatype="char" arraysize="*"/>
  <FIELD name="energy_bandpassname" datatype="char" arraysize="*"/>
  <FIELD name="dataproduct_type" datatype="char" arraysize="*"/>
  <FIELD name="access_url" datatype="char" arraysize="*"/>
  <FIELD name="obs_collection" datatype="char" arraysize="*"/>
  <FIELD name="t_min" datatype="double"/>
  <DATA><TABLEDATA>
   <TR><TD>2026W39_2A_0597_4</TD><TD>SPHEREx-D3</TD><TD>image</TD><TD>https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/x/3/b.fits</TD><TD>spherex_dr1</TD><TD>61310.3</TD></TR>
   <TR><TD>2026W18_1A_0516_1</TD><TD>SPHEREx-D3</TD><TD>image</TD><TD>""" + GOOD.encode() + b"""</TD><TD>spherex_dr1</TD><TD>61159.5</TD></TR>
   <TR><TD>evil</TD><TD>SPHEREx-D1</TD><TD>image</TD><TD>https://example.com/x.fits</TD><TD>spherex_dr1</TD><TD>61000</TD></TR>
  </TABLEDATA></DATA>
 </TABLE></RESOURCE>
</VOTABLE>"""

HTML_502 = b"<!DOCTYPE HTML PUBLIC><html><head><title>502 Proxy Error</title></head><body>Proxy Error</body></html>"


def fake(responses):
    calls = []

    def transport(url, timeout, max_bytes):
        calls.append(url)
        for key, resp in responses.items():
            if key in url:
                if isinstance(resp, Exception):
                    raise resp
                return resp
        raise AssertionError(f"unexpected url {url}")

    transport.calls = calls
    return transport


def test_url_allowlist():
    assert is_allowed_url(GOOD)
    assert not is_allowed_url(GOOD.replace("https://", "http://"))
    assert not is_allowed_url(GOOD.replace("irsa.ipac.caltech.edu", "irsa.ipac.caltech.edu.evil.com"))
    assert not is_allowed_url("https://irsa.ipac.caltech.edu/ibe/data/spherex/../../etc/passwd.fits")
    assert not is_allowed_url(GOOD + "?center=1,2&size=0.1")
    assert is_allowed_url(GOOD + "?center=1,2&size=0.1", allow_query=True)
    with pytest.raises(ValueError):
        cutout_url("https://example.com/a.fits", 1, 2)
    u = cutout_url(GOOD, 331.0966687831005, -56.80064917516836)
    assert u == GOOD + "?center=331.0966687831005%2C-56.80064917516836&size=0.1"  # same form as the ledger


def test_sia_url_rejects_unlisted_collection_and_bad_numbers():
    with pytest.raises(ValueError):
        sia_url("allwise", 1, 2, 0.01)
    with pytest.raises(ValueError):
        sia_url("spherex_dr1", float("nan"), 2, 0.01)
    assert "COLLECTION=spherex_dr1" in sia_url("spherex_dr1", 330.84, -56.786, 0.01)


def test_parse_sorts_filters_and_builds_frame_keys():
    obs = parse_sia_votable(VOTABLE, "spherex_dr1")
    assert [o["frame_key"] for o in obs] == ["2026W39_2A_0597_4_D3", "2026W18_1A_0516_1_D3"]  # evil host dropped
    r = search_spherex(330.84, -56.786, 0.01, collections=["spherex_dr1"],
                       transport=fake({"spherex_dr1": (200, "text/xml", VOTABLE)}))
    assert r.status == "ready"
    assert [o["frame_key"] for o in r.observations] == ["2026W18_1A_0516_1_D3", "2026W39_2A_0597_4_D3"]
    assert r.observations[0]["observed_at_utc"].endswith("Z")


def test_html_502_is_upstream_failure_not_empty():
    t = fake({"spherex_dr1": (200, "text/xml", VOTABLE), "spherex_qr3": (502, "text/html", HTML_502)})
    r = search_spherex(330.84, -56.786, 0.01, transport=t)
    assert r.status == "partial"
    assert r.failures[0]["collection_id"] == "spherex_qr3" and r.failures[0]["code"] == "UPSTREAM_UNAVAILABLE"
    assert r.total_matches is None  # unknown when a collection failed
    both = search_spherex(330.84, -56.786, 0.01, transport=fake({"SIA": (502, "text/html", HTML_502)}))
    assert both.status == "error" and both.observations == []
    # HTML with HTTP 200 is also not a VOTable
    r2 = search_spherex(1, 2, 0.01, collections=["spherex_dr1"], transport=fake({"SIA": (200, "text/html", HTML_502)}))
    assert r2.status == "error"


def test_timeout_maps_to_upstream_timeout():
    r = search_spherex(1, 2, 0.01, collections=["spherex_dr1"],
                       transport=fake({"SIA": ArchiveError("UPSTREAM_TIMEOUT", "timed out", True)}))
    assert r.failures[0]["code"] == "UPSTREAM_TIMEOUT"


def test_limit_truncates():
    r = search_spherex(1, 2, 0.01, collections=["spherex_dr1"], limit=1,
                       transport=fake({"SIA": (200, "text/xml", VOTABLE)}))
    assert len(r.observations) == 1 and r.truncated and r.status == "partial"
    with pytest.raises(ValueError):
        search_spherex(1, 2, 0.01, limit=49, transport=fake({}))


def test_fetch_cutout_checks_status_type_and_size():
    fits_like = b"SIMPLE  =" + b" " * 3000
    body, url, ts = fetch_cutout(GOOD, 1.0, 2.0, transport=fake({"center": (200, "application/fits", fits_like)}))
    assert body == fits_like and url.startswith(GOOD + "?") and ts.endswith("Z")
    with pytest.raises(ArchiveError) as e:
        fetch_cutout(GOOD, 1.0, 2.0, transport=fake({"center": (200, "text/html", HTML_502)}))
    assert e.value.code == "UPSTREAM_UNAVAILABLE"
    with pytest.raises(ArchiveError) as e:
        fetch_cutout(GOOD, 1.0, 2.0, max_bytes=100, transport=fake({"center": (200, "application/fits", fits_like)}))
    assert e.value.code == "UNSUPPORTED_DATA"
    with pytest.raises(ArchiveError):
        fetch_cutout(GOOD, 1.0, 2.0, transport=fake({"center": (503, "text/html", b"")}))


@pytest.mark.skipif(not os.environ.get("PERIGEE_DATA_ROOT"), reason="retained metadata not available")
def test_parse_retained_irsa_votable():
    p = Path(os.environ["PERIGEE_DATA_ROOT"], "metadata", "epsilon_indi_b_spherex_dr1.xml")
    obs = parse_sia_votable(p.read_bytes(), "spherex_dr1")
    keys = {o["frame_key"] for o in obs}
    assert "2026W18_1A_0516_1_D3" in keys
    assert all(o["collection_id"] == "spherex_dr1" for o in obs)
    assert len(obs) == len(keys)
