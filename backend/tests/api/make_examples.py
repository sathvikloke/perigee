"""Regenerate the example payloads in backend/tests/api/examples/.

    PERIGEE_DEV_MODE=1 .venv/bin/python -m backend.tests.api.make_examples [--live]

Files ending in ``.live.json`` came from the real IRSA archive through this API
(tokens are signed with the DEV secret and expire; they are illustrative only).
Files ending in ``.fixture.json`` were produced through the real routes with fixture
archive/processor stand-ins and are NOT NASA results.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from backend.main import app
from backend.routes._adapters import Services, resolve_services
from backend.security.tokens import issue_token
from backend.security.upstream import UpstreamUnavailable

from .conftest import make_settings
from .fixtures import FakeSearch, fixture_descriptor, fixture_fits_bytes, tiny_png

OUT = Path(__file__).parent / "examples"
SEARCH_REQ = {"schema_version": 1, "ra_deg": 330.84, "dec_deg": -56.786, "fov_arcmin": 6, "limit": 24}


def dump(name: str, data) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")
    print("wrote", OUT / name)


def fixture_services(search=None, processor=None, fetch=None) -> Services:
    settings = make_settings()
    handler = fetch or (lambda req: httpx.Response(200, content=fixture_fits_bytes()))
    return Services(
        settings=settings,
        search_collection=search or FakeSearch({}),
        processor=processor,
        processor_source="fixture" if processor else None,
        search_source="fixture",
        http_client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


# Example FrameRecord content: identity/date/wavelength/quality copied from the
# science-verified case JSON (fair_comparison frame A, origin/codex/sathvik-science).
# The IMAGE IS A SYNTHETIC PLACEHOLDER, so data_origin is "fixture".
CASE_A = {
    "observation_id": "2026W18_1A_0516_1",
    "detector": 3,
    "collection_id": "spherex_dr1",
    "observed_at_utc": "2026-04-29T12:05:47.874",
    "mjd": 61159.504026317,
    "source_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2026W18_1A/l2b-v27-2026-244/3/level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits",
}


def example_processor(fits_bytes: bytes, meta: dict) -> dict:
    q = meta["query"]
    return {
        "record": {
            "observed_at_utc": CASE_A["observed_at_utc"],
            "mjd": CASE_A["mjd"],
            "time_basis": "header_mjd_avg",
            "wavelength_um": 2.3232,
            "bandwidth_um": 0.0577,
            "wavelength_location": "Query center (RA, Dec) of this live search",
            "image": {"width": 256, "height": 256},
            "registration": {
                "center_ra_deg": q["ra_deg"],
                "center_dec_deg": q["dec_deg"],
                "fov_arcmin": q["fov_arcmin"],
                "scale_arcsec_per_pixel": q["fov_arcmin"] * 60 / 256,
                "orientation": "north_up_east_left",
                "projection": "TAN",
                "method": "bilinear reprojection of the IMAGE HDU onto a fixed north-up TAN grid",
                "width": 256,
                "height": 256,
            },
            "quality": {
                "status": "clear",
                "covered": True,
                "valid_aperture_pixels": 21,
                "adverse_aperture_pixels": 0,
                "flag_names": [],
                "notes": [
                    "No problem flags within 2.5 px of the position. A clear screen is not a detection or a brightness measurement."
                ],
            },
            "display_scale": {
                "mode": "per_frame",
                "method": "asinh stretch between the 1st and 99.5th percentile of finite pixels",
                "limits": {"low": -0.12, "high": 3.4},
                "comparable_brightness": False,
            },
            "marker": None,
            "provenance": {
                "data_origin": "fixture",
                "processing_version": "example-0",
                "acknowledgments": [
                    "This publication makes use of data products from SPHEREx, a NASA mission managed by JPL/Caltech, obtained from NASA/IPAC Infrared Science Archive (IRSA)."
                ],
            },
            "limitations": [
                "EXAMPLE PAYLOAD: identity, date, wavelength and quality copied from the science-verified case JSON (fair_comparison frame A); the image is a synthetic placeholder, not sky data.",
                "Per-frame contrast: brightness is not directly comparable between frames.",
                "Display pixels are resampled; they do not add physical resolution (SPHEREx pixels are ~6.15 arcsec).",
            ],
        },
        "image_png": tiny_png(16, 16),
        "flag_png": tiny_png(16, 16, value=0),
    }


def main(argv: list[str]) -> int:
    client = TestClient(app)
    dump("search_request.json", SEARCH_REQ)

    if "--live" in argv:
        app.dependency_overrides.pop(resolve_services, None)
        r = client.post("/api/v1/search", json=SEARCH_REQ)
        if r.status_code != 200:
            print("LIVE SEARCH FAILED", r.status_code, r.text[:500])
            return 1
        dump("search_response.ready.live.json", r.json())

    # partial (fixture)
    app.dependency_overrides[resolve_services] = lambda: fixture_services(
        search=FakeSearch(
            {
                "spherex_dr1": [
                    fixture_descriptor("2026W18_1A_0516_1", 3, 61159.50335),
                    fixture_descriptor("2026W18_1A_0516_1", 6, 61159.50335),
                ],
                "spherex_qr3": UpstreamUnavailable("archive returned HTTP 502", status=502, reason="upstream_5xx"),
            }
        )
    )
    dump("search_response.partial.fixture.json", client.post("/api/v1/search", json=SEARCH_REQ).json())
    # empty (fixture)
    app.dependency_overrides[resolve_services] = lambda: fixture_services(search=FakeSearch({}))
    dump("search_response.empty.fixture.json", client.post("/api/v1/search", json=SEARCH_REQ).json())
    # upstream error (fixture)
    err = UpstreamUnavailable("archive returned HTTP 502", status=502, reason="upstream_5xx")
    app.dependency_overrides[resolve_services] = lambda: fixture_services(
        search=FakeSearch({"spherex_dr1": err, "spherex_qr3": err})
    )
    dump("error.upstream_unavailable.json", client.post("/api/v1/search", json=SEARCH_REQ).json())
    dump(
        "error.invalid_coordinates.json",
        client.post("/api/v1/search", json={**SEARCH_REQ, "ra_deg": 360}).json(),
    )
    dump(
        "error.invalid_field_of_view.json",
        client.post("/api/v1/search", json={**SEARCH_REQ, "fov_arcmin": 12}).json(),
    )
    dump("error.not_found.json", client.get("/api/v1/does-not-exist").json())

    # frame (fixture processor through the real /frame route)
    settings = make_settings()
    token, _ = issue_token(
        settings.token_secret,
        source_url=CASE_A["source_url"],
        observation_id=CASE_A["observation_id"],
        detector=CASE_A["detector"],
        collection_id=CASE_A["collection_id"],
        frame_key=f"{CASE_A['observation_id']}_D{CASE_A['detector']}",
        mjd=61159.50335,
        observed_at_utc="2026-04-29T12:04:49.440",
        ra_deg=331.0966687831005,
        dec_deg=-56.80064917516836,
        fov_arcmin=6.0,
        ttl_s=6 * 3600,
    )
    frame_req = {"schema_version": 1, "frame_token": token}
    dump("frame_request.fixture.json", frame_req)
    app.dependency_overrides[resolve_services] = lambda: fixture_services(processor=example_processor)
    dump("frame_response.fixture.json", client.post("/api/v1/frame", json=frame_req).json())
    dump(
        "error.invalid_frame_token.json",
        client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": token[:-4] + "AAAA"}).json(),
    )
    expired, _ = issue_token(
        settings.token_secret,
        source_url=CASE_A["source_url"],
        observation_id=CASE_A["observation_id"],
        detector=3,
        collection_id="spherex_dr1",
        frame_key="2026W18_1A_0516_1_D3",
        mjd=None,
        observed_at_utc=None,
        ra_deg=331.0966687831005,
        dec_deg=-56.80064917516836,
        fov_arcmin=6.0,
        ttl_s=60,
        now=1_700_000_000,
    )
    dump(
        "error.token_expired.json",
        client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": expired}).json(),
    )
    app.dependency_overrides[resolve_services] = lambda: replace(fixture_services(), processor=None)
    dump("error.processor_unavailable.json", client.post("/api/v1/frame", json=frame_req).json())
    app.dependency_overrides.pop(resolve_services, None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
