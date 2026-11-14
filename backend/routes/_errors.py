"""Error envelope plumbing shared by every Perigee API route.

All failures leave the API as the contract error envelope (JSON), including FastAPI
validation errors, unknown /api paths, wrong methods and unexpected exceptions.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.models.common import ErrorBody, ErrorCode, ErrorEnvelope

log = logging.getLogger("perigee.api")


class ApiError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        http_status: int,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = retryable
        self.details = details


def request_id_of(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if not rid:
        rid = uuid.uuid4().hex
        request.state.request_id = rid
    return rid


def error_response(
    request: Request,
    code: ErrorCode,
    message: str,
    *,
    http_status: int,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    envelope = ErrorEnvelope(
        request_id=request_id_of(request),
        error=ErrorBody(code=code, message=message, retryable=retryable, details=details),
    )
    headers = {"Cache-Control": "no-store"}
    if code == ErrorCode.RATE_LIMITED:
        headers["Retry-After"] = "30"
    return JSONResponse(envelope.model_dump(mode="json"), status_code=http_status, headers=headers)


# Field -> public error code for request validation failures.
_FIELD_CODES: dict[str, ErrorCode] = {
    "ra_deg": ErrorCode.INVALID_COORDINATES,
    "dec_deg": ErrorCode.INVALID_COORDINATES,
    "fov_arcmin": ErrorCode.INVALID_FIELD_OF_VIEW,
    "limit": ErrorCode.INVALID_LIMIT,
    "collection_ids": ErrorCode.INVALID_COLLECTION,
    "schema_version": ErrorCode.UNSUPPORTED_SCHEMA_VERSION,
    "frame_token": ErrorCode.INVALID_FRAME_TOKEN,
}

_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_COORDINATES: "RA must be a finite number in [0, 360) and Dec in [-90, 90].",
    ErrorCode.INVALID_FIELD_OF_VIEW: "Field of view must be a number from 2 to 10 arcminutes.",
    ErrorCode.INVALID_LIMIT: "limit must be an integer from 1 to 48.",
    ErrorCode.INVALID_COLLECTION: "collection_ids must be a non-empty subset of the supported collections.",
    ErrorCode.UNSUPPORTED_SCHEMA_VERSION: "schema_version must be 1.",
    ErrorCode.INVALID_FRAME_TOKEN: "The frame token is missing or malformed. Run the search again.",
    ErrorCode.INVALID_REQUEST: "The request body is not valid JSON for this endpoint.",
}

# Priority when several fields fail at once: report the most fundamental first.
_PRIORITY = [
    ErrorCode.INVALID_REQUEST,
    ErrorCode.UNSUPPORTED_SCHEMA_VERSION,
    ErrorCode.INVALID_COORDINATES,
    ErrorCode.INVALID_FIELD_OF_VIEW,
    ErrorCode.INVALID_LIMIT,
    ErrorCode.INVALID_COLLECTION,
    ErrorCode.INVALID_FRAME_TOKEN,
]


def _classify(errors: list[dict[str, Any]]) -> tuple[ErrorCode, list[dict[str, Any]]]:
    codes: list[ErrorCode] = []
    fields: list[dict[str, Any]] = []
    for err in errors:
        loc = [str(p) for p in err.get("loc", ()) if p != "body"]
        etype = str(err.get("type", ""))
        field = loc[0] if loc else None
        if etype == "json_invalid":
            field, loc = None, []
        if etype in {"json_invalid", "model_attributes_type", "dict_type", "missing"} and not field:
            code = ErrorCode.INVALID_REQUEST
        elif etype == "extra_forbidden":
            code = ErrorCode.INVALID_REQUEST
        else:
            code = _FIELD_CODES.get(field or "", ErrorCode.INVALID_REQUEST)
        codes.append(code)
        fields.append({"field": ".".join(loc) or None, "problem": etype})
    best = min(codes, key=_PRIORITY.index) if codes else ErrorCode.INVALID_REQUEST
    return best, fields


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        log.info(
            "api_error code=%s status=%s request_id=%s",
            exc.code.value,
            exc.http_status,
            request_id_of(request),
        )
        return error_response(
            request,
            exc.code,
            exc.message,
            http_status=exc.http_status,
            retryable=exc.retryable,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        code, fields = _classify(list(exc.errors()))
        status = 400 if code == ErrorCode.INVALID_REQUEST or code == ErrorCode.INVALID_FRAME_TOKEN else 422
        return error_response(
            request,
            code,
            _MESSAGES.get(code, "Invalid request."),
            http_status=status,
            details={"fields": fields},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return error_response(
                request, ErrorCode.NOT_FOUND, "No such API route.", http_status=404
            )
        if exc.status_code == 405:
            return error_response(
                request,
                ErrorCode.METHOD_NOT_ALLOWED,
                "Method not allowed for this API route.",
                http_status=405,
            )
        code = ErrorCode.INVALID_REQUEST if exc.status_code < 500 else ErrorCode.INTERNAL_ERROR
        return error_response(request, code, "Request failed.", http_status=exc.status_code)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        log.exception("unhandled error request_id=%s", request_id_of(request))
        return error_response(
            request,
            ErrorCode.INTERNAL_ERROR,
            "Unexpected server error.",
            http_status=500,
            retryable=True,
        )
