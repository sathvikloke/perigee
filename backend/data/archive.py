"""Bounded IRSA access for SPHEREx: SIA search and allowlisted cutout fetch.

Network access lives here, separate from the pure FITS processor
(``process.py``). Everything is bounded: an allowlist of collections and
hosts, connect/read timeouts, a maximum response size, no redirects to
other hosts, and a result limit. Parsing is split from transport so unit
tests can feed local bytes.

Error codes map onto the public envelope: ``UPSTREAM_UNAVAILABLE``,
``UPSTREAM_TIMEOUT``, ``UNSUPPORTED_DATA``. IRSA sometimes answers with an
HTTP 502 HTML "Proxy Error" page; that is an upstream failure, never an empty
result.
"""

from __future__ import annotations

import math
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from astropy.time import Time

SIA_ENDPOINT = "https://irsa.ipac.caltech.edu/SIA"
ALLOWED_COLLECTIONS: Tuple[str, ...] = ("spherex_dr1", "spherex_qr3")
ALLOWED_HOST = "irsa.ipac.caltech.edu"
ALLOWED_DATA_PREFIX = "/ibe/data/spherex/"

DEFAULT_TIMEOUT_S = 20.0
MAX_SIA_BYTES = 8 * 1024 * 1024
MAX_CUTOUT_BYTES = 12 * 1024 * 1024  # a 6' cutout is ~4 MB (7 extensions)
MAX_LIMIT = 48

USER_AGENT = "perigee-spherex-viewer/0.1 (+https://github.com/sathvikloke/perigee)"


class ArchiveError(Exception):
    def __init__(self, code: str, message: str, retryable: bool, detail: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.detail = detail


# Transport: (url, timeout_s, max_bytes) -> (http_status, content_type, body)
Transport = Callable[[str, float, int], Tuple[int, str, bytes]]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        if not is_allowed_url(newurl, allow_query=True, allow_sia=True):
            raise ArchiveError("UPSTREAM_UNAVAILABLE", "upstream redirected outside the allowlist", False)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _ssl_context() -> ssl.SSLContext:
    """Verified TLS context; prefers the certifi bundle when installed (some
    standalone Python builds ship without a usable system CA path)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:  # pragma: no cover
        return ssl.create_default_context()


def urllib_transport(url: str, timeout_s: float, max_bytes: int) -> Tuple[int, str, bytes]:
    """Default transport (stdlib). Reads at most ``max_bytes + 1`` bytes."""
    opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=_ssl_context()))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=timeout_s) as resp:
            body = resp.read(max_bytes + 1)
            return resp.status, resp.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as exc:
        body = exc.read(min(max_bytes, 65536)) if exc.fp else b""
        return exc.code, exc.headers.get("Content-Type", "") if exc.headers else "", body
    except (socket.timeout, TimeoutError) as exc:
        raise ArchiveError("UPSTREAM_TIMEOUT", "archive request timed out", True) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise ArchiveError("UPSTREAM_TIMEOUT", "archive request timed out", True) from exc
        raise ArchiveError("UPSTREAM_UNAVAILABLE", "archive unreachable", True, type(exc.reason).__name__) from exc


# --------------------------------------------------------------------------- URLs


def is_allowed_url(url: str, *, allow_query: bool = False, allow_sia: bool = False) -> bool:
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    if p.scheme != "https" or p.hostname != ALLOWED_HOST or p.port not in (None, 443) or p.username or p.password:
        return False
    if allow_sia and p.path == "/SIA":
        return True
    if not p.path.startswith(ALLOWED_DATA_PREFIX) or not p.path.endswith(".fits") or ".." in p.path:
        return False
    return allow_query or not p.query


def sia_url(collection: str, ra_deg: float, dec_deg: float, radius_deg: float) -> str:
    if collection not in ALLOWED_COLLECTIONS:
        raise ValueError(f"collection {collection!r} not in allowlist")
    for name, v in (("ra_deg", ra_deg), ("dec_deg", dec_deg), ("radius_deg", radius_deg)):
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{name} must be finite")
    if not (0 <= ra_deg < 360 and -90 <= dec_deg <= 90 and 0 < radius_deg <= 0.2):
        raise ValueError("coordinate or radius out of range")
    pos = f"circle {ra_deg!r} {dec_deg!r} {radius_deg!r}"
    return SIA_ENDPOINT + "?" + urllib.parse.urlencode({"COLLECTION": collection, "POS": pos})


def cutout_url(source_url: str, ra_deg: float, dec_deg: float, size_deg: float = 0.1) -> str:
    """IRSA IBE cutout of an allowlisted SPHEREx image (same form as the retained ledger)."""
    if not is_allowed_url(source_url):
        raise ValueError("source_url not in the SPHEREx allowlist")
    if not (math.isfinite(size_deg) and 0 < size_deg <= 0.25):
        raise ValueError("size_deg out of range")
    q = urllib.parse.urlencode({"center": f"{ra_deg!r},{dec_deg!r}", "size": f"{size_deg!r}"})
    return f"{source_url}?{q}"


# --------------------------------------------------------------------------- parsing


@dataclass
class SearchResult:
    observations: List[Dict[str, Any]]
    collections_queried: List[str]
    failures: List[Dict[str, Any]] = field(default_factory=list)
    total_matches: Optional[int] = None
    truncated: bool = False
    queried_at_utc: str = ""

    @property
    def status(self) -> str:
        if self.observations:
            return "partial" if (self.failures or self.truncated) else "ready"
        if self.failures:
            # Nothing returned and something failed: caller should map to an error, not "empty".
            return "error"
        return "empty"


_DET_RE = re.compile(r"D(\d)\b")


def _detector(row: Dict[str, Any]) -> Optional[int]:
    for key in ("energy_bandpassname", "obs_publisher_did"):
        v = row.get(key)
        if v:
            m = re.search(r"D(\d)$", str(v).strip())
            if m:
                return int(m.group(1))
    m = re.search(r"_\d+D(\d)_spx_", str(row.get("access_url") or ""))
    return int(m.group(1)) if m else None


def _clean(v: Any) -> Any:
    try:
        import numpy as np

        if v is np.ma.masked:
            return None
        if isinstance(v, np.generic):
            v = v.item()
    except ImportError:  # pragma: no cover
        pass
    if isinstance(v, bytes):
        v = v.decode("utf-8", "replace")
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def parse_sia_votable(body: bytes, collection: str) -> List[Dict[str, Any]]:
    """Parse an SIA v2 VOTable into observation descriptors (no network).

    ``observed_at_utc``/``mjd`` here come from ``t_min`` (exposure start, the
    descriptor-time basis of INTEGRATION_BOARD decision 2); the processed
    FrameRecord replaces them with mid-exposure ``DATE-AVG``/``MJD-AVG``.
    """
    from astropy.io.votable import parse

    head = body[:512].lstrip().lower()
    if not (head.startswith(b"<?xml") or head.startswith(b"<votable")):
        raise ArchiveError("UPSTREAM_UNAVAILABLE", "archive returned a non-VOTable body", True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            vot = parse(BytesIO(body), verify="ignore")
        except Exception as exc:
            raise ArchiveError("UPSTREAM_UNAVAILABLE", "archive returned an unparsable VOTable", True,
                               type(exc).__name__) from exc
    # IVOA error documents carry INFO name=QUERY_STATUS value=ERROR
    for res in vot.resources:
        for info in getattr(res, "infos", []):
            if info.name == "QUERY_STATUS" and str(info.value).upper() == "ERROR":
                raise ArchiveError("UPSTREAM_UNAVAILABLE", "archive reported a query error", True,
                                   (info.content or "")[:200])
    tables = [t for res in vot.resources if res.type == "results" for t in res.tables]
    if not tables:
        raise ArchiveError("UPSTREAM_UNAVAILABLE", "VOTable has no results table", True)
    tab = tables[0]
    names = [f.name for f in tab.fields]
    out = []
    for raw in tab.array:
        row = {n: _clean(raw[n]) for n in names}
        if row.get("dataproduct_type") not in (None, "image"):
            continue
        url = row.get("access_url")
        if not url or not is_allowed_url(url):
            continue
        obs_id = row.get("obs_id")
        det = _detector(row)
        if not obs_id or det is None:
            continue
        t_min = row.get("t_min")
        out.append({
            "observation_id": obs_id,
            "detector": det,
            "frame_key": f"{obs_id}_D{det}",
            "collection_id": row.get("obs_collection") or collection,
            "observed_at_utc": (Time(t_min, format="mjd").utc.isot + "Z") if t_min is not None else None,
            "mjd": t_min,
            "time_basis": "SIA t_min (exposure start); the processed frame uses mid-exposure MJD-AVG",
            "source_url": url,
            "access_estsize_kb": row.get("access_estsize"),
            "s_region": row.get("s_region"),
        })
    return out


def _sort_key(d: Dict[str, Any]):
    return (d["mjd"] if d["mjd"] is not None else float("inf"), d["frame_key"])


# --------------------------------------------------------------------------- network


def search_spherex(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    *,
    collections: Iterable[str] = ALLOWED_COLLECTIONS,
    limit: int = 24,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    transport: Transport = urllib_transport,
) -> SearchResult:
    """Query SIA per allowlisted collection; one collection failing yields ``partial``."""
    if not 1 <= int(limit) <= MAX_LIMIT:
        raise ValueError(f"limit must be in [1, {MAX_LIMIT}]")
    cols = list(collections)
    for c in cols:
        if c not in ALLOWED_COLLECTIONS:
            raise ValueError(f"collection {c!r} not in allowlist")
    obs: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    for c in cols:
        url = sia_url(c, ra_deg, dec_deg, radius_deg)
        try:
            status, ctype, body = transport(url, timeout_s, MAX_SIA_BYTES)
            if len(body) > MAX_SIA_BYTES:
                raise ArchiveError("UPSTREAM_UNAVAILABLE", "archive response exceeded the size limit", False)
            if status != 200:
                raise ArchiveError("UPSTREAM_UNAVAILABLE", f"archive returned HTTP {status}", status >= 500)
            if "html" in (ctype or "").lower():
                raise ArchiveError("UPSTREAM_UNAVAILABLE", "archive returned HTML instead of a VOTable", True)
            obs.extend(parse_sia_votable(body, c))
        except ArchiveError as exc:
            failures.append({"collection_id": c, "code": exc.code, "message": exc.message, "retryable": exc.retryable})
    # De-duplicate by frame_key, sort by time then key, then bound.
    seen, uniq = set(), []
    for d in sorted(obs, key=_sort_key):
        if d["frame_key"] not in seen:
            seen.add(d["frame_key"])
            uniq.append(d)
    return SearchResult(
        observations=uniq[: int(limit)],
        collections_queried=cols,
        failures=failures,
        total_matches=len(uniq) if not failures else None,
        truncated=len(uniq) > int(limit),
        queried_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )


def fetch_cutout(
    source_url: str,
    ra_deg: float,
    dec_deg: float,
    *,
    size_deg: float = 0.1,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_bytes: int = MAX_CUTOUT_BYTES,
    transport: Transport = urllib_transport,
) -> Tuple[bytes, str, str]:
    """Download one allowlisted cutout. Returns (fits_bytes, cutout_url, retrieved_at_utc)."""
    url = cutout_url(source_url, ra_deg, dec_deg, size_deg)
    status, ctype, body = transport(url, timeout_s, max_bytes)
    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if status != 200:
        raise ArchiveError("UPSTREAM_UNAVAILABLE", f"archive returned HTTP {status}", status >= 500)
    if len(body) > max_bytes:
        raise ArchiveError("UNSUPPORTED_DATA", "cutout exceeded the size limit", False)
    if "html" in (ctype or "").lower() or not body.startswith(b"SIMPLE  ="):
        raise ArchiveError("UPSTREAM_UNAVAILABLE", "archive did not return FITS data", True)
    return body, url, retrieved
