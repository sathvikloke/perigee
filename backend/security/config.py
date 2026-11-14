"""Candidate B runtime settings, read once per process from environment variables.

Secrets never leave this module except as bytes handed to the token signer; health
reports only whether signing is configured. Environment names match candidate A so the
two are swappable on one deployment:

- ``PERIGEE_TOKEN_SECRET``: HMAC key, at least 32 bytes. Required outside dev mode.
- ``PERIGEE_DEV_MODE=1``: allows a fixed, public development secret when no secret is
  set. Ignored when ``VERCEL_ENV=production`` or ``PERIGEE_ENV=production``.
- ``PERIGEE_TOKEN_TTL_S``: frame-token lifetime (default 6 h, clamped to 5 min..24 h).
- ``PERIGEE_REQUEST_BUDGET_S``: soft per-request budget (default 45 s, below the 60 s
  Vercel function limit; clamped to 5..55 s).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional, Tuple

DEV_SECRET = b"perigee-dev-only-secret-not-for-deployment-0000"
MIN_SECRET_BYTES = 32


def _truthy(v: Optional[str]) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


def _num(name: str, default: float, lo: float, hi: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        v = float(raw)
    except ValueError:
        return default
    if v != v:  # NaN
        return default
    return min(hi, max(lo, v))


@dataclass(frozen=True)
class Settings:
    token_secret: Optional[bytes]
    token_secret_source: str  # "env" | "dev_fallback" | "missing" | "too_short"
    token_ttl_s: int
    production: bool
    # Budgets (seconds / bytes)
    request_budget_s: float
    connect_timeout_s: float = 4.0
    search_read_timeout_s: float = 15.0
    frame_read_timeout_s: float = 20.0
    max_search_bytes: int = 12 * 1024 * 1024  # ~2.1 KB per SIA row -> ~5k rows
    max_fits_bytes: int = 25 * 1024 * 1024
    max_request_body_bytes: int = 16 * 1024
    sia_maxrec: int = 2000
    processing_reserve_s: float = 6.0  # min budget left before starting FITS processing
    upstream_retries: int = 1  # one extra attempt on 502/503/connect error, budget permitting
    allowed_hosts: Tuple[str, ...] = ("irsa.ipac.caltech.edu",)
    # Per-client fixed-window limits (best effort, per function instance)
    search_per_minute: int = 30
    frame_per_minute: int = 120
    max_redirects: int = 2
    sia_url: str = "https://irsa.ipac.caltech.edu/SIA"
    collection_paths: Tuple[Tuple[str, str], ...] = field(default=(
        ("spherex_dr1", "/ibe/data/spherex/dr1/"),
        ("spherex_qr3", "/ibe/data/spherex/qr3/"),
    ))

    @property
    def signing_enabled(self) -> bool:
        return self.token_secret is not None

    def path_prefix(self, collection_id: str) -> Optional[str]:
        return dict(self.collection_paths).get(collection_id)


def load_settings() -> Settings:
    production = (os.environ.get("VERCEL_ENV", "").lower() == "production"
                  or os.environ.get("PERIGEE_ENV", "").lower() == "production")
    raw = os.environ.get("PERIGEE_TOKEN_SECRET", "")
    secret: Optional[bytes]
    if raw:
        b = raw.encode("utf-8")
        if len(b) >= MIN_SECRET_BYTES:
            secret, source = b, "env"
        else:
            secret, source = None, "too_short"
    elif _truthy(os.environ.get("PERIGEE_DEV_MODE")) and not production:
        secret, source = DEV_SECRET, "dev_fallback"
    else:
        secret, source = None, "missing"
    return Settings(
        token_secret=secret,
        token_secret_source=source,
        token_ttl_s=int(_num("PERIGEE_TOKEN_TTL_S", 6 * 3600, 300, 24 * 3600)),
        production=production,
        request_budget_s=_num("PERIGEE_REQUEST_BUDGET_S", 45.0, 5.0, 55.0),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
