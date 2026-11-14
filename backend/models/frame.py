"""POST /api/v1/frame request/response and the shared FrameRecord.

FrameRecord is also the shape curated preset frames use (served by the catalog
routes), so field names here are the public contract. Sub-models allow extra keys so
the processor (backend/data) can add documented fields without breaking validation.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import SCHEMA_VERSION


class _Open(BaseModel):
    model_config = ConfigDict(extra="allow")


class FrameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Annotated[int, Field(strict=True, ge=1, le=1, description="Must be 1.")]
    frame_token: str = Field(strict=True, min_length=1, max_length=4096)


class ImageRef(_Open):
    src: str = Field(description="PNG data URL (live) or allowlisted same-origin asset URL (curated).")
    width: int
    height: int
    media_type: Literal["image/png"] = "image/png"


class Registration(_Open):
    center_ra_deg: float
    center_dec_deg: float
    fov_arcmin: float
    scale_arcsec_per_px: float | None = Field(
        description="Display-grid scale. Resampling does not add physical resolution."
    )
    native_scale_arcsec_per_px: float | None = None
    grid_id: str | None = Field(
        default=None, description="Frames with equal grid_id share the same display grid."
    )
    orientation: str = Field(description='e.g. "north_up_east_left".')
    projection: str | None = Field(default=None, description='e.g. "TAN".')
    method: str = Field(description="Resampling/reprojection method actually used.")
    width: int | None = None
    height: int | None = None


class Quality(_Open):
    status: Literal["clear", "flagged", "not_covered", "unknown"]
    covered: bool | None
    valid_aperture_pixels: int | None = Field(description="null when unknown; never 0 for missing.")
    adverse_aperture_pixels: int | None = Field(description="null when unknown; never 0 for missing.")
    flag_names: list[str]
    notes: list[str]


class DisplayScale(_Open):
    mode: Literal["shared", "per_frame"]
    method: str
    low: float | None = Field(default=None, description="Value mapped to black (image unit).")
    high: float | None = Field(default=None, description="Value mapped to white (image unit).")
    unit: str | None = None
    basis: str | None = Field(default=None, description="How the limits were chosen; comparability.")
    comparable_brightness: bool | None = Field(
        default=None, description="False when per-frame contrast makes brightness not comparable."
    )


class Marker(_Open):
    x: float
    y: float
    kind: Literal["catalog_prediction"]
    label: str | None = Field(default=None, description='e.g. "Catalog prediction (not a detection)".')
    epoch_utc: str | None = None
    epoch_mjd: float | None = None
    source: str


class Provenance(_Open):
    # Field names follow backend/data (processor-a) output so curated presets and live
    # frames share one shape.
    data_origin: Literal["nasa_archive", "fixture"] | None = Field(
        default=None,
        description='"fixture" means synthetic/test data that must never be shown as sky data. '
        "Live API frames always set this.",
    )
    retrieved_at: str | None
    retrieved_at_basis: str | None = None
    original_url: str
    cutout_url: str | None = None
    sha256: str | None = Field(default=None, description="SHA-256 of the FITS bytes processed.")
    processing_version: str
    acknowledgments: list[str]


class FrameRecord(_Open):
    frame_id: str
    frame_key: str = Field(description="<observation_id>_D<detector>")
    observation_id: str
    detector: int | None
    collection_id: str
    observed_at_utc: str | None
    mjd: float | None
    time_basis: str | None = Field(default=None, description='e.g. "header_mjd_avg".')
    source_url: str
    wavelength_um: float | None = Field(description="null when the position is off the image.")
    bandwidth_um: float | None
    wavelength_location: str | None = Field(
        description="Which sky position the wavelength was evaluated at (not every pixel)."
    )
    image: ImageRef
    flag_image: ImageRef | None
    registration: Registration
    quality: Quality
    display_scale: DisplayScale
    marker: Marker | None
    provenance: Provenance
    limitations: list[str]


class FrameResponse(BaseModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    request_id: str
    frame: FrameRecord
    timing_ms: dict[str, int] | None = Field(
        default=None, description="Optional fetch/process durations for budget monitoring."
    )
