"""Frame-token unit tests (candidate B): HMAC, version, expiry, binding, allowlist."""

from __future__ import annotations

import base64
import dataclasses
import json
import time

import pytest

from backend.models.common import ErrorCode
from backend.models.errors import ApiError
from backend.security.tokens import FrameClaims, sign_frame_token, verify_frame_token

from .conftest import SRC_D3, make_settings

NOW = 1_800_000_000


def claims(**kw) -> FrameClaims:
    base = dict(collection_id="spherex_dr1", observation_id="2026W18_1A_0516_1", detector=3,
                frame_key="2026W18_1A_0516_1_D3", source_url=SRC_D3, mjd=61159.50335,
                ra_deg=330.84, dec_deg=-56.786, fov_arcmin=6.0, issued_at=NOW, expires_at=NOW + 3600)
    base.update(kw)
    return FrameClaims(**base)


def code_of(fn) -> tuple:
    with pytest.raises(ApiError) as ei:
        fn()
    return ei.value.code, (ei.value.details or {}).get("reason")


def _forge(token: str, mutate) -> str:
    v, p, s = token.split(".")
    body = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
    mutate(body)
    p2 = base64.urlsafe_b64encode(json.dumps(body).encode()).rstrip(b"=").decode()
    return f"{v}.{p2}.{s}"


def test_roundtrip_binds_descriptor_and_query():
    s = make_settings()
    tok = sign_frame_token(s, claims())
    got = verify_frame_token(s, tok, NOW + 10)
    assert got == claims()
    assert tok.startswith("pb1.")


@pytest.mark.parametrize("bad", ["", "garbage", "pb1.abc.def", "pb1..", "x" * 5000, "pb1.é.x", None, 12])
def test_malformed_is_invalid(bad):
    s = make_settings()
    assert code_of(lambda: verify_frame_token(s, bad, NOW))[0] == ErrorCode.INVALID_FRAME_TOKEN


def test_tampered_payload_rejected_by_signature():
    s = make_settings()
    tok = sign_frame_token(s, claims())
    forged = _forge(tok, lambda b: b.update(src=SRC_D3.replace("/3/", "/4/")))
    assert code_of(lambda: verify_frame_token(s, forged, NOW)) == (ErrorCode.INVALID_FRAME_TOKEN, "signature")


def test_wrong_secret_rejected():
    tok = sign_frame_token(make_settings(), claims())
    other = make_settings(token_secret=b"z" * 40)
    assert code_of(lambda: verify_frame_token(other, tok, NOW)) == (ErrorCode.INVALID_FRAME_TOKEN, "signature")


def test_unknown_version_rejected():
    s = make_settings()
    tok = sign_frame_token(s, claims())
    assert code_of(lambda: verify_frame_token(s, "pb2." + tok[4:], NOW)) == (ErrorCode.INVALID_FRAME_TOKEN, "version")


def test_expired_authentic_token():
    s = make_settings()
    tok = sign_frame_token(s, claims(expires_at=NOW + 60))
    with pytest.raises(ApiError) as ei:
        verify_frame_token(s, tok, NOW + 60)
    assert ei.value.code == ErrorCode.TOKEN_EXPIRED
    assert ei.value.details["action"] == "refresh_search"
    assert ei.value.status == 400


def test_forged_expired_token_reports_invalid_not_expired():
    s = make_settings()
    tok = sign_frame_token(s, claims(expires_at=NOW + 60))
    forged = _forge(tok, lambda b: b.update(exp=NOW - 5))
    assert code_of(lambda: verify_frame_token(s, forged, NOW))[0] == ErrorCode.INVALID_FRAME_TOKEN


def test_signed_but_disallowed_source_is_rejected():
    s = make_settings()
    evil = claims(source_url="https://evil.example/ibe/data/spherex/dr1/x.fits")
    tok = sign_frame_token(s, evil)
    assert code_of(lambda: verify_frame_token(s, tok, NOW)) == (ErrorCode.INVALID_FRAME_TOKEN, "descriptor")
    wrong_coll = claims(collection_id="spherex_qr3")  # dr1 path under qr3 claim
    tok = sign_frame_token(s, wrong_coll)
    assert code_of(lambda: verify_frame_token(s, tok, NOW)) == (ErrorCode.INVALID_FRAME_TOKEN, "descriptor")


def test_future_issued_token_rejected():
    s = make_settings()
    tok = sign_frame_token(s, claims(issued_at=NOW + 3600, expires_at=NOW + 7200))
    assert code_of(lambda: verify_frame_token(s, tok, NOW))[0] == ErrorCode.INVALID_FRAME_TOKEN


def test_no_secret_is_misconfigured():
    s = make_settings(token_secret=None, token_secret_source="missing")
    assert code_of(lambda: verify_frame_token(s, "pb1.x.y", NOW))[0] == ErrorCode.SERVICE_MISCONFIGURED


def test_dev_fallback_only_with_flag_and_never_in_production(monkeypatch):
    from backend.security.config import load_settings

    monkeypatch.delenv("PERIGEE_TOKEN_SECRET", raising=False)
    monkeypatch.delenv("PERIGEE_DEV_MODE", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.delenv("PERIGEE_ENV", raising=False)
    assert load_settings().token_secret is None
    monkeypatch.setenv("PERIGEE_DEV_MODE", "1")
    assert load_settings().token_secret_source == "dev_fallback"
    monkeypatch.setenv("VERCEL_ENV", "production")
    assert load_settings().token_secret is None
    monkeypatch.setenv("PERIGEE_TOKEN_SECRET", "short")
    assert load_settings().token_secret_source == "too_short"
    monkeypatch.setenv("PERIGEE_TOKEN_SECRET", "s" * 32)
    assert load_settings().token_secret_source == "env"
