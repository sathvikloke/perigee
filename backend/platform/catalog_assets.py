"""Allowlisted, versioned asset index for small generated preset products.

The index is built by walking ``backend/content/presets`` once. Only regular
files (never symlinks) with an allowlisted extension and a bounded size that
resolve inside the root are indexed. Each gets an opaque, versioned ID::

    <preset_id>--<sanitized relative stem>--<sha256[:12]><ext>

Requests are resolved only by dictionary lookup on that ID, so a caller can
never name a filesystem path. Serving re-checks the file (still a regular
file inside the root, same hash) before returning bytes.
"""

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MEDIA_TYPES = {
    ".png": "image/png",
    ".json": "application/json",
}
MAX_ASSET_BYTES = 4 * 1024 * 1024
ASSET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:--[A-Za-z0-9_-]+)*\.(?:png|json)$")
_SAFE_PART_RE = re.compile(r"[^A-Za-z0-9_-]+")
SHARED_GROUP = "shared"


@dataclass(frozen=True)
class AssetEntry:
    asset_id: str
    preset_id: str
    path: Path  # absolute, resolved
    relative_path: str  # POSIX path relative to the presets root
    media_type: str
    size: int
    sha256: str


def _sanitize(part: str) -> str:
    cleaned = _SAFE_PART_RE.sub("_", part).strip("_")
    return cleaned or "x"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_valid_asset_id(asset_id: str) -> bool:
    if not isinstance(asset_id, str) or len(asset_id) > 240:
        return False
    if ".." in asset_id or "/" in asset_id or "\\" in asset_id or "%" in asset_id:
        return False
    return bool(ASSET_ID_RE.match(asset_id))


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


class AssetIndex:
    def __init__(self, root: Path):
        self.root = Path(root)
        self._by_id: Dict[str, AssetEntry] = {}
        self._by_path: Dict[Path, AssetEntry] = {}
        self.skipped: List[str] = []
        self._build()

    # -- construction -------------------------------------------------
    def _build(self) -> None:
        if not self.root.is_dir() or self.root.is_symlink():
            return
        root_resolved = self.root.resolve()
        for dirpath, dirnames, filenames in os.walk(root_resolved, followlinks=False):
            # Never descend into hidden or symlinked directories.
            dirnames[:] = sorted(
                d for d in dirnames
                if not d.startswith(".") and not os.path.islink(os.path.join(dirpath, d))
            )
            for name in sorted(filenames):
                if name.startswith("."):
                    continue
                self._consider(root_resolved, Path(dirpath) / name)

    def _consider(self, root: Path, path: Path) -> None:
        rel_display = path.relative_to(root).as_posix() if _inside(root, path) else str(path)
        ext = path.suffix.lower()
        media_type = MEDIA_TYPES.get(ext)
        if media_type is None:
            return  # not an allowlisted type; silently ignored
        try:
            st = os.lstat(path)
        except OSError:
            self.skipped.append(f"{rel_display}: unreadable")
            return
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            self.skipped.append(f"{rel_display}: not a regular file (symlinks are never served)")
            return
        resolved = path.resolve()
        if not _inside(root, resolved):
            self.skipped.append(f"{rel_display}: resolves outside the presets root")
            return
        if st.st_size > MAX_ASSET_BYTES:
            self.skipped.append(f"{rel_display}: larger than {MAX_ASSET_BYTES} bytes")
            return
        rel = resolved.relative_to(root)
        parts = rel.parts
        if len(parts) >= 2:
            group = parts[0]
            inner = list(parts[1:])
        else:
            group = SHARED_GROUP
            inner = list(parts)
        inner[-1] = Path(inner[-1]).stem
        sha = _sha256(resolved)
        asset_id = "{}--{}--{}{}".format(
            _sanitize(group), "-".join(_sanitize(p) for p in inner), sha[:12], ext
        )
        if asset_id in self._by_id or not is_valid_asset_id(asset_id):
            self.skipped.append(f"{rel_display}: asset ID collision or invalid ID")
            return
        entry = AssetEntry(
            asset_id=asset_id,
            preset_id=group,
            path=resolved,
            relative_path=rel.as_posix(),
            media_type=media_type,
            size=st.st_size,
            sha256=sha,
        )
        self._by_id[asset_id] = entry
        self._by_path[resolved] = entry

    # -- lookup ------------------------------------------------------
    def __len__(self) -> int:
        return len(self._by_id)

    def entries(self) -> List[AssetEntry]:
        return [self._by_id[k] for k in sorted(self._by_id)]

    def for_preset(self, preset_id: str, media_type: Optional[str] = None) -> List[AssetEntry]:
        return [
            e for e in self.entries()
            if e.preset_id == preset_id and (media_type is None or e.media_type == media_type)
        ]

    def get(self, asset_id: str) -> Optional[AssetEntry]:
        if not is_valid_asset_id(asset_id):
            return None
        return self._by_id.get(asset_id)

    def by_path(self, path: Path) -> Optional[AssetEntry]:
        """Look up an indexed file by an absolute path (used to rewrite
        relative image references inside generated frame records)."""
        try:
            resolved = Path(path).resolve()
        except (TypeError, ValueError, OSError, RuntimeError):
            return None
        return self._by_path.get(resolved)

    def read(self, entry: AssetEntry) -> Optional[bytes]:
        """Return the bytes for an indexed asset after re-validating it, or
        None if the file changed, moved, or became a symlink since indexing."""
        root = self.root.resolve()
        try:
            st = os.lstat(entry.path)
        except OSError:
            return None
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            return None
        if not _inside(root, entry.path.resolve()) or st.st_size != entry.size:
            return None
        data = entry.path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry.sha256:
            return None
        return data


def png_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    """Width and height from a PNG IHDR chunk, or None if not a PNG."""
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
