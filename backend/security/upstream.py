"""Allowlisted, bounded upstream HTTP access (IRSA only).

Every upstream call made by the API goes through ``bounded_get``: https only, an exact
host allowlist, path patterns per purpose, manual redirect handling (each hop
re-checked), connect/read timeouts, an overall deadline and a byte cap enforced while
streaming. Failures are classified so routes can map them to distinct public codes:

* ``UpstreamTimeout``      -> UPSTREAM_TIMEOUT (504)
* ``UpstreamUnavailable``  -> UPSTREAM_UNAVAILABLE (502/503), incl. IRSA 5xx HTML pages
* ``UpstreamTooLarge``     -> UNSUPPORTED_DATA (502): response exceeded the byte cap
* ``UrlNotAllowed``        -> never fetched; a programming/config error or tampering
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

IRSA_HOST = "irsa.ipac.caltech.edu"
SIA_URL = f"https://{IRSA_HOST}/SIA"

# Original SPHEREx level-2 files as returned by IRSA SIA access_url.
_DATA_PATH_RE = re.compile(
    r"^/ibe/data/spherex/(dr1|qr3)/level2/[A-Za-z0-9_][A-Za-z0-9_.\-/]*\.fits$"
)
_SIA_PATH_RE = re.compile(r"^/SIA$")
_MAX_REDIRECTS = 3
USER_AGENT = "perigee-api/0.1 (NASA Space Apps educational viewer)"


class UpstreamError(Exception):
    def __init__(self, message: str, *, status: int | None = None, reason: str = ""):
        super().__init__(message)
        self.status = status
        self.reason = reason


class UpstreamTimeout(UpstreamError):
    pass


class UpstreamUnavailable(UpstreamError):
    pass


class UpstreamTooLarge(UpstreamError):
    pass


class UrlNotAllowed(UpstreamError):
    pass


def is_allowed_source_url(url: str) -> bool:
    """True for an original SPHEREx DR1/QR3 level-2 FITS URL on IRSA (no query/fragment)."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and parts.hostname == IRSA_HOST
        and parts.port is None
        and not parts.username
        and not parts.password
        and not parts.query
        and not parts.fragment
        and ".." not in parts.path
        and "//" not in parts.path
        and bool(_DATA_PATH_RE.match(parts.path))
    )


def _is_allowed_fetch_url(url: str, purpose: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme != "https" or parts.hostname != IRSA_HOST or parts.port is not None:
        return False
    if parts.username or parts.password or parts.fragment or ".." in parts.path:
        return False
    if purpose == "sia":
        return bool(_SIA_PATH_RE.match(parts.path))
    if purpose == "data":
        return "//" not in parts.path and bool(_DATA_PATH_RE.match(parts.path))
    return False


@dataclass
class UpstreamResponse:
    url: str
    status: int
    content_type: str
    body: bytes
    elapsed_s: float


async def bounded_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    purpose: str,
    params: dict[str, str] | list[tuple[str, str]] | None = None,
    max_bytes: int,
    deadline_s: float,
) -> UpstreamResponse:
    """GET ``url`` with allowlist, manual redirects, byte cap and an overall deadline."""
    if not _is_allowed_fetch_url(url, purpose):
        raise UrlNotAllowed("url not allowlisted", reason="not_allowlisted")
    try:
        return await asyncio.wait_for(
            _get_following(client, url, purpose=purpose, params=params, max_bytes=max_bytes),
            timeout=deadline_s,
        )
    except asyncio.TimeoutError as exc:
        raise UpstreamTimeout(
            f"upstream exceeded {deadline_s:.0f}s budget", reason="deadline"
        ) from exc


async def _get_following(client, url, *, purpose, params, max_bytes) -> UpstreamResponse:
    started = time.monotonic()
    current_url, current_params = url, params
    for _hop in range(_MAX_REDIRECTS + 1):
        try:
            async with client.stream(
                "GET",
                current_url,
                params=current_params,
                follow_redirects=False,
                headers={"User-Agent": USER_AGENT},
            ) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location", "")
                    nxt = urljoin(str(resp.url), location)
                    if not _is_allowed_fetch_url(nxt, purpose):
                        raise UpstreamUnavailable(
                            "upstream redirected outside the allowlist",
                            status=resp.status_code,
                            reason="redirect_not_allowlisted",
                        )
                    current_url, current_params = nxt, None
                    continue
                content_type = resp.headers.get("content-type", "").lower()
                if resp.status_code == 429:
                    raise UpstreamUnavailable(
                        "archive rate limited the request", status=429, reason="upstream_rate_limited"
                    )
                if resp.status_code >= 500:
                    raise UpstreamUnavailable(
                        f"archive returned HTTP {resp.status_code}",
                        status=resp.status_code,
                        reason="upstream_5xx",
                    )
                if resp.status_code == 404:
                    raise UpstreamUnavailable(
                        "archive resource not found", status=404, reason="upstream_404"
                    )
                if resp.status_code >= 400:
                    raise UpstreamUnavailable(
                        f"archive returned HTTP {resp.status_code}",
                        status=resp.status_code,
                        reason="upstream_4xx",
                    )
                declared = resp.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > max_bytes:
                    raise UpstreamTooLarge(
                        "upstream response larger than allowed", reason="content_length_cap"
                    )
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise UpstreamTooLarge(
                            "upstream response larger than allowed", reason="stream_cap"
                        )
                    chunks.append(chunk)
                return UpstreamResponse(
                    url=str(resp.url),
                    status=resp.status_code,
                    content_type=content_type,
                    body=b"".join(chunks),
                    elapsed_s=time.monotonic() - started,
                )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeout("archive request timed out", reason=type(exc).__name__) from exc
        except httpx.TransportError as exc:
            raise UpstreamUnavailable(
                "archive could not be reached", reason=type(exc).__name__
            ) from exc
    raise UpstreamUnavailable("too many upstream redirects", reason="redirect_loop")


def looks_like_html(content_type: str, body: bytes) -> bool:
    head = body[:512].lstrip().lower()
    return "text/html" in content_type or head.startswith(b"<!doctype html") or head.startswith(
        b"<html"
    )
