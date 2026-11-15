"""Local delay/fault proxy for the Perigee API (QA only, stdlib only).

    python qa/loading-recovery/fault_proxy.py --listen 8081 --upstream http://127.0.0.1:8080 \
        --cache /tmp/perigee-fault-cache

Point the frontend at it: PERIGEE_DEV_API=http://127.0.0.1:8081 npx vite ...

* Record/replay: a 200 from POST /search (keyed by request body) or POST /frame
  (keyed by frame_key inside the token) is saved under --cache and replayed
  afterwards, so repeated runs do not touch IRSA. Start the API with a long
  PERIGEE_TOKEN_TTL_S so replayed tokens stay valid.
* --force-limit N rewrites every /search body to limit N, so a reload (which
  uses the default limit) still replays the one recorded search.
* Faults: POST /__faults with a JSON object replaces the active rules; GET
  /__faults shows them. Rules (all optional):
    search_delay_s: float           delay before answering /search
    search_error: {status, code, message, retryable}   answer /search with an envelope
    search_partial: [collection]    rewrite a 200 /search as status=partial, those failed
    frame_delay_s: {"<index>": s}   delay /frame for result index (0-based, latest search)
    frame_fail_once: [index]        first attempt -> 502 UPSTREAM_UNAVAILABLE, later attempts pass
    frame_fail: {"<index>": status} always fail with that status
* Stats: GET /__stats -> max concurrent /frame requests, per-index attempt counts.
  POST /__stats/reset clears them.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOCK = threading.Lock()
FAULTS: dict = {}
STATS = {"frame_inflight": 0, "frame_max_inflight": 0, "frame_attempts": {}, "search_calls": 0, "upstream_calls": 0}
TOKEN_INDEX: dict[str, int] = {}  # frame_key -> index in the latest search response


def frame_key_of(token: str) -> str:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))["d"]["fk"]
    except Exception:
        return hashlib.sha256(token.encode()).hexdigest()[:16]


def envelope(code: str, message: str, retryable: bool) -> bytes:
    return json.dumps(
        {"schema_version": 1, "request_id": "fault-proxy", "error": {"code": code, "message": message, "retryable": retryable}}
    ).encode()


class Handler(BaseHTTPRequestHandler):
    upstream = "http://127.0.0.1:8080"
    cache_dir = Path("/tmp/perigee-fault-cache")
    force_limit = 0

    def log_message(self, fmt, *args):  # quieter
        print("[proxy]", self.command, self.path, fmt % args if args else "", flush=True)

    def _send(self, status: int, body: bytes, ctype: str = "application/json", extra: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _forward(self, body: bytes | None):
        req = urllib.request.Request(self.upstream + self.path, data=body, method=self.command)
        for k in ("Content-Type", "Accept", "X-Request-ID"):
            if self.headers.get(k):
                req.add_header(k, self.headers[k])
        with LOCK:
            STATS["upstream_calls"] += 1
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read(), r.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers.get("Content-Type", "application/json")

    def do_GET(self):
        if self.path == "/__faults":
            return self._send(200, json.dumps(FAULTS).encode())
        if self.path == "/__stats":
            with LOCK:
                return self._send(200, json.dumps(STATS).encode())
        status, data, ctype = self._forward(None)
        self._send(status, data, ctype)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if self.path == "/__faults":
            global FAULTS
            FAULTS = json.loads(body or b"{}")
            return self._send(200, json.dumps(FAULTS).encode())
        if self.path == "/__stats/reset":
            with LOCK:
                STATS.update(frame_inflight=0, frame_max_inflight=0, frame_attempts={}, search_calls=0, upstream_calls=0)
            return self._send(200, b"{}")
        if self.path.endswith("/search"):
            return self._search(body)
        if self.path.endswith("/frame"):
            return self._frame(body)
        status, data, ctype = self._forward(body)
        self._send(status, data, ctype)

    def _cached(self, kind: str, key: str, fetch):
        path = self.cache_dir / kind / (hashlib.sha256(key.encode()).hexdigest()[:24] + ".json")
        if path.exists():
            return 200, path.read_bytes(), "application/json"
        status, data, ctype = fetch()
        if status == 200:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return status, data, ctype

    def _search(self, body: bytes):
        f = FAULTS
        with LOCK:
            STATS["search_calls"] += 1
        if f.get("search_delay_s"):
            time.sleep(float(f["search_delay_s"]))
        if f.get("search_error"):
            e = f["search_error"]
            return self._send(
                int(e.get("status", 504)),
                envelope(e.get("code", "UPSTREAM_TIMEOUT"), e.get("message", "The NASA/IPAC archive did not answer in time."), e.get("retryable", True)),
            )
        if self.force_limit:
            req = json.loads(body or b"{}")
            req["limit"] = self.force_limit
            body = json.dumps(req, separators=(",", ":")).encode()  # same bytes as JSON.stringify
        status, data, ctype = self._cached("search", body.decode(), lambda: self._forward(body))
        if status == 200:
            doc = json.loads(data)
            with LOCK:
                TOKEN_INDEX.clear()
                for i, o in enumerate(doc.get("observations", [])):
                    TOKEN_INDEX[o.get("frame_key") or frame_key_of(o["frame_token"])] = i
            if f.get("search_partial"):
                failed = list(f["search_partial"])
                doc["status"] = "partial"
                doc["collections_failed"] = failed
                doc["total_matches"] = None
                if f.get("search_partial_empty"):
                    doc["observations"] = []
                    doc["returned_count"] = 0
                doc["warnings"] = [f"Some collections could not be searched ({', '.join(failed)}); results are incomplete."] + doc.get("warnings", [])
                data = json.dumps(doc).encode()
        self._send(status, data, ctype)

    def _frame(self, body: bytes):
        token = json.loads(body or b"{}").get("frame_token", "")
        fk = frame_key_of(token)
        idx = TOKEN_INDEX.get(fk, -1)
        f = FAULTS
        with LOCK:
            STATS["frame_inflight"] += 1
            STATS["frame_max_inflight"] = max(STATS["frame_max_inflight"], STATS["frame_inflight"])
            attempts = STATS["frame_attempts"].get(str(idx), 0) + 1
            STATS["frame_attempts"][str(idx)] = attempts
        try:
            delay = (f.get("frame_delay_s") or {}).get(str(idx))
            if delay:
                time.sleep(float(delay))
            fail = (f.get("frame_fail") or {}).get(str(idx))
            if fail:
                return self._send(int(fail), envelope("UPSTREAM_UNAVAILABLE", "The NASA/IPAC archive could not provide this image right now.", True))
            if idx in (f.get("frame_fail_once") or []) and attempts == 1:
                time.sleep(0.3)
                return self._send(502, envelope("UPSTREAM_UNAVAILABLE", "The NASA/IPAC archive could not provide this image right now.", True))
            status, data, ctype = self._cached("frame", fk, lambda: self._forward(body))
            self._send(status, data, ctype)
        finally:
            with LOCK:
                STATS["frame_inflight"] -= 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", type=int, default=8081)
    ap.add_argument("--upstream", default="http://127.0.0.1:8080")
    ap.add_argument("--cache", default="/tmp/perigee-fault-cache")
    ap.add_argument("--force-limit", type=int, default=0, help="rewrite /search limit (keeps replays on one recorded search)")
    a = ap.parse_args()
    Handler.force_limit = a.force_limit
    Handler.upstream = a.upstream.rstrip("/")
    Handler.cache_dir = Path(a.cache)
    ThreadingHTTPServer.daemon_threads = True
    print(f"fault proxy :{a.listen} -> {Handler.upstream}, cache {a.cache}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.listen), Handler).serve_forever()


if __name__ == "__main__":
    main()
