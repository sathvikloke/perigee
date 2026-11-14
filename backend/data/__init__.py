"""Perigee data adapter: SPHEREx archive search, cutout retrieval and frame processing.

Public interface for the API layer (see backend/data/README.md for examples):

    SearchQuery.validated(ra_deg, dec_deg, fov_arcmin=6, limit=24, collection_ids=None)
    search_observations(query)                       -> SearchResult        (network)
    fetch_cutout(observation, ra, dec, fov_arcmin)   -> CutoutBytes         (network)
    process_frame(fits_bytes, FrameContext)          -> FrameProduct        (pure)
    fetch_and_process(observation, ra, dec, fov)     -> FrameProduct        (both)
    process_frame_for_api(fits_bytes, meta: dict)    -> dict                (pure; API-A hook)

Every failure is a `DataError` subclass carrying a contract error code.
"""
from __future__ import annotations

from .api_adapter import process_frame_for_api
from .archive import CutoutBytes, HttpResponse, fetch_cutout, search_observations, urllib_get
from .errors import (
    DataError,
    InvalidCoordinates,
    InvalidFieldOfView,
    InvalidRequest,
    ProcessingFailed,
    UnsupportedData,
    UpstreamTimeout,
    UpstreamUnavailable,
)
from .process import PROCESSING_VERSION, process_frame
from .records import (
    SUPPORTED_COLLECTIONS,
    CatalogTarget,
    FrameContext,
    FrameProduct,
    ObservationDescriptor,
    SearchQuery,
    SearchResult,
    SharedScale,
    png_data_url,
)


def fetch_and_process(
    observation: ObservationDescriptor,
    center_ra_deg: float,
    center_dec_deg: float,
    fov_arcmin: float,
    *,
    target: CatalogTarget | None = None,
    grid_size: int = 256,
    http_get=urllib_get,
) -> FrameProduct:
    """Download one cutout around the field center and process it onto the fixed grid."""
    cut = fetch_cutout(observation, center_ra_deg, center_dec_deg, fov_arcmin, http_get=http_get)
    ctx = FrameContext(
        observation=observation,
        center_ra_deg=center_ra_deg,
        center_dec_deg=center_dec_deg,
        fov_arcmin=fov_arcmin,
        grid_size=grid_size,
        target=target,
        retrieved_at_utc=cut.retrieved_at_utc,
        retrieved_at_basis="Downloaded from the archive cutout service for this request.",
        cutout_url=cut.url,
    )
    return process_frame(cut.data, ctx)


__all__ = [
    "PROCESSING_VERSION",
    "SUPPORTED_COLLECTIONS",
    "CatalogTarget",
    "CutoutBytes",
    "DataError",
    "FrameContext",
    "FrameProduct",
    "HttpResponse",
    "InvalidCoordinates",
    "InvalidFieldOfView",
    "InvalidRequest",
    "ObservationDescriptor",
    "ProcessingFailed",
    "SearchQuery",
    "SearchResult",
    "SharedScale",
    "UnsupportedData",
    "UpstreamTimeout",
    "UpstreamUnavailable",
    "fetch_and_process",
    "fetch_cutout",
    "process_frame",
    "process_frame_for_api",
    "png_data_url",
    "search_observations",
]
