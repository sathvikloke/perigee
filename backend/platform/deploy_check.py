"""Pre-deployment checks for the Vercel Services layout (worker 07).

Run from the repository root:

    python -m backend.platform.deploy_check            # config + bundle hygiene
    python -m backend.platform.deploy_check --app      # also import backend.main:app

Checks only what the deployment contract needs; it does not test product
behaviour. Exits non-zero with a list of failures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW_SUFFIXES = (".fits", ".fit", ".fz", ".fits.gz")
# Files larger than this inside backend/ are suspicious for a function bundle.
MAX_BACKEND_FILE_BYTES = 5 * 1024 * 1024


def check_vercel_json(errors: list[str]) -> None:
    path = REPO / "vercel.json"
    try:
        cfg = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        errors.append(f"vercel.json unreadable: {exc}")
        return
    services = cfg.get("services") or {}
    api = services.get("api")
    web = services.get("web")
    if not api or not web:
        errors.append("vercel.json must define services 'api' and 'web'")
        return
    if api.get("entrypoint") != "backend.main:app":
        errors.append("api.entrypoint must be 'backend.main:app' (package imports; see docs/DEPLOYMENT.md)")
    if api.get("root", "").rstrip("/") not in ("", "."):
        errors.append("api.root must be the repo root: root 'backend/' shadows stdlib 'platform' with backend/platform")
    for key in ("functions", "buildCommand", "installCommand", "outputDirectory", "framework"):
        if key in cfg:
            errors.append(f"top-level '{key}' is invalid in services mode; move it into a service")
    rewrites = cfg.get("rewrites") or []
    order = [
        (r.get("source"), (r.get("destination") or {}).get("service"))
        for r in rewrites
        if isinstance(r.get("destination"), dict)
    ]
    api_idx = [i for i, (src, svc) in enumerate(order) if svc == "api" and src and src.startswith("/api")]
    web_idx = [i for i, (src, svc) in enumerate(order) if svc == "web" and src == "/(.*)"]
    if not api_idx or not web_idx:
        errors.append("rewrites must route /api/(.*) to 'api' and /(.*) to 'web'")
    elif max(api_idx) > min(web_idx):
        errors.append("an /api rewrite is ordered after the /(.*) catch-all; API calls would get index.html")


def check_bundle_hygiene(errors: list[str]) -> None:
    backend = REPO / "backend"
    if not backend.is_dir():
        errors.append("backend/ missing")
        return
    for f in backend.rglob("*"):
        if not f.is_file() or ".venv" in f.parts or "__pycache__" in f.parts:
            continue
        rel = f.relative_to(REPO)
        if f.name.lower().endswith(RAW_SUFFIXES):
            errors.append(f"raw FITS inside the function bundle: {rel}")
        elif f.stat().st_size > MAX_BACKEND_FILE_BYTES:
            errors.append(f"file over {MAX_BACKEND_FILE_BYTES // 2**20} MB in backend/: {rel}")
    ignore = REPO / ".vercelignore"
    text = ignore.read_text() if ignore.exists() else ""
    for needed in ("research/", "**/*.fits"):
        if needed not in text:
            errors.append(f".vercelignore must exclude {needed}")


def check_app(errors: list[str]) -> None:
    sys.path.insert(0, str(REPO))
    try:
        from fastapi.testclient import TestClient

        from backend.main import app
    except Exception as exc:  # noqa: BLE001 - report any import failure
        errors.append(f"cannot import backend.main:app: {exc!r}")
        return
    client = TestClient(app)
    r = client.get("/api/v1/health")
    if r.status_code != 200 or "application/json" not in r.headers.get("content-type", ""):
        errors.append(f"/api/v1/health -> {r.status_code} {r.headers.get('content-type')}")
    r = client.get("/api/v1/__deploy_check_unknown__")
    if r.status_code != 404 or "application/json" not in r.headers.get("content-type", ""):
        errors.append(f"unknown /api path -> {r.status_code} {r.headers.get('content-type')} (want JSON 404)")


def main(argv: list[str]) -> int:
    errors: list[str] = []
    check_vercel_json(errors)
    check_bundle_hygiene(errors)
    if "--app" in argv:
        check_app(errors)
    for e in errors:
        print(f"FAIL {e}")
    print("deploy_check:", "ok" if not errors else f"{len(errors)} failure(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
