"""HMAC-signed frame tokens.

Format: ``pf1.<base64url(canonical JSON payload)>.<base64url(HMAC-SHA256)>``

The signature covers the ``pf1.<payload>`` prefix, so the version cannot be swapped.
The payload binds one archive descriptor (source URL, observation ID, detector,
collection, frame_key) to the normalized query (RA, Dec, FOV), an issue time and an
expiry. The caller cannot replace the upstream URL: any change breaks the signature.

Verification order: structure -> version -> signature (constant time) -> payload
shape -> expiry. A tampered token is therefore always INVALID_FRAME_TOKEN, even if it
is also expired; TOKEN_EXPIRED is reported only for authentic tokens.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import math
import time
from dataclasses import dataclass

TOKEN_VERSION = 1
TOKEN_PREFIX = "pf1"


class TokenError(Exception):
    """Base class; never carries secret material."""


class InvalidToken(TokenError):
    pass


class ExpiredToken(TokenError):
    def __init__(self, expired_at: int):
        super().__init__("token expired")
        self.expired_at = expired_at


@dataclass(frozen=True)
class FrameClaims:
    source_url: str
    observation_id: str
    detector: int | None
    collection_id: str
    frame_key: str
    mjd: float | None
    observed_at_utc: str | None
    ra_deg: float
    dec_deg: float
    fov_arcmin: float
    issued_at: int
    expires_at: int


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    if not text or any(c not in _B64_ALPHABET for c in text):
        raise InvalidToken("bad encoding")
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError) as exc:
        raise InvalidToken("bad encoding") from exc


_B64_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def _sign(secret: bytes, signing_input: bytes) -> bytes:
    return hmac.new(secret, signing_input, hashlib.sha256).digest()


def issue_token(
    secret: bytes,
    *,
    source_url: str,
    observation_id: str,
    detector: int | None,
    collection_id: str,
    frame_key: str,
    mjd: float | None,
    observed_at_utc: str | None,
    ra_deg: float,
    dec_deg: float,
    fov_arcmin: float,
    ttl_s: int,
    now: float | None = None,
) -> tuple[str, int]:
    issued = int(now if now is not None else time.time())
    expires = issued + int(ttl_s)
    payload = {
        "v": TOKEN_VERSION,
        "d": {
            "src": source_url,
            "obs": observation_id,
            "det": detector,
            "col": collection_id,
            "fk": frame_key,
            "mjd": mjd,
            "utc": observed_at_utc,
        },
        "q": {"ra": ra_deg, "dec": dec_deg, "fov": fov_arcmin},
        "iat": issued,
        "exp": expires,
    }
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{TOKEN_PREFIX}.{body}".encode()
    return f"{TOKEN_PREFIX}.{body}.{_b64e(_sign(secret, signing_input))}", expires


def _finite(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def verify_token(secret: bytes, token: str, *, now: float | None = None) -> FrameClaims:
    if not isinstance(token, str) or len(token) > 4096:
        raise InvalidToken("malformed")
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidToken("malformed")
    prefix, body, sig_text = parts
    if prefix != TOKEN_PREFIX:
        raise InvalidToken("unsupported token version")
    signature = _b64d(sig_text)
    expected = _sign(secret, f"{prefix}.{body}".encode())
    if not hmac.compare_digest(signature, expected):
        raise InvalidToken("bad signature")
    try:
        payload = json.loads(_b64d(body))
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidToken("bad payload") from exc
    try:
        if payload["v"] != TOKEN_VERSION:
            raise InvalidToken("unsupported token version")
        d, q = payload["d"], payload["q"]
        claims = FrameClaims(
            source_url=str(d["src"]),
            observation_id=str(d["obs"]),
            detector=d["det"] if d["det"] is None else int(d["det"]),
            collection_id=str(d["col"]),
            frame_key=str(d["fk"]),
            mjd=d.get("mjd"),
            observed_at_utc=d.get("utc"),
            ra_deg=float(q["ra"]),
            dec_deg=float(q["dec"]),
            fov_arcmin=float(q["fov"]),
            issued_at=int(payload["iat"]),
            expires_at=int(payload["exp"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidToken("bad payload") from exc
    if not all(_finite(v) for v in (claims.ra_deg, claims.dec_deg, claims.fov_arcmin)):
        raise InvalidToken("bad payload")
    current = now if now is not None else time.time()
    if current >= claims.expires_at:
        raise ExpiredToken(claims.expires_at)
    return claims
