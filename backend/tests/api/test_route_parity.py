"""N5: route-level parity of the live path (search -> signed token -> /frame) with a
direct ``process_frame`` call on the same raw bytes and parameters.

Only the network is replaced. The archive search runs the real
``irsa_search_collection`` (SIA request building, VOTable parsing, descriptor
mapping) against a *subset of the real cached IRSA SIA responses* kept with the
retained data, and the cutout fetch returns the retained original FITS bytes.
Everything between (validation, token signing/verification, cutout URL,
allowlist, budgets, processor adapter, record assembly, data URLs, response
model) is the production code.

Two layers:

* Synthetic (always runs, also in CI): geometry at two FOVs and shifted
  coordinates, RA wrap and pole edges, and the missing-overlay vs no-adverse-flag
  distinction. SYNTHETIC FITS, NOT NASA DATA (backend/tests/data/synthetic.py).
* Retained data (``PERIGEE_DATA_ROOT``): exact record and PNG parity for
  near-IR, longer-wavelength, flagged/non-finite and geometric no-coverage
  frames, the same-observation FOV/shift matrix, and the curated-copy
  comparison. Skipped honestly when the raw files are absent.

Expected route-vs-direct differences: none, once ``provenance.retrieved_at``
(fetch time) is shared and the route's ``provenance.data_origin =
"nasa_archive"`` and image ``src`` data URLs are applied to the direct record.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest
from PIL import Image

from backend.data import process as proc
from backend.models.frame import FrameRecord, FrameResponse
from backend.routes import _adapters
from backend.routes._archive import SEARCH_RADIUS_DEG, SIA_MAXREC, irsa_search_collection
from backend.routes.frames import CUTOUT_MARGIN, GRID_PX, cutout_url_for
from backend.security.tokens import verify_token

from .conftest import TEST_SECRET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
import synthetic as syn  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
DATA_ROOT = os.environ.get("PERIGEE_DATA_ROOT")
VOT_NS = "http://www.ivoa.net/xml/VOTable/v1.3"
_URL_DET = re.compile(r"D(\d+)_spx")
NONFINITE_RGBA = (255, 200, 0, 200)
ADVERSE_RGBA = (255, 64, 64, 150)

# --------------------------------------------------------------------------- helpers


def png_sha(data_url_or_bytes: str | bytes | None) -> str | None:
    if data_url_or_bytes is None:
        return None
    raw = data_url_or_bytes
    if isinstance(raw, str):
        assert raw.startswith("data:image/png;base64,")
        raw = base64.b64decode(raw.split(",", 1)[1])
    return hashlib.sha256(raw).hexdigest()


def png_array(data_url: str) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1]))))


def data_url(png: bytes | None) -> str | None:
    return None if png is None else "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def subset_votable(xml: bytes, keep: set[str]) -> tuple[bytes, dict[str, dict[str, str]]]:
    """Real cached IRSA SIA VOTable with only the rows whose frame key is in ``keep``.

    Header, FIELD definitions and QUERY_STATUS are untouched, so the route's real
    VOTable parser sees the archive's own format. Returns (xml, kept rows by key)."""
    ET.register_namespace("", VOT_NS)
    root = ET.fromstring(xml)
    kept: dict[str, dict[str, str]] = {}
    for table in root.iter(f"{{{VOT_NS}}}TABLE"):
        names = [f.get("name", "") for f in table if f.tag == f"{{{VOT_NS}}}FIELD"]
        for tabledata in table.iter(f"{{{VOT_NS}}}TABLEDATA"):
            for tr in list(tabledata):
                row = dict(zip(names, [(td.text or "") for td in tr]))
                m = _URL_DET.search(row.get("access_url", ""))
                key = f"{row.get('obs_id', '').strip()}_D{m.group(1)}" if m else None
                if key in keep:
                    kept[key] = row
                else:
                    tabledata.remove(tr)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), kept


class ArchiveDouble:
    """Scripted IRSA: SIA answers per collection, IBE cutouts by archive path."""

    def __init__(self, votables: dict[str, bytes], files: dict[str, bytes]):
        self.votables = votables
        self.files = files
        self.sia_params: list[dict[str, str]] = []
        self.data_urls: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/SIA":
            params = dict(request.url.params)
            self.sia_params.append(params)
            body = self.votables.get(params.get("COLLECTION", ""))
            if body is None:
                body = EMPTY_VOTABLE
            return httpx.Response(200, content=body, headers={"content-type": "text/xml"})
        self.data_urls.append(str(request.url))
        data = self.files.get(request.url.path)
        if data is None:
            return httpx.Response(404, content=b"not found", headers={"content-type": "text/plain"})
        return httpx.Response(200, content=data, headers={"content-type": "application/fits"})


EMPTY_VOTABLE = (
    b'<?xml version="1.0"?><VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3" version="1.3">'
    b'<RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK"/><TABLE>'
    b'<FIELD name="obs_id" datatype="char" arraysize="*"/><FIELD name="access_url" datatype="char" arraysize="*"/>'
    b"<DATA><TABLEDATA/></DATA></TABLE></RESOURCE></VOTABLE>"
)


def use_real_route(harness, archive: ArchiveDouble) -> None:
    processor, source = _adapters.processor_a_adapter()
    assert processor is not None and "processor-a" in source
    harness.processor = processor
    harness.search = irsa_search_collection
    harness.fetch_handler = archive
    harness.settings = replace(harness.settings, frame_fetch_max_bytes=24 * 2**20, frame_budget_s=40.0, search_budget_s=10.0)


def search(client, ra: float, dec: float, fov: float, *, limit: int = 48, rid: str = "n5-search") -> dict:
    r = client.post(
        "/api/v1/search",
        json={"schema_version": 1, "ra_deg": ra, "dec_deg": dec, "fov_arcmin": fov, "limit": limit},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200, r.text[:1000]
    assert r.headers["x-request-id"] == rid == r.json()["request_id"]
    return r.json()


def frame(client, token: str, *, rid: str = "n5-frame") -> dict:
    r = client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": token}, headers={"X-Request-ID": rid})
    assert r.status_code == 200, r.text[:1000]
    body = r.json()
    FrameResponse.model_validate(body)
    assert r.headers["x-request-id"] == rid == body["request_id"]
    assert r.headers["cache-control"] == "no-store"
    return body["frame"]


def trace(client, ra: float, dec: float, fov: float, frame_key: str, *, tag: str = "") -> tuple[dict, dict, dict]:
    """search -> pick ``frame_key`` -> /frame. Returns (search body, descriptor, frame record)."""
    s = search(client, ra, dec, fov, rid=f"n5-s{tag}")
    obs = [o for o in s["observations"] if o["frame_key"] == frame_key]
    assert len(obs) == 1, [o["frame_key"] for o in s["observations"]]
    claims = verify_token(TEST_SECRET, obs[0]["frame_token"])
    assert (claims.ra_deg, claims.dec_deg, claims.fov_arcmin) == (ra, dec, fov)
    return s, obs[0], frame(client, obs[0]["frame_token"], rid=f"n5-f{tag}")


def direct(raw: bytes, obs: dict, rec: dict, ra: float, dec: float, fov: float) -> proc.ProcessedFrame:
    """process_frame on the same bytes and parameters; only fetch time is copied."""
    return proc.process_frame(
        raw,
        proc.FrameInput(
            query_ra_deg=ra,
            query_dec_deg=dec,
            fov_arcmin=fov,
            grid_size=GRID_PX,
            target=None,
            source_url=obs["source_url"],
            observation_id=obs["observation_id"],
            collection_id=obs["collection_id"],
            detector=obs["detector"],
            cutout_url=rec["provenance"]["cutout_url"],
            retrieved_at_utc=rec["provenance"]["retrieved_at"],
            retrieved_at_basis="Time this API fetched the cutout from IRSA for this request.",
            include_flag_image=True,
        ),
    )


def expected_record(out: proc.ProcessedFrame) -> dict:
    exp = proc.with_image_sources(out.record, data_url(out.png_bytes), data_url(out.flag_png_bytes))
    exp["provenance"]["data_origin"] = "nasa_archive"
    return json.loads(json.dumps(FrameRecord.model_validate(exp).model_dump(mode="json")))


def assert_parity(rec: dict, out: proc.ProcessedFrame) -> None:
    exp = expected_record(out)
    diff = sorted(k for k in set(exp) | set(rec) if exp.get(k) != rec.get(k))
    assert not diff, {k: (rec.get(k), exp.get(k)) for k in diff}
    assert png_sha(rec["image"]["src"]) == png_sha(out.png_bytes)
    assert png_sha(rec["flag_image"]["src"] if rec["flag_image"] else None) == png_sha(out.flag_png_bytes)


def assert_route_invariants(rec: dict, obs: dict, raw: bytes, ra: float, dec: float, fov: float, fetched: str) -> None:
    reg = rec["registration"]
    # Geometry comes from the signed query, never from a previous request.
    assert (reg["center_ra_deg"], reg["center_dec_deg"], reg["fov_arcmin"]) == (ra, dec, fov)
    assert (reg["width"], reg["height"]) == (GRID_PX, GRID_PX)
    assert reg["scale_arcsec_per_px"] == pytest.approx(fov * 60.0 / GRID_PX, rel=1e-12)
    assert reg["grid_id"] == proc.grid_id(ra, dec, fov, GRID_PX)
    img = png_array(rec["image"]["src"])
    assert img.shape[:2] == (rec["image"]["height"], rec["image"]["width"]) == (GRID_PX, GRID_PX)
    # Overlay alignment: same grid, and every non-finite overlay pixel is transparent in the image.
    if rec["flag_image"] is not None:
        flag = png_array(rec["flag_image"]["src"])
        assert flag.shape == (GRID_PX, GRID_PX, 4)
        nonfinite = np.all(flag == NONFINITE_RGBA, axis=-1)
        assert not np.any(img[..., -1][nonfinite]), "non-finite overlay pixel is opaque in the image"
        # Overlay pixels are only drawn on the image footprint (never on transparent off-image area
        # except where the pixel itself is non-finite).
        marked = flag[..., -1] > 0
        assert not np.any(marked & (img[..., -1] == 0) & ~nonfinite), "overlay marks an off-image pixel"
    # Sampled position is the query center (live queries carry no catalog target).
    sp = rec["sampled_position"]
    assert (sp["kind"], sp["ra_deg"], sp["dec_deg"]) == ("query_center", ra, dec)
    assert rec["marker"] is None
    # Provenance: exact bytes, URLs and processor identity.
    prov = rec["provenance"]
    assert prov["sha256"] == hashlib.sha256(raw).hexdigest()
    assert prov["original_url"] == obs["source_url"] == rec["source_url"]
    assert prov["cutout_url"] == fetched
    want = httpx.URL(fetched)
    assert str(want.copy_with(query=None)) == obs["source_url"]
    assert want.params["center"] == f"{ra!r},{dec!r}"
    assert float(want.params["size"]) == pytest.approx(fov * CUTOUT_MARGIN / 60.0, abs=1e-6)
    assert prov["processing_version"] == proc.PROCESSING_VERSION
    assert prov["data_origin"] == "nasa_archive"
    # Identity is the descriptor's (bound by the token).
    for k in ("observation_id", "detector", "frame_key", "collection_id"):
        assert rec[k] == obs[k]
    # Wavelength at the sampled position lies inside the archive's whole-detector range.
    if rec["wavelength_um"] is not None and obs["detector_wavelength_range_um"]:
        lo, hi = obs["detector_wavelength_range_um"]
        assert lo - 1e-4 <= rec["wavelength_um"] <= hi + 1e-4
    # Time: the descriptor carries SIA t_min (exposure start), the record MJD-AVG (mid-exposure).
    assert obs["time_basis"] == "sia_t_min"
    assert rec["time_basis"].startswith("DATE-AVG / MJD-AVG")


# --------------------------------------------------------------------------- synthetic layer (CI)

SYN_URL = "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2099W01_1A/l2b-v27-2099-001/3/level2_2099W01_1A_0001_1D3_spx_l2b-v27-2099-001.fits"


def synthetic_votable(t_min: float = 61000.4993) -> bytes:
    return (
        '<?xml version="1.0"?><VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3" version="1.3">'
        '<RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK"/><TABLE>'
        + "".join(
            f'<FIELD name="{n}" datatype="char" arraysize="*"/>'
            for n in ("obs_id", "access_url", "dataproduct_type", "obs_collection", "energy_bandpassname",
                      "em_min", "em_max", "t_min", "t_exptime")
        )
        + "<DATA><TABLEDATA><TR>"
        + "".join(
            f"<TD>{v}</TD>"
            for v in ("2099W01_1A_0001_1", SYN_URL, "image", "spherex_dr1", "SPHEREx-D3", "1.0e-06", "2.5e-06",
                      repr(t_min), "112.0")
        )
        + "</TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>"
    ).encode()


@pytest.fixture
def synthetic_center(monkeypatch):
    """Let a test place the synthetic cutout anywhere on the sky (RA wrap, poles)."""

    def place(ra: float, dec: float) -> None:
        monkeypatch.setattr(syn, "CENTER", (ra, dec))

    return place


def _synthetic_archive(raw: bytes) -> ArchiveDouble:
    return ArchiveDouble({"spherex_dr1": synthetic_votable()}, {httpx.URL(SYN_URL).path: raw})


SYN_KEY = "2099W01_1A_0001_1_D3"


def test_synthetic_trace_matches_direct_processing(client, harness):
    raw = syn.make_fits(sources=((29.5, 29.5, 5.0),))
    archive = _synthetic_archive(raw)
    use_real_route(harness, archive)
    ra, dec = syn.CENTER
    s, obs, rec = trace(client, ra, dec, 6.0, SYN_KEY)
    # The archive was asked for the fixed 3.6" coverage cone, not the field of view.
    sia = archive.sia_params[-1]
    assert sia["POS"] == f"CIRCLE {ra!r} {dec!r} {SEARCH_RADIUS_DEG}" and sia["MAXREC"] == str(SIA_MAXREC)
    assert obs["detector_wavelength_range_um"] == [1.0, 2.5]
    assert_route_invariants(rec, obs, raw, ra, dec, 6.0, archive.data_urls[-1])
    assert_parity(rec, direct(raw, obs, rec, ra, dec, 6.0))
    assert rec["quality"]["status"] == "clear"


def _geometry(rec: dict) -> tuple:
    reg = rec["registration"]
    return (reg["center_ra_deg"], reg["center_dec_deg"], reg["fov_arcmin"], reg["grid_id"],
            rec["sampled_position"]["native_x"], rec["sampled_position"]["native_y"], png_sha(rec["image"]["src"]))


def test_synthetic_same_observation_two_fovs_and_shift_never_reuse_geometry(client, harness):
    raw = syn.make_fits(sources=((20.0, 35.0, 8.0), (40.0, 22.0, 4.0)))
    archive = _synthetic_archive(raw)
    use_real_route(harness, archive)
    ra0, dec0 = syn.CENTER
    shift = 0.5 / 60.0  # 0.5 arcmin in Dec and in RA*cos(Dec)
    queries = {
        "fov2": (ra0, dec0, 2.0),
        "fov10": (ra0, dec0, 10.0),
        "shifted": (ra0 + shift / math.cos(math.radians(dec0)), dec0 + shift, 6.0),
    }
    seen = {}
    # Interleave and repeat: A, B, C, A, C, B. Each answer must follow its own token.
    for i, name in enumerate(["fov2", "fov10", "shifted", "fov2", "shifted", "fov10"]):
        ra, dec, fov = queries[name]
        _, obs, rec = trace(client, ra, dec, fov, SYN_KEY, tag=f"{i}")
        assert_route_invariants(rec, obs, raw, ra, dec, fov, archive.data_urls[-1])
        assert_parity(rec, direct(raw, obs, rec, ra, dec, fov))
        geom = _geometry(rec)
        if name in seen:
            assert geom == seen[name], f"{name} changed between identical requests"
        seen[name] = geom
    assert len({g[3] for g in seen.values()}) == 3, "grid_id must differ per geometry"
    assert len({g[6] for g in seen.values()}) == 3, "image bytes must differ per geometry"
    # Same frame_key for all three: a client cache keyed by frame_key alone returns old geometry.
    assert len(archive.data_urls) == 6  # no backend cache: every request refetches its own cutout
    sizes = {httpx.URL(u).params["size"] for u in archive.data_urls}
    assert sizes == {f"{2 * 1.5 / 60:.6f}", f"{10 * 1.5 / 60:.6f}", f"{6 * 1.5 / 60:.6f}"}
    # The shifted query samples a different native pixel, by the expected ~0.71' / 6.15" = 6.9 px.
    a, b = seen["fov2"], seen["shifted"]
    assert math.hypot(b[4] - a[4], b[5] - a[5]) == pytest.approx(math.sqrt(2) * 30.0 / 6.15, rel=0.02)


def test_synthetic_shift_off_the_cutout_is_not_covered_not_an_error(client, harness):
    raw = syn.make_fits()
    archive = _synthetic_archive(raw)
    use_real_route(harness, archive)
    ra0, dec0 = syn.CENTER
    ra = ra0 + (4.0 / 60.0) / math.cos(math.radians(dec0))  # 4' east: the 60 px cutout spans +/-3.1'
    _, obs, rec = trace(client, ra, dec0, 6.0, SYN_KEY)
    assert_route_invariants(rec, obs, raw, ra, dec0, 6.0, archive.data_urls[-1])
    assert_parity(rec, direct(raw, obs, rec, ra, dec0, 6.0))
    q = rec["quality"]
    assert (q["status"], q["covered"], rec["wavelength_um"]) == ("not_covered", False, None)
    assert q["valid_aperture_pixels"] is None and q["adverse_aperture_pixels"] is None
    assert rec["wavelength_location"].startswith("Not sampled")


@pytest.mark.parametrize(
    "center,query",
    [
        ((0.0, 10.0), (359.999, 10.0)),  # query just west of RA 0, cutout centred on RA 0
        ((359.9995, 10.0), (0.0005, 10.0)),  # cutout just west of RA 0, query east of it
        ((10.0, 89.99), (190.0, 89.995)),  # across the north pole
        ((10.0, -89.99), (200.0, -89.999)),  # near the south pole
        ((10.0, 90.0), (0.0, 90.0)),  # query exactly at the pole (Dec = 90 is allowed)
    ],
)
def test_synthetic_coordinate_edges_through_the_route(client, harness, synthetic_center, center, query):
    synthetic_center(*center)
    raw = syn.make_fits()
    archive = _synthetic_archive(raw)
    use_real_route(harness, archive)
    ra, dec = query
    _, obs, rec = trace(client, ra, dec, 6.0, SYN_KEY)
    assert_route_invariants(rec, obs, raw, ra, dec, 6.0, archive.data_urls[-1])
    assert_parity(rec, direct(raw, obs, rec, ra, dec, 6.0))
    assert rec["quality"]["covered"] is True and rec["quality"]["status"] == "clear"
    assert rec["wavelength_um"] is not None
    assert png_array(rec["image"]["src"])[..., -1].mean() > 0.8 * 255  # mostly opaque: the cutout is on the grid


def test_synthetic_missing_overlay_is_not_reported_as_clear(client, harness):
    """No FLAGS extension: no overlay (flag_image null) and status unknown, never clear.
    FLAGS present with nothing adverse: an overlay exists (all transparent) and status clear."""
    ra, dec = syn.CENTER
    raw_noflags = syn.make_fits(include_flags=False)
    use_real_route(harness, _synthetic_archive(raw_noflags))
    _, obs, rec = trace(client, ra, dec, 6.0, SYN_KEY)
    assert rec["flag_image"] is None
    assert rec["quality"]["status"] == "unknown"
    assert rec["quality"]["adverse_aperture_pixels"] is None and rec["quality"]["valid_aperture_pixels"] is None
    assert any("flag screen unavailable" in n for n in rec["quality"]["notes"])

    raw_clean = syn.make_fits()
    use_real_route(harness, _synthetic_archive(raw_clean))
    _, obs, rec = trace(client, ra, dec, 6.0, SYN_KEY)
    assert rec["flag_image"] is not None
    assert rec["quality"]["status"] == "clear" and rec["quality"]["adverse_aperture_pixels"] == 0
    assert not png_array(rec["flag_image"]["src"])[..., -1].any()  # overlay present, nothing marked

    # Adverse flag at the query center: overlay marks it and status is flagged.
    flags = np.zeros((syn.NY, syn.NX), dtype=np.int32)
    flags[29:31, 29:31] = 1 << syn.BIT["HOT"]
    raw_flagged = syn.make_fits(flags=flags)
    use_real_route(harness, _synthetic_archive(raw_flagged))
    _, obs, rec = trace(client, ra, dec, 6.0, SYN_KEY)
    assert rec["quality"]["status"] == "flagged" and rec["quality"]["flag_names"] == ["HOT"]
    assert np.all(png_array(rec["flag_image"]["src"]) == ADVERSE_RGBA, axis=-1).any()


def test_synthetic_nonfinite_pixels_cross_the_route_aligned(client, harness):
    ra, dec = syn.CENTER
    img = (0.5 + np.zeros((syn.NY, syn.NX))).astype(np.float32)
    img[28:32, 28:32] = np.nan
    raw = syn.make_fits(image=img)
    archive = _synthetic_archive(raw)
    use_real_route(harness, archive)
    _, obs, rec = trace(client, ra, dec, 6.0, SYN_KEY)
    assert_route_invariants(rec, obs, raw, ra, dec, 6.0, archive.data_urls[-1])
    assert_parity(rec, direct(raw, obs, rec, ra, dec, 6.0))
    q = rec["quality"]
    assert q["status"] == "flagged" and q["covered"] is True and q["nonfinite_aperture_pixels"] > 0
    flag = png_array(rec["flag_image"]["src"])
    image_alpha = png_array(rec["image"]["src"])[..., -1]
    nonfinite = np.all(flag == NONFINITE_RGBA, axis=-1)
    assert nonfinite.sum() > 0
    assert np.array_equal(nonfinite, (image_alpha == 0))  # cutout covers the whole 6' grid: holes == NaNs


# --------------------------------------------------------------------------- retained-data layer

needs_data = pytest.mark.skipif(
    not DATA_ROOT or not (Path(DATA_ROOT) / "manifest.json").is_file(),
    reason="needs PERIGEE_DATA_ROOT with the retained SPHEREx cutouts and cached SIA responses",
)

# (case id, preset, frame_key, why, expected quality status)
PARITY_CASES = [
    ("nir_d3_clear", "epsilon_indi_b", "2026W18_1A_0516_1_D3", "near-IR 2.32 um, fair_comparison A", "clear"),
    ("nir_d1_clear", "epsilon_indi_b", "2026W17_1B_0162_4_D1", "shortest band 0.77 um", "clear"),
    ("mwir_d6_clear", "epsilon_indi_b", "2026W18_1A_0516_1_D6", "longer wavelength 4.94 um, fair_comparison C", "clear"),
    ("mwir_d6_wise", "wise_0855", "2025W19_1B_0116_1_D6", "longer wavelength 4.97 um, WISE 0855 field", "clear"),
    ("flagged_nonfinite", "r_draconis", "2025W29_2A_0288_1_D4", "BLOOM/OVERFLOW/SUR_ERROR + 21 non-finite", "flagged"),
    ("flagged_case", "barnards_star", "2025W35_1A_0008_1_D3", "moving_neighbor A, adverse + non-finite", "flagged"),
    ("not_covered", "epsilon_indi_b", "2025W17_4B_0077_2_D1", "retained file does not cover the query center", "not_covered"),
]


def _manifest() -> dict:
    return json.loads((Path(DATA_ROOT) / "manifest.json").read_text())


def retained(preset: str, keys: set[str]) -> tuple[ArchiveDouble, dict, dict[str, bytes], tuple[float, float]]:
    """Archive double for ``preset``: real cached SIA rows for ``keys`` + their retained bytes."""
    m = _manifest()
    target = next(t for t in m["targets"] if t["id"] == preset)
    votables, rows = {}, {}
    for col in ("spherex_dr1", "spherex_qr3"):
        xml = (Path(DATA_ROOT) / "metadata" / f"{preset}_{col}.xml").read_bytes()
        votables[col], kept = subset_votable(xml, keys)
        rows.update(kept)
    assert set(rows) == keys, keys - set(rows)
    files, raw_by_key = {}, {}
    for f in m["files"]:
        if f.get("status") != "downloaded" or f["target_id"] != preset:
            continue
        key = f"{f['obs_id']}_D{_URL_DET.search(f['archive_url']).group(1)}"
        if key in keys:
            raw = (Path(DATA_ROOT) / f["file"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == f["sha256"]
            files[httpx.URL(f["archive_url"]).path] = raw
            raw_by_key[key] = raw
    assert set(raw_by_key) == keys
    return ArchiveDouble(votables, files), rows, raw_by_key, (target["query_ra_deg"], target["query_dec_deg"])


@needs_data
@pytest.mark.parametrize("case_id,preset,key,why,status", PARITY_CASES, ids=[c[0] for c in PARITY_CASES])
def test_retained_trace_matches_direct_processing(client, harness, case_id, preset, key, why, status):
    archive, rows, raws, (ra, dec) = retained(preset, {key})
    use_real_route(harness, archive)
    s, obs, rec = trace(client, ra, dec, 6.0, key)
    assert s["status"] == "ready" and s["total_matches"] == 1
    raw = raws[key]
    assert_route_invariants(rec, obs, raw, ra, dec, 6.0, archive.data_urls[-1])
    assert_parity(rec, direct(raw, obs, rec, ra, dec, 6.0))
    q = rec["quality"]
    assert q["status"] == status, why
    row = rows[key]
    # Mid-exposure (record) follows exposure start (descriptor) within one exposure time.
    if rec["mjd"] is not None:
        dt_s = (rec["mjd"] - obs["mjd"]) * 86400.0
        assert 0.0 < dt_s <= float(row["t_exptime"]) + 1.0, (dt_s, row["t_exptime"])
    if status == "not_covered":
        assert q["covered"] is False and rec["wavelength_um"] is None
        assert q["nonfinite_aperture_pixels"] is None and q["valid_aperture_pixels"] is None
    else:
        assert q["covered"] is True and rec["wavelength_um"] is not None
    if status == "flagged":
        assert q["adverse_aperture_pixels"] > 0 and q["flag_names"]
    if case_id == "flagged_nonfinite":
        assert q["nonfinite_aperture_pixels"] == 21
        assert {"BLOOM", "OVERFLOW", "SUR_ERROR"} <= set(q["flag_names"])
    if case_id.startswith("mwir"):
        assert rec["wavelength_um"] > 4.4
    if case_id.startswith("nir"):
        assert rec["wavelength_um"] < 2.5


@needs_data
def test_retained_same_observation_two_fovs_and_shift(client, harness):
    key = "2026W18_1A_0516_1_D3"
    archive, _rows, raws, (ra0, dec0) = retained("epsilon_indi_b", {key})
    use_real_route(harness, archive)
    raw = raws[key]
    shift = 0.5 / 60.0
    queries = {
        "fov2": (ra0, dec0, 2.0),
        "fov10": (ra0, dec0, 10.0),
        "shifted": (ra0 + shift / math.cos(math.radians(dec0)), dec0 + shift, 6.0),
        "off": (ra0 + (4.0 / 60.0) / math.cos(math.radians(dec0)), dec0, 6.0),
    }
    seen = {}
    for i, name in enumerate(["fov2", "fov10", "shifted", "off", "fov2", "shifted", "fov10"]):
        ra, dec, fov = queries[name]
        _, obs, rec = trace(client, ra, dec, fov, key, tag=f"{i}")
        assert_route_invariants(rec, obs, raw, ra, dec, fov, archive.data_urls[-1])
        assert_parity(rec, direct(raw, obs, rec, ra, dec, fov))
        geom = _geometry(rec) + (rec["quality"]["status"], rec["wavelength_um"])
        if name in seen:
            assert geom == seen[name]
        seen[name] = geom
    assert len({g[3] for g in seen.values()}) == 4 and len({g[6] for g in seen.values()}) == 4
    assert seen["off"][7:] == ("not_covered", None)
    assert seen["fov2"][7] == seen["fov10"][7] == "clear"
    # Wavelength depends on the sampled position, not on the field of view.
    assert seen["fov2"][8] == seen["fov10"][8]
    assert seen["shifted"][8] != seen["fov2"][8]


@needs_data
@pytest.mark.parametrize(
    "preset,key,case_dir,case_mode",
    [
        ("epsilon_indi_b", "2026W18_1A_0516_1_D3", "case-fair_comparison", "shared"),
        # fair_comparison C is a different wavelength: authored with its own per-frame stretch.
        ("epsilon_indi_b", "2026W18_1A_0516_1_D6", "case-fair_comparison", "per_frame"),
        ("barnards_star", "2025W35_1A_0008_1_D3", "case-moving_neighbor", "shared"),
    ],
)
def test_retained_live_pixels_equal_curated_per_frame_asset_not_case_copy(client, harness, preset, key, case_dir, case_mode):
    """Same raw bytes + same grid: the live PNG is byte-identical to the curated per-frame
    asset. An authored case copy differs exactly when it uses a shared stretch."""
    archive, _rows, raws, (ra, dec) = retained(preset, {key})
    use_real_route(harness, archive)
    _, _obs, rec = trace(client, ra, dec, 6.0, key)
    pdir = REPO / "backend" / "content" / "presets" / preset
    curated = json.loads((pdir / "frames" / f"{key}.json").read_text())
    assert curated["registration"]["grid_id"] == rec["registration"]["grid_id"]
    assert curated["provenance"]["sha256"] == rec["provenance"]["sha256"]
    assert curated["display_scale"]["mode"] == rec["display_scale"]["mode"] == "per_frame"
    assert png_sha((pdir / "frames" / f"{key}.png").read_bytes()) == png_sha(rec["image"]["src"])
    assert png_sha((pdir / "frames" / f"{key}.flags.png").read_bytes()) == png_sha(rec["flag_image"]["src"])
    for k in ("frame_key", "observation_id", "detector", "collection_id", "observed_at_utc", "mjd", "source_url"):
        assert curated[k] == rec[k], k
    # Same stretch limits; the live response additionally carries the model's optional
    # ``comparable_brightness: null`` default, which the curated file omits.
    assert curated["display_scale"] == {k: v for k, v in rec["display_scale"].items() if k != "comparable_brightness"}
    assert rec["display_scale"]["comparable_brightness"] is None
    # Documented differences: curated frames sample the catalog-predicted target position and
    # carry a catalog marker; live frames sample the query center and carry no marker.
    assert curated["sampled_position"]["kind"] == "catalog_prediction" and curated["marker"] is not None
    assert rec["sampled_position"]["kind"] == "query_center" and rec["marker"] is None
    case = json.loads((pdir / case_dir / f"{key}.json").read_text())
    assert case["display_scale"]["mode"] == case_mode
    assert case["registration"]["grid_id"] == rec["registration"]["grid_id"]
    same_pixels = png_sha((pdir / case_dir / f"{key}.png").read_bytes()) == png_sha(rec["image"]["src"])
    assert same_pixels == (case_mode == "per_frame")
    # The flag overlay does not depend on the stretch, so the case copy's overlay is identical.
    assert png_sha((pdir / case_dir / f"{key}.flags.png").read_bytes()) == png_sha(rec["flag_image"]["src"])


@needs_data
def test_retained_common_grid_identity_across_frames(client, harness):
    """Two frames of one query share grid_id and registration; their images differ."""
    keys = {"2026W18_1A_0516_1_D3", "2026W39_2A_0597_4_D3"}
    archive, _rows, raws, (ra, dec) = retained("epsilon_indi_b", keys)
    use_real_route(harness, archive)
    s = search(client, ra, dec, 6.0)
    assert s["status"] == "ready" and s["total_matches"] == 2
    assert [o["collection_id"] for o in s["observations"]] == ["spherex_dr1", "spherex_qr3"]  # time order
    recs = [frame(client, o["frame_token"], rid=f"n5-grid-{i}") for i, o in enumerate(s["observations"])]
    regs = [r["registration"] for r in recs]
    assert regs[0] == {**regs[1], "native_scale_arcsec_per_px": regs[0]["native_scale_arcsec_per_px"]}
    assert png_sha(recs[0]["image"]["src"]) != png_sha(recs[1]["image"]["src"])
    assert "Quick-release (QR) products may be reprocessed in a later data release." in recs[1]["limitations"]
