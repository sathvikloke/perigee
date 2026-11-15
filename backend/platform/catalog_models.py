"""Response models for the catalog routes (presets, cases, preset frames, errors).

These mirror field names from docs/INTEGRATION_CONTRACT.md and from the
authored content in backend/content/{targets.json,cases/*.json}. Authored
content is passed through unchanged (``extra="allow"``) so that serving it
never rewords or drops scientific fields; only the identity fields the
routes depend on are typed.

Integration note: ``ErrorBody``/``ErrorEnvelope`` duplicate the shared error
envelope that the API owner defines in ``backend/models``. At integration,
replace them with the shared models; the field names are identical.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1


class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: Optional[Dict[str, Any]] = None


class ErrorEnvelope(BaseModel):
    schema_version: int = SCHEMA_VERSION
    request_id: str
    error: ErrorBody


class CaseAssociation(BaseModel):
    """A case linked to a preset. ``available`` is false when the target
    lists a case ID whose authored file is not present (for example the
    optional ``coverage_is_not_detection``)."""

    case_id: str
    title: Optional[str] = None
    available: bool
    frames_available: bool = False


class PresetDescriptor(BaseModel):
    """One entry of targets.json, unchanged, plus serving fields.

    Added by the server (not authored content): ``preset_id`` (equal to
    ``id``), ``cases``, ``frames_available``, ``frame_count``.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    preset_id: str
    display_name: str
    case_ids: List[str] = Field(default_factory=list)
    cases: List[CaseAssociation] = Field(default_factory=list)
    frames_available: bool = False
    frame_count: int = 0


class PresetListResponse(BaseModel):
    schema_version: int = SCHEMA_VERSION
    content_version: Optional[str] = None
    coordinate_conventions: Optional[Dict[str, Any]] = None
    count: int
    presets: List[PresetDescriptor]


class CaseDocument(BaseModel):
    """An authored case file served verbatim. Typed fields are the ones the
    catalog relies on; all others are preserved as authored."""

    model_config = ConfigDict(extra="allow")

    schema_version: int
    case_id: str
    title: str
    target_id: str


class PresetFramesResponse(BaseModel):
    """Ordered curated frame records for one preset.

    ``status``: ``ready`` (records found, none skipped), ``partial`` (some
    product files could not be used; see ``warnings``) or ``missing`` (no
    generated products yet). Frames are never synthesized: when ``missing``,
    ``frames`` is empty and ``reason`` explains why. ``case_id`` is set when
    the listing is restricted to a case's product set; ``sets`` names the
    processor output sets (subdirectories, "." for the preset root) used.
    """

    schema_version: int = SCHEMA_VERSION
    preset_id: str
    case_id: Optional[str] = None
    status: str
    frames_available: bool
    frame_count: int
    order: str = "mjd_then_frame_key"
    frames: List[Dict[str, Any]]
    reason: Optional[str] = None
    sets: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    source_dir: str
