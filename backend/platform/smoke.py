"""Release smoke check against a *deployed* Perigee URL (Suhrit, platform).

Run from the repository root:

    python -m backend.platform.smoke --base https://<deployment-host>
    python -m backend.platform.smoke --base https://<deployment-host> --no-live   # skip IRSA calls

It answers one question: does this exact deployment serve the real frontend and
API to a visitor? Checks, in order:

  access     a logged-out request is not redirected to Vercel Authentication
  frontend   `/` and a direct deep link return the SPA as text/html
  health     /api/v1/health is JSON and token signing comes from the env secret
  catalog    five presets; one preset's frames; its first image asset is a PNG
  routing    an unknown /api path is a JSON 404, never the SPA's index.html
  live       a NON-preset coordinate search reaches IRSA, then one frame is processed

Exit codes keep the two kinds of failure apart:

  0  every check passed
  1  application/config defect (wrong content type, missing asset, bad signing, ...)
  2  ACCESS RESTRICTED: Deployment Protection blocks a logged-out visitor.
     Not a code failure; the project owner decides access.

Protected previews: set VERCEL_AUTOMATION_BYPASS_SECRET (Project Settings >
Deployment Protection > Protection Bypass for Automation) and pass --bypass to
send it as `x-vercel-protection-bypass`. The value is never printed. A bypassed
run proves the app works; it does NOT prove judge access, so --bypass skips the
access check and the summary says so.

Live checks cost one archive search (limit 2) and one cutout per run.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from urllib.parse import urlsplit

import httpx

PRESET_IDS = ["barnards_star", "epsilon_indi_b", "wise_0855", "rw_aurigae", "r_draconis"]
# Orion Nebula: far from all five presets and inside SPHEREx all-sky coverage.
NON_PRESET_QUERY = {"schema_version": 1, "ra_deg": 83.822, "dec_deg": -5.391, "fov_arcmin": 6, "limit": 2}
DEEP_LINKS = ["/?preset=barnards_star", "/?view=query&ra=83.822&dec=-5.391&fov=6", "/smoke/unknown/client/path"]
SSO_HOSTS = ("vercel.com",)


class Results:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, name: str, ok: bool, evidence: str) -> bool:
        self.rows.append((name, "PASS" if ok else "FAIL", evidence))
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {evidence}", flush=True)
        return ok

    def failed(self) -> list[str]:
        return [n for n, s, _ in self.rows if s == "FAIL"]


def ctype(r: httpx.Response) -> str:
    return r.headers.get("content-type", "").split(";")[0].strip()


def is_protection_redirect(r: httpx.Response) -> bool:
    if r.status_code in (301, 302, 303, 307, 308):
        host = urlsplit(r.headers.get("location", "")).hostname or ""
        return host in SSO_HOSTS or host.endswith(".vercel.com")
    return r.status_code == 401 and "vercel" in r.text[:2000].lower()


def is_json(r: httpx.Response) -> bool:
    return ctype(r) == "application/json"


def check_access(res: Results, c: httpx.Client, base: str) -> bool:
    blocked = []
    for path in ("/", "/api/v1/health"):
        r = c.get(base + path)
        if is_protection_redirect(r):
            blocked.append(f"{path} -> {r.status_code} {urlsplit(r.headers.get('location', '')).hostname}")
    return res.add("access (logged-out visitor)", not blocked,
                   "public" if not blocked else "Vercel Authentication: " + "; ".join(blocked))


def check_frontend(res: Results, c: httpx.Client, base: str) -> None:
    for path in ["/"] + DEEP_LINKS:
        r = c.get(base + path)
        html = r.text[:4000].lower()
        ok = r.status_code == 200 and ctype(r) == "text/html" and "<div id=\"root\"" in html
        res.add(f"frontend {path}", ok, f"{r.status_code} {ctype(r)} root={'yes' if 'id=\"root\"' in html else 'no'}")


def check_health(res: Results, c: httpx.Client, base: str) -> None:
    r = c.get(base + "/api/v1/health")
    if not res.add("health is JSON", r.status_code == 200 and is_json(r), f"{r.status_code} {ctype(r)}"):
        return
    body = r.json()
    caps = body.get("capabilities") or {}
    signing = caps.get("token_signing")
    res.add("health token signing from env secret", signing == "env",
            f"token_signing={signing} (expect 'env'; 'missing'/'too_short' means PERIGEE_TOKEN_SECRET "
            f"is not set for this environment, 'dev_fallback' means PERIGEE_DEV_MODE is on)")
    res.add("health status ok", body.get("status") == "ok",
            f"status={body.get('status')} api_version={body.get('api_version')} "
            f"processor={caps.get('frame_processor')}")


def check_catalog(res: Results, c: httpx.Client, base: str) -> None:
    r = c.get(base + "/api/v1/presets")
    if not res.add("presets is JSON", r.status_code == 200 and is_json(r), f"{r.status_code} {ctype(r)}"):
        return
    ids = [p.get("id") for p in r.json().get("presets", [])]
    res.add("five presets", sorted(ids) == sorted(PRESET_IDS), f"{ids}")
    r = c.get(base + "/api/v1/presets/barnards_star/frames")
    if not res.add("barnards_star frames is JSON", r.status_code == 200 and is_json(r), f"{r.status_code} {ctype(r)}"):
        return
    frames = r.json().get("frames") or []
    srcs = [((f.get("image") or {}).get("src")) for f in frames]
    srcs = [s for s in srcs if s]
    res.add("barnards_star frames listed", bool(srcs), f"{len(frames)} frames, {len(srcs)} with image src")
    if not srcs:
        return
    a = c.get(base + srcs[0] if srcs[0].startswith("/") else srcs[0])
    res.add("preset image asset is PNG", a.status_code == 200 and ctype(a) == "image/png" and a.content[:8] == b"\x89PNG\r\n\x1a\n",
            f"{srcs[0]} -> {a.status_code} {ctype(a)} {len(a.content)} B cache={a.headers.get('cache-control')}")
    r = c.get(base + "/api/v1/cases/fair_comparison")
    res.add("case fair_comparison is JSON", r.status_code == 200 and is_json(r), f"{r.status_code} {ctype(r)}")


def check_routing(res: Results, c: httpx.Client, base: str) -> None:
    for path in ("/api/v1/__smoke_unknown__", "/api/__smoke_unknown__", "/api/v1/assets/..%2F..%2Fmain.py"):
        r = c.get(base + path)
        res.add(f"JSON 404 {path}", r.status_code == 404 and is_json(r),
                f"{r.status_code} {ctype(r)}" + (" <- SPA HTML swallowed an API route" if ctype(r) == "text/html" else ""))


def check_live(res: Results, c: httpx.Client, base: str) -> None:
    t = time.monotonic()
    r = c.post(base + "/api/v1/search", json=NON_PRESET_QUERY, timeout=60)
    dt = time.monotonic() - t
    body = r.json() if is_json(r) else {}
    q = body.get("query") or {}
    ok = (r.status_code == 200 and body.get("status") in ("ready", "partial")
          and q.get("ra_deg") == NON_PRESET_QUERY["ra_deg"] and q.get("dec_deg") == NON_PRESET_QUERY["dec_deg"])
    res.add("live non-preset /search", ok,
            f"{r.status_code} {ctype(r)} status={body.get('status')} total={body.get('total_matches')} "
            f"collections={body.get('collections_queried')} query={q.get('ra_deg')},{q.get('dec_deg')} "
            f"{dt:.1f}s{' error=' + str((body.get('error') or {}).get('code')) if body.get('error') else ''}")
    obs = body.get("observations") or []
    if not obs:
        return
    t = time.monotonic()
    f = c.post(base + "/api/v1/frame", json={"schema_version": 1, "frame_token": obs[0]["frame_token"]}, timeout=90)
    dt = time.monotonic() - t
    fb = f.json() if is_json(f) else {}
    fr = fb.get("frame") or {}
    src = (fr.get("image") or {}).get("src", "")
    ok = f.status_code == 200 and fr.get("observation_id") == obs[0]["observation_id"] and src.startswith("data:image/png")
    res.add("live /frame", ok,
            f"{f.status_code} {fr.get('observation_id') or (fb.get('error') or {}).get('code')} "
            f"quality={(fr.get('quality') or {}).get('status')} lambda={fr.get('wavelength_um')} "
            f"{dt:.1f}s {len(f.content) // 1024} KB")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", required=True, help="deployment origin, e.g. https://perigee-git-...vercel.app")
    ap.add_argument("--bypass", action="store_true", help="send VERCEL_AUTOMATION_BYPASS_SECRET as a bypass header")
    ap.add_argument("--no-live", action="store_true", help="skip the archive search and frame")
    args = ap.parse_args(argv)
    base = args.base.rstrip("/")
    if base.endswith("perigee.vercel.app") and "-" not in urlsplit(base).hostname.split(".")[0]:
        print("REFUSED: perigee.vercel.app belongs to an unrelated app; use the project's own deployment URL.")
        return 1

    headers = {"user-agent": "perigee-release-smoke"}
    if args.bypass:
        secret = os.environ.get("VERCEL_AUTOMATION_BYPASS_SECRET")
        if not secret:
            print("FAIL  --bypass given but VERCEL_AUTOMATION_BYPASS_SECRET is not set")
            return 1
        headers["x-vercel-protection-bypass"] = secret

    res = Results()
    print(f"Perigee release smoke: {base}{' (protection bypass header sent)' if args.bypass else ''}")
    with httpx.Client(headers=headers, timeout=30, follow_redirects=False) as c:
        if not args.bypass and not check_access(res, c, base):
            print("\nRESULT: ACCESS RESTRICTED (exit 2). Logged-out visitors are sent to Vercel login; "
                  "nothing about the app itself was tested. Owner action: Deployment Protection.")
            return 2
        check_frontend(res, c, base)
        check_health(res, c, base)
        check_catalog(res, c, base)
        check_routing(res, c, base)
        if not args.no_live:
            check_live(res, c, base)

    failed = res.failed()
    note = " Judge access NOT verified (bypass used)." if args.bypass else " Logged-out access verified."
    if args.no_live:
        note += " Live archive path skipped."
    print(f"\nRESULT: {'PASS' if not failed else 'FAIL'} {len(res.rows) - len(failed)}/{len(res.rows)}.{note}")
    if failed:
        print("Failed: " + "; ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
