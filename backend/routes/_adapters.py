"""The seam between API orchestration and the data/processor package (backend/data).

The API owns HTTP validation, tokens, budgets, the allowlisted fetch and error
mapping. backend/data owns FITS -> image science. The routes only depend on the two
callables below; tests replace them through FastAPI dependency overrides.

Expected from backend/data (worker 05) at integration
-----------------------------------------------------

``process_frame(fits_bytes: bytes, meta: dict) -> dict``  (sync, pure, no network)

``meta`` (built by routes/frames.py, all JSON-serializable)::

    {
      "meta_version": 1,
      "observation_id": str, "detector": int | None, "frame_key": str,
      "collection_id": str, "source_url": str, "cutout_url": str,
      "descriptor_mjd": float | None,          # SIA t_min (exposure start)
      "descriptor_observed_at_utc": str | None,
      "query": {"ra_deg": float, "dec_deg": float, "fov_arcmin": float},
      "grid": {"width": 256, "height": 256, "center_ra_deg": float,
               "center_dec_deg": float, "fov_arcmin": float,
               "orientation": "north_up_east_left"},
      "marker_target": None,                   # live queries have no catalog target
      "wavelength_location": "Query center (RA, Dec) of this live search",
      "retrieved_at_utc": str, "file_sha256": str, "byte_length": int,
    }

Return value::

    {
      "record": {...FrameRecord fields (backend/models/frame.py)...;
                 image/flag_image may omit "src" -- the API fills data URLs},
      "image_png": bytes,              # required, the display-grid PNG
      "flag_png": bytes | None,        # optional flag overlay PNG
    }

Errors: raise an exception whose class name contains "Unsupported" (or which has
``code = "UNSUPPORTED_DATA"``) for unusable/corrupt FITS; anything else is mapped to
PROCESSING_FAILED. Never raise for "position not covered" -- that is
``quality.status = "not_covered"`` in a successful record.

Optional: ``search_collection(*, ra_deg, dec_deg, fov_arcmin, collection_id,
deadline_s) -> list[dict] | CollectionResult`` (sync or async) to replace the built-in
IRSA SIA adapter in routes/_archive.py. Descriptor dict keys are listed there.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

import httpx

from backend.security.config import Settings, load_settings

from ._archive import CollectionResult, irsa_search_collection


class Processor(Protocol):
    def __call__(self, fits_bytes: bytes, meta: dict[str, Any]) -> dict[str, Any]: ...


SearchCollection = Callable[..., Awaitable[CollectionResult]]

# Where to look for the processor at runtime (first hit wins).
PROCESSOR_LOCATIONS: tuple[tuple[str, str], ...] = (
    ("backend.data", "process_frame"),
    ("backend.data.processor", "process_frame"),
    ("backend.data.frames", "process_frame"),
)
SEARCH_LOCATIONS: tuple[tuple[str, str], ...] = (
    ("backend.data", "search_collection"),
    ("backend.data.archive", "search_collection"),
)


@dataclass
class Services:
    settings: Settings
    search_collection: SearchCollection
    processor: Processor | None
    processor_source: str | None
    search_source: str
    http_client_factory: Callable[[], httpx.AsyncClient]


def _find(locations: tuple[tuple[str, str], ...]) -> tuple[Callable | None, str | None]:
    for module_name, attr in locations:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        fn = getattr(module, attr, None)
        if callable(fn):
            return fn, f"{module_name}.{attr}"
    return None, None


def _wrap_external_search(fn: Callable) -> SearchCollection:
    async def _search(client: httpx.AsyncClient, **kwargs: Any) -> CollectionResult:
        if inspect.iscoroutinefunction(fn):
            result = await fn(**kwargs)
        else:
            from starlette.concurrency import run_in_threadpool

            result = await run_in_threadpool(fn, **kwargs)
        if isinstance(result, CollectionResult):
            return result
        return CollectionResult(kwargs["collection_id"], list(result))

    return _search


def default_client_factory(settings: Settings) -> Callable[[], httpx.AsyncClient]:
    def make() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=settings.upstream_connect_timeout_s,
                read=settings.upstream_read_timeout_s,
                write=10.0,
                pool=5.0,
            ),
            follow_redirects=False,
        )

    return make


_cached: Services | None = None


def resolve_services() -> Services:
    """FastAPI dependency. Resolved lazily so env changes in tests are honoured."""
    global _cached
    if _cached is None:
        settings = load_settings()
        processor, processor_source = _find(PROCESSOR_LOCATIONS)
        ext_search, ext_source = _find(SEARCH_LOCATIONS)
        _cached = Services(
            settings=settings,
            search_collection=(
                _wrap_external_search(ext_search) if ext_search else irsa_search_collection
            ),
            processor=processor,
            processor_source=processor_source,
            search_source=ext_source or "backend.routes._archive.irsa_search_collection",
            http_client_factory=default_client_factory(settings),
        )
    return _cached


def reset_services_cache() -> None:
    global _cached
    _cached = None
