"""POST /api/v1/frame: verify token -> allowlisted cutout fetch -> processor -> FrameRecord.

Order matters: the token is verified (signature, then expiry) before any network
access; the processor's availability is checked before fetching so no upstream
bandwidth is spent when processing cannot happen.

Distinct outcomes (each a different public code):
  malformed/tampered token -> 400 INVALID_FRAME_TOKEN
  authentic but expired    -> 400 TOKEN_EXPIRED (details.action = "refresh_search")
  archive down / 5xx / HTML-> 502 UPSTREAM_UNAVAILABLE
  archive slow             -> 504 UPSTREAM_TIMEOUT
  not FITS / over byte cap -> 502 UNSUPPORTED_DATA (upstream content) or 422 from processor
  processor raised         -> 500 PROCESSING_FAILED
  processor not installed  -> 503 PROCESSOR_UNAVAILABLE
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import math
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from backend.models.common import ErrorCode
from backend.models.frame import FrameRecord, FrameRequest, FrameResponse
from backend.security.tokens import ExpiredToken, FrameClaims, InvalidToken, verify_token
from backend.security.upstream import (
    UpstreamTimeout,
    UpstreamTooLarge,
    UpstreamUnavailable,
    UrlNotAllowed,
    bounded_get,
    is_allowed_source_url,
    looks_like_html,
)

from ._adapters import Services, resolve_services
from ._errors import ApiError, request_id_of

router = APIRouter()

GRID_PX = 256
# Cutout side = FOV x this factor, so a north-up display square is fully covered for
# any detector rotation (needs >= sqrt(2)); the processor crops to the fixed grid.
CUTOUT_MARGIN = 1.5
FITS_MAGIC = b"SIMPLE  ="
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 2 * 1024 * 1024


def cutout_url_for(claims: FrameClaims) -> str:
    size_deg = claims.fov_arcmin * CUTOUT_MARGIN / 60.0
    query = urlencode(
        {"center": f"{claims.ra_deg!r},{claims.dec_deg!r}", "size": f"{size_deg:.6f}"}
    )
    return f"{claims.source_url}?{query}"


def _verify(services: Services, token: str) -> FrameClaims:
    secret = services.settings.token_secret
    if secret is None:
        raise ApiError(
            ErrorCode.SERVICE_MISCONFIGURED,
            "Frame signing is not configured on this deployment.",
            http_status=503,
            details={"token_signing": services.settings.token_secret_source},
        )
    try:
        claims = verify_token(secret, token)
    except ExpiredToken as exc:
        raise ApiError(
            ErrorCode.TOKEN_EXPIRED,
            "This frame link has expired. Run the search again to refresh it; your notes are kept.",
            http_status=400,
            retryable=False,
            details={
                "action": "refresh_search",
                "expired_at_utc": datetime.fromtimestamp(exc.expired_at, timezone.utc).isoformat(
                    timespec="seconds"
                ),
            },
        ) from exc
    except InvalidToken as exc:
        raise ApiError(
            ErrorCode.INVALID_FRAME_TOKEN,
            "The frame token is invalid. Run the search again.",
            http_status=400,
            retryable=False,
        ) from exc
    if not is_allowed_source_url(claims.source_url):
        # Authentic token but a source outside today's allowlist (e.g. policy changed).
        raise ApiError(
            ErrorCode.INVALID_FRAME_TOKEN,
            "The frame source is not allowed by this deployment.",
            http_status=400,
            details={"reason": "source_not_allowlisted"},
        )
    return claims


def _data_url(png: object, field: str) -> str:
    if not isinstance(png, (bytes, bytearray)) or not bytes(png).startswith(PNG_MAGIC):
        raise ApiError(
            ErrorCode.PROCESSING_FAILED,
            "The processor did not return a PNG image.",
            http_status=500,
            details={"field": field},
        )
    if len(png) > MAX_PNG_BYTES:
        raise ApiError(
            ErrorCode.PROCESSING_FAILED,
            "The processed image exceeded the response size limit.",
            http_status=500,
            details={"field": field, "bytes": len(png)},
        )
    return "data:image/png;base64," + base64.b64encode(bytes(png)).decode("ascii")


def _processor_error(exc: Exception) -> ApiError:
    code_attr = str(getattr(exc, "code", "") or "")
    unsupported = code_attr == "UNSUPPORTED_DATA" or "unsupported" in type(exc).__name__.lower()
    if unsupported:
        return ApiError(
            ErrorCode.UNSUPPORTED_DATA,
            "This archive file could not be read as a supported SPHEREx image.",
            http_status=422,
            details={"stage": "process", "error_type": type(exc).__name__},
        )
    return ApiError(
        ErrorCode.PROCESSING_FAILED,
        "Processing this frame failed.",
        http_status=500,
        retryable=False,
        details={"stage": "process", "error_type": type(exc).__name__},
    )


def build_record(claims: FrameClaims, meta: dict, result: dict) -> FrameRecord:
    if not isinstance(result, dict) or not isinstance(result.get("record"), dict):
        raise ApiError(
            ErrorCode.PROCESSING_FAILED,
            "The processor returned an unexpected result.",
            http_status=500,
            details={"stage": "validate"},
        )
    rec = dict(result["record"])
    # Identity comes from the signed token; the processor may not change it.
    rec["observation_id"] = claims.observation_id
    rec["detector"] = claims.detector if rec.get("detector") is None else rec["detector"]
    rec["frame_key"] = claims.frame_key
    rec["collection_id"] = claims.collection_id
    rec["source_url"] = claims.source_url
    rec.setdefault("frame_id", f"{claims.collection_id}:{claims.frame_key}")
    if rec.get("detector") != claims.detector:
        raise ApiError(
            ErrorCode.PROCESSING_FAILED,
            "Processed detector does not match the requested image.",
            http_status=500,
            details={"stage": "validate", "reason": "detector_mismatch"},
        )
    image = dict(rec.get("image") or {})
    image["src"] = _data_url(result.get("image_png"), "image_png")
    image.setdefault("width", GRID_PX)
    image.setdefault("height", GRID_PX)
    image["media_type"] = "image/png"
    rec["image"] = image
    flag_png = result.get("flag_png")
    if flag_png is None:
        rec["flag_image"] = None
    else:
        flag = dict(rec.get("flag_image") or {})
        flag["src"] = _data_url(flag_png, "flag_png")
        flag.setdefault("width", image["width"])
        flag.setdefault("height", image["height"])
        flag["media_type"] = "image/png"
        rec["flag_image"] = flag
    prov = dict(rec.get("provenance") or {})
    prov["original_url"] = claims.source_url
    prov["cutout_url"] = meta["cutout_url"]
    prov.setdefault("retrieved_at_utc", meta["retrieved_at_utc"])
    prov.setdefault("file_sha256", meta["file_sha256"])
    prov.setdefault("data_origin", "nasa_archive")
    rec["provenance"] = prov
    mjd = rec.get("mjd")
    if isinstance(mjd, float) and not math.isfinite(mjd):
        rec["mjd"] = None
    try:
        return FrameRecord.model_validate(rec)
    except ValidationError as exc:
        raise ApiError(
            ErrorCode.PROCESSING_FAILED,
            "The processor returned a record that does not match the FrameRecord contract.",
            http_status=500,
            details={
                "stage": "validate",
                "fields": [".".join(str(p) for p in e["loc"]) for e in exc.errors()][:20],
            },
        ) from exc


@router.post("/frame", response_model=FrameResponse)
async def frame(body: FrameRequest, request: Request, services: Services = Depends(resolve_services)):
    claims = _verify(services, body.frame_token)
    if services.processor is None:
        raise ApiError(
            ErrorCode.PROCESSOR_UNAVAILABLE,
            "Frame processing is not installed on this deployment yet.",
            http_status=503,
            retryable=False,
            details={"missing": "backend.data.process_frame"},
        )

    settings = services.settings
    started = time.monotonic()
    cutout_url = cutout_url_for(claims)
    try:
        async with services.http_client_factory() as client:
            resp = await bounded_get(
                client,
                cutout_url,
                purpose="data",
                max_bytes=settings.frame_fetch_max_bytes,
                deadline_s=settings.frame_budget_s * 0.6,
            )
    except UpstreamTimeout as exc:
        raise ApiError(
            ErrorCode.UPSTREAM_TIMEOUT,
            "The NASA/IPAC archive did not return this image in time.",
            http_status=504,
            retryable=True,
            details={"stage": "fetch", "reason": exc.reason},
        ) from exc
    except UpstreamTooLarge as exc:
        raise ApiError(
            ErrorCode.UNSUPPORTED_DATA,
            "The archive file was larger than this service accepts.",
            http_status=502,
            details={"stage": "fetch", "reason": exc.reason, "max_bytes": settings.frame_fetch_max_bytes},
        ) from exc
    except UrlNotAllowed as exc:
        raise ApiError(
            ErrorCode.INVALID_FRAME_TOKEN,
            "The frame source is not allowed by this deployment.",
            http_status=400,
            details={"reason": "source_not_allowlisted"},
        ) from exc
    except UpstreamUnavailable as exc:
        raise ApiError(
            ErrorCode.UPSTREAM_UNAVAILABLE,
            "The NASA/IPAC archive could not provide this image right now.",
            http_status=502,
            retryable=exc.status != 404,
            details={"stage": "fetch", "reason": exc.reason, "upstream_status": exc.status},
        ) from exc
    fetch_ms = int((time.monotonic() - started) * 1000)

    data = resp.body
    if looks_like_html(resp.content_type, data):
        raise ApiError(
            ErrorCode.UPSTREAM_UNAVAILABLE,
            "The NASA/IPAC archive returned an error page instead of the image.",
            http_status=502,
            retryable=True,
            details={"stage": "fetch", "reason": "html_body"},
        )
    if not data.startswith(FITS_MAGIC):
        raise ApiError(
            ErrorCode.UNSUPPORTED_DATA,
            "The archive returned data that is not a FITS file.",
            http_status=502,
            details={"stage": "fetch", "reason": "not_fits", "content_type": resp.content_type[:80]},
        )

    meta = {
        "meta_version": 1,
        "observation_id": claims.observation_id,
        "detector": claims.detector,
        "frame_key": claims.frame_key,
        "collection_id": claims.collection_id,
        "source_url": claims.source_url,
        "cutout_url": cutout_url,
        "descriptor_mjd": claims.mjd,
        "descriptor_observed_at_utc": claims.observed_at_utc,
        "query": {"ra_deg": claims.ra_deg, "dec_deg": claims.dec_deg, "fov_arcmin": claims.fov_arcmin},
        "grid": {
            "width": GRID_PX,
            "height": GRID_PX,
            "center_ra_deg": claims.ra_deg,
            "center_dec_deg": claims.dec_deg,
            "fov_arcmin": claims.fov_arcmin,
            "orientation": "north_up_east_left",
        },
        "marker_target": None,
        "wavelength_location": "Query center (RA, Dec) of this live search",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "byte_length": len(data),
    }

    remaining = max(1.0, settings.frame_budget_s - (time.monotonic() - started))
    proc_started = time.monotonic()
    try:
        result = await asyncio.wait_for(
            run_in_threadpool(services.processor, data, dict(meta)), timeout=remaining
        )
    except asyncio.TimeoutError as exc:
        raise ApiError(
            ErrorCode.PROCESSING_FAILED,
            "Processing this frame exceeded the time budget.",
            http_status=500,
            retryable=True,
            details={"stage": "process", "reason": "budget"},
        ) from exc
    except ApiError:
        raise
    except Exception as exc:  # processor-defined errors are mapped, never leaked
        raise _processor_error(exc) from exc
    process_ms = int((time.monotonic() - proc_started) * 1000)

    record = build_record(claims, meta, result)
    response = FrameResponse(
        request_id=request_id_of(request),
        frame=record,
        timing_ms={"fetch": fetch_ms, "process": process_ms},
    )
    return JSONResponse(
        response.model_dump(mode="json"),
        headers={
            "Cache-Control": "no-store",
            "Server-Timing": f"fetch;dur={fetch_ms}, process;dur={process_ms}",
        },
    )
