"""Perigee API, candidate B (FastAPI). Run from the repo root: ``uvicorn backend.main:app``.

All public routes live under ``/api/v1``. Every failure, including unknown ``/api``
paths, wrong methods, malformed JSON and oversized bodies, is the contract's JSON error
envelope; nothing here can produce HTML.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.models.common import ErrorBody, ErrorCode, ErrorEnvelope
from backend.models.errors import ERROR_TABLE, PAYLOAD_TOO_LARGE_STATUS, ApiError
from backend.routes import frames, health, search
from backend.security.config import get_settings

API_PREFIX = "/api/v1"
_CLIENT_RID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
log = logging.getLogger("perigee.api")
logging.getLogger("httpx").setLevel(logging.WARNING)


def envelope(request_id: str, code: ErrorCode, message: str, retryable: bool, details: Any,
             status: int, headers: Dict[str, str] | None = None) -> JSONResponse:
    body = ErrorEnvelope(request_id=request_id,
                         error=ErrorBody(code=code, message=message, retryable=retryable, details=details))
    h = {"Cache-Control": "no-store", "X-Request-ID": request_id, **(headers or {})}
    return JSONResponse(body.model_dump(mode="json"), status_code=status, headers=h)


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or uuid.uuid4().hex


class BodyLimitAndRequestId:
    """Pure ASGI middleware: assigns a request id and caps request bodies (no buffering)."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        supplied = headers.get("x-request-id", "")
        rid = supplied if _CLIENT_RID.match(supplied) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = rid

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                hs = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"]
                hs.append((b"x-request-id", rid.encode()))
                message = {**message, "headers": hs}
            await send(message)

        clen = headers.get("content-length", "")
        too_big = clen.isdigit() and int(clen) > self.max_bytes
        seen = 0

        async def limited_receive():
            nonlocal seen
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > self.max_bytes:
                    raise _BodyTooLarge()
            return msg

        if not too_big:
            try:
                return await self.app(scope, limited_receive, send_with_id)
            except _BodyTooLarge:
                pass
        resp = envelope(rid, ErrorCode.INVALID_REQUEST, f"Request body exceeds {self.max_bytes} bytes.",
                        False, {"max_bytes": self.max_bytes}, PAYLOAD_TOO_LARGE_STATUS)
        await resp(scope, receive, send)


class _BodyTooLarge(Exception):
    pass


_FIELD_CODES = (
    ({"ra_deg", "dec_deg"}, ErrorCode.INVALID_COORDINATES),
    ({"fov_arcmin"}, ErrorCode.INVALID_FIELD_OF_VIEW),
    ({"limit"}, ErrorCode.INVALID_LIMIT),
    ({"collection_ids"}, ErrorCode.INVALID_COLLECTION),
    ({"frame_token"}, ErrorCode.INVALID_FRAME_TOKEN),
    ({"schema_version"}, ErrorCode.UNSUPPORTED_SCHEMA_VERSION),
)


def classify_validation(errors: List[Dict[str, Any]]) -> tuple[ErrorCode, List[Dict[str, str]]]:
    fields = []
    for e in errors:
        loc = [str(p) for p in e.get("loc", ()) if p != "body"]
        fields.append({"field": loc[0] if loc else "body", "problem": str(e.get("type", "invalid"))})
    if any(e.get("type") in ("json_invalid", "model_attributes_type", "dict_type") or
           (e.get("type") == "missing" and tuple(e.get("loc", ())) == ("body",)) for e in errors):
        return ErrorCode.INVALID_REQUEST, fields
    names = {f["field"] for f in fields}
    for keys, code in _FIELD_CODES:
        if names & keys:
            return code, [f for f in fields if f["field"] in keys]
    return ErrorCode.INVALID_REQUEST, fields


def create_app() -> FastAPI:
    app = FastAPI(title="Perigee API (candidate B)", version=health.API_VERSION,
                  docs_url=f"{API_PREFIX}/docs", redoc_url=None, openapi_url=f"{API_PREFIX}/openapi.json")

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return envelope(_rid(request), exc.code, exc.message, bool(exc.retryable),
                        dict(exc.details) if exc.details else None, int(exc.status), dict(exc.headers or {}))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        code, fields = classify_validation(list(exc.errors()))
        status, retry, msg = ERROR_TABLE[code]
        if code == ErrorCode.INVALID_FRAME_TOKEN:
            details = {"reason": "format"}
        else:
            details = {"fields": fields}
        return envelope(_rid(request), code, msg, retry, details, status)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = {404: ErrorCode.NOT_FOUND, 405: ErrorCode.METHOD_NOT_ALLOWED}.get(
            exc.status_code, ErrorCode.INVALID_REQUEST if exc.status_code < 500 else ErrorCode.INTERNAL_ERROR)
        _, retry, msg = ERROR_TABLE[code]
        headers = {"Allow": exc.headers["Allow"]} if exc.headers and "Allow" in exc.headers else None
        return envelope(_rid(request), code, msg, retry, None, exc.status_code, headers)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        log.exception("unhandled error")
        _, retry, msg = ERROR_TABLE[ErrorCode.INTERNAL_ERROR]
        return envelope(_rid(request), ErrorCode.INTERNAL_ERROR, msg, retry, None, 500)

    app.include_router(health.router, prefix=API_PREFIX, tags=["health"])
    app.include_router(search.router, prefix=API_PREFIX, tags=["search"])
    app.include_router(frames.router, prefix=API_PREFIX, tags=["frame"])

    # Catalog/assets routes (worker 08, backend/routes/catalog.py) are owned elsewhere and
    # mounted when present so this branch also runs standalone.
    try:
        from backend.routes import catalog  # noqa: WPS433
    except ImportError as exc:
        log.warning("catalog routes not mounted: %s", exc)
        app.state.catalog_mounted = False
    else:
        app.include_router(catalog.router, prefix=API_PREFIX, tags=["catalog"])
        app.state.catalog_mounted = True

    app.add_middleware(BodyLimitAndRequestId, max_bytes=get_settings().max_request_body_bytes)
    return app


app = create_app()  # Vercel/uvicorn entrypoint: backend.main:app
