"""Probe a LOCAL `wrangler dev` of a fault-injection copy of the Worker whose fixed
origin points at a closed local port (http://127.0.0.1:9), i.e. the live Python API is
down. Checks, in the real workerd runtime, that curated routes and assets are served
byte-exact from the bundle while the live routes answer with the JSON envelope.

Setup (copy only; the repository Worker source is not modified):
    cp -R cloudflare/{src,build,wrangler.jsonc,worker-identity.mjs} $W/cloudflare/
    sed -i '' 's#"https://perigee-liard.vercel.app"#"http://127.0.0.1:9"#' $W/cloudflare/src/app.js
    (drop "account_id"), then in $W/cloudflare:  npx -y wrangler@4.162.0 dev --local --port 8799
Run:
    python qa/overnight-backend/wrangler_dev_origin_down.py http://127.0.0.1:8799
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[2] / "cloudflare" / "build" / "public"


def get(base: str, path: str, method: str = "GET", body: bytes | None = None):
    req = urllib.request.Request(base + path, method=method, data=body, headers={"content-type": "application/json",
                                                                                 "x-request-id": "n6-wrangler"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read(), time.monotonic() - t0
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(), time.monotonic() - t0


def main(base: str) -> None:
    manifest = json.loads((PUBLIC / "api/__perigee/catalog-manifest.json").read_text())
    identity = json.loads((PUBLIC / "perigee-build.json").read_text())
    results = {"live": [], "curated_ok": 0, "curated_total": 0, "worker_headers": set(), "failures": []}
    for method, path, body in [("GET", "/api/v1/health", None),
                               ("POST", "/api/v1/search", b'{"schema_version":1,"ra_deg":1,"dec_deg":2}'),
                               ("POST", "/api/v1/frame", b'{"schema_version":1,"frame_token":"pf1.a.b"}')]:
        status, headers, data, dt = get(base, path, method, body)
        env = json.loads(data)
        results["live"].append({"path": path, "status": status, "code": env["error"]["code"],
                                "request_id": env["request_id"], "seconds": round(dt, 3)})
        results["worker_headers"].add(headers.get("x-perigee-worker") or headers.get("X-Perigee-Worker"))
    routes = [("/api/v1/presets", manifest["presets_document"])]
    routes += [(f"/api/v1/cases/{i}", rel) for i, rel in manifest["cases"].items()]
    for pid, p in manifest["presets"].items():
        routes.append((f"/api/v1/presets/{pid}/frames", p["frames"]))
        routes += [(f"/api/v1/presets/{pid}/frames?case_id={c}", rel) for c, rel in p["cases"].items()]
    assets = list(manifest["assets"].items())
    routes += [(f"/api/v1/assets/{i}", a["path"]) for i, a in assets[:: max(1, len(assets) // 60)]]  # ~60-asset sample
    for path, rel in routes:
        status, headers, data, _ = get(base, path)
        results["curated_total"] += 1
        if status == 200 and hashlib.sha256(data).hexdigest() == hashlib.sha256((PUBLIC / rel).read_bytes()).hexdigest():
            results["curated_ok"] += 1
        else:
            results["failures"].append((path, status))
        results["worker_headers"].add(headers.get("x-perigee-worker") or headers.get("X-Perigee-Worker"))
    status, _h, data, _ = get(base, "/perigee-build.json")
    results["static_build_identity_served"] = status == 200 and json.loads(data)["release_digest"] == identity["release_digest"]
    results["worker_headers"] = sorted(h for h in results["worker_headers"] if h)
    print(json.dumps(results, indent=1))
    assert all(r["status"] == 502 and r["code"] == "UPSTREAM_UNAVAILABLE" for r in results["live"]), results["live"]
    assert results["curated_ok"] == results["curated_total"], results["failures"]
    assert len(results["worker_headers"]) == 1


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8799")
