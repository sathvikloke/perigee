"""POST /api/v1/frame (candidate B).

Order of work, each step bounded by one soft request budget:

1. rate limit, then verify the signed frame token (nothing is fetched for a bad token);
2. resolve the processor through :class:`FrameProcessor` (a Protocol, so processor A
   or B can be plugged in); if none is installed -> 503 PROCESSOR_UNAVAILABLE;
3. fetch the IRSA cutout of the token-bound source URL (allowlist, redirects, byte cap);
4. refuse to start processing if less than ``processing_reserve_s`` of budget is left;
5. process in a worker thread, normalize the record to the public FrameRecord, validate.

Failure classes stay distinct: token (400), upstream (502/503/504), unsupported or
corrupt data (422 UNSUPPORTED_DATA), processor bug or contract mismatch (500).
"""

from __future__ import annotations

import base64
import logging
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.models.common import ErrorCode
from backend.models.errors import ApiError
from backend.models.frame import FrameRecord, FrameRequest, FrameResponse
from backend.security.context import enforce_rate_limit, get_state, upstream_error
from backend.security.egress import Budget, UpstreamFailure, fetch
from backend.security.tokens import FrameClaims, iso_utc, verify_frame_token

router = APIRouter()
log = logging.getLogger("perigee.frame")

# Cutout edge = FOV diagonal plus 10 % so the corners of the square display grid are sampled.
CUTOUT_FACTOR = math.sqrt(2.0) * 1.1
FITS_MAGIC = b"SIMPLE  ="


# --------------------------------------------------------------------------- processor seam


@dataclass(frozen=True)
class ProcessJob:
    query_ra_deg: float
    query_dec_deg: float
    fov_arcmin: float
    observation_id: str
    detector: Optional[int]
    collection_id: str
    source_url: str
    cutout_url: str
    retrieved_at_utc: str


@dataclass
class ProcessorOutput:
    record: Dict[str, Any]
    png_bytes: bytes
    flag_png_bytes: Optional[bytes]


class ProcessorRejected(Exception):
    """Raised by adapters: ``kind`` is 'unsupported' (bad/corrupt/mismatched data) or 'failed'."""

    def __init__(self, kind: str, detail: str):
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


@runtime_checkable
class FrameProcessor(Protocol):
    name: str

    def __call__(self, fits_bytes: bytes, job: ProcessJob) -> ProcessorOutput: ...


class ProcessFrameAdapter:
    """Adapter for ``backend.data.process.process_frame(fits_bytes, FrameInput)``.

    Works for any processor exposing that signature (processor A today). Exceptions are
    classified by class name so the API does not import processor-specific types:
    ``*Unsupported*``/``*Integrity*`` -> unsupported data; anything else -> failed.
    """

    def __init__(self, module: Any):
        self._m = module
        self.name = getattr(module, "PROCESSING_VERSION", module.__name__)

    def __call__(self, fits_bytes: bytes, job: ProcessJob) -> ProcessorOutput:
        meta = self._m.FrameInput(
            query_ra_deg=job.query_ra_deg, query_dec_deg=job.query_dec_deg, fov_arcmin=job.fov_arcmin,
            source_url=job.source_url, observation_id=job.observation_id, collection_id=job.collection_id,
            detector=job.detector, cutout_url=job.cutout_url, retrieved_at_utc=job.retrieved_at_utc,
            retrieved_at_basis="API server clock at cutout download",
        )
        try:
            out = self._m.process_frame(fits_bytes, meta)
        except Exception as exc:  # classify without importing processor types
            names = " ".join(c.__name__ for c in type(exc).__mro__)
            kind = "unsupported" if ("Unsupported" in names or "Integrity" in names) else "failed"
            raise ProcessorRejected(kind, f"{type(exc).__name__}: {exc}"[:300]) from exc
        return ProcessorOutput(out.record, out.png_bytes, getattr(out, "flag_png_bytes", None))


def load_default_processor() -> Optional[FrameProcessor]:
    try:
        from backend.data import process as module  # noqa: WPS433 (optional dependency)
    except ImportError:
        return None
    if not hasattr(module, "process_frame") or not hasattr(module, "FrameInput"):
        return None
    return ProcessFrameAdapter(module)


_cached: Dict[str, Optional[FrameProcessor]] = {}


def resolve_processor() -> Optional[FrameProcessor]:
    loader = get_state().processor_loader
    if loader is not None:
        return loader()
    if "default" not in _cached:
        _cached["default"] = load_default_processor()
    return _cached["default"]


# --------------------------------------------------------------------------- record normalization


def _data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def normalize_record(out: ProcessorOutput, claims: FrameClaims, cutout_url: str, retrieved_at: str) -> Dict[str, Any]:
    """Fill API-owned fields and alias processor names onto the public FrameRecord names.

    Processor extras are kept (sub-models allow extra keys). Never invents science values.
    """
    r = dict(out.record)
    r.setdefault("frame_key", claims.frame_key)
    r.setdefault("frame_id", r["frame_key"])
    r.setdefault("observation_id", claims.observation_id)
    r.setdefault("detector", claims.detector)
    if not r.get("collection_id"):
        r["collection_id"] = claims.collection_id
    if not r.get("source_url"):
        r["source_url"] = claims.source_url

    img = dict(r.get("image") or {})
    img["src"] = _data_url(out.png_bytes)
    img.setdefault("media_type", "image/png")
    r["image"] = img
    if r.get("flag_image") is not None and out.flag_png_bytes:
        fi = dict(r["flag_image"])
        fi["src"] = _data_url(out.flag_png_bytes)
        r["flag_image"] = fi
    else:
        r["flag_image"] = None

    reg = dict(r.get("registration") or {})
    if "scale_arcsec_per_pixel" not in reg:
        reg["scale_arcsec_per_pixel"] = reg.get("scale_arcsec_per_px")
    r["registration"] = reg

    ds = dict(r.get("display_scale") or {})
    if "limits" not in ds and ("low" in ds or "high" in ds):
        ds["limits"] = {"low": ds.get("low"), "high": ds.get("high")}
    if "comparable_brightness" not in ds and ds.get("mode") in ("shared", "per_frame"):
        ds["comparable_brightness"] = ds["mode"] == "shared"
    r["display_scale"] = ds

    if r.get("marker") is not None:
        mk = dict(r["marker"])
        if "epoch" not in mk:
            mk["epoch"] = mk.get("epoch_utc") or (f"MJD {mk['epoch_mjd']}" if mk.get("epoch_mjd") else None)
        r["marker"] = mk

    pv = dict(r.get("provenance") or {})
    pv.setdefault("data_origin", "nasa_archive")
    pv.setdefault("retrieved_at_utc", pv.get("retrieved_at") or retrieved_at)
    pv.setdefault("original_url", claims.source_url)
    pv.setdefault("cutout_url", cutout_url)
    pv.setdefault("file_sha256", pv.get("sha256"))
    pv.setdefault("processing_version", "unknown")
    pv.setdefault("acknowledgments", [])
    r["provenance"] = pv
    r.setdefault("limitations", [])
    return r


# --------------------------------------------------------------------------- route


def cutout_url_for(claims: FrameClaims) -> str:
    size_deg = round(claims.fov_arcmin / 60.0 * CUTOUT_FACTOR, 6)
    q = urlencode({"center": f"{claims.ra_deg!r},{claims.dec_deg!r}", "size": f"{size_deg:.6f}"})
    return f"{claims.source_url}?{q}"


@router.post("/frame", response_model=FrameResponse)
async def frame(body: FrameRequest, request: Request) -> JSONResponse:
    st = get_state()
    settings = st.settings()
    enforce_rate_limit(request, "frame", settings.frame_per_minute)
    budget = Budget(settings.request_budget_s)
    claims = verify_frame_token(settings, body.frame_token, time.time())

    processor = resolve_processor()
    if processor is None:
        raise ApiError(ErrorCode.PROCESSOR_UNAVAILABLE, details={"missing": "backend.data.process_frame"})

    cutout_url = cutout_url_for(claims)
    t_fetch = time.monotonic()
    try:
        async with st.client_factory() as client:
            res = await fetch(client, settings, cutout_url, budget=budget,
                              read_timeout=settings.frame_read_timeout_s, max_bytes=settings.max_fits_bytes)
    except UpstreamFailure as exc:
        log.warning("frame fetch failed %s %s", claims.frame_key, exc)
        raise upstream_error(exc, frame_key=claims.frame_key) from None
    fetch_ms = int((time.monotonic() - t_fetch) * 1000)
    retrieved_at = iso_utc(time.time())

    if not res.body.startswith(FITS_MAGIC):
        raise ApiError(ErrorCode.UNSUPPORTED_DATA, details={"reason": "not_fits", "frame_key": claims.frame_key})
    if budget.remaining() < settings.processing_reserve_s:
        raise ApiError(ErrorCode.UPSTREAM_TIMEOUT, details={
            "reason": "budget_exhausted_before_processing", "fetch_ms": fetch_ms, "frame_key": claims.frame_key})

    job = ProcessJob(
        query_ra_deg=claims.ra_deg, query_dec_deg=claims.dec_deg, fov_arcmin=claims.fov_arcmin,
        observation_id=claims.observation_id, detector=claims.detector, collection_id=claims.collection_id,
        source_url=claims.source_url, cutout_url=cutout_url, retrieved_at_utc=retrieved_at,
    )
    t_proc = time.monotonic()
    try:
        out = await run_in_threadpool(processor, res.body, job)
    except ProcessorRejected as exc:
        log.warning("processor rejected %s: %s", claims.frame_key, exc.detail)
        code = ErrorCode.UNSUPPORTED_DATA if exc.kind == "unsupported" else ErrorCode.PROCESSING_FAILED
        raise ApiError(code, details={"frame_key": claims.frame_key}) from None
    except Exception as exc:  # adapter bug: never leak a traceback
        log.exception("processor crashed %s", claims.frame_key)
        raise ApiError(ErrorCode.PROCESSING_FAILED, details={"frame_key": claims.frame_key}) from exc
    process_ms = int((time.monotonic() - t_proc) * 1000)

    record = normalize_record(out, claims, cutout_url, retrieved_at)
    if record.get("observation_id") != claims.observation_id or record.get("detector") != claims.detector:
        raise ApiError(ErrorCode.UNSUPPORTED_DATA, details={"reason": "identity_mismatch",
                                                            "frame_key": claims.frame_key})
    try:
        frame_record = FrameRecord.model_validate(record)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})[:10]
        log.error("processor record violates FrameRecord: %s", fields)
        raise ApiError(ErrorCode.PROCESSING_FAILED, details={"reason": "contract_mismatch", "fields": fields}) from None

    resp = FrameResponse(request_id=request.state.request_id, frame=frame_record,
                         timing_ms={"fetch": fetch_ms, "process": process_ms, "total": budget.elapsed_ms(),
                                    "fits_bytes": len(res.body), "attempts": res.attempts})
    return JSONResponse(resp.model_dump(mode="json"), headers={
        "Cache-Control": "no-store",
        "Server-Timing": f"fetch;dur={fetch_ms}, process;dur={process_ms}",
    })
