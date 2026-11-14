"""Catalog store: authored presets/cases and generated preset frame records.

Content sources (all read-only, bundled with the backend):

* ``<content_root>/targets.json`` -- authored preset descriptors (science owner).
* ``<content_root>/cases/<case_id>.json`` -- authored investigation cases.
* ``<content_root>/presets/<preset_id>/**`` -- generated products from the
  processor: PNG images and FrameRecord JSON files.

The store never rewords authored content and never synthesizes frames. When
generated products are absent the preset reports ``frames_available: false``
with a reason.

Processor layout (tools/ingest/ingest.py on codex/parallel-05-processor-a)::

    presets/<preset_id>/<set>/<frame_key>.png         intensity image
    presets/<preset_id>/<set>/<frame_key>.flags.png   optional flag overlay
    presets/<preset_id>/<set>/<frame_key>.json        FrameRecord
    presets/<preset_id>/<set>/frames.json             {"frames": [...], "assets": {id: path}}

``<set>`` is ``frames`` for a preset run and ``case-<case_id>`` for a case
(cases may use a shared stretch, so their records are kept separate). Records
directly under ``presets/<preset_id>/`` belong to the default set.

Accepted FrameRecord JSON shapes (any file, any depth):

* one record per file (an object with ``frame_key``, or with
  ``observation_id`` plus ``detector`` or ``frame_id``);
* a wrapper ``{"frame": {...}}`` as returned by ``POST /api/v1/frame``;
* a manifest ``{"frames": [{...}, ...]}`` or a bare list of records.

Image references (``image.src`` / ``flag_image.src``) are resolved to an
indexed PNG of the same preset -- either a relative file path or an asset URL
whose ID the processor declared in a manifest ``assets`` map -- and rewritten
to the canonical, content-versioned ``/api/v1/assets/<asset_id>``. Anything
unresolvable is dropped with a warning rather than handed to the browser.
"""

import copy
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from backend.platform.catalog_assets import SHARED_GROUP, AssetEntry, AssetIndex, png_dimensions
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
CASE_SET_PREFIX = "case-"
REQUIRED_FRAME_FIELDS = (
    "frame_id",
    "observation_id",
    "collection_id",
    "observed_at_utc",
    "mjd",
    "source_url",
)


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


def _set_name(relative_path: str) -> str:
    """``<preset>/<set>/...`` -> ``<set>``; files directly in the preset dir
    belong to the default set ``""``. perigee-data layout (PR #19 trial):
    ``<preset>/sets/<case_id>.json`` -> ``case-<case_id>``."""
    parts = relative_path.split("/")
    if len(parts) == 3 and parts[1] == "sets" and parts[2].endswith(".json"):
        return CASE_SET_PREFIX + parts[2][: -len(".json")]
    return parts[1] if len(parts) > 2 else ""


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
        self._frames: Dict[Tuple[str, Optional[str]], PresetFramesResponse] = {}
        self._json_docs: Dict[str, Any] = {}  # asset_id -> parsed JSON (presets only)
        self._json_errors: Dict[str, str] = {}
        self.assets = AssetIndex(self.presets_root)
        self._load_targets()
        self._load_cases()
        self._load_product_json()

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

    # -- generated products -----------------------------------------------
    def _load_product_json(self) -> None:
        """Parse every indexed JSON product once and register processor-declared
        asset aliases (manifest ``assets`` maps)."""
        for entry in self.assets.entries():
            if entry.media_type != "application/json":
                continue
            data = self.assets.read(entry)
            if data is None:
                self._json_errors[entry.asset_id] = "changed or unreadable since indexing"
                continue
            try:
                doc = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                self._json_errors[entry.asset_id] = "not valid JSON; skipped"
                continue
            self._json_docs[entry.asset_id] = doc
            aliases = doc.get("assets") if isinstance(doc, dict) else None
            if not isinstance(aliases, dict):
                continue
            for alias_id, rel in aliases.items():
                expected: Dict[str, Any] = {}
                owner = entry.preset_id
                if isinstance(rel, dict):
                    # perigee-data manifest (PR #19 trial): {id: {path, sha256, bytes,
                    # media_type}} at the presets root. The declared hash and size must
                    # match the indexed file; the owning preset is the ID's first
                    # segment and must also own the target file.
                    expected = {"sha256": rel.get("sha256"), "size": rel.get("bytes")}
                    rel = rel.get("path")
                    if entry.preset_id == SHARED_GROUP and isinstance(alias_id, str):
                        owner = alias_id.split(".", 1)[0]
                if not isinstance(alias_id, str) or not isinstance(rel, str):
                    continue
                error = "relative path rejected"
                if not os.path.isabs(rel) and "\\" not in rel:
                    # Paths are relative to the presets root (ingest.py), or
                    # failing that, to the manifest's own directory.
                    for base in (self.presets_root.resolve(), entry.path.parent):
                        error = self.assets.add_alias(alias_id, base / rel, owner, **expected)
                        if error is None:
                            break
                if error is not None:
                    self.load_issues.append(
                        "{}: asset alias '{}' not registered ({})".format(entry.relative_path, alias_id, error)
                    )

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

    def case_ids_for_preset(self, preset_id: str) -> List[str]:
        target = self._targets.get(preset_id) or {}
        ordered: List[str] = []
        for cid in target.get("case_ids") or []:
            if isinstance(cid, str) and cid not in ordered:
                ordered.append(cid)
        for cid in sorted(self._cases):
            if self._cases[cid].get("target_id") == preset_id and cid not in ordered:
                ordered.append(cid)
        return ordered

    def _case_associations(self, preset_id: str) -> List[CaseAssociation]:
        out = []
        for cid in self.case_ids_for_preset(preset_id):
            case = self._cases.get(cid)
            frames = self.get_frames(preset_id, cid) if case is not None else None
            out.append(
                CaseAssociation(
                    case_id=cid,
                    title=case.get("title") if case else None,
                    available=case is not None,
                    frames_available=bool(frames and frames.frames_available),
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
                    "cases": [c.model_dump() for c in self._case_associations(tid)],
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
    def get_frames(self, preset_id: str, case_id: Optional[str] = None) -> Optional[PresetFramesResponse]:
        """Frames for a preset, or for one of its cases. None means the preset
        (or the case for this preset) is unknown."""
        if not self.has_preset(preset_id):
            return None
        if case_id is not None and (
            case_id not in self._cases or case_id not in self.case_ids_for_preset(preset_id)
        ):
            return None
        key = (preset_id, case_id)
        if key not in self._frames:
            self._frames[key] = self._build_frames(preset_id, case_id)
        return self._frames[key].model_copy(deep=True)

    def _image_from_entry(self, entry: AssetEntry, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        image = dict(base or {})
        image["src"] = self.asset_url_prefix + entry.asset_id
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
        if src.startswith("data:image/"):
            return value
        if src.startswith("https://") or src.startswith("http://"):
            return value
        if src.startswith(self.asset_url_prefix):
            entry = self.assets.get(src[len(self.asset_url_prefix):])
        elif src.startswith("file:") or os.path.isabs(src) or "\\" in src:
            warnings.append("{}: image src is a filesystem path and is never served; omitted".format(label))
            return None
        else:
            entry = self.assets.by_path(json_dir / src)
        if entry is None or entry.preset_id != preset_id or entry.media_type != "image/png":
            warnings.append(
                "{}: image '{}' is not an allowlisted PNG in this preset; omitted".format(label, src)
            )
            return None
        return self._image_from_entry(entry, value)

    def _build_frames(self, preset_id: str, case_id: Optional[str]) -> PresetFramesResponse:
        source_dir = "backend/content/presets/{}".format(preset_id)
        wanted_set = CASE_SET_PREFIX + case_id if case_id else None
        base = {"preset_id": preset_id, "case_id": case_id, "source_dir": source_dir}
        preset_dir = self.presets_root / preset_id
        if not preset_dir.is_dir() or preset_dir.is_symlink():
            return PresetFramesResponse(
                status="missing",
                frames_available=False,
                frame_count=0,
                frames=[],
                reason=(
                    "No generated products for this preset yet: {}/ is not present. "
                    "Frames come from the processor and are never synthesized by the catalog."
                ).format(source_dir),
                **base,
            )

        warnings: List[str] = [s for s in self.assets.skipped if s.startswith(preset_id + "/")]
        pngs_by_set_stem = {
            (_set_name(e.relative_path), Path(e.relative_path).stem): e
            for e in self.assets.for_preset(preset_id, "image/png")
        }
        # set name -> frame_key -> record
        by_set: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for entry in self.assets.for_preset(preset_id, "application/json"):
            label = entry.relative_path
            set_name = _set_name(label)
            if wanted_set is not None and set_name != wanted_set:
                continue
            if entry.asset_id in self._json_errors:
                warnings.append("{}: {}".format(label, self._json_errors[entry.asset_id]))
                continue
            for raw in _extract_records(self._json_docs.get(entry.asset_id)):
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
                if record.get("image") is None and (set_name, key) in pngs_by_set_stem:
                    # A real generated PNG named after the frame_key in the same set.
                    record["image"] = self._image_from_entry(pngs_by_set_stem[(set_name, key)])
                missing = [f for f in REQUIRED_FRAME_FIELDS if record.get(f) is None]
                bucket = by_set.setdefault(set_name, {})
                if key in bucket:
                    if bucket[key] != record:
                        warnings.append(
                            "{}: duplicate frame_key {} with different content; first kept".format(label, key)
                        )
                    continue
                if missing:
                    warnings.append(
                        "{}: missing contract fields {} (left absent, not invented)".format(
                            rec_label, ", ".join(missing)
                        )
                    )
                bucket[key] = record

        # Default listing prefers non-case sets; case-set records fill in only
        # frame_keys that no preset run produced. A case listing uses its set only.
        merged: Dict[str, Dict[str, Any]] = {}
        used_sets: List[str] = []
        ordered_sets = sorted(by_set, key=lambda s: (s.startswith(CASE_SET_PREFIX), s))
        for set_name in ordered_sets:
            added = False
            for key, record in by_set[set_name].items():
                if key not in merged:
                    merged[key] = record
                    added = True
            if added:
                used_sets.append(set_name or ".")

        frames = sorted(merged.values(), key=_sort_key)
        if not frames:
            where = "{}/{}/".format(source_dir, wanted_set) if wanted_set else source_dir + "/"
            return PresetFramesResponse(
                status="missing",
                frames_available=False,
                frame_count=0,
                frames=[],
                reason=(
                    "{} contains no usable FrameRecord JSON. Frames are never synthesized by the catalog."
                ).format(where),
                warnings=warnings,
                **base,
            )
        return PresetFramesResponse(
            status="partial" if warnings else "ready",
            frames_available=True,
            frame_count=len(frames),
            frames=frames,
            sets=used_sets,
            warnings=warnings,
            **base,
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
