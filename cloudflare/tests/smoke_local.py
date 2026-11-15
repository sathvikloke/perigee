"""Live-local smoke against `wrangler dev` (or any deployed Perigee Worker origin).

    (cd cloudflare && npx wrangler@4.162.0 dev --port 8799 --ip 127.0.0.1)
    .venv/bin/python cloudflare/tests/smoke_local.py --base http://127.0.0.1:8799

Checks the Cloudflare-specific surface over real HTTP: the static frontend,
deck PDF and favicon; every catalog document and a sample of assets against
the exported build; FastAPI-parity answers for the recorded route table
(cloudflare/build/route-expectations.json); and that internal build paths are
not reachable. The API proxy and the live archive path are covered by
`python -m backend.platform.smoke --base <same origin>`, run after this.
Exit 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
PUBLIC = REPO / "cloudflare" / "build" / "public"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--cloudflare-edge", action="store_true", help="Check the deployed Cloudflare edge's documented compression and observed NUL rejection")
    args = ap.parse_args(argv)
    base = args.base.rstrip("/")
    manifest = json.loads((PUBLIC / "api/__perigee/catalog-manifest.json").read_text(encoding="utf-8"))
    rows = json.loads((REPO / "cloudflare/build/route-expectations.json").read_text(encoding="utf-8"))
    results = []

    def check(name, ok, evidence=""):
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {evidence}")

    c = httpx.Client(timeout=30, follow_redirects=False, headers={"user-agent": "perigee-cf-smoke"})

    # Static frontend
    for p in ["/", "/?preset=epsilon_indi_b", "/some/client/route"]:
        r = c.get(base + p)
        check(f"SPA {p}", r.status_code == 200 and r.headers.get("content-type", "").startswith("text/html")
              and '<div id="root">' in r.text, f"{r.status_code} {r.headers.get('content-type')}")
    r = c.get(base + "/demo/perigee-demo.pdf")
    want = (PUBLIC / "demo/perigee-demo.pdf").read_bytes()
    check("demo PDF", r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf")
          and r.content == want and r.content[:5] == b"%PDF-", f"{r.status_code} {r.headers.get('content-type')} {len(r.content)} B")
    # B3: the deployed static release identity equals the local build being verified.
    ident_file = PUBLIC / "perigee-build.json"
    if ident_file.is_file():
        want = json.loads(ident_file.read_text(encoding="utf-8"))
        r = c.get(base + "/perigee-build.json")
        got = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        check("static build identity equals local build", r.status_code == 200 and got == want,
              f"{r.status_code} {r.headers.get('content-type')} live {str((got or {}).get('release_digest'))[:16]} "
              f"vs local {want['release_digest'][:16]} ({want['source']['label']})")
        r = c.get(base + "/api/v1/presets")
        got_worker = r.headers.get("x-perigee-worker")
        check("deployed Worker equals local build", got_worker == want["worker"]["digest"],
              f"X-Perigee-Worker {str(got_worker)[:16]} vs local {want['worker']['digest'][:16]}")
    r = c.get(base + "/favicon.svg")
    check("favicon", r.status_code == 200 and "svg" in r.headers.get("content-type", ""), f"{r.status_code} {r.headers.get('content-type')}")
    js = next((PUBLIC / "assets").glob("index-*.js"))
    r = c.get(base + f"/assets/{js.name}")
    check("JS bundle", r.status_code == 200 and r.content == js.read_bytes(), f"{r.status_code} {len(r.content)} B")

    # Catalog documents equal the export
    docs = [("/api/v1/presets", manifest["presets_document"])]
    docs += [(f"/api/v1/cases/{k}", v) for k, v in manifest["cases"].items()]
    for pid, p in manifest["presets"].items():
        docs.append((f"/api/v1/presets/{pid}/frames", p["frames"]))
        docs += [(f"/api/v1/presets/{pid}/frames?case_id={k}", v) for k, v in p["cases"].items()]
    for path, rel in docs:
        r = c.get(base + path)
        ok = r.status_code == 200 and r.headers.get("content-type") == "application/json" and r.json() == json.loads((PUBLIC / rel).read_text(encoding="utf-8"))
        check(f"catalog {path}", ok, f"{r.status_code} {r.headers.get('content-type')}")

    # Assets: one of each kind, plus an alias
    picks = {}
    for aid, a in manifest["assets"].items():
        picks.setdefault((a["media_type"], a["canonical"]), aid)
    for (mt, canonical), aid in sorted(picks.items()):
        a = manifest["assets"][aid]
        r = c.get(base + f"/api/v1/assets/{aid}")
        expected_etag = f'"{a["sha256"]}"'
        etag_ok = r.headers.get("etag") == expected_etag
        if args.cloudflare_edge and r.headers.get("content-encoding") in {"gzip", "br", "zstd"}:
            etag_ok = etag_ok or r.headers.get("etag") == "W/" + expected_etag
        ok = (r.status_code == 200 and r.headers.get("content-type") == mt and hashlib.sha256(r.content).hexdigest() == a["sha256"]
              and etag_ok and ("immutable" in r.headers.get("cache-control", "")) == canonical)
        check(f"asset {mt} canonical={canonical}", ok, f"{r.status_code} {r.headers.get('content-type')} {r.headers.get('cache-control')}")

    # FastAPI parity over real HTTP (HEAD rows skipped: no body to compare)
    mismatches = []
    for row in rows:
        if row["method"] == "HEAD":
            continue
        r = c.request(row["method"], base + row["path"])
        if args.cloudflare_edge and row["path"] == "/api/v1/assets/x%00.png":
            # Cloudflare rejects NUL before invoking the Worker. Do not exempt
            # any other malformed path or weaken application-route parity.
            check("edge rejects encoded NUL before Worker", r.status_code == 400
                  and r.headers.get("server") == "cloudflare"
                  and not r.headers.get("x-request-id"), f"{r.status_code} {r.headers.get('content-type')}")
            continue
        ctype = (r.headers.get("content-type") or "").split(";")[0] or None
        code = r.json().get("error", {}).get("code") if ctype == "application/json" and r.status_code >= 400 else None
        ok = r.status_code == row["status"] and (row["status"] == 307 or ctype == row["content_type"])
        if row["status"] == 307:
            ok = ok and r.headers.get("location") == row["location"]
        elif "%25" not in row["path"] and row["error_code"] is not None:
            ok = ok and code == row["error_code"]
        if not ok:
            mismatches.append(f"{row['method']} {row['path']} -> {r.status_code} {ctype} {code}")
    check(f"route parity ({len(rows)} recorded FastAPI answers)", not mismatches, "; ".join(mismatches[:5]) or "all match")

    # Internal build paths are not reachable from outside
    for p in ["/api/__perigee/catalog-manifest.json", "/api/v1/presets.json", "/api/v1/presets/epsilon_indi_b/frames.json"]:
        r = c.get(base + p)
        check(f"internal path hidden {p}", r.status_code == 404 and r.headers.get("content-type") == "application/json", f"{r.status_code} {r.headers.get('content-type')}")

    failed = results.count(False)
    print(f"\nRESULT: {'PASS' if not failed else 'FAIL'} {len(results) - failed}/{len(results)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
