"""Perigee API (FastAPI). Run locally: ``uvicorn backend.main:app --reload``.

All public routes live under ``/api/v1``. Every API failure, including unknown
``/api/...`` paths, returns the JSON error envelope (never the SPA's HTML).
"""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import FastAPI, Request

from backend.routes import frames, health, search
from backend.routes._errors import install_error_handlers

API_PREFIX = "/api/v1"
_CLIENT_RID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(
    title="Perigee API",
    version=health.API_VERSION,
    description="SPHEREx coordinate search and single-frame processing for the Perigee viewer.",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=None,
    openapi_url=f"{API_PREFIX}/openapi.json",
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    # A client-supplied X-Request-ID is echoed only if it is short and plain; otherwise
    # the server generates one. It identifies a response, it is not an auth token.
    supplied = request.headers.get("x-request-id", "")
    request.state.request_id = supplied if _CLIENT_RID.match(supplied) else uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


install_error_handlers(app)

app.include_router(health.router, prefix=API_PREFIX, tags=["health"])
app.include_router(search.router, prefix=API_PREFIX, tags=["search"])
app.include_router(frames.router, prefix=API_PREFIX, tags=["frame"])

# --- Integration point: catalog/assets routes (worker 08 / Suhrit) -----------------
# backend/routes/catalog.py will export ``router = APIRouter()`` with paths relative to
# the prefix (/presets, /presets/{preset_id}/frames, /cases/{case_id}, /assets/{asset_id}).
# At integration, uncomment:
#
#     from backend.routes import catalog
#     app.include_router(catalog.router, prefix=API_PREFIX, tags=["catalog"])
# -----------------------------------------------------------------------------------
