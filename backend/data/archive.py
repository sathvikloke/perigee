"""Network side of the data adapter: bounded IRSA metadata search and cutout download.

This module talks to the archive. It does not touch pixels; `process.py` does that from bytes.
Tests swap in a fake `http_get` so nothing here needs the network to be unit tested.

Archive interface used (official IRSA services):
  * SIA v2 image search:   https://irsa.ipac.caltech.edu/SIA?COLLECTION=<c>&POS=circle+ra+dec+r
  * IBE cutout service:    <full-file URL>?center=<ra>,<dec>&size=<deg>
See https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
"""
from __future__ import annotations

import hashlib
import io
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from .errors import DataError, UnsupportedData, UpstreamTimeout, UpstreamUnavailable
from .timeutil import mjd_to_iso
from .records import (
    CollectionOutcome,
    ObservationDescriptor,
    SearchQuery,
    SearchResult,
)

ARCHIVE_HOST = "irsa.ipac.caltech.edu"
SIA_ENDPOINT = f"https://{ARCHIVE_HOST}/SIA"

# Search radius around the field center. A record is returned when its footprint touches this
# small circle, so every returned exposure covers (or nearly covers) the center. 18 arcsec is
# about three SPHEREx pixels.
SEARCH_RADIUS_DEG = 0.005
SIA_MAXREC = 2000  # archive-side cap per collection; hitting it is reported as overflow

SEARCH_TIMEOUT_S = 20.0
SEARCH_MAX_BYTES = 8 * 1024 * 1024
CUTOUT_TIMEOUT_S = 25.0
CUTOUT_MAX_BYTES = 16 * 1024 * 1024  # Level 2 cutouts are ~4 MB, mostly the EPSF table
# IRSA's SIA service answered ~50% of requests with a fast "502 Proxy Error" during the event
# (2026-11-14), while cutout downloads were reliable. Searches therefore get more attempts,
# inside a hard time budget; cutouts get one retry.
SEARCH_ATTEMPTS = 4
SEARCH_BUDGET_S = 25.0  # whole search, both collections in parallel
CUTOUT_ATTEMPTS = 2
RETRY_BACKOFF_S = 0.5  # waits 0.5 s, 1.0 s, 1.5 s between attempts

# Cutout side length relative to the display field. The display grid is north-up, while
# SPHEREx detectors sit at any angle, so a square cutout needs ~sqrt(2) times the field to
# cover the grid corners. 1.5 adds a small margin.
CUTOUT_FOV_FACTOR = 1.5

# Full-file Level 2 URLs we will ever request. Anything else is refused before any network call.
_SOURCE_URL_RE = re.compile(
    r"^https://irsa\.ipac\.caltech\.edu/ibe/data/spherex/(?P<release>dr1|qr3)/level2/"
    r"[A-Za-z0-9_]+/l2b-[A-Za-z0-9.\-]+/(?P<det>[1-6])/"
    r"level2_[A-Za-z0-9_]+D(?P=det)_spx_l2b-[A-Za-z0-9.\-]+\.fits$"
)
_COLLECTION_RELEASE = {"spherex_dr1": "dr1", "spherex_qr3": "qr3"}


# --------------------------------------------------------------------------- HTTP layer


@dataclass
class HttpResponse:
    status: int
    content_type: str
    body: bytes
    url: str


class HttpGet(Protocol):
    def __call__(self, url: str, *, timeout: float, max_bytes: int) -> HttpResponse: ...


class _ArchiveOnlyRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only if it stays on https://irsa.ipac.caltech.edu."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https" or parsed.hostname != ARCHIVE_HOST:
            raise UpstreamUnavailable("archive redirected to an unexpected host", details={"status": code})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_ArchiveOnlyRedirects())


def urllib_get(url: str, *, timeout: float, max_bytes: int) -> HttpResponse:
    """Default HTTP GET: archive-host only, bounded time and size, typed failures."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ARCHIVE_HOST:
        raise UpstreamUnavailable("refused to contact a non-archive host")
    req = urllib.request.Request(url, headers={"User-Agent": "perigee-data/0.1 (+https://github.com/sathvikloke/perigee)"})
    try:
        with _opener.open(req, timeout=timeout) as resp:
            chunks, total = [], 0
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise UpstreamUnavailable("archive response exceeded the size limit", details={"max_bytes": max_bytes})
                chunks.append(chunk)
            return HttpResponse(resp.status, resp.headers.get("Content-Type", ""), b"".join(chunks), resp.geturl())
    except urllib.error.HTTPError as exc:
        if exc.code >= 500:
            raise UpstreamUnavailable("archive returned an HTTP error", details={"status": exc.code}) from None
        raise _non_retryable(exc.code) from None
    except (socket.timeout, TimeoutError) as exc:
        raise UpstreamTimeout("archive did not answer in time") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise UpstreamTimeout("archive did not answer in time") from None
        raise UpstreamUnavailable("could not reach the archive") from None


def _non_retryable(status: int) -> UpstreamUnavailable:
    err = UpstreamUnavailable("archive rejected the request", details={"status": status})
    err.retryable = False
    return err


def _with_retries(
    fn: Callable[[], HttpResponse],
    *,
    attempts: int,
    backoff_s: float,
    sleep=time.sleep,
    deadline: float | None = None,
    clock=time.monotonic,
) -> HttpResponse:
    """Bounded retries for retryable upstream failures. Never retries past `deadline`."""
    last: DataError | None = None
    for i in range(attempts):
        try:
            resp = fn()
            if resp.status >= 500:
                raise UpstreamUnavailable("archive returned an HTTP error", details={"status": resp.status})
            return resp
        except (UpstreamUnavailable, UpstreamTimeout) as exc:
            last = exc
            wait = backoff_s * (i + 1)
            if not exc.retryable or i == attempts - 1:
                break
            if deadline is not None and clock() + wait >= deadline:
                break
            sleep(wait)
    assert last is not None
    raise last


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --------------------------------------------------------------------------- search


def sia_url(collection_id: str, ra_deg: float, dec_deg: float, radius_deg: float = SEARCH_RADIUS_DEG) -> str:
    params = {
        "COLLECTION": collection_id,
        "POS": f"circle {ra_deg:.8f} {dec_deg:.8f} {radius_deg:g}",
        "MAXREC": str(SIA_MAXREC),
    }
    return SIA_ENDPOINT + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)


def _looks_like_html(body: bytes) -> bool:
    head = body[:512].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<html" in head[:200]


def parse_sia_votable(body: bytes, collection_id: str) -> tuple[list[ObservationDescriptor], str]:
    """Parse an SIA v2 VOTable. Returns (descriptors, query_status).

    query_status is the archive's QUERY_STATUS INFO value: "OK", "OVERFLOW" or "ERROR".
    """
    if _looks_like_html(body) or b"VOTABLE" not in body[:4096]:
        raise UpstreamUnavailable("archive search returned something other than a VOTable")
    from astropy.io.votable import parse as parse_votable

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            vot = parse_votable(io.BytesIO(body))
        except Exception as exc:  # malformed XML from upstream
            raise UpstreamUnavailable("archive search returned an unreadable VOTable") from exc

    status = "OK"
    for res in vot.resources:
        for info in res.infos:
            if info.name == "QUERY_STATUS":
                status = (info.value or "OK").upper()
    if status == "ERROR":
        raise UpstreamUnavailable("archive search reported an error", details={"collection_id": collection_id})

    try:
        table = vot.get_first_table()
    except Exception:
        return [], status
    names = [f.name for f in table.fields]
    arr = table.array
    cols = arr.dtype.names

    def col(name: str):
        if name not in names:
            return None
        return arr[cols[names.index(name)]]

    obs_id, url, t_min, band = col("obs_id"), col("access_url"), col("t_min"), col("energy_bandpassname")
    did, em_min, em_max, texp = col("obs_publisher_did"), col("em_min"), col("em_max"), col("t_exptime")
    if obs_id is None or url is None:
        raise UpstreamUnavailable("archive search table is missing obs_id or access_url")

    out: list[ObservationDescriptor] = []
    for i in range(len(arr)):
        source_url = _str(url[i])
        m = _SOURCE_URL_RE.match(source_url or "")
        if not m:
            continue  # not a Level 2 spectral image we know how to cut out
        det = int(m.group("det"))
        base = _str(obs_id[i])
        mjd = _float(t_min[i]) if t_min is not None else None
        if not base:
            continue
        out.append(
            ObservationDescriptor(
                observation_id=base,
                collection_id=collection_id,
                observed_at_utc=mjd_to_iso(mjd),
                mjd=mjd,
                detector=det,
                source_url=source_url,
                publisher_did=_str(did[i]) if did is not None else None,
                band_min_um=_m_to_um(em_min[i]) if em_min is not None else None,
                band_max_um=_m_to_um(em_max[i]) if em_max is not None else None,
                exposure_s=_float(texp[i]) if texp is not None else None,
            )
        )
    return out, status


def search_observations(
    query: SearchQuery,
    *,
    http_get: HttpGet = urllib_get,
    sleep=time.sleep,
) -> SearchResult:
    """Bounded metadata search of the allowlisted SPHEREx collections around one position.

    * Returns at most `query.limit` descriptors, spread evenly across the time range found
      (not just the earliest ones), sorted by observation time with frame_key as tie breaker.
    * A collection that fails is listed as failed; if every collection fails, raises.
    * `total_matches` is the number of records found, or None if the archive overflowed.
    """
    outcomes: list[CollectionOutcome] = []
    found: dict[str, ObservationDescriptor] = {}
    warnings_out: list[str] = []
    errors: list[DataError] = []
    overflow = False
    deadline = time.monotonic() + SEARCH_BUDGET_S

    def one(cid: str):
        url = sia_url(cid, query.ra_deg, query.dec_deg)
        try:
            resp = _with_retries(
                lambda: http_get(url, timeout=SEARCH_TIMEOUT_S, max_bytes=SEARCH_MAX_BYTES),
                attempts=SEARCH_ATTEMPTS,
                backoff_s=RETRY_BACKOFF_S,
                sleep=sleep,
                deadline=deadline,
            )
            return parse_sia_votable(resp.body, cid)
        except (UpstreamUnavailable, UpstreamTimeout) as exc:
            return exc

    # Collections are independent, so search them at the same time (at most 2 threads).
    with ThreadPoolExecutor(max_workers=max(1, len(query.collection_ids))) as pool:
        results = list(pool.map(one, query.collection_ids))

    for cid, res in zip(query.collection_ids, results):
        if isinstance(res, DataError):
            errors.append(res)
            outcomes.append(CollectionOutcome(cid, "failed", None, res.code))
            warnings_out.append(f"{cid} could not be searched ({res.code}); its observations are missing from this result.")
            continue
        descs, qstatus = res
        if qstatus == "OVERFLOW":
            overflow = True
            warnings_out.append(f"{cid} hit the archive record limit; more observations may exist.")
            outcomes.append(CollectionOutcome(cid, "overflow", len(descs)))
        else:
            outcomes.append(CollectionOutcome(cid, "ok", len(descs)))
        for d in descs:
            found.setdefault(d.frame_key, d)

    if len(errors) == len(query.collection_ids):
        first = errors[0]
        raise type(first)("no supported collection could be searched", details={"collections": list(query.collection_ids)})

    ordered = sorted(found.values(), key=lambda d: (d.mjd if d.mjd is not None else float("inf"), d.frame_key))
    total = len(ordered)
    selected = select_spread(ordered, query.limit)
    truncated = overflow or total > len(selected)
    if total > len(selected):
        warnings_out.append(
            f"Showing {len(selected)} of {total} observations found, spaced across the full date range."
        )
    failed_any = any(o.status == "failed" for o in outcomes)

    if failed_any or overflow:
        status = "partial"
    elif total == 0:
        status = "empty"
    else:
        status = "ready"
    if failed_any and total == 0:
        # Nothing useful and one collection unknown: do not call that "empty".
        raise UpstreamUnavailable(
            "part of the archive could not be searched and the rest returned nothing",
            details={"collections": [o.collection_id for o in outcomes if o.status == "failed"]},
        )

    return SearchResult(
        query=query,
        status=status,
        observations=selected,
        total_matches=None if overflow else total,
        truncated=truncated,
        warnings=warnings_out,
        collections_queried=outcomes,
        queried_at_utc=_utc_now(),
    )


def select_spread(ordered: list[ObservationDescriptor], limit: int) -> list[ObservationDescriptor]:
    """Pick `limit` items spread evenly through a time-ordered list (deterministic)."""
    n = len(ordered)
    if n <= limit:
        return list(ordered)
    if limit == 1:
        return [ordered[0]]
    idx = sorted({round(i * (n - 1) / (limit - 1)) for i in range(limit)})
    return [ordered[i] for i in idx]


# --------------------------------------------------------------------------- cutouts


@dataclass(frozen=True)
class CutoutBytes:
    data: bytes
    url: str
    sha256: str
    retrieved_at_utc: str


def validate_source_url(source_url: str, collection_id: str | None = None) -> None:
    m = _SOURCE_URL_RE.match(source_url or "")
    if not m:
        raise UnsupportedData("source is not a supported SPHEREx Level 2 archive file")
    if collection_id is not None and _COLLECTION_RELEASE.get(collection_id) != m.group("release"):
        raise UnsupportedData("source file does not belong to the stated collection")


def cutout_url(source_url: str, center_ra_deg: float, center_dec_deg: float, size_deg: float) -> str:
    validate_source_url(source_url)
    if not (0.0 <= center_ra_deg < 360.0 and -90.0 <= center_dec_deg <= 90.0):
        raise UnsupportedData("cutout center is outside the sky")
    if not (0.0 < size_deg <= 0.5):
        raise UnsupportedData("cutout size outside the supported range")
    q = urllib.parse.urlencode({"center": f"{center_ra_deg:.8f},{center_dec_deg:.8f}", "size": f"{size_deg:.5f}"})
    return f"{source_url}?{q}"


def cutout_size_deg(fov_arcmin: float) -> float:
    return fov_arcmin / 60.0 * CUTOUT_FOV_FACTOR


def fetch_cutout(
    observation: ObservationDescriptor,
    center_ra_deg: float,
    center_dec_deg: float,
    fov_arcmin: float,
    *,
    http_get: HttpGet = urllib_get,
    sleep=time.sleep,
) -> CutoutBytes:
    """Download one small cutout and check that it is a FITS file before anyone parses it."""
    validate_source_url(observation.source_url, observation.collection_id)
    url = cutout_url(observation.source_url, center_ra_deg, center_dec_deg, cutout_size_deg(fov_arcmin))
    resp = _with_retries(
        lambda: http_get(url, timeout=CUTOUT_TIMEOUT_S, max_bytes=CUTOUT_MAX_BYTES),
        attempts=CUTOUT_ATTEMPTS,
        backoff_s=RETRY_BACKOFF_S,
        sleep=sleep,
    )
    if resp.status != 200:
        raise UpstreamUnavailable("archive did not return the cutout", details={"status": resp.status})
    body = resp.body
    if _looks_like_html(body):
        raise UpstreamUnavailable("archive returned a web page instead of a FITS file")
    if not body.startswith(b"SIMPLE  ="):
        raise UnsupportedData("archive response is not a FITS file")
    if len(body) % 2880 != 0:
        raise UnsupportedData("FITS file is truncated")
    return CutoutBytes(body, url, hashlib.sha256(body).hexdigest(), _utc_now())


# --------------------------------------------------------------------------- helpers


def _str(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, bytes):
        v = v.decode("utf-8", "replace")
    s = str(v).strip()
    return s or None


def _float(v) -> float | None:
    import numpy as np

    if v is None or np.ma.is_masked(v):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN / masked
        return None
    return f


def _m_to_um(v) -> float | None:
    f = _float(v)
    return None if f is None else f * 1e6
