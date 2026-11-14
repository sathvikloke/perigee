"""Catalog routes: presets, cases, curated preset frames and allowlisted assets.

Paths are relative to ``/api/v1``. Mount with::

    from backend.routes import catalog
    app.include_router(catalog.router, prefix="/api/v1")

Every failure from these routes is a JSON error envelope; nothing here
returns HTML or a filesystem path.
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from backend.platform.catalog import CatalogStore, ContentUnavailable, get_catalog_store
from backend.platform.catalog_models import (
    CaseDocument,
    ErrorBody,
    ErrorEnvelope,
    PresetFramesResponse,
    PresetListResponse,
)

router = APIRouter(tags=["catalog"])

_ERROR_RESPONSES: Dict[int, Dict[str, Any]] = {
    404: {"model": ErrorEnvelope, "description": "Unknown preset, case or asset"},
    503: {"model": ErrorEnvelope, "description": "Authored content unavailable"},
}


def _new_request_id() -> str:
    return uuid.uuid4().hex


def error_response(
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    envelope = ErrorEnvelope(
        request_id=_new_request_id(),
        error=ErrorBody(code=code, message=message, retryable=retryable, details=details),
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(),
        headers={"Cache-Control": "no-store"},
    )


def _content_unavailable(exc: ContentUnavailable) -> JSONResponse:
    return error_response(503, "CONTENT_UNAVAILABLE", str(exc), retryable=False)


@router.get("/presets", response_model=PresetListResponse, responses=_ERROR_RESPONSES)
def list_presets(store: CatalogStore = Depends(get_catalog_store)):
    try:
        return store.list_presets()
    except ContentUnavailable as exc:
        return _content_unavailable(exc)


@router.get("/cases/{case_id}", response_model=CaseDocument, responses=_ERROR_RESPONSES)
def get_case(case_id: str, store: CatalogStore = Depends(get_catalog_store)):
    case = store.get_case(case_id)
    if case is None:
        return error_response(
            404,
            "CASE_NOT_FOUND",
            "Unknown case.",
            details={"available_case_ids": store.case_ids()},
        )
    return JSONResponse(content=case)


@router.get(
    "/presets/{preset_id}/frames",
    response_model=PresetFramesResponse,
    responses=_ERROR_RESPONSES,
)
def get_preset_frames(
    preset_id: str,
    case_id: Optional[str] = Query(
        None, description="Restrict to the processor's product set for this case (case-<case_id>)."
    ),
    store: CatalogStore = Depends(get_catalog_store),
):
    try:
        if not store.has_preset(preset_id):
            return error_response(
                404,
                "PRESET_NOT_FOUND",
                "Unknown preset.",
                details={"available_preset_ids": store.preset_ids()},
            )
        frames = store.get_frames(preset_id, case_id)
        if frames is None:
            return error_response(
                404,
                "CASE_NOT_FOUND",
                "Unknown case for this preset.",
                details={"available_case_ids": [
                    c for c in store.case_ids_for_preset(preset_id) if store.get_case(c) is not None
                ]},
            )
    except ContentUnavailable as exc:
        return _content_unavailable(exc)
    return frames


@router.get(
    "/assets/{asset_id}",
    responses={
        200: {"content": {"image/png": {}, "application/json": {}}},
        404: {"model": ErrorEnvelope, "description": "Unknown or unavailable asset"},
    },
)
def get_asset(asset_id: str, store: CatalogStore = Depends(get_catalog_store)):
    entry = store.assets.get(asset_id)
    data = store.assets.read(entry) if entry is not None else None
    if entry is None or data is None:
        return error_response(404, "ASSET_NOT_FOUND", "Unknown or unavailable asset.")
    # Canonical IDs embed the content hash, so they are immutable. Processor
    # alias IDs are not content-versioned; they must revalidate.
    cache = (
        "public, max-age=31536000, immutable"
        if store.assets.is_canonical(asset_id)
        else "public, max-age=300, must-revalidate"
    )
    return Response(
        content=data,
        media_type=entry.media_type,
        headers={
            "Cache-Control": cache,
            "ETag": '"{}"'.format(entry.sha256),
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )
