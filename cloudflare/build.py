"""Build the Cloudflare Workers static-assets bundle for Perigee.

Run from the repository root, with a Python that has backend/requirements.txt
installed, after building the frontend::

    (cd frontend && npm ci && npm run build)
    .venv/bin/python cloudflare/build.py            # writes cloudflare/build/

Output (generated, git-ignored; never raw FITS):

    cloudflare/build/public/                 Worker static assets directory
        index.html, assets/**, demo/perigee-demo.pdf, favicon.svg   (copied from frontend/dist)
        api/v1/presets.json                  == GET /api/v1/presets
        api/v1/cases/<case_id>.json          == GET /api/v1/cases/<case_id>
        api/v1/presets/<p>/frames.json       == GET /api/v1/presets/<p>/frames
        api/v1/presets/<p>/frames.case-<c>.json == GET ...?case_id=<c> (valid cases only)
        api/v1/assets/<asset_id>             == GET /api/v1/assets/<asset_id> (exact bytes)
        api/__perigee/catalog-manifest.json  route table read by the Worker
    cloudflare/build/build-info.json         what was built from what

Every ``/api/*`` request runs the Worker first (wrangler.jsonc
``run_worker_first``), so the files under ``public/api/`` are only reachable
through the Worker's routing, never directly.

The JSON documents come from the same ``CatalogStore`` the FastAPI routes use
(``backend.platform.catalog``), serialized with ``model_dump(mode="json")``
exactly as FastAPI serializes the response models. Asset bytes come from
``AssetIndex.read`` (which re-checks each file's SHA-256), and each exported
file's hash is checked again after writing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.platform.catalog import CatalogStore  # noqa: E402
from backend.platform.catalog_assets import AssetEntry  # noqa: E402

DEFAULT_OUT = REPO / "cloudflare" / "build"
DEFAULT_DIST = REPO / "frontend" / "dist"
DEFAULT_CONTENT = REPO / "backend" / "content"
MANIFEST_REL = "api/__perigee/catalog-manifest.json"
REQUIRED_DIST_FILES = ("index.html", "demo/perigee-demo.pdf")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Same compact form as FastAPI's JSONResponse (ensure_ascii=False, no spaces).
    path.write_text(json.dumps(doc, ensure_ascii=False, allow_nan=False, separators=(",", ":")), encoding="utf-8")


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _all_asset_entries(store: CatalogStore) -> Dict[str, AssetEntry]:
    """Canonical asset IDs plus any processor-declared aliases, as served by /assets/{id}."""
    out = {e.asset_id: e for e in store.assets.entries()}
    for alias_id in sorted(getattr(store.assets, "_aliases", {})):
        entry = store.assets.get(alias_id)
        if entry is not None:
            out[alias_id] = entry
    return out


def build(out: Path, dist: Path, content: Path) -> Dict[str, Any]:
    out = out.resolve()
    if out.name != "build" or out.parent != (REPO / "cloudflare").resolve():
        # Refuse to clear anything except cloudflare/build (or an explicit tmp dir via --out-any).
        raise SystemExit(f"refusing to write to {out}; expected {DEFAULT_OUT}")
    return _build_into(out, dist, content)


def _build_into(out: Path, dist: Path, content: Path) -> Dict[str, Any]:
    dist = dist.resolve()
    for rel in REQUIRED_DIST_FILES:
        if not (dist / rel).is_file():
            raise SystemExit(f"{dist / rel} is missing: run `cd frontend && npm ci && npm run build` first")
    if (dist / "api").exists():
        raise SystemExit("frontend/dist must not contain an api/ directory")

    if out.exists():
        # Only ever replace a previous build of this script (or an empty directory).
        if any(out.iterdir()) and not (out / "build-info.json").is_file():
            raise SystemExit(f"refusing to clear {out}: not a previous Perigee Cloudflare build")
        shutil.rmtree(out)
    public = out / "public"
    shutil.copytree(dist, public)

    store = CatalogStore(content.resolve())
    api = public / "api" / "v1"

    # GET /api/v1/presets
    presets_doc = store.list_presets().model_dump(mode="json")
    _write_json(api / "presets.json", presets_doc)

    # GET /api/v1/cases/{case_id}
    cases: Dict[str, str] = {}
    for cid in store.case_ids():
        case = store.get_case(cid)
        if case is None:
            continue
        rel = f"api/v1/cases/{cid}.json"
        _write_json(public / rel, case)
        cases[cid] = rel

    # GET /api/v1/presets/{preset_id}/frames[?case_id=]
    presets: Dict[str, Any] = {}
    for pid in store.preset_ids():
        frames = store.get_frames(pid)
        if frames is None:  # has_preset was false; cannot happen for listed ids
            continue
        rel = f"api/v1/presets/{pid}/frames.json"
        _write_json(public / rel, frames.model_dump(mode="json"))
        case_files: Dict[str, str] = {}
        for cid in store.case_ids_for_preset(pid):
            cf = store.get_frames(pid, cid)
            if cf is None:
                continue
            crel = f"api/v1/presets/{pid}/frames.case-{cid}.json"
            _write_json(public / crel, cf.model_dump(mode="json"))
            case_files[cid] = crel
        presets[pid] = {
            "frames": rel,
            "cases": case_files,
            # Exactly what the FastAPI route reports for an unknown case of this preset.
            "available_case_ids": [c for c in store.case_ids_for_preset(pid) if store.get_case(c) is not None],
        }

    # GET /api/v1/assets/{asset_id}
    assets: Dict[str, Any] = {}
    total_bytes = 0
    for asset_id, entry in sorted(_all_asset_entries(store).items()):
        data = store.assets.read(entry)
        if data is None:
            raise SystemExit(f"asset {asset_id} failed its hash check; refusing to export")
        rel = f"api/v1/assets/{asset_id}"
        dest = public / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        if _sha256(dest.read_bytes()) != entry.sha256:
            raise SystemExit(f"asset {asset_id} changed while exporting")
        assets[asset_id] = {
            "path": rel,
            "media_type": entry.media_type,
            "sha256": entry.sha256,
            "bytes": len(data),
            "canonical": store.assets.is_canonical(asset_id),
        }
        total_bytes += len(data)

    # Every image/flag src referenced by an exported frame must resolve.
    prefix = store.asset_url_prefix
    missing = []
    for p in sorted(public.joinpath("api/v1/presets").rglob("*.json")):
        for rec in json.loads(p.read_text(encoding="utf-8")).get("frames", []):
            for key in ("image", "flag_image"):
                src = (rec.get(key) or {}).get("src")
                if isinstance(src, str) and src.startswith(prefix) and src[len(prefix):] not in assets:
                    missing.append(src)
    if missing:
        raise SystemExit(f"{len(missing)} frame image references do not resolve, e.g. {missing[:3]}")

    manifest = {
        "schema_version": 1,
        "content_version": presets_doc.get("content_version"),
        "preset_ids": store.preset_ids(),
        "case_ids": store.case_ids(),
        "presets_document": "api/v1/presets.json",
        "presets": presets,
        "cases": cases,
        "assets": assets,
    }
    _write_json(public / MANIFEST_REL, manifest)

    info = {
        "source_commit": _git_commit(),
        "content_version": manifest["content_version"],
        "frontend_dist": str(dist.relative_to(REPO)) if dist.is_relative_to(REPO) else str(dist),
        "demo_pdf_sha256": _sha256((dist / "demo/perigee-demo.pdf").read_bytes()),
        "counts": {
            "presets": len(presets),
            "cases": len(cases),
            "case_frame_sets": sum(len(v["cases"]) for v in presets.values()),
            "assets": len(assets),
            "asset_bytes": total_bytes,
        },
    }
    _write_json(out / "build-info.json", info)
    return info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dist", type=Path, default=DEFAULT_DIST, help="built frontend (default frontend/dist)")
    ap.add_argument("--content", type=Path, default=DEFAULT_CONTENT, help="content root (default backend/content)")
    ap.add_argument("--out-any", type=Path, default=None, help=argparse.SUPPRESS)  # tests: build into a temp dir
    args = ap.parse_args(argv)
    info = _build_into(args.out_any.resolve(), args.dist, args.content) if args.out_any else build(DEFAULT_OUT, args.dist, args.content)
    print(json.dumps(info, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
