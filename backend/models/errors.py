"""Candidate B: one exception type for every expected API failure.

Each ``ErrorCode`` has exactly one HTTP status and one retryable default, kept in
``ERROR_TABLE`` so behavior is predictable and testable in one place. Routes raise
``ApiError``; ``backend.main`` renders it as the contract's JSON error envelope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

from .common import ErrorCode

# code -> (HTTP status, retryable, default user-facing message)
ERROR_TABLE: Dict[ErrorCode, Tuple[int, bool, str]] = {
    ErrorCode.INVALID_COORDINATES: (
        422, False, "RA must be a finite number in [0, 360) and Dec in [-90, 90]."),
    ErrorCode.INVALID_FIELD_OF_VIEW: (
        422, False, "Field of view must be a number from 2 to 10 arcminutes."),
    ErrorCode.INVALID_LIMIT: (422, False, "Limit must be a whole number from 1 to 48."),
    ErrorCode.INVALID_COLLECTION: (422, False, "Unsupported collection. Use spherex_dr1 or spherex_qr3."),
    ErrorCode.INVALID_REQUEST: (400, False, "The request body is not valid JSON for this endpoint."),
    ErrorCode.UNSUPPORTED_SCHEMA_VERSION: (422, False, "Only schema_version 1 is supported."),
    ErrorCode.INVALID_FRAME_TOKEN: (400, False, "The frame token is invalid. Run the search again."),
    ErrorCode.TOKEN_EXPIRED: (
        400, False,
        "This frame link has expired. Run the search again to refresh it; your notes are kept."),
    ErrorCode.RATE_LIMITED: (429, True, "Too many requests. Wait a moment and try again."),
    ErrorCode.UPSTREAM_UNAVAILABLE: (502, True, "The NASA/IPAC archive is unavailable right now."),
    ErrorCode.UPSTREAM_TIMEOUT: (504, True, "The NASA/IPAC archive did not answer in time."),
    ErrorCode.UNSUPPORTED_DATA: (
        422, False, "The archive returned data this viewer cannot process."),
    ErrorCode.PROCESSING_FAILED: (500, False, "Processing this frame failed."),
    ErrorCode.PROCESSOR_UNAVAILABLE: (
        503, False, "Frame processing is not installed on this deployment yet."),
    ErrorCode.SERVICE_MISCONFIGURED: (
        503, False, "The service is not configured to issue frame links."),
    ErrorCode.NOT_FOUND: (404, False, "No such API route."),
    ErrorCode.METHOD_NOT_ALLOWED: (405, False, "Method not allowed for this API route."),
    ErrorCode.INTERNAL_ERROR: (500, False, "Unexpected server error."),
}

PAYLOAD_TOO_LARGE_STATUS = 413


@dataclass
class ApiError(Exception):
    code: ErrorCode
    message: Optional[str] = None
    details: Optional[Mapping[str, Any]] = None
    status: Optional[int] = None
    retryable: Optional[bool] = None
    headers: Optional[Mapping[str, str]] = None

    def __post_init__(self) -> None:
        default_status, default_retry, default_msg = ERROR_TABLE[self.code]
        if self.status is None:
            self.status = default_status
        if self.retryable is None:
            self.retryable = default_retry
        if self.message is None:
            self.message = default_msg
        super().__init__(f"{self.code.value}: {self.message}")
