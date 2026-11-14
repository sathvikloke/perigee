"""Protocol-test harness. No network: archive search, upstream fetch and the processor
are all replaced by labeled fixtures (see fixtures.py)."""

from __future__ import annotations

import warnings
from dataclasses import replace
from typing import Callable

import httpx
import pytest

warnings.filterwarnings("ignore", category=DeprecationWarning)

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from backend.routes._adapters import Services, resolve_services  # noqa: E402
from backend.security.config import Settings  # noqa: E402

from .fixtures import FakeSearch, fixture_fits_bytes, fixture_processor  # noqa: E402

TEST_SECRET = b"test-secret-for-protocol-tests-only-0123456789"


def make_settings(**overrides) -> Settings:
    base = Settings(
        token_secret=TEST_SECRET,
        token_secret_source="env",
        token_ttl_s=3600,
        upstream_connect_timeout_s=1.0,
        upstream_read_timeout_s=1.0,
        search_budget_s=5.0,
        frame_fetch_max_bytes=64 * 1024,
        frame_budget_s=5.0,
        is_production=False,
    )
    return replace(base, **overrides)


class Harness:
    def __init__(self):
        self.settings = make_settings()
        self.search = FakeSearch({})
        self.processor: Callable | None = fixture_processor
        self.fetch_handler: Callable[[httpx.Request], httpx.Response] = lambda req: httpx.Response(
            200, content=fixture_fits_bytes(), headers={"content-type": "application/fits"}
        )
        self.fetched: list[str] = []

    def services(self) -> Services:
        def handler(request: httpx.Request) -> httpx.Response:
            self.fetched.append(str(request.url))
            return self.fetch_handler(request)

        return Services(
            settings=self.settings,
            search_collection=self.search,
            processor=self.processor,
            processor_source="tests.fixture_processor" if self.processor else None,
            search_source="tests.FakeSearch",
            http_client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )


@pytest.fixture
def harness():
    h = Harness()
    app.dependency_overrides[resolve_services] = h.services
    yield h
    app.dependency_overrides.pop(resolve_services, None)


@pytest.fixture
def client(harness):
    return TestClient(app, raise_server_exceptions=False)
