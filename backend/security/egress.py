"""Candidate B: budgeted, allowlisted HTTP egress to the archive.

Every upstream byte the API reads goes through :func:`fetch`. It enforces:

- https only, host allowlist, no credentials in URLs, at most N manually followed
  redirects each re-checked against the allowlist (httpx auto-redirects are off);
- per-attempt connect/read timeouts *and* a wall-clock cap equal to the remaining
  request :class:`Budget`, so a slow-drip response cannot exceed the soft deadline;
- a maximum response size (Content-Length precheck plus a streaming byte counter);
- a content-type guard (IRSA returns ``502 Proxy Error`` HTML bodies);
- at most ``retries`` extra attempts, only for transient failures (connect error,
  HTTP 502/503/504) and only when enough budget remains. No unbounded loops.

Failures raise :class:`UpstreamFailure` with a stable ``kind`` that routes map to
public error codes; reasons never include response bodies or secrets.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple
from urllib.parse import urljoin, urlsplit

import httpx

from .config import Settings

_REDIRECTS = {301, 302, 303, 307, 308}
_TRANSIENT_STATUS = {502, 503, 504}
MIN_ATTEMPT_S = 1.0  # do not start an attempt with less budget than this
RETRY_MIN_REMAINING_S = 3.0
RETRY_BACKOFF_S = 0.3


class Budget:
    """Soft per-request deadline on a monotonic clock."""

    def __init__(self, total_s: float, clock: Callable[[], float] = time.monotonic):
        self.total_s = float(total_s)
        self._clock = clock
        self.start = clock()
        self.deadline = self.start + self.total_s

    def remaining(self) -> float:
        return max(0.0, self.deadline - self._clock())

    def elapsed_ms(self) -> int:
        return int(round((self._clock() - self.start) * 1000))


@dataclass
class UpstreamFailure(Exception):
    kind: str  # timeout | budget_exhausted | unavailable | upstream_4xx | rate_limited | too_large | bad_content | redirect_blocked | not_allowed
    detail: str = ""
    http_status: Optional[int] = None
    attempts: int = 1

    @property
    def is_timeout(self) -> bool:
        return self.kind in {"timeout", "budget_exhausted"}

    @property
    def transient(self) -> bool:
        return self.kind == "timeout_connect" or (
            self.kind == "unavailable" and (self.http_status in _TRANSIENT_STATUS or self.http_status is None)
        )

    def __str__(self) -> str:
        return f"{self.kind}({self.http_status}) {self.detail}".strip()


@dataclass
class FetchResult:
    body: bytes
    url: str
    status: int
    content_type: str
    elapsed_ms: int
    attempts: int
    redirects: List[str] = field(default_factory=list)


def url_allowed(settings: Settings, url: str) -> bool:
    try:
        p = urlsplit(url)
    except ValueError:
        return False
    return (p.scheme == "https" and p.hostname in settings.allowed_hosts and p.port in (None, 443)
            and not p.username and not p.password)


async def _attempt(client: httpx.AsyncClient, settings: Settings, url: str, *, read_timeout: float,
                   max_bytes: int, reject_types: Tuple[str, ...], budget: Budget) -> FetchResult:
    started = time.monotonic()
    redirects: List[str] = []
    current = url
    for _hop in range(settings.max_redirects + 1):
        if not url_allowed(settings, current):
            raise UpstreamFailure("redirect_blocked" if redirects else "not_allowed", "url outside allowlist")
        rem = budget.remaining()
        timeout = httpx.Timeout(connect=min(settings.connect_timeout_s, rem), read=min(read_timeout, rem),
                                write=min(5.0, rem), pool=min(2.0, rem))
        async with client.stream("GET", current, timeout=timeout, follow_redirects=False,
                                 headers={"Accept-Encoding": "identity"}) as r:
            if r.status_code in _REDIRECTS:
                loc = r.headers.get("location")
                if not loc:
                    raise UpstreamFailure("unavailable", "redirect without location", r.status_code)
                current = urljoin(current, loc)
                redirects.append(current)
                continue
            if r.status_code == 429:
                raise UpstreamFailure("rate_limited", "archive rate limited", 429)
            if r.status_code >= 500:
                raise UpstreamFailure("unavailable", "archive server error", r.status_code)
            if r.status_code != 200:
                raise UpstreamFailure("upstream_4xx", "archive rejected request", r.status_code)
            ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
            if any(ctype.startswith(t) for t in reject_types):
                raise UpstreamFailure("bad_content", f"unexpected content type {ctype}", r.status_code)
            clen = r.headers.get("content-length")
            if clen and clen.isdigit() and int(clen) > max_bytes:
                raise UpstreamFailure("too_large", f"content-length {clen} > {max_bytes}", r.status_code)
            buf = bytearray()
            async for chunk in r.aiter_bytes():  # decoded bytes: caps decompression too
                buf.extend(chunk)
                if len(buf) > max_bytes:
                    raise UpstreamFailure("too_large", f"body exceeded {max_bytes} bytes", r.status_code)
            return FetchResult(bytes(buf), current, r.status_code, ctype,
                               int((time.monotonic() - started) * 1000), 1, redirects)
    raise UpstreamFailure("redirect_blocked", "too many redirects")


async def fetch(client: httpx.AsyncClient, settings: Settings, url: str, *, budget: Budget,
                read_timeout: float, max_bytes: int, reject_types: Tuple[str, ...] = ("text/html",),
                retries: Optional[int] = None) -> FetchResult:
    retries = settings.upstream_retries if retries is None else retries
    last: Optional[UpstreamFailure] = None
    for attempt in range(1, retries + 2):
        rem = budget.remaining()
        if rem < MIN_ATTEMPT_S:
            raise UpstreamFailure("budget_exhausted", "request budget exhausted before attempt",
                                  last.http_status if last else None, attempt - 1)
        try:
            res = await asyncio.wait_for(
                _attempt(client, settings, url, read_timeout=read_timeout, max_bytes=max_bytes,
                         reject_types=reject_types, budget=budget),
                timeout=rem,
            )
            res.attempts = attempt
            return res
        except UpstreamFailure as exc:
            exc.attempts = attempt
            last = exc
        except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
            kind = "timeout_connect" if isinstance(exc, httpx.ConnectTimeout) else "timeout"
            last = UpstreamFailure(kind, type(exc).__name__, None, attempt)
        except httpx.TransportError as exc:  # connect refused, reset, protocol errors
            last = UpstreamFailure("unavailable", type(exc).__name__, None, attempt)
        if attempt <= retries and last.transient and budget.remaining() > RETRY_MIN_REMAINING_S:
            await asyncio.sleep(RETRY_BACKOFF_S)
            continue
        break
    assert last is not None
    if last.kind == "timeout_connect":
        last.kind = "timeout"
    raise last
