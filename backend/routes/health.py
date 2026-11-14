"""GET /api/v1/health: version, service state and capabilities. No secrets."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from backend.models.health import HealthResponse
from backend.models.search import FOV_MAX_ARCMIN, FOV_MIN_ARCMIN, LIMIT_MAX, SUPPORTED_COLLECTIONS

from ._adapters import Services, resolve_services
from ._errors import request_id_of

API_VERSION = "0.1.0"

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request, services: Services = Depends(resolve_services)):
    signing = services.settings.token_secret is not None
    processor = services.processor is not None
    body = HealthResponse(
        request_id=request_id_of(request),
        api_version=API_VERSION,
        status="ok" if signing and processor else "degraded",
        capabilities={
            "search": signing,
            "frame": signing and processor,
            "frame_processor": services.processor_source or "not_installed",
            "archive_search": services.search_source,
            "token_signing": services.settings.token_secret_source,
            "collections": list(SUPPORTED_COLLECTIONS),
            "fov_arcmin_min": FOV_MIN_ARCMIN,
            "fov_arcmin_max": FOV_MAX_ARCMIN,
            "limit_max": LIMIT_MAX,
        },
        checked_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    return JSONResponse(body.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
