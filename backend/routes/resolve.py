"""POST /resolve: a name becomes an explicit, sourced search position."""
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ._adapters import Services, resolve_services
from ._errors import request_id_of
from ._resolver import resolve_name

router = APIRouter()


class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, name: str) -> str:
        if any(ord(c) < 32 or ord(c) == 127 for c in name):
            raise ValueError("Enter one object name.")
        name = " ".join(name.replace("’", "'").split())
        if not name:
            raise ValueError("Enter an object name.")
        return name


@router.post("/resolve")
async def resolve(body: ResolveRequest, request: Request, services: Services = Depends(resolve_services)):
    async with services.http_client_factory() as client:
        result = await resolve_name(client, body.name)
    return JSONResponse({"schema_version": 1, "request_id": request_id_of(request), **result},
                        headers={"Cache-Control": "no-store"})
