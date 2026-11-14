"""Candidate B frame tokens: versioned, HMAC-SHA256 signed, expiring, opaque to clients.

Format: ``pb1.<base64url(canonical JSON claims)>.<base64url(HMAC-SHA256)>``

The MAC covers the version prefix and the encoded claims, using a key derived from
``PERIGEE_TOKEN_SECRET`` with a fixed domain label so the raw secret is never used
directly. Claims bind one archive descriptor (collection, observation, detector,
source URL, start MJD) to the normalized query (RA, Dec, FOV), plus issue/expiry times.

Verification order matters and is fixed:

1. shape and version prefix (cheap, no secret involved);
2. constant-time MAC comparison (``hmac.compare_digest``);
3. strict claim parsing and type checks;
4. expiry (only reported for authentic tokens, so a forger cannot probe it);
5. semantic re-validation of the bound descriptor against the *current* allowlist
   (collection, https host, collection path prefix) as defense in depth.

Any failure before step 4 is ``INVALID_FRAME_TOKEN``; step 4 is ``TOKEN_EXPIRED``.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

from backend.models.common import ErrorCode
from backend.models.errors import ApiError
from backend.models.search import FOV_MAX_ARCMIN, FOV_MIN_ARCMIN, SUPPORTED_COLLECTIONS

from .config import Settings

TOKEN_VERSION = 1
PREFIX = "pb1"
_DOMAIN = b"perigee/frame-token/v1"
_TOKEN_RE = re.compile(r"^(pb\d{1,3})\.([A-Za-z0-9_-]{16,3000})\.([A-Za-z0-9_-]{43})$")
_CLAIM_KEYS = frozenset({"v", "iat", "exp", "col", "obs", "det", "fk", "src", "mjd", "q"})
_Q_KEYS = frozenset({"ra", "dec", "fov"})
_OBS_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
MAX_CLOCK_SKEW_S = 300


@dataclass(frozen=True)
class FrameClaims:
    collection_id: str
    observation_id: str
    detector: Optional[int]
    frame_key: str
    source_url: str
    mjd: Optional[float]
    ra_deg: float
    dec_deg: float
    fov_arcmin: float
    issued_at: int
    expires_at: int


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _key(secret: bytes) -> bytes:
    return hmac.new(secret, _DOMAIN, hashlib.sha256).digest()


def _mac(secret: bytes, signing_input: str) -> bytes:
    return hmac.new(_key(secret), signing_input.encode("ascii"), hashlib.sha256).digest()


def _invalid(reason: str) -> ApiError:
    # ``reason`` is a fixed internal label (logged, safe to expose); never echoes token text.
    return ApiError(ErrorCode.INVALID_FRAME_TOKEN, details={"reason": reason})


def iso_utc(epoch_s: float) -> str:
    return datetime.fromtimestamp(epoch_s, tz=timezone.utc).replace(microsecond=0).isoformat()


def sign_frame_token(settings: Settings, claims: FrameClaims) -> str:
    if settings.token_secret is None:
        raise ApiError(ErrorCode.SERVICE_MISCONFIGURED)
    body: Dict[str, Any] = {
        "v": TOKEN_VERSION,
        "iat": int(claims.issued_at),
        "exp": int(claims.expires_at),
        "col": claims.collection_id,
        "obs": claims.observation_id,
        "det": claims.detector,
        "fk": claims.frame_key,
        "src": claims.source_url,
        "mjd": claims.mjd,
        "q": {"ra": claims.ra_deg, "dec": claims.dec_deg, "fov": claims.fov_arcmin},
    }
    payload = _b64e(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    signing_input = f"{PREFIX}.{payload}"
    return f"{signing_input}.{_b64e(_mac(settings.token_secret, signing_input))}"


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-finite constant {name}")


def _finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def source_url_allowed(settings: Settings, collection_id: str, url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    prefix = settings.path_prefix(collection_id)
    return (
        parts.scheme == "https"
        and parts.hostname in settings.allowed_hosts
        and parts.port in (None, 443)
        and not parts.username and not parts.password
        and prefix is not None
        and parts.path.startswith(prefix)
        and ".." not in parts.path
        and parts.path.endswith(".fits")
        and not parts.query and not parts.fragment
    )


def verify_frame_token(settings: Settings, token: Any, now: float) -> FrameClaims:
    if settings.token_secret is None:
        raise ApiError(ErrorCode.SERVICE_MISCONFIGURED)
    if not isinstance(token, str) or len(token) > 4096 or not token.isascii():
        raise _invalid("format")
    m = _TOKEN_RE.match(token)
    if not m:
        raise _invalid("format")
    version, payload, sig = m.groups()
    if version != PREFIX:
        raise _invalid("version")
    try:
        given = _b64d(sig)
    except (binascii.Error, ValueError):
        raise _invalid("format") from None
    expected = _mac(settings.token_secret, f"{version}.{payload}")
    if not hmac.compare_digest(given, expected):
        raise _invalid("signature")

    try:
        c = json.loads(_b64d(payload), parse_constant=_reject_constant)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise _invalid("claims") from None
    if not isinstance(c, dict) or set(c) != _CLAIM_KEYS or c.get("v") != TOKEN_VERSION:
        raise _invalid("claims")
    q = c["q"]
    ok = (
        isinstance(c["iat"], int) and isinstance(c["exp"], int)
        and not isinstance(c["iat"], bool) and not isinstance(c["exp"], bool)
        and isinstance(c["col"], str) and isinstance(c["obs"], str) and isinstance(c["fk"], str)
        and isinstance(c["src"], str)
        and (c["det"] is None or (isinstance(c["det"], int) and not isinstance(c["det"], bool)))
        and (c["mjd"] is None or _finite(c["mjd"]))
        and isinstance(q, dict) and set(q) == _Q_KEYS and all(_finite(q[k]) for k in _Q_KEYS)
    )
    if not ok:
        raise _invalid("claims")
    if c["iat"] > now + MAX_CLOCK_SKEW_S or c["exp"] <= c["iat"]:
        raise _invalid("claims")

    if now >= c["exp"]:
        raise ApiError(
            ErrorCode.TOKEN_EXPIRED,
            details={"action": "refresh_search", "expired_at_utc": iso_utc(c["exp"])},
        )

    # Defense in depth: the descriptor must still satisfy today's allowlist.
    expected_fk = f"{c['obs']}_D{c['det']}" if c["det"] is not None else c["obs"]
    if (
        c["col"] not in SUPPORTED_COLLECTIONS
        or not _OBS_RE.match(c["obs"])
        or c["fk"] != expected_fk
        or (c["det"] is not None and not 1 <= c["det"] <= 6)
        or not source_url_allowed(settings, c["col"], c["src"])
        or not (0.0 <= q["ra"] < 360.0 and -90.0 <= q["dec"] <= 90.0)
        or not (FOV_MIN_ARCMIN <= q["fov"] <= FOV_MAX_ARCMIN)
    ):
        raise _invalid("descriptor")

    return FrameClaims(
        collection_id=c["col"], observation_id=c["obs"], detector=c["det"], frame_key=c["fk"],
        source_url=c["src"], mjd=float(c["mjd"]) if c["mjd"] is not None else None,
        ra_deg=float(q["ra"]), dec_deg=float(q["dec"]), fov_arcmin=float(q["fov"]),
        issued_at=c["iat"], expires_at=c["exp"],
    )
