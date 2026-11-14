"""Typed failures raised by the data adapter.

Each error carries one of the public error codes from docs/INTEGRATION_CONTRACT.md so the
API layer can map it straight into the shared error envelope without guessing.

    code                  HTTP   retryable   meaning
    INVALID_COORDINATES   400    no          RA/Dec missing, non-finite or out of range
    INVALID_FIELD_OF_VIEW 400    no          field of view outside 2-10 arcmin
    INVALID_REQUEST       400    no          bad limit or unsupported collection (proposed code, see handoff)
    UPSTREAM_UNAVAILABLE  502    yes         IRSA answered with an error, an HTML page, or nothing usable
    UPSTREAM_TIMEOUT      504    yes         IRSA did not answer inside the time budget
    UNSUPPORTED_DATA      422    no          bytes are not a SPHEREx Level 2 FITS file we can read
    PROCESSING_FAILED     500    no          our own processing broke on otherwise valid input

Messages are short and safe to show a user. `details` never contains file paths, secrets
or stack traces.
"""
from __future__ import annotations

from typing import Any


class DataError(Exception):
    code = "PROCESSING_FAILED"
    http_status = 500
    retryable = False

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"code": self.code, "message": self.message, "retryable": self.retryable}
        if self.details:
            out["details"] = self.details
        return out


class InvalidCoordinates(DataError):
    code = "INVALID_COORDINATES"
    http_status = 400


class InvalidFieldOfView(DataError):
    code = "INVALID_FIELD_OF_VIEW"
    http_status = 400


class InvalidRequest(DataError):
    """Bad `limit` or a collection outside the allowlist. Not yet in the contract's code list;
    the API owner may map it to a 422 validation error instead."""

    code = "INVALID_REQUEST"
    http_status = 400


class UpstreamUnavailable(DataError):
    code = "UPSTREAM_UNAVAILABLE"
    http_status = 502
    retryable = True


class UpstreamTimeout(DataError):
    code = "UPSTREAM_TIMEOUT"
    http_status = 504
    retryable = True


class UnsupportedData(DataError):
    code = "UNSUPPORTED_DATA"
    http_status = 422


class ProcessingFailed(DataError):
    code = "PROCESSING_FAILED"
    http_status = 500
