"""N5 evidence: run the route-level parity matrix and record hashes and parameters.

    PERIGEE_DATA_ROOT=.../research/build_data .venv/bin/python qa/overnight-backend/n5_parity_evidence.py

Uses the same helpers as backend/tests/api/test_route_parity.py (real search adapter on
subsets of the cached IRSA SIA responses, real token, real /frame route, processor A),
and writes:

* qa/overnight-backend/n5_parity_evidence.json   -- per case: raw sha256, normalized
  request, cutout URL, record/PNG hashes, route-vs-direct equality, curated comparison
* qa/overnight-backend/fixtures/request_identity_fixture.json -- one observation at
  2', 10' and shifted coordinates: identical frame_key, different geometry. Input for
  the frontend frame-cache fix (no image data; hashes only).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
OUT = Path(__file__).resolve().parent

from fastapi.testclient import TestClient  # noqa: E402

from backend.data import process as proc  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routes._adapters import resolve_services  # noqa: E402
from backend.tests.api import test_route_parity as rp  # noqa: E402
from backend.tests.api.conftest import Harness  # noqa: E402


def record_hash(rec: dict) -> str:
    """sha256 of the record JSON without the per-request fetch time and image payloads."""
    r = json.loads(json.dumps(rec))
    r["provenance"].pop("retrieved_at", None)
    r["image"]["src"] = rp.png_sha(r["image"]["src"])
    if r.get("flag_image"):
        r["flag_image"]["src"] = rp.png_sha(r["flag_image"]["src"])
    return hashlib.sha256(json.dumps(r, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_case(client, h: Harness, preset: str, key: str, ra=None, dec=None, fov=6.0, tag="") -> dict:
    archive, rows, raws, (ra0, dec0) = rp.retained(preset, {key})
    rp.use_real_route(h, archive)
    ra = ra0 if ra is None else ra
    dec = dec0 if dec is None else dec
    s, obs, rec = rp.trace(client, ra, dec, fov, key, tag=tag)
    out = rp.direct(raws[key], obs, rec, ra, dec, fov)
    exp = rp.expected_record(out)
    equal_fields = sorted(k for k in exp if exp.get(k) == rec.get(k))
    diff_fields = sorted(k for k in set(exp) | set(rec) if exp.get(k) != rec.get(k))
    q = rec["quality"]
    row = {
        "preset": preset,
        "frame_key": key,
        "raw_sha256": hashlib.sha256(raws[key]).hexdigest(),
        "raw_bytes": len(raws[key]),
        "request": {"ra_deg": ra, "dec_deg": dec, "fov_arcmin": fov, "limit": 48,
                    "collection_ids": ["spherex_dr1", "spherex_qr3"], "grid_px": rp.GRID_PX},
        "sia_pos": archive.sia_params[-1]["POS"],
        "cutout_url": rec["provenance"]["cutout_url"],
        "descriptor": {k: obs[k] for k in ("observation_id", "detector", "collection_id", "mjd", "observed_at_utc",
                                           "time_basis", "detector_wavelength_range_um")},
        "record": {
            "observed_at_utc": rec["observed_at_utc"], "mjd": rec["mjd"],
            "wavelength_um": rec["wavelength_um"], "quality_status": q["status"], "covered": q["covered"],
            "nonfinite_aperture_pixels": q["nonfinite_aperture_pixels"], "flag_names": q["flag_names"],
            "grid_id": rec["registration"]["grid_id"], "scale_arcsec_per_px": rec["registration"]["scale_arcsec_per_px"],
            "native_x": rec["sampled_position"]["native_x"], "native_y": rec["sampled_position"]["native_y"],
            "image": [rec["image"]["width"], rec["image"]["height"]],
            "processing_version": rec["provenance"]["processing_version"],
        },
        "route_png_sha256": rp.png_sha(rec["image"]["src"]),
        "direct_png_sha256": rp.png_sha(out.png_bytes),
        "route_flag_png_sha256": rp.png_sha(rec["flag_image"]["src"]) if rec["flag_image"] else None,
        "direct_flag_png_sha256": rp.png_sha(out.flag_png_bytes),
        "record_sha256_without_fetch_time": record_hash(rec),
        "route_equals_direct": not diff_fields,
        "differing_fields": diff_fields,
        "compared_fields": len(equal_fields),
    }
    curated = REPO / "backend/content/presets" / preset / "frames" / f"{key}.json"
    if curated.is_file() and fov == 6.0 and (ra, dec) == (ra0, dec0):
        c = json.loads(curated.read_text())
        row["curated_per_frame"] = {
            "grid_id_equal": c["registration"]["grid_id"] == rec["registration"]["grid_id"],
            "png_equal": rp.png_sha((curated.parent / f"{key}.png").read_bytes()) == row["route_png_sha256"],
            "flag_png_equal": rp.png_sha((curated.parent / f"{key}.flags.png").read_bytes()) == row["route_flag_png_sha256"],
            "sampled_position": [c["sampled_position"]["kind"], rec["sampled_position"]["kind"]],
            "wavelength_um": [c["wavelength_um"], rec["wavelength_um"]],
            "quality_status": [c["quality"]["status"], q["status"]],
        }
    return row


def main() -> None:
    if not os.environ.get("PERIGEE_DATA_ROOT"):
        raise SystemExit("set PERIGEE_DATA_ROOT to research/build_data")
    h = Harness()
    app.dependency_overrides[resolve_services] = h.services
    client = TestClient(app, raise_server_exceptions=False)
    cases = [run_case(client, h, preset, key, tag=cid) for cid, preset, key, _why, _st in rp.PARITY_CASES]
    for (cid, _p, _k, why, st), row in zip(rp.PARITY_CASES, cases):
        row["case_id"], row["why"], row["expected_status"] = cid, why, st

    key, preset = "2026W18_1A_0516_1_D3", "epsilon_indi_b"
    _a, _r, _raws, (ra0, dec0) = rp.retained(preset, {key})
    shift = 0.5 / 60.0
    geometry = {
        "fov2": (ra0, dec0, 2.0),
        "fov10": (ra0, dec0, 10.0),
        "shifted_0.5arcmin_NE": (ra0 + shift / math.cos(math.radians(dec0)), dec0 + shift, 6.0),
        "off_cutout_4arcmin_E": (ra0 + (4.0 / 60.0) / math.cos(math.radians(dec0)), dec0, 6.0),
    }
    geo_rows = {name: run_case(client, h, preset, key, ra, dec, fov, tag=name) for name, (ra, dec, fov) in geometry.items()}

    versions = {"python": platform.python_version()}
    for pkg in ("fastapi", "starlette", "pydantic", "httpx", "numpy", "astropy", "pillow"):
        versions[pkg] = metadata.version(pkg)
    evidence = {
        "generated_by": "qa/overnight-backend/n5_parity_evidence.py",
        "processing_version": proc.PROCESSING_VERSION,
        "versions": versions,
        "tolerances": "exact: record JSON equal field-by-field and PNG bytes equal (sha256); no float tolerance used",
        "cases": cases,
        "geometry_matrix": geo_rows,
    }
    (OUT / "n5_parity_evidence.json").write_text(json.dumps(evidence, indent=1) + "\n")

    fixture = {
        "description": "One SPHEREx observation requested at different geometries. frame_key is identical; "
                       "geometry, grid_id and image bytes are not. A client frame cache must key on the full "
                       "request identity, not frame_key. Real retained Eps Ind B cutout via the live route; "
                       "hashes only, no pixels.",
        "frame_key": key,
        "requests": [
            {
                "name": name,
                "request_identity": {
                    "observation_id": r["descriptor"]["observation_id"], "detector": r["descriptor"]["detector"],
                    "collection_id": r["descriptor"]["collection_id"],
                    "source_url": json.loads(json.dumps(r["cutout_url"])).split("?", 1)[0],
                    "ra_deg": r["request"]["ra_deg"], "dec_deg": r["request"]["dec_deg"],
                    "fov_arcmin": r["request"]["fov_arcmin"], "grid_px": rp.GRID_PX,
                    "processing_version": r["record"]["processing_version"],
                },
                "expect": {
                    "registration.grid_id": r["record"]["grid_id"],
                    "registration.scale_arcsec_per_px": r["record"]["scale_arcsec_per_px"],
                    "quality.status": r["record"]["quality_status"],
                    "wavelength_um": r["record"]["wavelength_um"],
                    "image_png_sha256": r["route_png_sha256"],
                },
            }
            for name, r in geo_rows.items()
        ],
    }
    (OUT / "fixtures").mkdir(exist_ok=True)
    (OUT / "fixtures" / "request_identity_fixture.json").write_text(json.dumps(fixture, indent=1) + "\n")

    print(f"{'case':18s} {'status':12s} {'wl_um':>7s} {'route==direct':>13s}  png sha256 (first 12)")
    for row in cases:
        wl = row["record"]["wavelength_um"]
        print(f"{row['case_id']:18s} {row['record']['quality_status']:12s} {wl if wl is None else round(wl, 4)!s:>7s} "
              f"{row['route_equals_direct']!s:>13s}  {row['route_png_sha256'][:12]}"
              + (f"  curated png equal={row['curated_per_frame']['png_equal']}" if "curated_per_frame" in row else ""))
    for name, row in geo_rows.items():
        print(f"{name:22s} grid_id={row['record']['grid_id']} status={row['record']['quality_status']} "
              f"route==direct={row['route_equals_direct']} png={row['route_png_sha256'][:12]}")


if __name__ == "__main__":
    main()
