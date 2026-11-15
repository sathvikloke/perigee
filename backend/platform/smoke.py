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
send it as `x-vercel-protection-bypass`, only on requests to the --base
origin (never to another host, e.g. an absolute asset URL). The value is never printed. A bypassed
run proves the app works; it does NOT prove judge access, so --bypass skips the
access check and the summary says so.

Live checks cost one archive search (limit 2) and one cutout per run. An empty
search result is a FAIL (the live frame path was not exercised), and the frame's
image must decode as a PNG. Network errors and malformed JSON are reported as
FAIL rows with exit 1, never a traceback.

--base must be an https origin (http only for loopback). The unrelated
perigee.vercel.app is refused in every spelling (case, trailing dot, port).
"""

from __future__ import annotations

import argparse
import base64
import binascii
import io
import ipaddress
import json
from pathlib import Path
import os
import sys
import time
from typing import Any
from urllib.parse import urlsplit

import httpx

PRESET_IDS = ["barnards_star", "epsilon_indi_b", "wise_0855", "rw_aurigae", "r_draconis"]
# Orion Nebula: far from all five presets and inside SPHEREx all-sky coverage.
NON_PRESET_QUERY = {"schema_version": 1, "ra_deg": 83.822, "dec_deg": -5.391, "fov_arcmin": 6, "limit": 2}
DEEP_LINKS = ["/?preset=barnards_star", "/?view=query&ra=83.822&dec=-5.391&fov=6", "/smoke/unknown/client/path"]
SSO_HOSTS = ("vercel.com",)
UNRELATED_HOST = "perigee.vercel.app"  # an unrelated third-party app: never ours
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LOCAL_HOSTS = ("localhost",)


class BaseURLError(ValueError):
    """The --base value is not a usable deployment origin."""


def normalize_host(host: str) -> str:
    return host.strip().lower().rstrip(".")


def _is_local(host: str) -> bool:
    if host in LOCAL_HOSTS or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_base(raw: str) -> str:
    """Return the deployment origin (scheme://host[:port]) or raise BaseURLError.

    Accepts https origins, and http only for loopback (local uvicorn). Refuses
    credentials, paths, queries and fragments, and the unrelated
    perigee.vercel.app in any case, with a trailing dot or with a port.
    """
    try:
        parts = urlsplit(raw.strip())
        port = parts.port  # raises ValueError on a malformed port
    except ValueError as exc:
        raise BaseURLError(f"not a valid URL: {exc}") from None
    host = normalize_host(parts.hostname or "")
    if not host:
        raise BaseURLError("no host; pass an origin such as https://<deployment-host>")
    if host == UNRELATED_HOST:
        raise BaseURLError("perigee.vercel.app belongs to an unrelated app; use the project's own deployment URL")
    if parts.scheme not in ("https", "http"):
        raise BaseURLError(f"scheme must be https (got {parts.scheme or 'none'!r})")
    if parts.scheme == "http" and not _is_local(host):
        raise BaseURLError("plain http is only allowed for localhost / loopback; use https")
    if parts.username or parts.password:
        raise BaseURLError("credentials in the URL are not allowed")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise BaseURLError("pass the origin only (no path, query or fragment)")
    netloc = host if ":" not in host else f"[{host}]"
    if port is not None:
        netloc += f":{port}"
    return f"{parts.scheme}://{netloc}"


def same_origin(url: str, base: str) -> bool:
    """True when ``url`` is on the deployment origin ``base`` (scheme, host, port)."""
    try:
        u, b = urlsplit(url), urlsplit(base)
        u_port, b_port = u.port, b.port
    except ValueError:
        return False
    default = {"https": 443, "http": 80}
    return (
        u.scheme == b.scheme
        and normalize_host(u.hostname or "") == normalize_host(b.hostname or "")
        and (u_port or default.get(u.scheme)) == (b_port or default.get(b.scheme))
    )


class Session:
    """HTTP calls to one deployment. The bypass header is attached per request
    and only to URLs on the deployment origin, never to another host; network
    errors become a FAIL row instead of a crash."""

    def __init__(self, client: httpx.Client, base: str, bypass_secret: str | None = None) -> None:
        self.client, self.base, self._bypass = client, base, bypass_secret

    def url(self, path_or_url: str) -> str:
        return self.base + path_or_url if path_or_url.startswith("/") else path_or_url

    def request(self, res: "Results", name: str, method: str, path_or_url: str, **kw: Any) -> httpx.Response | None:
        url = self.url(path_or_url)
        headers = dict(kw.pop("headers", {}) or {})
        if self._bypass and same_origin(url, self.base):
            headers["x-vercel-protection-bypass"] = self._bypass
        try:
            return self.client.request(method, url, headers=headers, **kw)
        except httpx.HTTPError as exc:
            res.add(name, False, f"network error: {type(exc).__name__}: {str(exc)[:160] or 'no detail'}")
            return None


def json_body(res: "Results", name: str, r: httpx.Response) -> dict | None:
    """Parsed JSON object, or None after recording a FAIL (never raises)."""
    try:
        body = r.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        res.add(name, False, f"{r.status_code} {ctype(r)}: body is not valid JSON ({len(r.content)} B)")
        return None
    if not isinstance(body, dict):
        res.add(name, False, f"{r.status_code}: JSON is {type(body).__name__}, expected an object")
        return None
    return body


def png_problem(data: bytes) -> str | None:
    """None when ``data`` decodes as a real PNG with a positive size, else why not."""
    if data[:8] != PNG_SIGNATURE:
        return "missing PNG signature"
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as im:
            im.load()
            if im.format != "PNG" or im.width < 1 or im.height < 1:
                return f"decoded as {im.format} {im.width}x{im.height}"
    except Exception as exc:  # noqa: BLE001 - any decoder failure is a defect here
        return f"PNG does not decode: {type(exc).__name__}"
    return None


def data_url_png(src: Any) -> tuple[bytes | None, str]:
    """Decode a ``data:image/png;base64,...`` URL. Returns (bytes, '') or (None, why)."""
    if not isinstance(src, str) or not src.startswith("data:image/png;base64,"):
        return None, "image.src is not a base64 PNG data URL"
    try:
        return base64.b64decode(src.split(",", 1)[1], validate=True), ""
    except (binascii.Error, ValueError):
        return None, "image.src base64 does not decode"


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


def check_access(res: Results, s: Session) -> bool | None:
    """True public, False protected, None when the host could not be reached."""
    blocked = []
    for path in ("/", "/api/v1/health"):
        r = s.request(res, f"access {path}", "GET", path)
        if r is None:
            return None
        if is_protection_redirect(r):
            blocked.append(f"{path} -> {r.status_code} {urlsplit(r.headers.get('location', '')).hostname}")
    return res.add("access (logged-out visitor)", not blocked,
                   "no Vercel login redirect" if not blocked else "Vercel Authentication: " + "; ".join(blocked))


def check_frontend(res: Results, s: Session) -> None:
    for path in ["/"] + DEEP_LINKS:
        name = f"frontend {path}"
        r = s.request(res, name, "GET", path)
        if r is None:
            continue
        html = r.text[:4000].lower()
        ok = r.status_code == 200 and ctype(r) == "text/html" and "<div id=\"root\"" in html
        res.add(name, ok, f"{r.status_code} {ctype(r)} root={'yes' if 'id=\"root\"' in html else 'no'}")


def check_health(res: Results, s: Session) -> None:
    r = s.request(res, "health is JSON", "GET", "/api/v1/health")
    if r is None or not res.add("health is JSON", r.status_code == 200 and is_json(r), f"{r.status_code} {ctype(r)}"):
        return
    body = json_body(res, "health body", r)
    if body is None:
        return
    caps = body.get("capabilities") if isinstance(body.get("capabilities"), dict) else {}
    signing = caps.get("token_signing")
    res.add("health token signing from env secret", signing == "env",
            f"token_signing={signing} (expect 'env'; 'missing'/'too_short' means PERIGEE_TOKEN_SECRET "
            f"is not set for this environment; 'dev_secret_refused'/'dev_mode_refused' mean the public dev "
            f"secret or PERIGEE_DEV_MODE reached a hosted deployment)")
    res.add("health status ok", body.get("status") == "ok",
            f"status={body.get('status')} api_version={body.get('api_version')} "
            f"processor={caps.get('frame_processor')}")


def check_catalog(res: Results, s: Session) -> None:
    r = s.request(res, "presets is JSON", "GET", "/api/v1/presets")
    if r is None or not res.add("presets is JSON", r.status_code == 200 and is_json(r), f"{r.status_code} {ctype(r)}"):
        return
    body = json_body(res, "presets body", r)
    if body is None:
        return
    presets = body.get("presets") if isinstance(body.get("presets"), list) else []
    ids = [p.get("id") for p in presets if isinstance(p, dict)]
    res.add("five presets", sorted(map(str, ids)) == sorted(PRESET_IDS), f"{ids}")
    r = s.request(res, "barnards_star frames is JSON", "GET", "/api/v1/presets/barnards_star/frames")
    if r is None or not res.add("barnards_star frames is JSON", r.status_code == 200 and is_json(r),
                                f"{r.status_code} {ctype(r)}"):
        return
    body = json_body(res, "barnards_star frames body", r)
    if body is None:
        return
    frames = body.get("frames") if isinstance(body.get("frames"), list) else []
    srcs = [(f.get("image") or {}).get("src") for f in frames if isinstance(f, dict) and isinstance(f.get("image"), dict)]
    srcs = [x for x in srcs if isinstance(x, str) and x]
    res.add("barnards_star frames listed", bool(srcs), f"{len(frames)} frames, {len(srcs)} with image src")
    if srcs:
        src = srcs[0]
        if not src.startswith("/") and not same_origin(src, s.base):
            # Assets must come from this deployment; never fetch (or send the bypass header) elsewhere.
            res.add("preset image asset is PNG", False, f"{src[:120]} is not on the deployment origin; not fetched")
        else:
            a = s.request(res, "preset image asset is PNG", "GET", src)
            if a is not None:
                why = png_problem(a.content) if a.status_code == 200 and ctype(a) == "image/png" else "not a 200 image/png"
                res.add("preset image asset is PNG", why is None,
                        f"{src} -> {a.status_code} {ctype(a)} {len(a.content)} B cache={a.headers.get('cache-control')}"
                        + (f" ({why})" if why else ""))
    r = s.request(res, "case fair_comparison is JSON", "GET", "/api/v1/cases/fair_comparison")
    if r is not None and res.add("case fair_comparison is JSON", r.status_code == 200 and is_json(r),
                                 f"{r.status_code} {ctype(r)}"):
        body = json_body(res, "case body", r)
        if body is not None:
            res.add("case fair_comparison content", body.get("case_id") == "fair_comparison"
                    and isinstance(body.get("limitations"), list) and len(body["limitations"]) > 0,
                    f"case_id={body.get('case_id')} limitations={len(body.get('limitations') or [])}")


def check_routing(res: Results, s: Session) -> None:
    for path in ("/api/v1/__smoke_unknown__", "/api/__smoke_unknown__", "/api/v1/assets/..%2F..%2Fmain.py"):
        name = f"JSON 404 {path}"
        r = s.request(res, name, "GET", path)
        if r is None:
            continue
        res.add(name, r.status_code == 404 and is_json(r),
                f"{r.status_code} {ctype(r)}" + (" <- SPA HTML swallowed an API route" if ctype(r) == "text/html" else ""))


def check_live(res: Results, s: Session) -> None:
    """A non-preset search must return at least one observation, and one frame
    from it must process into a decodable PNG. An empty result is a FAIL: the
    live path was not exercised."""
    name = "live non-preset /search"
    t = time.monotonic()
    r = s.request(res, name, "POST", "/api/v1/search", json=NON_PRESET_QUERY, timeout=60)
    if r is None:
        return
    dt = time.monotonic() - t
    if not is_json(r):
        res.add(name, False, f"{r.status_code} {ctype(r)} (expected application/json) {dt:.1f}s")
        return
    body = json_body(res, name, r)
    if body is None:
        return
    q = body.get("query") if isinstance(body.get("query"), dict) else {}
    obs = body.get("observations") if isinstance(body.get("observations"), list) else []
    usable = [o for o in obs if isinstance(o, dict) and isinstance(o.get("frame_token"), str) and o.get("frame_token")
              and isinstance(o.get("observation_id"), str) and o.get("observation_id")]
    err = (body.get("error") or {}).get("code") if isinstance(body.get("error"), dict) else None
    ok = (r.status_code == 200 and body.get("status") in ("ready", "partial")
          and q.get("ra_deg") == NON_PRESET_QUERY["ra_deg"] and q.get("dec_deg") == NON_PRESET_QUERY["dec_deg"]
          and bool(usable))
    res.add(name, ok,
            f"{r.status_code} status={body.get('status')} total={body.get('total_matches')} "
            f"observations={len(obs)} usable={len(usable)} collections={body.get('collections_queried')} "
            f"query={q.get('ra_deg')},{q.get('dec_deg')} {dt:.1f}s"
            + (f" error={err}" if err else "")
            + ("" if usable or r.status_code != 200 else " <- no observation with a frame token; live frame NOT checked"))
    if not usable:
        res.add("live /frame", False, "not attempted: the search returned no usable observation")
        return
    first = usable[0]
    name = "live /frame"
    t = time.monotonic()
    f = s.request(res, name, "POST", "/api/v1/frame",
                  json={"schema_version": 1, "frame_token": first["frame_token"]}, timeout=90)
    if f is None:
        return
    dt = time.monotonic() - t
    if not is_json(f):
        res.add(name, False, f"{f.status_code} {ctype(f)} (expected application/json) {dt:.1f}s")
        return
    fb = json_body(res, name, f)
    if fb is None:
        return
    fr = fb.get("frame") if isinstance(fb.get("frame"), dict) else {}
    img = fr.get("image") if isinstance(fr.get("image"), dict) else {}
    png, why = data_url_png(img.get("src"))
    if png is not None:
        why = png_problem(png) or ""
    ok = (f.status_code == 200 and fr.get("observation_id") == first["observation_id"]
          and isinstance(fr.get("frame_key"), str) and isinstance(fr.get("quality"), dict) and not why)
    err = (fb.get("error") or {}).get("code") if isinstance(fb.get("error"), dict) else None
    res.add(name, ok,
            f"{f.status_code} {fr.get('observation_id') or err} "
            f"quality={(fr.get('quality') or {}).get('status') if isinstance(fr.get('quality'), dict) else None} "
            f"lambda={fr.get('wavelength_um')} {dt:.1f}s {len(f.content) // 1024} KB"
            + (f" ({why})" if why else f" png={len(png or b'')} B"))


IDENTITY_PATH = "/perigee-build.json"  # written by cloudflare/build.py (static release identity)
WORKER_HEADER = "x-perigee-worker"  # set by the Cloudflare Worker on /api responses


def load_expected_identity(path: str) -> dict:
    """Expected static identity from a build's build-info.json (key "identity") or perigee-build.json."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    ident = doc.get("identity", doc) if isinstance(doc, dict) else None
    if not isinstance(ident, dict) or not isinstance(ident.get("release_digest"), str):
        raise ValueError(f"{path} has no release_digest")
    return ident


def fetch_identity(res: Results, s: Session) -> dict | None:
    r = s.request(res, "static build identity", "GET", IDENTITY_PATH)
    if r is None:
        return None
    if r.status_code != 200 or not is_json(r):
        res.add("static build identity", False, f"{IDENTITY_PATH} -> {r.status_code} {ctype(r)} (no identity published)")
        return None
    return json_body(res, "static build identity", r)


def _sha(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def check_static_identity(res: Results, s: Session, expected: dict | None, expected_digest: str | None) -> dict | None:
    """Compare the deployed static release with the build that was meant to be deployed.

    Checks the published identity document AND the served bytes it describes (index.html,
    entry scripts, the deck PDF with its MIME type), so a stale or partial upload fails.
    """
    live = fetch_identity(res, s)
    want_digest = expected_digest or (expected or {}).get("release_digest")
    if live is None:
        return None
    if want_digest:
        res.add("static release digest matches expected", live.get("release_digest") == want_digest,
                f"live {str(live.get('release_digest'))[:16]} vs expected {want_digest[:16]}; "
                f"live source label {(live.get('source') or {}).get('label')}")
    if expected:
        for part in ("frontend", "catalog", "worker"):
            a, b = (live.get(part) or {}).get("digest"), (expected.get(part) or {}).get("digest")
            res.add(f"static {part} digest matches expected", a == b, f"live {str(a)[:16]} vs expected {str(b)[:16]}")
        # The build that was meant to be deployed, not merely identical content.
        a, b = (live.get("source") or {}).get("label"), (expected.get("source") or {}).get("label")
        res.add("source label matches expected build", a == b, f"live {a} vs expected {b}")
    # The Worker code actually answering /api must be the one this identity describes
    # (Wrangler deploys the Worker and the static files together, but a stale build
    # directory or a separate Worker upload would otherwise go unnoticed).
    r = s.request(res, "deployed Worker matches identity", "GET", "/api/v1/presets")
    if r is not None:
        got = r.headers.get(WORKER_HEADER)
        claimed = (live.get("worker") or {}).get("digest")
        want = (expected.get("worker") or {}).get("digest") if expected else claimed
        res.add("deployed Worker matches identity", bool(got) and got == claimed and got == want,
                f"X-Perigee-Worker {str(got)[:16]}; identity {str(claimed)[:16]}; expected {str(want)[:16]}")
    # The bytes actually served must match the identity being claimed.
    fe = live.get("frontend") or {}
    r = s.request(res, "served index.html matches identity", "GET", "/")
    if r is not None:
        res.add("served index.html matches identity", r.status_code == 200 and _sha(r.content) == fe.get("index_html_sha256"),
                f"{r.status_code} sha {_sha(r.content)[:16]}")
    for rel, digest in sorted((fe.get("entry_scripts") or {}).items()):
        r = s.request(res, f"served {rel} matches identity", "GET", "/" + rel)
        if r is not None:
            res.add(f"served {rel} matches identity", r.status_code == 200 and _sha(r.content) == digest,
                    f"{r.status_code} {len(r.content)} B")
    pdf = live.get("demo_pdf") or {}
    if pdf.get("path"):
        r = s.request(res, "deck PDF type and bytes", "GET", "/" + pdf["path"])
        if r is not None:
            ok = (r.status_code == 200 and ctype(r) == "application/pdf" and r.content[:5] == b"%PDF-"
                  and _sha(r.content) == pdf.get("sha256")
                  and (not expected or pdf.get("sha256") == (expected.get("demo_pdf") or {}).get("sha256")))
            res.add("deck PDF type and bytes", ok, f"{r.status_code} {ctype(r)} {len(r.content)} B sha {_sha(r.content)[:16]}")
    return live


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", required=True, help="deployment origin, e.g. https://perigee-git-...vercel.app")
    ap.add_argument("--bypass", action="store_true", help="send VERCEL_AUTOMATION_BYPASS_SECRET as a bypass header")
    ap.add_argument("--no-live", action="store_true", help="skip the archive search and frame")
    ap.add_argument("--expect-build", metavar="PATH",
                    help="build-info.json (or perigee-build.json) of the build that should be deployed; "
                         "a different static release fails the run")
    ap.add_argument("--expect-release-digest", metavar="SHA256",
                    help="expected static release_digest (alternative to --expect-build)")
    args = ap.parse_args(argv)
    expected = None
    if args.expect_build:
        try:
            expected = load_expected_identity(args.expect_build)
        except (OSError, ValueError) as exc:
            print(f"REFUSED: --expect-build: {exc}")
            return 1
    try:
        base = validate_base(args.base)
    except BaseURLError as exc:
        print(f"REFUSED: {exc}")
        return 1

    secret = None
    if args.bypass:
        secret = os.environ.get("VERCEL_AUTOMATION_BYPASS_SECRET")
        if not secret:
            print("FAIL  --bypass given but VERCEL_AUTOMATION_BYPASS_SECRET is not set")
            return 1

    res = Results()
    print(f"Perigee release smoke: {base}"
          f"{' (protection bypass header sent to this origin only)' if args.bypass else ''}")
    try:
        with httpx.Client(headers={"user-agent": "perigee-release-smoke"}, timeout=30, follow_redirects=False) as c:
            s = Session(c, base, secret)
            if not args.bypass:
                access = check_access(res, s)
                if access is None:
                    print("\nRESULT: FAIL (exit 1). The deployment could not be reached; see the network error above.")
                    return 1
                if not access:
                    print("\nRESULT: ACCESS RESTRICTED (exit 2). Logged-out visitors are sent to Vercel login; "
                          "nothing about the app itself was tested. Owner action: Deployment Protection.")
                    return 2
            check_frontend(res, s)
            identity = None
            if expected or args.expect_release_digest:
                identity = check_static_identity(res, s, expected, args.expect_release_digest)
            else:
                identity = fetch_identity(Results(), s)  # informational only
            health = s.request(Results(), "health (report)", "GET", "/api/v1/health")
            check_health(res, s)
            check_catalog(res, s)
            check_routing(res, s)
            if not args.no_live:
                check_live(res, s)

    except Exception as exc:  # noqa: BLE001 - report, never a traceback, for a release check
        print(f"\nRESULT: FAIL (exit 1). Unexpected error: {type(exc).__name__}: {str(exc)[:200]}")
        return 1

    # Two separately deployed parts, reported separately: never one combined "version".
    print("\nStatic release at this origin (frontend + catalog + deck):")
    if identity:
        src = identity.get("source") or {}
        print(f"  release_digest {identity.get('release_digest')}  source {src.get('label')}  "
              f"content {(identity.get('catalog') or {}).get('content_version')}  "
              f"worker {str((identity.get('worker') or {}).get('digest'))[:16]}")
        if expected or args.expect_release_digest:
            print("  compared with the expected build: see the 'static ...' checks above")
        else:
            print("  not compared (pass --expect-build or --expect-release-digest to require a specific build)")
    else:
        print(f"  no identity document at {IDENTITY_PATH} (origin is not a Cloudflare build, or predates it)")
    print("Live Python API behind /api/v1/health, /search, /frame:")
    try:
        hb = health.json() if health is not None and is_json(health) else {}
    except ValueError:
        hb = {}
    caps = hb.get("capabilities") if isinstance(hb.get("capabilities"), dict) else {}
    print(f"  health status {hb.get('status')}, api_version {hb.get('api_version')}, token_signing {caps.get('token_signing')}; "
          "its deployed commit is not exposed by /health and is not implied by the static release above")

    failed = res.failed()
    if args.bypass:
        note = " Judge access NOT verified (bypass used)."
    elif failed:
        note = " Not redirected to Vercel login, but the app checks above failed."
    else:
        note = " Logged-out access verified."
    if args.no_live:
        note += " Live archive path skipped."
    print(f"\nRESULT: {'PASS' if not failed else 'FAIL'} {len(res.rows) - len(failed)}/{len(res.rows)}.{note}")
    if failed:
        print("Failed: " + "; ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
