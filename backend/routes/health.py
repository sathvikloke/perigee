"""GET /api/v1/health (candidate B). No upstream calls, no secrets."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.models.health import HealthResponse
from backend.models.search import FOV_MAX_ARCMIN, FOV_MIN_ARCMIN, LIMIT_MAX, SUPPORTED_COLLECTIONS
from backend.security.context import get_state

API_VERSION = "1.0.0-b"
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> JSONResponse:
    from backend.routes.frames import resolve_processor  # avoid import cycle at module load

    settings = get_state().settings()
    processor = resolve_processor()
    signing = settings.signing_enabled
    caps = {
        "candidate": "b",
        "search": signing,
        "frame": signing and processor is not None,
        "frame_tokens": settings.token_secret_source,  # env | dev_fallback | missing | too_short
        "processor": getattr(processor, "name", None) or "not_installed",
        "collections": list(SUPPORTED_COLLECTIONS),
        "fov_arcmin_range": f"{FOV_MIN_ARCMIN:g}-{FOV_MAX_ARCMIN:g}",
        "max_limit": LIMIT_MAX,
        "token_ttl_s": settings.token_ttl_s,
        "request_budget_s": settings.request_budget_s,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
    }
    ok = signing and processor is not None and settings.token_secret_source == "env"
    resp = HealthResponse(
        request_id=request.state.request_id,
        api_version=API_VERSION,
        status="ok" if ok else "degraded",
        capabilities=caps,
        checked_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )
    return JSONResponse(resp.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
