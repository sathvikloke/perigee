"""Shared fixtures for candidate B protocol tests (no network: httpx.MockTransport)."""

from __future__ import annotations

import asyncio
import dataclasses
import io
from typing import Callable, Dict, List, Optional

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.security import context
from backend.security.config import DEV_SECRET, Settings, load_settings

SRC_D3 = ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2026W18_1A/l2b-v27-2026-244/3/"
          "level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits")


def make_settings(**kw) -> Settings:
    base = load_settings()
    base = dataclasses.replace(base, token_secret=DEV_SECRET, token_secret_source="env", request_budget_s=10.0)
    return dataclasses.replace(base, **kw)


def votable(rows: List[Dict[str, str]], status: str = "OK") -> bytes:
    names = ["obs_id", "energy_bandpassname", "em_min", "em_max", "access_url", "obs_collection",
             "dataproduct_type", "t_min", "obs_publisher_did"]
    fields = "".join(f'<FIELD name="{n}" datatype="char" arraysize="*"/>' for n in names)
    trs = "".join("<TR>" + "".join(f"<TD>{r.get(n, '')}</TD>" for n in names) + "</TR>" for r in rows)
    return (f'<?xml version="1.0"?><VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">'
            f'<RESOURCE type="results"><INFO name="QUERY_STATUS" value="{status}"/><TABLE>{fields}'
            f'<DATA><TABLEDATA>{trs}</TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>').encode()


def sia_row(obs: str, det: int, t_min: float, collection: str = "spherex_dr1") -> Dict[str, str]:
    rel = "dr1" if collection == "spherex_dr1" else "qr3"
    week = obs.split("_")[0] + "_" + obs.split("_")[1]
    url = (f"https://irsa.ipac.caltech.edu/ibe/data/spherex/{rel}/level2/{week}/l2b-v27-2026-244/{det}/"
           f"level2_{obs}D{det}_spx_l2b-v27-2026-244.fits")
    return {"obs_id": obs, "energy_bandpassname": f"SPHEREx-D{det}", "em_min": "2.2e-06", "em_max": "3.8e-06",
            "access_url": url, "obs_collection": collection, "dataproduct_type": "image", "t_min": str(t_min),
            "obs_publisher_did": f"ivo://irsa.ipac/{collection}?{obs}/D{det}"}


HTML_502 = b"<!DOCTYPE HTML PUBLIC><html><head><title>502 Proxy Error</title></head></html>"


class Archive:
    """Scriptable fake IRSA. ``routes`` maps collection id / 'cutout' to a handler."""

    def __init__(self):
        self.calls: List[str] = []
        self.handlers: Dict[str, Callable[[httpx.Request], object]] = {}

    def on(self, key: str, handler):
        self.handlers[key] = handler

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.calls.append(url)
        key = request.url.params.get("COLLECTION") if request.url.path == "/SIA" else "cutout"
        h = self.handlers.get(key)
        if h is None:
            return httpx.Response(404)
        out = h(request)
        if asyncio.iscoroutine(out):
            out = await out
        return out


@pytest.fixture()
def archive() -> Archive:
    return Archive()


@pytest.fixture()
def settings() -> Settings:
    return make_settings()


@pytest.fixture()
def processor_slot():
    return {"p": None}


@pytest.fixture()
def client(archive, settings, processor_slot):
    holder = {"settings": settings}
    context.reset_state(
        settings_loader=lambda: holder["settings"],
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(archive)),
        processor_loader=lambda: processor_slot["p"],
    )
    from backend.main import app

    c = TestClient(app, raise_server_exceptions=False)
    c.holder = holder  # tests may swap settings
    yield c
    context.reset_state()


def fake_fits() -> bytes:
    return b"SIMPLE  =                    T" + b" " * 2850


def png_bytes() -> bytes:
    from PIL import Image  # pillow is a runtime dependency of the processor

    buf = io.BytesIO()
    Image.new("LA", (4, 4)).save(buf, format="PNG")
    return buf.getvalue()
