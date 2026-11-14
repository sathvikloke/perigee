"""Plain typed inputs and outputs for the data adapter.

Nothing here imports the web app. Every object turns into JSON-safe dicts with `to_dict()`.
Field names and units follow docs/INTEGRATION_CONTRACT.md: degrees for sky positions,
arcminutes for field of view, micrometers for wavelength, UTC ISO strings for times.
`None` always means "not known", never zero.
"""
from __future__ import annotations

import base64
import math
from dataclasses import asdict, dataclass, field
from typing import Any

from .errors import InvalidCoordinates, InvalidFieldOfView, InvalidRequest, UnsupportedData

FOV_MIN_ARCMIN = 2.0
FOV_MAX_ARCMIN = 10.0
FOV_DEFAULT_ARCMIN = 6.0
LIMIT_MIN = 1
LIMIT_MAX = 48
LIMIT_DEFAULT = 24

# Collections the service is allowed to query. Users pick from these names only.
SUPPORTED_COLLECTIONS: tuple[str, ...] = ("spherex_dr1", "spherex_qr3")


def _finite_number(value: Any, name: str) -> float:
    # bool is an int subclass; reject it so `true` is not read as 1 degree.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidCoordinates(f"{name} must be a number in decimal degrees", details={"field": name})
    out = float(value)
    if not math.isfinite(out):
        raise InvalidCoordinates(f"{name} must be a finite number", details={"field": name})
    return out


@dataclass(frozen=True)
class SearchQuery:
    ra_deg: float
    dec_deg: float
    fov_arcmin: float = FOV_DEFAULT_ARCMIN
    limit: int = LIMIT_DEFAULT
    collection_ids: tuple[str, ...] = SUPPORTED_COLLECTIONS

    @classmethod
    def validated(
        cls,
        ra_deg: Any,
        dec_deg: Any,
        fov_arcmin: Any = FOV_DEFAULT_ARCMIN,
        limit: Any = LIMIT_DEFAULT,
        collection_ids: Any = None,
    ) -> "SearchQuery":
        """Apply the contract's input rules. Nothing is clipped or silently replaced."""
        ra = _finite_number(ra_deg, "ra_deg")
        dec = _finite_number(dec_deg, "dec_deg")
        if not (0.0 <= ra < 360.0):
            raise InvalidCoordinates("ra_deg must be in [0, 360)", details={"field": "ra_deg"})
        if not (-90.0 <= dec <= 90.0):
            raise InvalidCoordinates("dec_deg must be in [-90, 90]", details={"field": "dec_deg"})
        if isinstance(fov_arcmin, bool) or not isinstance(fov_arcmin, (int, float)) or not math.isfinite(float(fov_arcmin)):
            raise InvalidFieldOfView("fov_arcmin must be a finite number")
        fov = float(fov_arcmin)
        if not (FOV_MIN_ARCMIN <= fov <= FOV_MAX_ARCMIN):
            raise InvalidFieldOfView(
                f"fov_arcmin must be between {FOV_MIN_ARCMIN:g} and {FOV_MAX_ARCMIN:g}",
                details={"min": FOV_MIN_ARCMIN, "max": FOV_MAX_ARCMIN},
            )
        if isinstance(limit, bool) or not isinstance(limit, int) or not (LIMIT_MIN <= limit <= LIMIT_MAX):
            raise InvalidRequest(
                f"limit must be an integer from {LIMIT_MIN} to {LIMIT_MAX}", details={"field": "limit"}
            )
        if collection_ids is None:
            cols = SUPPORTED_COLLECTIONS
        else:
            cols = tuple(dict.fromkeys(collection_ids))
            bad = [c for c in cols if c not in SUPPORTED_COLLECTIONS]
            if bad or not cols:
                raise InvalidRequest(
                    "collection_ids must come from the supported list",
                    details={"supported": list(SUPPORTED_COLLECTIONS)},
                )
        return cls(ra, dec, fov, limit, cols)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["collection_ids"] = list(self.collection_ids)
        return d


@dataclass(frozen=True)
class ObservationDescriptor:
    """One SPHEREx Level 2 exposure on one detector, as returned by the archive.

    `observation_id` is the archive obs_id (e.g. "2026W18_1A_0516_1"). One obs_id covers up to
    six detector images at different wavelengths, so the per-image identity is
    `frame_key` = "<observation_id>_D<detector>" (integration board decision 1).
    `observed_at_utc`/`mjd` here are the SIA `t_min` (exposure start); the processed frame
    replaces them with the file's mid-exposure DATE-AVG/MJD-AVG (decision 2).
    `source_url` is the public full-file archive URL. Cutout URLs are derived from it.
    """

    observation_id: str
    collection_id: str
    observed_at_utc: str | None
    mjd: float | None
    detector: int | None
    source_url: str
    # Extra archive context. Not part of the public descriptor unless the API owner adds it.
    publisher_did: str | None = None
    band_min_um: float | None = None  # whole-detector band edges, NOT the wavelength at a position
    band_max_um: float | None = None
    exposure_s: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_public_dict(cls, d: dict[str, Any]) -> "ObservationDescriptor":
        """Rebuild a descriptor from `public_dict()` output (e.g. a verified frame-token payload).

        Only the public fields are read (`frame_key` is derived, never trusted). The source URL is checked against the archive
        allowlist and the collection here, so a payload can never point the fetcher elsewhere.
        """
        from .archive import validate_source_url

        if not isinstance(d, dict):
            raise UnsupportedData("observation payload must be an object")
        if d.get("collection_id") not in SUPPORTED_COLLECTIONS:
            raise UnsupportedData("observation collection is not supported")
        oid, url = d.get("observation_id"), d.get("source_url")
        if not isinstance(oid, str) or not isinstance(url, str):
            raise UnsupportedData("observation payload is missing its id or source")
        validate_source_url(url, d["collection_id"])
        mjd = d.get("mjd")
        det = d.get("detector")
        return cls(
            observation_id=oid,
            collection_id=d["collection_id"],
            observed_at_utc=d.get("observed_at_utc"),
            mjd=float(mjd) if isinstance(mjd, (int, float)) and not isinstance(mjd, bool) else None,
            detector=int(det) if isinstance(det, int) and not isinstance(det, bool) else None,
            source_url=url,
        )

    @property
    def frame_key(self) -> str:
        return frame_key(self.observation_id, self.detector)

    def public_dict(self) -> dict[str, Any]:
        """Contract descriptor fields plus `frame_key` (frame_token is added by the API)."""
        return {
            "observation_id": self.observation_id,
            "collection_id": self.collection_id,
            "observed_at_utc": self.observed_at_utc,
            "mjd": self.mjd,
            "detector": self.detector,
            "frame_key": self.frame_key,
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class CollectionOutcome:
    collection_id: str
    status: str  # "ok" | "overflow" | "failed"
    records: int | None
    error_code: str | None = None


@dataclass
class SearchResult:
    query: SearchQuery
    status: str  # "ready" | "partial" | "empty"
    observations: list[ObservationDescriptor]
    total_matches: int | None
    truncated: bool
    warnings: list[str]
    collections_queried: list[CollectionOutcome]
    queried_at_utc: str

    @property
    def returned_count(self) -> int:
        return len(self.observations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query.to_dict(),
            "status": self.status,
            "observations": [o.public_dict() for o in self.observations],
            "returned_count": self.returned_count,
            "total_matches": self.total_matches,
            "truncated": self.truncated,
            "warnings": list(self.warnings),
            "collections_queried": [asdict(c) for c in self.collections_queried],
            "queried_at_utc": self.queried_at_utc,
        }


@dataclass(frozen=True)
class CatalogTarget:
    """A catalog position used only to place a *predicted* marker. Never a measurement."""

    target_id: str
    name: str
    ra_deg: float
    dec_deg: float
    epoch_jyear: float
    pm_ra_cosdec_masyr: float | None
    pm_dec_masyr: float | None
    source: str  # where the catalog numbers came from (e.g. SIMBAD resolver URL)
    parallax_mas: float | None = None
    radial_velocity_kms: float | None = None


@dataclass(frozen=True)
class SharedScale:
    """Display limits shared by several frames (curated comparisons)."""

    low: float  # after background offset, MJy/sr
    high: float
    asinh_softening: float


@dataclass(frozen=True)
class FrameContext:
    """Everything the processor needs besides the FITS bytes. No paths, no HTTP session."""

    observation: ObservationDescriptor
    center_ra_deg: float
    center_dec_deg: float
    fov_arcmin: float = FOV_DEFAULT_ARCMIN
    grid_size: int = 256
    target: CatalogTarget | None = None
    shared_scale: SharedScale | None = None
    retrieved_at_utc: str | None = None
    retrieved_at_basis: str | None = None  # e.g. "live download" or how a curated time was set
    cutout_url: str | None = None  # exact URL the bytes came from, if known


@dataclass
class FrameProduct:
    """Processor output: a contract FrameRecord (as a dict) plus the two PNGs.

    `record["image"]["src"]` and `record["flag_image"]["src"]` are left as None. The caller
    fills them with `with_data_urls()` (live frames) or with an asset URL (curated frames).
    """

    record: dict[str, Any]
    image_png: bytes
    flag_png: bytes | None
    stats: dict[str, Any] = field(default_factory=dict)  # numbers used for a shared scale

    def with_data_urls(self) -> dict[str, Any]:
        rec = _deep_copy(self.record)
        rec["image"]["src"] = png_data_url(self.image_png)
        if rec.get("flag_image") is not None and self.flag_png is not None:
            rec["flag_image"]["src"] = png_data_url(self.flag_png)
        return rec


def frame_key(observation_id: str, detector: int | None) -> str:
    return f"{observation_id}_D{detector}" if detector is not None else observation_id


def png_data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _deep_copy(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(v) for v in obj]
    return obj
