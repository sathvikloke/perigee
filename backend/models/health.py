"""GET /api/v1/health response."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .common import SCHEMA_VERSION


class HealthResponse(BaseModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    request_id: str
    service: Literal["perigee-api"] = "perigee-api"
    api_version: str
    status: Literal["ok", "degraded"]
    capabilities: dict[str, bool | str | list[str] | int | float] = Field(
        description="What this deployment can do. Never contains secrets."
    )
    checked_at_utc: str
