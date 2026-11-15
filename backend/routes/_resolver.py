"""Bounded SIMBAD name lookup via the CDS-endorsed Harvard Sesame mirror.

Protocol: https://vizier.idia.ac.za/vizier/doc/sesame.htx
Mirror list: https://cds.unistra.fr/ (verified 2026-11-15).
The URL, resolver and output format are fixed; names are encoded as one value.
"""
from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree

import httpx

from backend.models.common import ErrorCode
from ._errors import ApiError

SESAME_URL = "https://vizier.cfa.harvard.edu/viz-bin/nph-sesame/-oxp/S?"
MAX_RESOLVER_BYTES = 128 * 1024
RESOLVER_TIMEOUT_S = 12.0
TARGETS_PATH = Path(__file__).resolve().parents[1] / "content" / "targets.json"


def _unavailable() -> ApiError:
    return ApiError(ErrorCode.UPSTREAM_UNAVAILABLE,
                    "Object names could not be looked up right now. Try again or enter coordinates.",
                    http_status=503, retryable=True)


def _name_key(value: str) -> str:
    return " ".join(value.casefold().replace("’", "'").removeprefix("name ").split())


def parse_position(data: bytes, requested_name: str) -> dict:
    # ElementTree never fetches external entities. Reject DTDs as well, including
    # internal entity expansion; the input is capped before parsing.
    try:
        text = data.decode("utf-8")
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise _unavailable()
        root = ElementTree.fromstring(text)
    except (UnicodeDecodeError, ElementTree.ParseError):
        raise _unavailable() from None
    if root.tag != "Sesame":
        raise _unavailable()
    resolvers = root.findall("./Target/Resolver")
    if not resolvers:
        info = " ".join(root.itertext()).casefold()
        if "nothing found" not in info and "not found" not in info:
            raise _unavailable()
        raise ApiError(ErrorCode.OBJECT_NOT_FOUND,
                       "That object name was not found. Check its spelling or enter coordinates.",
                       http_status=404)
    for resolver in resolvers:
        if not resolver.get("name", "").startswith("S"):
            continue
        try:
            ra = float(resolver.findtext("jradeg", ""))
            dec = float(resolver.findtext("jdedeg", ""))
        except ValueError:
            continue
        if not (math.isfinite(ra) and math.isfinite(dec) and 0 <= ra < 360 and -90 <= dec <= 90):
            continue
        name = (resolver.findtext("oname") or requested_name).strip()[:160]
        catalog = {"ra_deg": ra, "dec_deg": dec, "epoch_jyear": 2000.0}
        center = {**catalog, "kind": "catalog_position"}
        note = "Catalog position at epoch 2000.0. Moving stars may be elsewhere in recent images."
        # The curated centers were science-checked for the SPHEREx observing era.
        # Use one only when both the identity and live catalog position agree;
        # a name match alone must never silently substitute a different object.
        targets = json.loads(TARGETS_PATH.read_text())["targets"]
        for target in targets:
            names = {_name_key(target["display_name"]), _name_key(target["simbad_name"])}
            cat = target["catalog_position"]
            separation = math.hypot(((ra - cat["ra_deg"] + 180) % 360 - 180) * math.cos(math.radians(dec)), dec - cat["dec_deg"]) * 3600
            if _name_key(name) in names and separation < 1:
                known = target["query_center"]
                center = {k: known[k] for k in ("ra_deg", "dec_deg", "epoch_jyear", "kind")}
                name = target["display_name"]
                note = f"Search centered on the catalog prediction for {known['epoch_jyear']:.1f}, adjusted for the star’s motion. This is a finder position, not a detection."
                break
        return {"name": name, "catalog_position": catalog, "search_center": center,
                "source": "SIMBAD via CDS Sesame", "source_url": SESAME_URL + quote(requested_name, safe=""),
                "position_reference": (resolver.findtext("refPos") or "")[:160] or None,
                "note": note}
    raise _unavailable()


async def resolve_name(client: httpx.AsyncClient, name: str) -> dict:
    try:
        async with asyncio.timeout(RESOLVER_TIMEOUT_S):
            async with client.stream("GET", SESAME_URL + quote(name, safe=""),
                                     headers={"Accept": "text/plain, application/xml", "User-Agent": "Perigee/1 name resolver"},
                                     follow_redirects=False, timeout=httpx.Timeout(RESOLVER_TIMEOUT_S, connect=4.0)) as response:
                if response.status_code != 200:
                    raise _unavailable()
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_RESOLVER_BYTES:
                        raise _unavailable()
        return parse_position(bytes(data), name)
    except (httpx.TimeoutException, TimeoutError):
        raise ApiError(ErrorCode.UPSTREAM_TIMEOUT,
                       "Object lookup took too long. Try again or enter coordinates.",
                       http_status=504, retryable=True) from None
    except httpx.HTTPError:
        raise _unavailable() from None
