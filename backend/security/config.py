"""Runtime settings read from environment variables.

Secrets come only from the backend environment (Vercel project env vars), never from
public frontend variables. Nothing here is ever echoed in a response.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

MIN_SECRET_BYTES = 32
# Dev-only fallback for LOCAL development. Used only when PERIGEE_DEV_MODE=1 and the
# platform does not report a hosted deployment (Vercel Preview or Production). The
# value is public in this repository, so tokens signed with it are worthless.
_DEV_SECRET = "perigee-dev-only-secret-not-for-production-use-0001"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    token_secret: bytes | None
    # Safe to expose: "env", "dev_fallback" (local only), "missing", "too_short",
    # "dev_secret_refused" or "dev_mode_refused" (hosted deployments).
    token_secret_source: str
    token_ttl_s: int
    upstream_connect_timeout_s: float
    upstream_read_timeout_s: float
    search_budget_s: float
    frame_fetch_max_bytes: int
    frame_budget_s: float
    is_production: bool


HOSTED_ENVS = frozenset({"production", "preview"})


def is_production_env() -> bool:
    return os.environ.get("VERCEL_ENV", "").lower() == "production" or os.environ.get(
        "PERIGEE_ENV", ""
    ).lower() == "production"


def is_hosted_env() -> bool:
    """True on a hosted deployment (Vercel Preview or Production, or PERIGEE_ENV
    set to either). Local runs, including ``vercel dev`` (VERCEL_ENV=development),
    are not hosted."""
    return (
        os.environ.get("VERCEL_ENV", "").lower() in HOSTED_ENVS
        or os.environ.get("PERIGEE_ENV", "").lower() in HOSTED_ENVS
    )


def load_settings() -> Settings:
    production = is_production_env()
    hosted = is_hosted_env()
    secret_raw = os.environ.get("PERIGEE_TOKEN_SECRET", "")
    dev_mode = _truthy(os.environ.get("PERIGEE_DEV_MODE"))
    if hosted and secret_raw == _DEV_SECRET:
        # The dev secret is public in this repository; never sign with it on a
        # hosted deployment (Preview or Production).
        secret, source = None, "dev_secret_refused"
    elif secret_raw and len(secret_raw.encode()) >= MIN_SECRET_BYTES:
        secret: bytes | None = secret_raw.encode()
        source = "env"
    elif dev_mode and not hosted:
        secret = _DEV_SECRET.encode()
        source = "dev_fallback"
    elif dev_mode and hosted and not secret_raw:
        # PERIGEE_DEV_MODE set on Preview/Production: refuse the fallback and say so.
        secret, source = None, "dev_mode_refused"
    else:
        secret = None
        source = "missing" if not secret_raw else "too_short"
    return Settings(
        token_secret=secret,
        token_secret_source=source,
        token_ttl_s=max(60, _int_env("PERIGEE_TOKEN_TTL_S", 6 * 3600)),
        upstream_connect_timeout_s=_float_env("PERIGEE_UPSTREAM_CONNECT_TIMEOUT_S", 5.0),
        # Valid SIA responses can take over 20 seconds before their first byte.
        # Keep reads inside the search budget, and the budget inside the hosted
        # function's 60-second limit. The browser allows 60 seconds for search.
        upstream_read_timeout_s=_float_env("PERIGEE_UPSTREAM_READ_TIMEOUT_S", 40.0),
        search_budget_s=_float_env("PERIGEE_SEARCH_BUDGET_S", 50.0),
        frame_fetch_max_bytes=_int_env("PERIGEE_FRAME_MAX_BYTES", 24 * 1024 * 1024),
        frame_budget_s=_float_env("PERIGEE_FRAME_BUDGET_S", 40.0),
        is_production=production,
    )
