"""Shared public-contract pieces: schema version, error envelope, error codes.

The error envelope is defined by docs/INTEGRATION_CONTRACT.md ("Error and loading
behavior"). Every API failure, including unknown /api routes, returns this shape as
JSON; the SPA fallback must never answer an /api path with HTML.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal[1] = 1


class ErrorCode(str, Enum):
    # Contract-listed codes
    INVALID_COORDINATES = "INVALID_COORDINATES"
    INVALID_FIELD_OF_VIEW = "INVALID_FIELD_OF_VIEW"
    INVALID_FRAME_TOKEN = "INVALID_FRAME_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    UNSUPPORTED_DATA = "UNSUPPORTED_DATA"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    # Additive codes (contract says "expected codes include"); documented in
    # backend/tests/api/README.md.
    INVALID_LIMIT = "INVALID_LIMIT"
    INVALID_COLLECTION = "INVALID_COLLECTION"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
    PROCESSOR_UNAVAILABLE = "PROCESSOR_UNAVAILABLE"
    SERVICE_MISCONFIGURED = "SERVICE_MISCONFIGURED"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str = Field(description="Short, user-presentable summary. No secrets or stack traces.")
    retryable: bool
    details: dict[str, Any] | None = Field(
        default=None, description="Optional non-sensitive details (e.g. which field failed)."
    )


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    schema_version: Literal[1] = SCHEMA_VERSION
    request_id: str
    error: ErrorBody
