// N6 local fault injection for the Cloudflare Worker (no network, no public origin):
//   node --test qa/overnight-backend/worker_origin_failure.test.mjs
// Needs cloudflare/build/ (python cloudflare/build.py), like cloudflare/test/.
//
// For every way the live Python origin can fail, the curated catalog (presets,
// cases, frames, every asset) must still be served byte-exact from the bundle
// without touching the origin, the live routes must answer with the JSON error
// envelope, and every /api answer must keep naming the Worker build. A failed
// overlay asset is a JSON 404, never a substitute image, and no frame record is
// rewritten to look "clear".
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { handle, resetManifestCache, WORKER_HEADER } from "../../cloudflare/src/app.js";
import { WORKER_DIGEST } from "../../cloudflare/build/worker-identity.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC = path.join(HERE, "..", "..", "cloudflare", "build", "public");
const manifest = JSON.parse(readFileSync(path.join(PUBLIC, "api/__perigee/catalog-manifest.json"), "utf8"));
const identity = JSON.parse(readFileSync(path.join(PUBLIC, "perigee-build.json"), "utf8"));
const sha = (b) => createHash("sha256").update(b).digest("hex");

function assetsBinding({ missing = new Set() } = {}) {
  return {
    async fetch(req) {
      const p = decodeURIComponent(new URL(req.url).pathname);
      const file = path.join(PUBLIC, p);
      if (!file.startsWith(PUBLIC) || missing.has(p) || !existsSync(file)) {
        return new Response("<!doctype html><div id=root></div>", { status: 404, headers: { "content-type": "text/html" } });
      }
      return new Response(readFileSync(file), { status: 200 });
    },
  };
}

/** Every curated GET route with the exported file that must come back byte-for-byte. */
function curatedRoutes() {
  const routes = [["/api/v1/presets", manifest.presets_document]];
  for (const [id, rel] of Object.entries(manifest.cases)) routes.push([`/api/v1/cases/${id}`, rel]);
  for (const [id, p] of Object.entries(manifest.presets)) {
    routes.push([`/api/v1/presets/${id}/frames`, p.frames]);
    for (const [c, rel] of Object.entries(p.cases)) routes.push([`/api/v1/presets/${id}/frames?case_id=${c}`, rel]);
  }
  for (const [id, a] of Object.entries(manifest.assets)) routes.push([`/api/v1/assets/${id}`, a.path]);
  return routes;
}

// Ways the single fixed origin can fail.
const FAILURES = {
  network_error: { fetch: async () => { throw new TypeError("fetch failed"); }, status: 502, code: "UPSTREAM_UNAVAILABLE" },
  hangs: { fetch: (url, init) => new Promise((_, rej) => init.signal.addEventListener("abort", () => rej(new Error("aborted")))), timeoutMs: 30, status: 504, code: "UPSTREAM_TIMEOUT" },
  html_500: { fetch: async () => new Response("<html>Internal Server Error</html>", { status: 500, headers: { "content-type": "text/html" } }), status: 502, code: "UPSTREAM_UNAVAILABLE" },
  vercel_platform_error: { fetch: async () => new Response("FUNCTION_INVOCATION_FAILED", { status: 500, headers: { "content-type": "text/plain" } }), status: 502, code: "UPSTREAM_UNAVAILABLE" },
  json_not_json: { fetch: async () => new Response("{not json", { status: 200, headers: { "content-type": "application/json" } }), status: 502, code: "UPSTREAM_UNAVAILABLE" },
  redirect: { fetch: async () => new Response(null, { status: 302, headers: { location: "https://elsewhere.example/" } }), status: 502, code: "UPSTREAM_UNAVAILABLE" },
  oversized: { fetch: async () => new Response(new Uint8Array(9 * 1024 * 1024).fill(32), { status: 200, headers: { "content-type": "application/json" } }), status: 502, code: "UPSTREAM_UNAVAILABLE" },
  origin_envelope_503: { fetch: async () => new Response(JSON.stringify({ schema_version: 1, request_id: "x", error: { code: "SERVICE_MISCONFIGURED", message: "m", retryable: false, details: null } }), { status: 503, headers: { "content-type": "application/json" } }), status: 503, code: "SERVICE_MISCONFIGURED" },
};

for (const [name, f] of Object.entries(FAILURES)) {
  test(`origin ${name}: live routes give an envelope, curated catalog is unaffected`, async () => {
    const calls = [];
    const fetchImpl = (url, init) => {
      calls.push(url);
      return f.fetch(url, init);
    };
    const deps = { fetch: fetchImpl, timeoutMs: f.timeoutMs };
    const env = { ASSETS: assetsBinding() };
    resetManifestCache();
    for (const [method, p, body] of [
      ["GET", "/api/v1/health"],
      ["POST", "/api/v1/search", '{"schema_version":1,"ra_deg":1,"dec_deg":2}'],
      ["POST", "/api/v1/frame", '{"schema_version":1,"frame_token":"pf1.a.b"}'],
    ]) {
      const r = await handle(new Request(`http://localhost:8787${p}`, { method, body, headers: { "x-request-id": `n6-${name}` } }), env, deps);
      assert.equal(r.status, f.status, `${name} ${p}`);
      assert.equal(r.headers.get("content-type").split(";")[0], "application/json");
      const j = await r.json();
      assert.equal(j.error.code, f.code, `${name} ${p}`);
      assert.equal(r.headers.get(WORKER_HEADER), WORKER_DIGEST);
      if (name !== "origin_envelope_503") assert.equal(j.request_id, `n6-${name}`);
    }
    assert.equal(calls.length, 3);
    assert.ok(calls.every((u) => u.startsWith("https://perigee-liard.vercel.app/api/v1/")), "fixed origin only");

    const routes = curatedRoutes();
    for (const [p, rel] of routes) {
      const r = await handle(new Request(`http://localhost:8787${p}`), env, deps);
      assert.equal(r.status, 200, `${name} ${p}`);
      assert.equal(sha(new Uint8Array(await r.arrayBuffer())), sha(readFileSync(path.join(PUBLIC, rel))), p);
      assert.equal(r.headers.get(WORKER_HEADER), WORKER_DIGEST, p);
    }
    assert.equal(calls.length, 3, "curated routes never call the live origin");
  });
}

test("a missing overlay asset is a JSON 404 and the frame record is never rewritten to clear", async () => {
  const overlays = Object.entries(manifest.assets).filter(([id]) => id.endsWith(".flags.png"));
  assert.ok(overlays.length > 100);
  const missing = new Set(overlays.map(([, a]) => `/${a.path}`));
  const env = { ASSETS: assetsBinding({ missing }) };
  resetManifestCache();
  const deps = { fetch: async () => { throw new Error("origin down"); } };
  for (const [id] of overlays.slice(0, 25)) {
    const r = await handle(new Request(`http://localhost:8787/api/v1/assets/${id}`), env, deps);
    assert.equal(r.status, 404);
    assert.equal((await r.json()).error.code, "ASSET_NOT_FOUND");
  }
  // Frames documents are still served verbatim: quality comes from the record, not the asset.
  let clear = 0, flagged = 0, notCovered = 0;
  for (const [pid, p] of Object.entries(manifest.presets)) {
    for (const rel of [p.frames, ...Object.values(p.cases)]) {
      const url = rel === p.frames ? `/api/v1/presets/${pid}/frames` : `/api/v1/presets/${pid}/frames?case_id=${Object.keys(p.cases).find((c) => p.cases[c] === rel)}`;
      const r = await handle(new Request(`http://localhost:8787${url}`), env, deps);
      assert.equal(r.status, 200);
      const text = await r.text();
      assert.equal(sha(Buffer.from(text)), sha(readFileSync(path.join(PUBLIC, rel))));
      for (const fr of JSON.parse(text).frames) {
        const s = fr.quality.status;
        if (s === "clear") clear++;
        if (s === "flagged") flagged++;
        if (s === "not_covered") notCovered++;
        // Data invariant: "clear" is only ever stated with flag evidence (an overlay) behind it.
        if (s === "clear") assert.ok(fr.flag_image && fr.flag_image.src, `${fr.frame_key} clear without overlay`);
      }
    }
  }
  assert.ok(clear > 0 && flagged > 0 && notCovered > 0, JSON.stringify({ clear, flagged, notCovered }));
});

test("build identity is retained: header digest == bundled perigee-build.json worker digest", async () => {
  assert.equal(identity.worker.digest, WORKER_DIGEST);
  assert.match(identity.release_digest, /^[0-9a-f]{64}$/);
  const env = { ASSETS: assetsBinding() };
  resetManifestCache();
  for (const p of ["/api/v1/presets", "/api/v1/nope", "/api/v1/search"]) {
    const r = await handle(new Request(`http://localhost:8787${p}`), env, { fetch: async () => { throw new Error("down"); } });
    assert.equal(r.headers.get(WORKER_HEADER), WORKER_DIGEST, p);
  }
});
