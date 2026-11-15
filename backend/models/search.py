"""POST /api/v1/search request and response models (contract v1 + integration board decisions)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import SCHEMA_VERSION

# Server-maintained collection allowlist. Users choose among these IDs only; they can
# never supply an upstream URL or an arbitrary collection expression.
SUPPORTED_COLLECTIONS: tuple[str, ...] = ("spherex_dr1", "spherex_qr3")
DEFAULT_COLLECTIONS: tuple[str, ...] = SUPPORTED_COLLECTIONS
CollectionId = Literal["spherex_dr1", "spherex_qr3"]

FOV_MIN_ARCMIN = 2.0
FOV_MAX_ARCMIN = 10.0
LIMIT_MIN = 1
LIMIT_MAX = 48

# Strict numbers: JSON strings ("12.5", "12abc"), booleans, NaN and +/-Infinity are
# rejected; out-of-range values are rejected, never clipped.
RaDeg = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=0.0, lt=360.0)]
DecDeg = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=-90.0, le=90.0)]
FovArcmin = Annotated[
    float, Field(strict=True, allow_inf_nan=False, ge=FOV_MIN_ARCMIN, le=FOV_MAX_ARCMIN)
]
Limit = Annotated[int, Field(strict=True, ge=LIMIT_MIN, le=LIMIT_MAX)]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Annotated[int, Field(strict=True, ge=1, le=1, description="Must be 1.")]
    ra_deg: RaDeg = Field(description="ICRS right ascension in degrees, [0, 360).")
    dec_deg: DecDeg = Field(description="ICRS declination in degrees, [-90, 90].")
    fov_arcmin: FovArcmin = Field(default=6.0, description="Square display field, 2-10 arcmin.")
    limit: Limit = Field(default=24, description="Maximum descriptors returned, 1-48.")
    collection_ids: list[CollectionId] | None = Field(
        default=None,
        min_length=1,
        max_length=len(SUPPORTED_COLLECTIONS),
        description="Subset of the server allowlist. Omitted means all supported collections.",
    )


class NormalizedQuery(BaseModel):
    ra_deg: float
    dec_deg: float
    fov_arcmin: float
    limit: int
    collection_ids: list[str]
    search_radius_deg: float = Field(
        description="Radius of the archive coverage search around the query center."
    )


class ObservationDescriptor(BaseModel):
    observation_id: str = Field(description="SPHEREx observation ID, e.g. 2026W18_1A_0516_1.")
    detector: int | None = Field(description="SPHEREx detector number 1-6; null if not provided.")
    frame_key: str = Field(
        description="Stable per-image identity: <observation_id>_D<detector> (integration board decision 1)."
    )
    collection_id: str
    observed_at_utc: str | None = Field(
        description="Observation time (UTC ISO 8601). From archive t_min until the frame is processed."
    )
    mjd: float | None
    time_basis: Literal["sia_t_min", "header_mjd_avg"] = Field(
        description="sia_t_min: exposure start from the archive search. The FrameRecord replaces it "
        "with MJD-AVG (mid-exposure) from the IMAGE header."
    )
    band_name: str | None = Field(default=None, description="Archive bandpass name, e.g. SPHEREx-D3.")
    detector_wavelength_range_um: list[float] | None = Field(
        default=None,
        description="[min, max] wavelength over the WHOLE detector (archive em_min/em_max). "
        "Not the wavelength at the query position; see FrameRecord.wavelength_um.",
    )
    source_url: str = Field(description="Original archive file URL (IRSA IBE).")
    frame_token: str = Field(description="Opaque server-signed token for POST /api/v1/frame.")


class SearchResponse(BaseModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    request_id: str
    query: NormalizedQuery
    status: Literal["ready", "partial", "empty"]
    observations: list[ObservationDescriptor]
    returned_count: int
    total_matches: int | None = Field(description="Matches across queried collections when known.")
    truncated: bool
    selection: Literal["all", "evenly_spaced_in_time"] = Field(
        description="How returned descriptors were chosen when total_matches > limit."
    )
    warnings: list[str]
    collections_queried: list[str]
    collections_failed: list[str] = Field(
        default_factory=list, description="Collections whose archive query failed (status partial)."
    )
    collections_capped: list[str] = Field(
        default_factory=list,
        description="Collections where the archive returned its record cap (SIA MAXREC), so not every "
        "match was retrieved (status partial, total_matches null, truncated true).",
    )
    token_expires_at_utc: str | None = None
    queried_at_utc: str
