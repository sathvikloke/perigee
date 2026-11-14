"""Catalog store: authored presets/cases and generated preset frame records.

Content sources (all read-only, bundled with the backend):

* ``<content_root>/targets.json`` -- authored preset descriptors (science owner).
* ``<content_root>/cases/<case_id>.json`` -- authored investigation cases.
* ``<content_root>/presets/<preset_id>/**`` -- generated products from the
  processor: PNG images and FrameRecord JSON files.

The store never rewords authored content and never synthesizes frames. When
generated products are absent the preset reports ``frames_available: false``
with a reason.

Accepted FrameRecord JSON shapes under a preset directory (any depth):

* one record per file (an object with ``frame_key``, or with
  ``observation_id`` plus ``detector`` or ``frame_id``);
* a wrapper ``{"frame": {...}}`` as returned by ``POST /api/v1/frame``;
* a manifest ``{"frames": [{...}, ...]}`` or a bare list of records.

Other JSON files (provenance, audit) are ignored by the frame listing but are
still servable as allowlisted assets. Relative ``image.src`` / ``flag_image.src``
values that name an indexed PNG inside the same preset directory are rewritten
to ``/api/v1/assets/<asset_id>``; anything else unresolvable is dropped with a
warning rather than handed to the browser as a filesystem path.
"""

import copy
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from backend.platform.catalog_assets import AssetEntry, AssetIndex, png_dimensions
from backend.platform.catalog_models import (
    CaseAssociation,
    CaseDocument,
    PresetDescriptor,
    PresetFramesResponse,
    PresetListResponse,
)

DEFAULT_CONTENT_ROOT = Path(__file__).resolve().parent.parent / "content"
CONTENT_ROOT_ENV = "PERIGEE_CONTENT_ROOT"
DEFAULT_ASSET_URL_PREFIX = "/api/v1/assets/"
ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")
FRAME_IMAGE_FIELDS = ("image", "flag_image")


class ContentUnavailable(Exception):
    """Authored content needed for a route could not be loaded."""


def is_valid_content_id(value: str) -> bool:
    return isinstance(value, str) and bool(ID_RE.match(value))


def _is_regular_file(path: Path) -> bool:
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode)


def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _looks_like_frame(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if isinstance(value.get("frame_key"), str):
        return True
    return isinstance(value.get("observation_id"), str) and (
        "detector" in value or "frame_id" in value
    )


def _extract_records(doc: Any) -> List[Dict[str, Any]]:
    if _looks_like_frame(doc):
        return [doc]
    if isinstance(doc, dict):
        if _looks_like_frame(doc.get("frame")):
            return [doc["frame"]]
        if isinstance(doc.get("frames"), list):
            return [f for f in doc["frames"] if _looks_like_frame(f)]
    if isinstance(doc, list):
        return [f for f in doc if _looks_like_frame(f)]
    return []


def frame_key_for(record: Dict[str, Any]) -> Optional[str]:
    """frame_key per science/INTEGRATION_BOARD.md decision 1:
    ``<observation_id>_D<detector>``. Derived only from fields the record
    already carries."""
    key = record.get("frame_key")
    if isinstance(key, str) and key:
        return key
    obs = record.get("observation_id")
    det = record.get("detector")
    if isinstance(obs, str) and obs and isinstance(det, int) and not isinstance(det, bool):
        return "{}_D{}".format(obs, det)
    frame_id = record.get("frame_id")
    if isinstance(frame_id, str) and frame_id:
        return frame_id
    return None


def _sort_key(record: Dict[str, Any]) -> Tuple[int, float, str]:
    mjd = record.get("mjd")
    if isinstance(mjd, (int, float)) and not isinstance(mjd, bool) and mjd == mjd:
        return (0, float(mjd), record.get("frame_key") or "")
    return (1, 0.0, record.get("frame_key") or "")


REQUIRED_FRAME_FIELDS = (
    "frame_id",
    "observation_id",
    "collection_id",
    "observed_at_utc",
    "mjd",
    "source_url",
)


class CatalogStore:
    def __init__(self, content_root: Path, asset_url_prefix: str = DEFAULT_ASSET_URL_PREFIX):
        self.content_root = Path(content_root)
        self.presets_root = self.content_root / "presets"
        self.asset_url_prefix = asset_url_prefix
        self.load_issues: List[str] = []
        self._targets_doc: Optional[Dict[str, Any]] = None
        self._targets_error: Optional[str] = None
        self._targets: Dict[str, Dict[str, Any]] = {}
        self._cases: Dict[str, Dict[str, Any]] = {}
        self._frames: Dict[str, PresetFramesResponse] = {}
        self.assets = AssetIndex(self.presets_root)
        self._load_targets()
        self._load_cases()

    # -- authored content ---------------------------------------------
    def _load_targets(self) -> None:
        path = self.content_root / "targets.json"
        if not _is_regular_file(path):
            self._targets_error = "targets.json is not present in the content bundle."
            return
        try:
            doc = _load_json(path)
        except (OSError, ValueError) as exc:
            self._targets_error = "targets.json could not be parsed: {}".format(type(exc).__name__)
            return
        targets = doc.get("targets") if isinstance(doc, dict) else None
        if not isinstance(targets, list):
            self._targets_error = "targets.json has no 'targets' list."
            return
        for target in targets:
            tid = target.get("id") if isinstance(target, dict) else None
            if not is_valid_content_id(tid) or not isinstance(target.get("display_name"), str):
                self.load_issues.append("targets.json: skipped an entry without a valid id/display_name")
                continue
            if tid in self._targets:
                self.load_issues.append("targets.json: duplicate id {}".format(tid))
                continue
            self._targets[tid] = target
        self._targets_doc = doc

    def _load_cases(self) -> None:
        cases_dir = self.content_root / "cases"
        if not cases_dir.is_dir():
            return
        for path in sorted(cases_dir.glob("*.json")):
            if not _is_regular_file(path):
                self.load_issues.append("cases/{}: not a regular file".format(path.name))
                continue
            try:
                doc = _load_json(path)
                CaseDocument.model_validate(doc)
            except (OSError, ValueError, ValidationError) as exc:
                self.load_issues.append("cases/{}: invalid ({})".format(path.name, type(exc).__name__))
                continue
            case_id = doc["case_id"]
            if case_id != path.stem or not is_valid_content_id(case_id):
                self.load_issues.append(
                    "cases/{}: case_id '{}' does not match file name".format(path.name, case_id)
                )
                continue
            self._cases[case_id] = doc

    def _require_targets(self) -> None:
        if self._targets_doc is None:
            raise ContentUnavailable(self._targets_error or "targets.json unavailable")

    # -- presets --------------------------------------------------------
    def preset_ids(self) -> List[str]:
        self._require_targets()
        return list(self._targets)

    def has_preset(self, preset_id: str) -> bool:
        self._require_targets()
        return is_valid_content_id(preset_id) and preset_id in self._targets

    def _case_associations(self, target: Dict[str, Any]) -> List[CaseAssociation]:
        tid = target["id"]
        ordered: List[str] = []
        for cid in target.get("case_ids") or []:
            if isinstance(cid, str) and cid not in ordered:
                ordered.append(cid)
        for cid in sorted(self._cases):
            if self._cases[cid].get("target_id") == tid and cid not in ordered:
                ordered.append(cid)
        out = []
        for cid in ordered:
            case = self._cases.get(cid)
            out.append(
                CaseAssociation(
                    case_id=cid,
                    title=case.get("title") if case else None,
                    available=case is not None,
                )
            )
        return out

    def list_presets(self) -> PresetListResponse:
        self._require_targets()
        doc = self._targets_doc or {}
        presets = []
        for tid, target in self._targets.items():
            frames = self.get_frames(tid)
            descriptor = copy.deepcopy(target)
            descriptor.update(
                {
                    "preset_id": tid,
                    "cases": [c.model_dump() for c in self._case_associations(target)],
                    "frames_available": frames.frames_available if frames else False,
                    "frame_count": frames.frame_count if frames else 0,
                }
            )
            presets.append(PresetDescriptor.model_validate(descriptor))
        return PresetListResponse(
            content_version=doc.get("content_version"),
            coordinate_conventions=doc.get("coordinate_conventions"),
            count=len(presets),
            presets=presets,
        )

    # -- cases ----------------------------------------------------------
    def case_ids(self) -> List[str]:
        return sorted(self._cases)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        if not is_valid_content_id(case_id):
            return None
        case = self._cases.get(case_id)
        return copy.deepcopy(case) if case is not None else None

    # -- frames ---------------------------------------------------------
    def get_frames(self, preset_id: str) -> Optional[PresetFramesResponse]:
        if not self.has_preset(preset_id):
            return None
        if preset_id not in self._frames:
            self._frames[preset_id] = self._build_frames(preset_id)
        return self._frames[preset_id].model_copy(deep=True)

    def _asset_url(self, entry: AssetEntry) -> str:
        return self.asset_url_prefix + entry.asset_id

    def _resolve_image(
        self, value: Any, json_dir: Path, preset_id: str, label: str, warnings: List[str]
    ) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            value = {"src": value}
        if not isinstance(value, dict):
            warnings.append("{}: image reference has an unsupported shape; omitted".format(label))
            return None
        src = value.get("src")
        if not isinstance(src, str) or not src:
            warnings.append("{}: image has no src; omitted".format(label))
            return None
        if src.startswith("data:image/") or src.startswith(self.asset_url_prefix):
            return value
        if src.startswith("https://") or src.startswith("http://"):
            return value
        if src.startswith("file:") or os.path.isabs(src) or "\\" in src:
            warnings.append("{}: image src is a filesystem path and is never served; omitted".format(label))
            return None
        entry = self.assets.by_path(json_dir / src)
        if entry is None or entry.preset_id != preset_id or entry.media_type != "image/png":
            warnings.append(
                "{}: image '{}' is not an allowlisted PNG in this preset; omitted".format(label, src)
            )
            return None
        return self._image_from_entry(entry, value)

    def _image_from_entry(self, entry: AssetEntry, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        image = dict(base or {})
        image["src"] = self._asset_url(entry)
        image["asset_id"] = entry.asset_id
        image.setdefault("media_type", entry.media_type)
        if image.get("width") is None or image.get("height") is None:
            data = self.assets.read(entry)
            dims = png_dimensions(data) if data else None
            if dims:
                # Read from the PNG header of the real file, not assumed.
                if image.get("width") is None:
                    image["width"] = dims[0]
                if image.get("height") is None:
                    image["height"] = dims[1]
        return image

    def _build_frames(self, preset_id: str) -> PresetFramesResponse:
        source_dir = "backend/content/presets/{}".format(preset_id)
        preset_dir = self.presets_root / preset_id
        if not preset_dir.is_dir() or preset_dir.is_symlink():
            return PresetFramesResponse(
                preset_id=preset_id,
                status="missing",
                frames_available=False,
                frame_count=0,
                frames=[],
                reason=(
                    "No generated products for this preset yet: {}/ is not present. "
                    "Frames come from the processor and are never synthesized by the catalog."
                ).format(source_dir),
                source_dir=source_dir,
            )

        warnings: List[str] = [
            s for s in self.assets.skipped if s.startswith(preset_id + "/")
        ]
        records: Dict[str, Dict[str, Any]] = {}
        pngs_by_stem = {
            Path(e.relative_path).stem: e
            for e in self.assets.for_preset(preset_id, "image/png")
        }
        for entry in self.assets.for_preset(preset_id, "application/json"):
            label = entry.relative_path
            data = self.assets.read(entry)
            if data is None:
                warnings.append("{}: changed or unreadable since indexing".format(label))
                continue
            try:
                doc = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                warnings.append("{}: not valid JSON; skipped".format(label))
                continue
            for raw in _extract_records(doc):
                record = copy.deepcopy(raw)
                key = frame_key_for(record)
                if key is None:
                    warnings.append("{}: record without frame identity; skipped".format(label))
                    continue
                record.setdefault("frame_key", key)
                rec_preset = record.get("preset_id")
                if rec_preset is not None and rec_preset != preset_id:
                    warnings.append(
                        "{}: record {} belongs to preset '{}'; skipped".format(label, key, rec_preset)
                    )
                    continue
                rec_label = "{}#{}".format(label, key)
                for field in FRAME_IMAGE_FIELDS:
                    if field in record:
                        record[field] = self._resolve_image(
                            record[field], entry.path.parent, preset_id, rec_label, warnings
                        )
                if record.get("image") is None and key in pngs_by_stem:
                    # A real generated PNG named after the frame_key.
                    record["image"] = self._image_from_entry(pngs_by_stem[key])
                missing = [f for f in REQUIRED_FRAME_FIELDS if record.get(f) is None]
                if missing:
                    warnings.append(
                        "{}: missing contract fields {} (left absent, not invented)".format(
                            rec_label, ", ".join(missing)
                        )
                    )
                if key in records:
                    if records[key] != record:
                        warnings.append(
                            "{}: duplicate frame_key {} with different content; first kept".format(label, key)
                        )
                    continue
                records[key] = record

        frames = sorted(records.values(), key=_sort_key)
        if not frames:
            return PresetFramesResponse(
                preset_id=preset_id,
                status="missing",
                frames_available=False,
                frame_count=0,
                frames=[],
                reason=(
                    "{}/ exists but contains no usable FrameRecord JSON. "
                    "Frames are never synthesized by the catalog."
                ).format(source_dir),
                warnings=warnings,
                source_dir=source_dir,
            )
        return PresetFramesResponse(
            preset_id=preset_id,
            status="partial" if warnings else "ready",
            frames_available=True,
            frame_count=len(frames),
            frames=frames,
            warnings=warnings,
            source_dir=source_dir,
        )


_DEFAULT_STORE: Optional[CatalogStore] = None


def get_catalog_store() -> CatalogStore:
    """Process-wide store over the bundled content (or ``PERIGEE_CONTENT_ROOT``).

    Built once per process: content is immutable within a deployment.
    Tests override this dependency with a store over a fixture directory.
    """
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        root = os.environ.get(CONTENT_ROOT_ENV) or str(DEFAULT_CONTENT_ROOT)
        _DEFAULT_STORE = CatalogStore(Path(root))
    return _DEFAULT_STORE
