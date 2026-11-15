"""POST /api/v1/search: bounded SPHEREx coverage search at one coordinate.

* Input is validated strictly (see backend/models/search.py); nothing is clipped.
* Every selected collection is queried at the actual coordinate (no preset fallback).
* status (docs/INTEGRATION_CONTRACT.md, "Search"):
  - ready: every collection answered in full and >=1 image matched. Choosing an
    evenly spaced subset because of the caller's ``limit`` keeps ``ready``
    (retrieval finished; ``truncated`` true, ``total_matches`` known).
  - partial: >=1 image, but retrieval was incomplete: a collection failed
    (``collections_failed``) or the archive hit its documented record cap,
    SIA MAXREC (``collections_capped``; ``truncated`` true, ``total_matches`` null).
  - empty: every collection answered in full and none matched.
  Upstream failure with no results is an error envelope, never "empty".
* Matching is a coverage search: images whose footprint contains the query center
  (``SEARCH_RADIUS_DEG``, 3.6"). ``fov_arcmin`` sets the cutout/display field only and
  does not change which images match. There is no date filter or pagination in v1.
* Descriptors are sorted by mjd then frame_key. When more than ``limit`` match, an
  evenly spaced-in-time subset (always including the first and last) is returned and
  ``truncated`` is true.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from backend.models.common import ErrorCode
from backend.models.search import (
    DEFAULT_COLLECTIONS,
    LIMIT_MAX,
    SUPPORTED_COLLECTIONS,
    NormalizedQuery,
    ObservationDescriptor,
    SearchRequest,
    SearchResponse,
)
from backend.security.tokens import issue_token
from backend.security.upstream import UpstreamError, UpstreamTimeout, UrlNotAllowed

from ._adapters import Services, resolve_services
from ._archive import SEARCH_RADIUS_DEG, SIA_MAXREC, CollectionResult
from ._errors import ApiError, request_id_of

router = APIRouter()

SCOPE_NOTE = (
    "Scope: SPHEREx {cols} level-2 wide-survey images whose footprint covers the query "
    "center. A zero result here is not a claim that no telescope ever observed this position."
)


def _sort_key(d: dict) -> tuple:
    mjd = d.get("mjd")
    return (mjd is None, mjd if mjd is not None else 0.0, d["frame_key"])


def select_evenly(items: list[dict], limit: int) -> list[dict]:
    """Pick ``limit`` items evenly spaced across a time-sorted list (keeps first and last)."""
    n = len(items)
    if n <= limit:
        return list(items)
    if limit == 1:
        return [items[0]]
    idx = sorted({round(i * (n - 1) / (limit - 1)) for i in range(limit)})
    return [items[i] for i in idx]


def _require_secret(services: Services) -> bytes:
    if services.settings.token_secret is None:
        raise ApiError(
            ErrorCode.SERVICE_MISCONFIGURED,
            "Frame signing is not configured on this deployment.",
            http_status=503,
            retryable=False,
            details={"token_signing": services.settings.token_secret_source},
        )
    return services.settings.token_secret


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest, request: Request, services: Services = Depends(resolve_services)
):
    secret = _require_secret(services)
    collections = list(body.collection_ids or DEFAULT_COLLECTIONS)
    # Preserve allowlist order and drop duplicates.
    collections = [c for c in SUPPORTED_COLLECTIONS if c in set(collections)]
    started = time.monotonic()
    budget = services.settings.search_budget_s

    async with services.http_client_factory() as client:
        tasks = [
            services.search_collection(
                client,
                ra_deg=body.ra_deg,
                dec_deg=body.dec_deg,
                fov_arcmin=body.fov_arcmin,
                collection_id=c,
                deadline_s=budget,
            )
            for c in collections
        ]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    succeeded: list[CollectionResult] = []
    failed: dict[str, BaseException] = {}
    for c, out in zip(collections, outcomes):
        if isinstance(out, CollectionResult):
            succeeded.append(out)
        elif isinstance(out, BaseException):
            if not isinstance(out, (UpstreamError, asyncio.TimeoutError)):
                raise out  # programming error -> INTERNAL_ERROR handler
            failed[c] = out

    merged: list[dict] = []
    seen: set[str] = set()
    duplicates = 0
    for res in succeeded:  # allowlist order: DR1 preferred over QR3 for the same frame_key
        for d in res.descriptors:
            if d["frame_key"] in seen:
                duplicates += 1
                continue
            seen.add(d["frame_key"])
            merged.append(d)
    merged.sort(key=_sort_key)

    if failed and not merged:
        any_timeout = any(isinstance(e, (UpstreamTimeout, asyncio.TimeoutError)) for e in failed.values())
        not_allowed = any(isinstance(e, UrlNotAllowed) for e in failed.values())
        code = ErrorCode.UPSTREAM_TIMEOUT if any_timeout else ErrorCode.UPSTREAM_UNAVAILABLE
        raise ApiError(
            code,
            "The NASA/IPAC archive did not answer in time." if any_timeout
            else "The NASA/IPAC archive is unavailable right now.",
            http_status=504 if any_timeout else (500 if not_allowed else 502),
            retryable=not not_allowed,
            details={
                "collections_failed": sorted(failed),
                "collections_succeeded_empty": [r.collection_id for r in succeeded],
                "reasons": {c: getattr(e, "reason", "") or type(e).__name__ for c, e in failed.items()},
                "attempts": {c: getattr(e, "attempts", 1) for c, e in failed.items()},
            },
        )

    warnings: list[str] = []
    capped = sorted(r.collection_id for r in succeeded if r.overflow)
    overflow = bool(capped)
    # Unknown (null) when the archive capped records or a collection failed.
    total = None if (overflow or failed) else len(merged)
    selected = select_evenly(merged, body.limit)
    truncated = len(selected) < len(merged) or overflow
    if failed:
        warnings.append(
            "Some collections could not be searched ({}); results are incomplete.".format(
                ", ".join(sorted(failed))
            )
        )
    if overflow:
        warnings.append(
            "The archive returned its maximum number of records for {} ({} per collection), so the total "
            "is unknown and some matching images were not retrieved. The search matches images that cover "
            "this position; the field of view sets the cutout size, not which images match.".format(
                ", ".join(capped), SIA_MAXREC
            )
        )
    if len(selected) < len(merged):
        warnings.append(
            f"Showing {len(selected)} of {len(merged)} matching images, evenly spaced in time from the "
            f"earliest to the latest. Raising the limit (up to {LIMIT_MAX}) shows more; the field of view "
            "sets the cutout size, not which images match."
        )
    if duplicates:
        warnings.append(f"{duplicates} image(s) appeared in more than one release; kept the DR1 copy.")
    skipped = sum(r.skipped for r in succeeded)
    if skipped:
        warnings.append(f"{skipped} archive record(s) were not level-2 SPHEREx images and were skipped.")
    if not merged:
        warnings.append(SCOPE_NOTE.format(cols=" and ".join(collections)))

    if not merged:
        status = "empty" if not overflow else "partial"
    else:
        status = "partial" if (failed or overflow) else "ready"
    ttl = services.settings.token_ttl_s
    now = time.time()
    observations: list[ObservationDescriptor] = []
    expires_at = None
    for d in selected:
        token, expires_at = issue_token(
            secret,
            source_url=d["source_url"],
            observation_id=d["observation_id"],
            detector=d.get("detector"),
            collection_id=d["collection_id"],
            frame_key=d["frame_key"],
            mjd=d.get("mjd"),
            observed_at_utc=d.get("observed_at_utc"),
            ra_deg=body.ra_deg,
            dec_deg=body.dec_deg,
            fov_arcmin=body.fov_arcmin,
            ttl_s=ttl,
            now=now,
        )
        observations.append(
            ObservationDescriptor(
                observation_id=d["observation_id"],
                detector=d.get("detector"),
                frame_key=d["frame_key"],
                collection_id=d["collection_id"],
                observed_at_utc=d.get("observed_at_utc"),
                mjd=d.get("mjd"),
                time_basis=d.get("time_basis", "sia_t_min"),
                band_name=d.get("band_name"),
                detector_wavelength_range_um=d.get("detector_wavelength_range_um"),
                source_url=d["source_url"],
                frame_token=token,
            )
        )

    response = SearchResponse(
        request_id=request_id_of(request),
        query=NormalizedQuery(
            ra_deg=body.ra_deg,
            dec_deg=body.dec_deg,
            fov_arcmin=body.fov_arcmin,
            limit=body.limit,
            collection_ids=collections,
            search_radius_deg=SEARCH_RADIUS_DEG,
        ),
        status=status,
        observations=observations,
        returned_count=len(observations),
        total_matches=total,
        truncated=truncated,
        selection="evenly_spaced_in_time" if len(selected) < len(merged) else "all",
        warnings=warnings,
        collections_queried=collections,
        collections_failed=sorted(failed),
        collections_capped=capped,
        token_expires_at_utc=(
            datetime.fromtimestamp(expires_at, timezone.utc).isoformat(timespec="seconds")
            if expires_at
            else None
        ),
        queried_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    return JSONResponse(
        response.model_dump(mode="json"),
        headers={"Cache-Control": "no-store", "Server-Timing": f"archive;dur={elapsed_ms}"},
    )

