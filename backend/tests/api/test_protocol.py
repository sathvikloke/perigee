"""HTTP protocol tests (candidate B): validation, error envelope, routing, health, examples."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.models import ErrorEnvelope, FrameResponse, SearchResponse

EXAMPLES = Path(__file__).parent / "examples"
OK = {"schema_version": 1, "ra_deg": 330.84, "dec_deg": -56.786}


def err(r, status, code):
    assert r.status_code == status, r.text
    assert r.headers["content-type"].startswith("application/json")
    body = r.json()
    ErrorEnvelope.model_validate(body)
    assert body["error"]["code"] == code, body
    assert body["request_id"] == r.headers["x-request-id"]
    return body


@pytest.mark.parametrize("raw,code", [
    (b'{"schema_version":1,"ra_deg":NaN,"dec_deg":0}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":Infinity,"dec_deg":0}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":1e999,"dec_deg":0}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":-Infinity}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":"330.84","dec_deg":0}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":"330abc","dec_deg":0}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":true,"dec_deg":0}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":360,"dec_deg":0}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":-0.1,"dec_deg":0}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":90.0001}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":10}', "INVALID_COORDINATES"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":0,"fov_arcmin":1.99}', "INVALID_FIELD_OF_VIEW"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":0,"fov_arcmin":10.01}', "INVALID_FIELD_OF_VIEW"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":0,"fov_arcmin":NaN}', "INVALID_FIELD_OF_VIEW"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":0,"limit":0}', "INVALID_LIMIT"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":0,"limit":49}', "INVALID_LIMIT"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":0,"limit":2.5}', "INVALID_LIMIT"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":0,"collection_ids":["https://evil"]}', "INVALID_COLLECTION"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":0,"collection_ids":[]}', "INVALID_COLLECTION"),
    (b'{"schema_version":2,"ra_deg":10,"dec_deg":0}', "UNSUPPORTED_SCHEMA_VERSION"),
    (b'{"schema_version":1,"ra_deg":10,"dec_deg":0,"url":"x"}', "INVALID_REQUEST"),
    (b'{"schema_version":1,', "INVALID_REQUEST"),
    (b'[]', "INVALID_REQUEST"),
    (b'', "INVALID_REQUEST"),
])
def test_search_validation(client, archive, raw, code):
    r = client.post("/api/v1/search", content=raw, headers={"content-type": "application/json"})
    status = 400 if code == "INVALID_REQUEST" else 422
    err(r, status, code)
    assert archive.calls == []  # nothing reached the archive


def test_frame_token_shape_errors(client, archive):
    err(client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": 5}), 400, "INVALID_FRAME_TOKEN")
    err(client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": ""}), 400, "INVALID_FRAME_TOKEN")
    err(client.post("/api/v1/frame", json={"schema_version": 1, "frame_token": "pb1.aaaa.bbbb"}), 400,
        "INVALID_FRAME_TOKEN")
    assert archive.calls == []


def test_unknown_api_paths_are_json(client):
    err(client.get("/api/v1/does-not-exist"), 404, "NOT_FOUND")
    err(client.get("/api/whatever"), 404, "NOT_FOUND")
    err(client.post("/api/v1/health"), 405, "METHOD_NOT_ALLOWED")
    err(client.get("/api/v1/search"), 405, "METHOD_NOT_ALLOWED")


def test_oversized_body_is_413_json(client, archive):
    r = client.post("/api/v1/search", content=b"{" + b" " * 20000 + b"}",
                    headers={"content-type": "application/json"})
    err(r, 413, "INVALID_REQUEST")
    assert archive.calls == []


def test_request_id_echo_only_when_plain(client):
    r = client.get("/api/v1/health", headers={"x-request-id": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123" and r.json()["request_id"] == "abc-123"
    r = client.get("/api/v1/health", headers={"x-request-id": "<script>"})
    assert r.headers["x-request-id"] != "<script>"


def test_health_reports_no_secret(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    text = r.text
    assert "perigee-dev-only" not in text
    caps = r.json()["capabilities"]
    assert caps["candidate"] == "b" and caps["frame_tokens"] == "env"


def test_missing_secret_blocks_search_before_upstream(client, archive):
    import dataclasses

    client.holder["settings"] = dataclasses.replace(client.holder["settings"], token_secret=None,
                                                    token_secret_source="missing")
    err(client.post("/api/v1/search", json=OK), 503, "SERVICE_MISCONFIGURED")
    assert archive.calls == []
    assert client.get("/api/v1/health").json()["status"] == "degraded"


def test_rate_limited(client, archive):
    import dataclasses

    from .conftest import sia_row, votable

    archive.on("spherex_dr1", lambda r: __import__("httpx").Response(
        200, content=votable([sia_row("2026W18_1A_0516_1", 3, 61159.5)]),
        headers={"content-type": "application/x-votable+xml"}))
    archive.on("spherex_qr3", archive.handlers["spherex_dr1"])
    client.holder["settings"] = dataclasses.replace(client.holder["settings"], search_per_minute=2)
    assert client.post("/api/v1/search", json=OK).status_code == 200
    assert client.post("/api/v1/search", json=OK).status_code == 200
    r = client.post("/api/v1/search", json=OK)
    body = err(r, 429, "RATE_LIMITED")
    assert body["error"]["retryable"] is True and int(r.headers["retry-after"]) >= 1


@pytest.mark.parametrize("name", sorted(p.name for p in EXAMPLES.glob("*.json")))
def test_candidate_a_examples_validate_against_shared_models(name):
    """The shared interface: A's example payloads must parse with the models B serves."""
    data = json.loads((EXAMPLES / name).read_text())
    if name.startswith("error."):
        ErrorEnvelope.model_validate(data)
    elif name.startswith("search_response"):
        SearchResponse.model_validate(data)
    elif name.startswith("frame_response"):
        FrameResponse.model_validate(data)
