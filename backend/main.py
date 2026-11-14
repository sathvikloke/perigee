"""DEPLOYMENT PLACEHOLDER - replaced by workers 01/03 at integration.

Minimal FastAPI app used only to prove the Vercel Services preview:
routing of /api/* to Python, JSON 404s for unknown API paths, and that
package-style imports (``backend.platform``) resolve in the deployed bundle.
"""

from fastapi import FastAPI

from backend.platform.runtime import runtime_info

app = FastAPI(title="Perigee deployment placeholder", docs_url=None, redoc_url=None)


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "placeholder": True, "runtime": runtime_info()}
