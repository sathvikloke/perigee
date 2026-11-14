"""POST /api/v1/search (candidate B).

Queries each allowlisted SPHEREx collection at IRSA SIA v2 concurrently under one soft
request budget, parses the VOTable without trusting it, signs a frame token per
descriptor, and reports per-collection failures honestly:

- every collection failed               -> error envelope (UPSTREAM_TIMEOUT if all timed out,
                                            else UPSTREAM_UNAVAILABLE)
- some failed, the others returned rows -> ``status: partial`` with warnings
- some failed, the others returned none -> error envelope (cannot claim "empty")
- all succeeded, no rows                -> ``status: empty`` (scope-limited claim)
- archive overflow (MAXREC hit)         -> ``status: partial``, ``total_matches: null``
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.models.common import ErrorCode
from backend.models.errors import ApiError
from backend.models.search import (
    DEFAULT_COLLECTIONS,
    NormalizedQuery,
    ObservationDescriptor,
    SearchRequest,
    SearchResponse,
)
from backend.security.config import Settings
from backend.security.context import enforce_rate_limit, get_state
from backend.security.egress import Budget, UpstreamFailure, fetch
from backend.security.tokens import FrameClaims, iso_utc, sign_frame_token, source_url_allowed

router = APIRouter()
log = logging.getLogger("perigee.search")

SEARCH_RADIUS_DEG = 0.001  # point-in-image coverage at the query center (~3.6 arcsec)
_MJD0 = datetime(1858, 11, 17, tzinfo=timezone.utc)
_DET_BAND = re.compile(r"^SPHEREx-D([1-6])$")
_DET_DID = re.compile(r"/D([1-6])$")
_DET_URL = re.compile(r"/([1-6])/level2_[^/]*D([1-6])_spx_[^/]*\.fits$")
_OBS_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")


@dataclass
class CollectionOutcome:
    collection_id: str
    rows: List[Dict[str, Any]] = field(default_factory=list)
    failure: Optional[UpstreamFailure] = None
    overflow: bool = False
    skipped: int = 0
    elapsed_ms: int = 0
    response_bytes: int = 0
    attempts: int = 0


def _strip(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_votable(body: bytes) -> Tuple[List[Dict[str, Optional[str]]], str]:
    """Return (rows as name->text dicts, QUERY_STATUS). Raises UpstreamFailure(bad_content)."""
    head = body[:4096]
    if b"<!DOCTYPE" in head or b"<!ENTITY" in body:
        raise UpstreamFailure("bad_content", "VOTable with DTD/entities refused")
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise UpstreamFailure("bad_content", "VOTable XML parse error") from None
    if _strip(root.tag) != "VOTABLE":
        raise UpstreamFailure("bad_content", "not a VOTable")
    status = "OK"
    results = None
    for res in root.iter():
        if _strip(res.tag) == "RESOURCE" and res.get("type") == "results":
            results = res
            break
    scope = results if results is not None else root
    for el in scope.iter():
        if _strip(el.tag) == "INFO" and el.get("name") == "QUERY_STATUS":
            status = (el.get("value") or "").upper()
    if status == "ERROR":
        raise UpstreamFailure("unavailable", "archive QUERY_STATUS=ERROR")
    table = next((el for el in scope.iter() if _strip(el.tag) == "TABLE"), None)
    if table is None:
        return [], status
    names = [f.get("name") or "" for f in table if _strip(f.tag) == "FIELD"]
    data = next((el for el in table if _strip(el.tag) == "DATA"), None)
    if data is None:
        return [], status
    tabledata = next((el for el in data if _strip(el.tag) == "TABLEDATA"), None)
    if tabledata is None:
        raise UpstreamFailure("bad_content", "VOTable serialization is not TABLEDATA")
    rows: List[Dict[str, Optional[str]]] = []
    for tr in tabledata:
        if _strip(tr.tag) != "TR":
            continue
        cells = [td.text for td in tr if _strip(td.tag) == "TD"]
        if len(cells) != len(names):
            raise UpstreamFailure("bad_content", "VOTable row width mismatch")
        rows.append(dict(zip(names, cells)))
    return rows, status


def _float(v: Optional[str]) -> Optional[float]:
    try:
        f = float(v) if v not in (None, "") else None
    except ValueError:
        return None
    return f if f is not None and math.isfinite(f) else None


def mjd_to_iso(mjd: Optional[float]) -> Optional[str]:
    if mjd is None:
        return None
    dt = _MJD0 + timedelta(days=mjd)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


def _detector(row: Dict[str, Optional[str]]) -> Optional[int]:
    for pattern, key in ((_DET_BAND, "energy_bandpassname"), (_DET_DID, "obs_publisher_did")):
        m = pattern.search(row.get(key) or "")
        if m:
            return int(m.group(1))
    m = _DET_URL.search(row.get("access_url") or "")
    if m and m.group(1) == m.group(2):
        return int(m.group(1))
    return None


def row_to_descriptor(settings: Settings, collection_id: str, row: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
    """Validated plain descriptor, or None if the row must not be signed."""
    obs = (row.get("obs_id") or "").strip()
    url = (row.get("access_url") or "").strip()
    if not _OBS_RE.match(obs) or (row.get("obs_collection") or collection_id) != collection_id:
        return None
    if (row.get("dataproduct_type") or "image") != "image":
        return None
    if not source_url_allowed(settings, collection_id, url):
        return None
    det = _detector(row)
    mjd = _float(row.get("t_min"))
    em_min, em_max = _float(row.get("em_min")), _float(row.get("em_max"))
    return {
        "observation_id": obs,
        "detector": det,
        "frame_key": f"{obs}_D{det}" if det is not None else obs,
        "collection_id": collection_id,
        "observed_at_utc": mjd_to_iso(mjd),
        "mjd": mjd,
        "time_basis": "sia_t_min",
        "band_name": (row.get("energy_bandpassname") or None),
        "detector_wavelength_range_um": (
            [round(em_min * 1e6, 4), round(em_max * 1e6, 4)] if em_min is not None and em_max is not None else None
        ),
        "source_url": url,
    }


async def query_collection(settings: Settings, client, collection_id: str, ra: float, dec: float,
                           budget: Budget) -> CollectionOutcome:
    out = CollectionOutcome(collection_id)
    params = {
        "COLLECTION": collection_id,
        "POS": f"CIRCLE {ra!r} {dec!r} {SEARCH_RADIUS_DEG}",
        "RESPONSEFORMAT": "VOTABLE",
        "MAXREC": str(settings.sia_maxrec),
    }
    url = f"{settings.sia_url}?{urlencode(params)}"
    t0 = time.monotonic()
    try:
        res = await fetch(client, settings, url, budget=budget, read_timeout=settings.search_read_timeout_s,
                          max_bytes=settings.max_search_bytes)
        out.attempts, out.response_bytes = res.attempts, len(res.body)
        rows, status = parse_votable(res.body)
        out.overflow = status == "OVERFLOW"
        seen = set()
        for row in rows:
            d = row_to_descriptor(settings, collection_id, row)
            if d is None:
                out.skipped += 1
            elif d["frame_key"] not in seen:
                seen.add(d["frame_key"])
                out.rows.append(d)
    except UpstreamFailure as exc:
        out.failure = exc
        out.attempts = exc.attempts
    out.elapsed_ms = int((time.monotonic() - t0) * 1000)
    return out


def evenly_spaced(n: int, k: int) -> List[int]:
    if n <= k:
        return list(range(n))
    if k == 1:
        return [0]
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def _sort_key(d: Dict[str, Any]) -> Tuple[bool, float, str]:
    return (d["mjd"] is None, d["mjd"] if d["mjd"] is not None else 0.0, d["frame_key"])


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, request: Request) -> JSONResponse:
    st = get_state()
    settings = st.settings()
    enforce_rate_limit(request, "search", settings.search_per_minute)
    if not settings.signing_enabled:
        raise ApiError(ErrorCode.SERVICE_MISCONFIGURED)
    budget = Budget(settings.request_budget_s)
    collections = list(dict.fromkeys(body.collection_ids or DEFAULT_COLLECTIONS))
    ra, dec, fov = float(body.ra_deg), float(body.dec_deg), float(body.fov_arcmin)

    async with st.client_factory() as client:
        outcomes = await asyncio.gather(*[
            query_collection(settings, client, c, ra, dec, budget) for c in collections
        ])

    failed = [o for o in outcomes if o.failure is not None]
    ok = [o for o in outcomes if o.failure is None]
    rows = [d for o in ok for d in o.rows]
    timing = ", ".join(f"{o.collection_id};dur={o.elapsed_ms}" for o in outcomes)
    log.info("search ra=%.5f dec=%.5f %s", ra, dec,
             {o.collection_id: (o.failure.kind if o.failure else len(o.rows), o.elapsed_ms, o.attempts)
              for o in outcomes})

    if failed and not rows:
        details = {
            "collections_failed": [o.collection_id for o in failed],
            "collections_succeeded_empty": [o.collection_id for o in ok],
            "reasons": {o.collection_id: o.failure.kind for o in failed},
            "attempts": {o.collection_id: o.attempts for o in failed},
        }
        # All failures timed out -> 504; otherwise 502 (503 if the archive rate-limited us).
        if all(o.failure.is_timeout for o in failed):
            raise ApiError(ErrorCode.UPSTREAM_TIMEOUT, details=details, headers={"Server-Timing": timing})
        limited = any(o.failure.kind == "rate_limited" for o in failed)
        raise ApiError(ErrorCode.UPSTREAM_UNAVAILABLE, status=503 if limited else None, details=details,
                       headers={"Server-Timing": timing})

    rows.sort(key=_sort_key)
    n = len(rows)
    overflow = any(o.overflow for o in ok)
    picked = [rows[i] for i in evenly_spaced(n, body.limit)]
    warnings: List[str] = []
    if failed:
        names = ", ".join(o.collection_id for o in failed)
        warnings.append(f"Some collections could not be searched ({names}); results are incomplete.")
    if overflow:
        warnings.append(f"The archive capped a collection at {settings.sia_maxrec} records; "
                        "the total number of matches is unknown.")
    if n > len(picked):
        warnings.append(f"Showing {len(picked)} of {n} matching images, evenly spaced in time. "
                        f"Narrow the request or raise the limit (max 48) to see others.")
    skipped = sum(o.skipped for o in ok)
    if skipped:
        warnings.append(f"{skipped} archive record(s) were ignored because they were not allowlisted "
                        "SPHEREx image files.")
    if n == 0:
        warnings.append("No SPHEREx images in the searched collections ("
                        + ", ".join(collections) + ") cover this position. "
                        "This is not a claim that no telescope ever observed it.")

    now = time.time()
    exp = int(now) + settings.token_ttl_s
    observations: List[Dict[str, Any]] = []
    for d in picked:
        claims = FrameClaims(
            collection_id=d["collection_id"], observation_id=d["observation_id"], detector=d["detector"],
            frame_key=d["frame_key"], source_url=d["source_url"], mjd=d["mjd"],
            ra_deg=ra, dec_deg=dec, fov_arcmin=fov, issued_at=int(now), expires_at=exp,
        )
        observations.append({**d, "frame_token": sign_frame_token(settings, claims)})

    status = "empty" if n == 0 else ("partial" if failed or overflow else "ready")
    resp = SearchResponse(
        request_id=request.state.request_id,
        query=NormalizedQuery(ra_deg=ra, dec_deg=dec, fov_arcmin=fov, limit=body.limit,
                              collection_ids=collections, search_radius_deg=SEARCH_RADIUS_DEG),
        status=status,
        observations=[ObservationDescriptor(**o) for o in observations],
        returned_count=len(observations),
        total_matches=None if (overflow or failed) else n,  # unknown if any collection failed
        truncated=n > len(observations) or overflow,
        selection="evenly_spaced_in_time" if n > len(observations) else "all",
        warnings=warnings,
        collections_queried=collections,
        collections_failed=[o.collection_id for o in failed],
        token_expires_at_utc=iso_utc(exp) if observations else None,
        queried_at_utc=iso_utc(now),
    )
    return JSONResponse(resp.model_dump(mode="json"),
                        headers={"Cache-Control": "no-store", "Server-Timing": timing})
