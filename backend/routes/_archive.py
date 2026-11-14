"""IRSA SIA v2 coverage search for SPHEREx DR1/QR3 level-2 images.

This is the API team's built-in archive adapter. It is network + VOTable parsing only;
no FITS processing lives here. If backend/data later provides an equivalent
``search_collection`` function, ``_adapters.resolve_services`` prefers it.

Returned descriptor dicts (one per detector image):

    {
      "observation_id": "2025W18_1B_0081_1",
      "detector": 6,                      # int | None
      "frame_key": "2025W18_1B_0081_1_D6",
      "collection_id": "spherex_dr1",
      "observed_at_utc": "2025-04-30T01:31:10.848",   # from SIA t_min
      "mjd": 60794.06332,                 # SIA t_min (exposure start)
      "time_basis": "sia_t_min",
      "band_name": "SPHEREx-D6",
      "detector_wavelength_range_um": [4.4115, 5.0096],
      "source_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/...fits",
    }
"""

from __future__ import annotations

import asyncio
import math
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx

from backend.security.upstream import (
    SIA_URL,
    UpstreamUnavailable,
    bounded_get,
    is_allowed_source_url,
    looks_like_html,
)

# Coverage search radius around the query center. Small on purpose: we want images
# whose footprint contains (essentially) the center, not ones that merely graze the
# field. 0.001 deg = 3.6 arcsec, well under one 6.15" SPHEREx pixel.
SEARCH_RADIUS_DEG = 0.001
SIA_MAXREC = 2000
SIA_MAX_BYTES = 12 * 1024 * 1024
SIA_MAX_ATTEMPTS = 5
SIA_RETRY_BACKOFF_S = 0.3
_RETRY_STATUSES = {502, 503, 504}
_RETRY_REASONS = {"html_body", "ConnectError", "RemoteProtocolError", "ReadError"}

_MJD_EPOCH = datetime(1858, 11, 17, tzinfo=timezone.utc)
_DID_DET_RE = re.compile(r"/D(\d+)$")
_BAND_DET_RE = re.compile(r"-D(\d+)$")
_URL_DET_RE = re.compile(r"D(\d+)_spx")


@dataclass
class CollectionResult:
    collection_id: str
    descriptors: list[dict] = field(default_factory=list)
    overflow: bool = False
    skipped: int = 0


def mjd_to_iso(mjd: float | None) -> str | None:
    if mjd is None or not math.isfinite(mjd):
        return None
    dt = _MJD_EPOCH + timedelta(days=mjd)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


def _float_or_none(text: str | None) -> float | None:
    if text is None or text.strip() == "":
        return None
    try:
        v = float(text)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _detector(row: dict[str, str]) -> int | None:
    for key, rx in (
        ("obs_publisher_did", _DID_DET_RE),
        ("energy_bandpassname", _BAND_DET_RE),
        ("access_url", _URL_DET_RE),
    ):
        m = rx.search(row.get(key) or "")
        if m:
            return int(m.group(1))
    return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_votable(body: bytes) -> tuple[list[dict[str, str]], bool]:
    """Return (rows as dicts, overflow flag). Raises UpstreamUnavailable on archive errors."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise UpstreamUnavailable("archive returned unparseable XML", reason="votable_parse") from exc
    if _local(root.tag) != "VOTABLE":
        raise UpstreamUnavailable("archive response is not a VOTable", reason="not_votable")
    overflow = False
    rows: list[dict[str, str]] = []
    for resource in root.iter():
        if _local(resource.tag) != "RESOURCE" or resource.get("type") != "results":
            continue
        for info in resource:
            if _local(info.tag) == "INFO" and info.get("name") == "QUERY_STATUS":
                status = (info.get("value") or "").upper()
                if status == "ERROR":
                    raise UpstreamUnavailable(
                        "archive reported a query error", reason="query_status_error"
                    )
                if status == "OVERFLOW":
                    overflow = True
        for table in resource.iter():
            if _local(table.tag) != "TABLE":
                continue
            names = [f.get("name", "") for f in table if _local(f.tag) == "FIELD"]
            for tr in table.iter():
                if _local(tr.tag) != "TR":
                    continue
                cells = [(td.text or "") for td in tr if _local(td.tag) == "TD"]
                rows.append(dict(zip(names, cells)))
    # Post-table INFO elements can also carry OVERFLOW.
    for info in root.iter():
        if _local(info.tag) == "INFO" and info.get("name") == "QUERY_STATUS":
            if (info.get("value") or "").upper() == "OVERFLOW":
                overflow = True
    return rows, overflow


def rows_to_descriptors(rows: list[dict[str, str]], collection_id: str) -> tuple[list[dict], int]:
    out: list[dict] = []
    skipped = 0
    for row in rows:
        url = (row.get("access_url") or "").strip()
        obs_id = (row.get("obs_id") or "").strip()
        if (
            not obs_id
            or not is_allowed_source_url(url)
            or (row.get("dataproduct_type") or "image") != "image"
            or (row.get("obs_collection") or collection_id) != collection_id
        ):
            skipped += 1
            continue
        det = _detector(row)
        mjd = _float_or_none(row.get("t_min"))
        em_min, em_max = _float_or_none(row.get("em_min")), _float_or_none(row.get("em_max"))
        out.append(
            {
                "observation_id": obs_id,
                "detector": det,
                "frame_key": f"{obs_id}_D{det}" if det is not None else obs_id,
                "collection_id": collection_id,
                "observed_at_utc": mjd_to_iso(mjd),
                "mjd": mjd,
                "time_basis": "sia_t_min",
                "band_name": (row.get("energy_bandpassname") or None),
                "detector_wavelength_range_um": (
                    [round(em_min * 1e6, 5), round(em_max * 1e6, 5)]
                    if em_min is not None and em_max is not None
                    else None
                ),
                "source_url": url,
            }
        )
    return out, skipped


async def irsa_search_collection(
    client: httpx.AsyncClient,
    *,
    ra_deg: float,
    dec_deg: float,
    fov_arcmin: float,
    collection_id: str,
    deadline_s: float,
) -> CollectionResult:
    """Query IRSA SIA v2 for images in one collection covering the query center."""
    params = [
        ("COLLECTION", collection_id),
        ("POS", f"CIRCLE {ra_deg!r} {dec_deg!r} {SEARCH_RADIUS_DEG}"),
        ("MAXREC", str(SIA_MAXREC)),
    ]
    started = time.monotonic()
    attempt = 0
    while True:
        attempt += 1
        remaining = deadline_s - (time.monotonic() - started)
        try:
            resp = await bounded_get(
                client,
                SIA_URL,
                purpose="sia",
                params=params,
                max_bytes=SIA_MAX_BYTES,
                deadline_s=max(0.5, remaining),
            )
            if looks_like_html(resp.content_type, resp.body):
                # IRSA serves HTML proxy-error pages (seen with HTTP 502, sometimes 200).
                raise UpstreamUnavailable("archive returned an HTML error page", reason="html_body")
            break
        except UpstreamUnavailable as exc:
            # IRSA's proxy returns intermittent fast 502s (~50% of SIA calls on
            # 2026-11-14, ~0.4 s each) that succeed on retry. Retry a bounded number of
            # times inside the search budget; the attempt count is reported on failure.
            transient = exc.status in _RETRY_STATUSES or exc.reason in _RETRY_REASONS
            remaining = deadline_s - (time.monotonic() - started)
            if not transient or attempt >= SIA_MAX_ATTEMPTS or remaining < 2.0:
                exc.attempts = attempt  # type: ignore[attr-defined]
                raise
            await asyncio.sleep(SIA_RETRY_BACKOFF_S * attempt)
    if "xml" not in resp.content_type and not resp.body.lstrip().startswith(b"<"):
        raise UpstreamUnavailable("archive returned an unexpected content type", reason="content_type")
    rows, overflow = parse_votable(resp.body)
    descriptors, skipped = rows_to_descriptors(rows, collection_id)
    return CollectionResult(collection_id, descriptors, overflow=overflow, skipped=skipped)
