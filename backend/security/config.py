"""Runtime settings read from environment variables.

Secrets come only from the backend environment (Vercel project env vars), never from
public frontend variables. Nothing here is ever echoed in a response.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

MIN_SECRET_BYTES = 32
# Dev-only fallback. Used only when PERIGEE_DEV_MODE=1 *and* the platform does not
# report a production environment. Tokens signed with it are worthless elsewhere.
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
    token_secret_source: str  # "env", "dev_fallback" or "missing" (safe to expose)
    token_ttl_s: int
    upstream_connect_timeout_s: float
    upstream_read_timeout_s: float
    search_budget_s: float
    frame_fetch_max_bytes: int
    frame_budget_s: float
    is_production: bool


def is_production_env() -> bool:
    return os.environ.get("VERCEL_ENV", "").lower() == "production" or os.environ.get(
        "PERIGEE_ENV", ""
    ).lower() == "production"


def load_settings() -> Settings:
    production = is_production_env()
    secret_raw = os.environ.get("PERIGEE_TOKEN_SECRET", "")
    if production and secret_raw == _DEV_SECRET:
        # The dev secret is public in this repository; never sign with it in production.
        secret, source = None, "dev_secret_refused"
    elif secret_raw and len(secret_raw.encode()) >= MIN_SECRET_BYTES:
        secret: bytes | None = secret_raw.encode()
        source = "env"
    elif _truthy(os.environ.get("PERIGEE_DEV_MODE")) and not production:
        secret = _DEV_SECRET.encode()
        source = "dev_fallback"
    else:
        secret = None
        source = "missing" if not secret_raw else "too_short"
    return Settings(
        token_secret=secret,
        token_secret_source=source,
        token_ttl_s=max(60, _int_env("PERIGEE_TOKEN_TTL_S", 6 * 3600)),
        upstream_connect_timeout_s=_float_env("PERIGEE_UPSTREAM_CONNECT_TIMEOUT_S", 5.0),
        upstream_read_timeout_s=_float_env("PERIGEE_UPSTREAM_READ_TIMEOUT_S", 20.0),
        search_budget_s=_float_env("PERIGEE_SEARCH_BUDGET_S", 25.0),
        frame_fetch_max_bytes=_int_env("PERIGEE_FRAME_MAX_BYTES", 24 * 1024 * 1024),
        frame_budget_s=_float_env("PERIGEE_FRAME_BUDGET_S", 40.0),
        is_production=production,
    )
