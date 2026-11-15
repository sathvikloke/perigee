// Worker tests (Node's built-in runner; no dependencies):
//   node --test cloudflare/test/
// Needs cloudflare/build/ (python cloudflare/build.py) and
// cloudflare/build/route-expectations.json (written by pytest cloudflare/tests).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";
import worker from "../src/index.js";

import { handle, resetManifestCache, UPSTREAM_ORIGIN, MAX_REQUEST_BODY_BYTES } from "../src/app.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUILD = path.join(HERE, "..", "build");
const PUBLIC = path.join(BUILD, "public");
const manifest = JSON.parse(readFileSync(path.join(PUBLIC, "api/__perigee/catalog-manifest.json"), "utf8"));

/** Stand-in for the Workers static-assets binding, reading cloudflare/build/public. */
function assetsBinding({ tamper = null, missing = new Set() } = {}) {
  return {
    calls: [],
    async fetch(req) {
      const p = decodeURIComponent(new URL(req.url).pathname);
      this.calls.push(p);
      const file = path.join(PUBLIC, p);
      if (!file.startsWith(PUBLIC) || missing.has(p) || !existsSync(file)) {
        return new Response("<!doctype html><div id=root></div>", { status: 404, headers: { "content-type": "text/html" } });
      }
      let data = readFileSync(file);
      if (tamper && p === tamper) data = Buffer.concat([data, Buffer.from("x")]);
      return new Response(data, { status: 200 });
    },
  };
}

function noFetch() {
  const f = async () => {
    throw new Error("upstream must not be called");
  };
  f.calls = [];
  return f;
}

function recordingFetch(respond) {
  const f = async (url, init) => {
    f.calls.push({ url, init });
    return respond(url, init);
  };
  f.calls = [];
  return f;
}

const jsonResponse = (obj, status = 200, headers = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", ...headers } });

async function run(method, p, { env = { ASSETS: assetsBinding() }, deps = { fetch: noFetch() }, headers = {}, body } = {}) {
  resetManifestCache();
  const init = { method, headers, body };
  if (body instanceof ReadableStream) init.duplex = "half";
  return handle(new Request(`http://localhost:8787${p}`, init), env, deps);
}

// ------------------------------------------------------------------ route parity with FastAPI

test("every recorded FastAPI route answer is reproduced by the Worker", async () => {
  const rows = JSON.parse(readFileSync(path.join(BUILD, "route-expectations.json"), "utf8"));
  assert.ok(rows.length >= 50);
  for (const row of rows) {
    const r = await run(row.method, row.path);
    const ctype = (r.headers.get("content-type") || "").split(";")[0] || null;
    const label = `${row.method} ${row.path}`;
    assert.equal(r.status, row.status, label);
    if (row.status === 307) {
      assert.equal(r.headers.get("location"), row.location, label);
      continue;
    }
    assert.equal(ctype, row.content_type, label);
    assert.notEqual(ctype, "text/html", label);
    if (row.method === "HEAD") continue; // FastAPI sends no body for HEAD
    let code = null;
    if (ctype === "application/json") code = (await r.json()).error?.code ?? null;
    if (row.path.includes("%25")) {
      // httpx (TestClient) decodes %25 before sending; real clients do not. Both are JSON 404s.
      assert.ok(["NOT_FOUND", "ASSET_NOT_FOUND"].includes(code), label);
    } else {
      assert.equal(code, row.error_code, label);
    }
  }
});

test("error envelopes carry details, no-store and an X-Request-ID", async () => {
  const r = await run("GET", "/api/v1/presets/nope/frames", { headers: { "x-request-id": "abc-123" } });
  assert.equal(r.status, 404);
  assert.equal(r.headers.get("cache-control"), "no-store");
  assert.equal(r.headers.get("x-request-id"), "abc-123");
  const b = await r.json();
  assert.equal(b.schema_version, 1);
  assert.equal(b.request_id, "abc-123");
  assert.deepEqual(b.error.details, { available_preset_ids: manifest.preset_ids });
  assert.equal(b.error.retryable, false);

  const c = await run("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id=moving_neighbor");
  assert.deepEqual((await c.json()).error.details, { available_case_ids: ["fair_comparison"] });
  const k = await run("GET", "/api/v1/cases/nope");
  assert.deepEqual((await k.json()).error.details, { available_case_ids: manifest.case_ids });

  const bad = await run("GET", "/api/v1/nope", { headers: { "x-request-id": "<script>" } });
  assert.match(bad.headers.get("x-request-id"), /^[0-9a-f]{32}$/);
});

// ------------------------------------------------------------------ static catalogs and assets

test("catalog documents are served exactly from the export as JSON", async () => {
  const docs = [["/api/v1/presets", manifest.presets_document]];
  for (const [cid, rel] of Object.entries(manifest.cases)) docs.push([`/api/v1/cases/${cid}`, rel]);
  for (const [pid, p] of Object.entries(manifest.presets)) {
    docs.push([`/api/v1/presets/${pid}/frames`, p.frames]);
    for (const [cid, rel] of Object.entries(p.cases)) docs.push([`/api/v1/presets/${pid}/frames?case_id=${cid}`, rel]);
  }
  assert.equal(docs.length, 1 + 2 + 5 + 2);
  for (const [p, rel] of docs) {
    const r = await run("GET", p);
    assert.equal(r.status, 200, p);
    assert.equal(r.headers.get("content-type"), "application/json", p);
    assert.equal(Buffer.from(await r.arrayBuffer()).toString("utf8"), readFileSync(path.join(PUBLIC, rel), "utf8"), p);
  }
});

test("every asset is served with exact bytes, type, ETag and cache policy", async () => {
  const ids = Object.keys(manifest.assets);
  assert.ok(ids.length > 500);
  const env = { ASSETS: assetsBinding() };
  resetManifestCache();
  for (const id of ids) {
    const a = manifest.assets[id];
    const r = await handle(new Request(`http://localhost/api/v1/assets/${encodeURIComponent(id)}`), env, { fetch: noFetch() });
    assert.equal(r.status, 200, id);
    assert.equal(r.headers.get("content-type"), a.media_type, id);
    assert.equal(r.headers.get("etag"), `"${a.sha256}"`, id);
    assert.equal(r.headers.get("x-content-type-options"), "nosniff");
    assert.equal(r.headers.get("cache-control").includes("immutable"), a.canonical, id);
    const data = Buffer.from(await r.arrayBuffer());
    assert.equal(createHash("sha256").update(data).digest("hex"), a.sha256, id);
  }
});

test("a tampered asset file is refused, not served", async () => {
  const [id, a] = Object.entries(manifest.assets).find(([, v]) => v.media_type === "image/png");
  const r = await run("GET", `/api/v1/assets/${id}`, { env: { ASSETS: assetsBinding({ tamper: `/${a.path}` }) } });
  assert.equal(r.status, 404);
  assert.equal((await r.json()).error.code, "ASSET_NOT_FOUND");
});

test("a missing manifest or document is a JSON 503, never HTML", async () => {
  const noManifest = assetsBinding({ missing: new Set(["/api/__perigee/catalog-manifest.json"]) });
  let r = await run("GET", "/api/v1/presets", { env: { ASSETS: noManifest } });
  assert.equal(r.status, 503);
  assert.equal((await r.json()).error.code, "CONTENT_UNAVAILABLE");
  const noDoc = assetsBinding({ missing: new Set([`/${manifest.presets_document}`]) });
  r = await run("GET", "/api/v1/presets", { env: { ASSETS: noDoc } });
  assert.equal(r.status, 503);
  assert.equal(r.headers.get("content-type"), "application/json");
});

test("non-API paths are handed to the static assets binding", async () => {
  const env = { ASSETS: assetsBinding() };
  const r = await run("GET", "/demo/perigee-demo.pdf", { env });
  assert.equal(r.status, 200);
  assert.deepEqual(env.ASSETS.calls, ["/demo/perigee-demo.pdf"]);
});

// ------------------------------------------------------------------ fixed-origin proxy

test("search is proxied only to the fixed origin, with credentials and query dropped", async () => {
  const f = recordingFetch(() => jsonResponse({ status: "ready" }, 200, { "set-cookie": "a=b", "x-request-id": "up-1" }));
  const body = JSON.stringify({ schema_version: 1, ra_deg: 83.822, dec_deg: -5.391 });
  const r = await run("POST", "/api/v1/search?url=https://evil.example/&host=evil.example", {
    deps: { fetch: f },
    body,
    headers: {
      "content-type": "application/json",
      cookie: "session=secret",
      authorization: "Bearer secret",
      "x-vercel-protection-bypass": "secret",
      "x-forwarded-host": "evil.example",
      "cf-connecting-ip": "1.2.3.4",
      "x-request-id": "rid-1",
    },
  });
  assert.equal(r.status, 200);
  assert.equal(f.calls.length, 1);
  const { url, init } = f.calls[0];
  assert.equal(url, `${UPSTREAM_ORIGIN}/api/v1/search`);
  assert.equal(init.method, "POST");
  assert.equal(init.redirect, "manual");
  const sent = Object.fromEntries(init.headers.entries());
  assert.deepEqual(Object.keys(sent).sort(), ["accept", "content-type", "user-agent", "x-request-id"]);
  assert.equal(sent["x-request-id"], "rid-1");
  assert.equal(Buffer.from(init.body).toString("utf8"), body);
  assert.equal(r.headers.get("set-cookie"), null);
  assert.equal(r.headers.get("x-request-id"), "up-1");
});

test("health and frame proxy to their fixed paths; wrong methods never reach upstream", async () => {
  const f = recordingFetch(() => jsonResponse({ status: "ok" }, 200, { "cache-control": "no-store" }));
  let r = await run("GET", "/api/v1/health?x=1", { deps: { fetch: f } });
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("cache-control"), "no-store");
  r = await run("POST", "/api/v1/frame", { deps: { fetch: f }, body: '{"schema_version":1,"frame_token":"t"}', headers: { "content-type": "application/json" } });
  assert.equal(r.status, 200);
  assert.deepEqual(f.calls.map((c) => c.url), [`${UPSTREAM_ORIGIN}/api/v1/health`, `${UPSTREAM_ORIGIN}/api/v1/frame`]);
  for (const [m, p] of [["GET", "/api/v1/search"], ["PUT", "/api/v1/frame"], ["HEAD", "/api/v1/health"], ["OPTIONS", "/api/v1/search"], ["DELETE", "/api/v1/frame"]]) {
    const x = await run(m, p, { deps: { fetch: f } });
    assert.equal(x.status, 405, `${m} ${p}`);
  }
  assert.equal(f.calls.length, 2);
});

test("upstream status codes, Retry-After and error bodies pass through", async () => {
  for (const [status, code, extra] of [[503, "UPSTREAM_UNAVAILABLE", { "retry-after": "30" }], [410, "TOKEN_EXPIRED", {}], [422, "INVALID_COORDINATES", {}], [429, "RATE_LIMITED", { "retry-after": "30" }]]) {
    const f = recordingFetch(() => jsonResponse({ schema_version: 1, request_id: "u", error: { code } }, status, extra));
    const r = await run("POST", "/api/v1/search", { deps: { fetch: f }, body: "{}" });
    assert.equal(r.status, status);
    assert.equal(r.headers.get("retry-after"), extra["retry-after"] ?? null);
    assert.equal((await r.json()).error.code, code);
  }
});

test("redirects are not followed and non-JSON upstream answers become a JSON 502", async () => {
  const redirect = recordingFetch(() => new Response(null, { status: 302, headers: { location: "https://vercel.com/sso-api" } }));
  let r = await run("GET", "/api/v1/health", { deps: { fetch: redirect } });
  assert.equal(r.status, 502);
  assert.equal(r.headers.get("location"), null);
  assert.equal((await r.json()).error.code, "UPSTREAM_UNAVAILABLE");
  const html = recordingFetch(() => new Response("<!doctype html>", { status: 200, headers: { "content-type": "text/html" } }));
  r = await run("GET", "/api/v1/health", { deps: { fetch: html } });
  assert.equal(r.status, 502);
  assert.equal(r.headers.get("content-type"), "application/json");
});

test("transport failures and timeouts return the error envelope", async () => {
  const down = recordingFetch(() => {
    throw new TypeError("network down");
  });
  let r = await run("POST", "/api/v1/frame", { deps: { fetch: down }, body: "{}" });
  assert.equal(r.status, 502);
  let b = await r.json();
  assert.equal(b.error.code, "UPSTREAM_UNAVAILABLE");
  assert.equal(b.error.retryable, true);

  const hang = recordingFetch((url, init) => new Promise((_, reject) => init.signal.addEventListener("abort", () => reject(new Error("aborted")))));
  r = await run("POST", "/api/v1/frame", { deps: { fetch: hang, timeoutMs: 30 }, body: "{}" });
  assert.equal(r.status, 504);
  b = await r.json();
  assert.equal(b.error.code, "UPSTREAM_TIMEOUT");
});

test("request and upstream bodies are bounded", async () => {
  const f = recordingFetch(() => jsonResponse({}));
  const big = "x".repeat(MAX_REQUEST_BODY_BYTES + 1);
  let r = await run("POST", "/api/v1/search", { deps: { fetch: f }, body: big, headers: { "content-length": String(big.length) } });
  assert.equal(r.status, 413);
  // Streamed body without a usable length.
  const stream = new ReadableStream({
    start(c) {
      for (let i = 0; i < 70; i++) c.enqueue(new Uint8Array(1024));
      c.close();
    },
  });
  r = await run("POST", "/api/v1/search", { deps: { fetch: f }, body: stream, headers: {} });
  assert.equal(r.status, 413);
  assert.equal(f.calls.length, 0);

  const huge = recordingFetch(() => new Response(new Uint8Array(9 * 1024 * 1024), { headers: { "content-type": "application/json" } }));
  r = await run("POST", "/api/v1/frame", { deps: { fetch: huge }, body: "{}" });
  assert.equal(r.status, 502);
  assert.equal((await r.json()).error.code, "UPSTREAM_UNAVAILABLE");
});

test("the entry module exports only the default handler", async () => {
  const mod = await import("../src/index.js");
  assert.deepEqual(Object.keys(mod), ["default"]);
  assert.equal(typeof worker.fetch, "function");
});

test("the default fetch is called unbound (Workers rejects fetch with a foreign `this`)", async () => {
  const original = globalThis.fetch;
  let seenThis = "unset";
  globalThis.fetch = function (url) {
    seenThis = this;
    if (this !== undefined && this !== globalThis) throw new TypeError("Illegal invocation");
    return Promise.resolve(jsonResponse({ status: "ok", url }));
  };
  try {
    resetManifestCache();
    const r = await handle(new Request("http://localhost/api/v1/health"), { ASSETS: assetsBinding() });
    assert.equal(r.status, 200);
    assert.ok(seenThis === undefined || seenThis === globalThis);
  } finally {
    globalThis.fetch = original;
  }
});
