"""Runtime/deployment introspection for the health endpoint.

Reports only non-secret facts: Python version, whether the process runs on
Vercel, the Vercel environment name and the deployed commit. It reports
whether PERIGEE_TOKEN_SECRET is set, never its value.
"""

from __future__ import annotations

import os
import platform as _stdlib_platform  # must resolve to the stdlib, not backend/platform


def runtime_info() -> dict:
    return {
        "python": _stdlib_platform.python_version(),
        "on_vercel": os.environ.get("VERCEL") == "1",
        "vercel_env": os.environ.get("VERCEL_ENV"),
        "commit": (os.environ.get("VERCEL_GIT_COMMIT_SHA") or "")[:12] or None,
        "region": os.environ.get("VERCEL_REGION"),
        "token_secret_configured": bool(os.environ.get("PERIGEE_TOKEN_SECRET")),
    }
