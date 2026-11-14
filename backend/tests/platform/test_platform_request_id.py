"""Catalog error envelopes echo the X-Request-ID header (review finding R7)."""

from fastapi.testclient import TestClient

from backend.main import app


def test_catalog_404_request_id_matches_header():
    client = TestClient(app)
    for path in ("/api/v1/cases/nope", "/api/v1/presets/nope/frames", "/api/v1/assets/nope"):
        r = client.get(path)
        assert r.status_code == 404
        assert r.json()["request_id"] == r.headers["x-request-id"], path


def test_catalog_echoes_client_supplied_request_id():
    r = TestClient(app).get("/api/v1/cases/nope", headers={"X-Request-ID": "judge-check-1"})
    assert r.json()["request_id"] == "judge-check-1"
