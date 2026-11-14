"""Candidate B: per-process collaborators shared by the search and frame routes.

Tests replace ``state.client_factory`` / ``state.processor_loader`` / limiters via
``reset_state``; nothing here keeps per-request data between requests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import httpx
from fastapi import Request

from backend.models.common import ErrorCode
from backend.models.errors import ApiError

from .config import Settings, get_settings
from .egress import UpstreamFailure
from .ratelimit import FixedWindowLimiter

USER_AGENT = "perigee-api/1 (+NASA Space Apps viewer; candidate-b)"


def default_client_factory() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=False,
                             limits=httpx.Limits(max_connections=8, max_keepalive_connections=4))


@dataclass
class AppState:
    settings_loader: Callable[[], Settings] = get_settings
    client_factory: Callable[[], httpx.AsyncClient] = default_client_factory
    processor_loader: Optional[Callable[[], Any]] = None  # set by routes.frames
    limiters: Dict[str, FixedWindowLimiter] = field(default_factory=dict)

    def settings(self) -> Settings:
        return self.settings_loader()

    def limiter(self, name: str, per_minute: int) -> FixedWindowLimiter:
        lim = self.limiters.get(name)
        if lim is None or lim.per_window != per_minute:
            lim = self.limiters[name] = FixedWindowLimiter(per_minute)
        return lim


state = AppState()


def reset_state(**overrides: Any) -> AppState:
    global state
    state = AppState(**overrides)
    return state


def get_state() -> AppState:
    return state


def client_key(request: Request) -> str:
    # Vercel sets x-forwarded-for with the client first; locally fall back to the peer.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, name: str, per_minute: int) -> None:
    wait = get_state().limiter(name, per_minute).check(client_key(request))
    if wait is not None:
        raise ApiError(ErrorCode.RATE_LIMITED, details={"retry_after_s": wait},
                       headers={"Retry-After": str(wait)})


def upstream_error(fail: UpstreamFailure, **details: Any) -> ApiError:
    """Map one upstream failure to the public envelope (no bodies, no URLs with secrets)."""
    info = {"reason": fail.kind, "attempts": fail.attempts, **details}
    if fail.http_status is not None:
        info["upstream_status"] = fail.http_status
    if fail.is_timeout:
        return ApiError(ErrorCode.UPSTREAM_TIMEOUT, details=info)
    if fail.kind == "rate_limited":
        return ApiError(ErrorCode.UPSTREAM_UNAVAILABLE, status=503, details=info)
    if fail.kind in {"too_large", "redirect_blocked", "not_allowed", "upstream_4xx"}:
        return ApiError(ErrorCode.UPSTREAM_UNAVAILABLE, retryable=False, details=info)
    return ApiError(ErrorCode.UPSTREAM_UNAVAILABLE, details=info)
