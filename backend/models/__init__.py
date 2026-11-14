"""Public API contract models (docs/INTEGRATION_CONTRACT.md, version 1)."""

from .common import SCHEMA_VERSION, ErrorBody, ErrorCode, ErrorEnvelope
from .frame import (
    DisplayScale,
    FrameRecord,
    FrameRequest,
    FrameResponse,
    ImageRef,
    Marker,
    Provenance,
    Quality,
    Registration,
)
from .health import HealthResponse
from .search import (
    DEFAULT_COLLECTIONS,
    SUPPORTED_COLLECTIONS,
    NormalizedQuery,
    ObservationDescriptor,
    SearchRequest,
    SearchResponse,
)

__all__ = [
    "SCHEMA_VERSION",
    "ErrorBody",
    "ErrorCode",
    "ErrorEnvelope",
    "DisplayScale",
    "FrameRecord",
    "FrameRequest",
    "FrameResponse",
    "ImageRef",
    "Marker",
    "Provenance",
    "Quality",
    "Registration",
    "HealthResponse",
    "DEFAULT_COLLECTIONS",
    "SUPPORTED_COLLECTIONS",
    "NormalizedQuery",
    "ObservationDescriptor",
    "SearchRequest",
    "SearchResponse",
]
