// Perigee on Cloudflare Workers (static assets + a small API router): the logic.
// src/index.js is the Worker entry and must export only the default handler
// (the runtime treats every named export of the main module as an entrypoint).
//
// - Everything outside /api is the static frontend (SPA fallback in wrangler.jsonc).
// - /api/v1/presets, /cases/{id}, /presets/{id}/frames[?case_id=], /assets/{id}
//   are served locally from the catalog exported by cloudflare/build.py, with the
//   same status codes, error envelopes and headers as the FastAPI routes.
// - /api/v1/health, /search and /frame are proxied to ONE fixed origin (the
//   public Vercel Python API). No user-chosen hosts or URLs, no redirect
//   following, no cookies/credentials forwarded, bounded bodies and time.
// - Anything else under /api is a JSON 404, never the SPA's HTML.

export const UPSTREAM_ORIGIN = "https://perigee-liard.vercel.app";
export const MANIFEST_PATH = "/api/__perigee/catalog-manifest.json";
export const MAX_REQUEST_BODY_BYTES = 64 * 1024; // search/frame bodies are well under 2 KiB
export const MAX_UPSTREAM_BODY_BYTES = 8 * 1024 * 1024; // Vercel caps responses at 4.5 MB
export const UPSTREAM_TIMEOUT_MS = 70_000; // the Python function's maxDuration is 60 s

const PROXY_ROUTES = new Map([
  ["/api/v1/health", "GET"],
  ["/api/v1/search", "POST"],
  ["/api/v1/frame", "POST"],
]);
const CLIENT_RID = /^[A-Za-z0-9._:-]{1,64}$/;
const UPSTREAM_PASS_HEADERS = ["content-type", "cache-control", "retry-after", "x-request-id"];
const JSON_CACHE = "public, max-age=0, must-revalidate";
const hasOwn = (o, k) => o != null && Object.prototype.hasOwnProperty.call(o, k);

// ------------------------------------------------------------------ helpers

function requestIdFor(request) {
  const supplied = request.headers.get("x-request-id") || "";
  return CLIENT_RID.test(supplied) ? supplied : crypto.randomUUID().replaceAll("-", "");
}

export function envelope(rid, status, code, message, { retryable = false, details = null, headers = {} } = {}) {
  const body = JSON.stringify({
    schema_version: 1,
    request_id: rid,
    error: { code, message, retryable, details },
  });
  return new Response(body, {
    status,
    headers: {
      "content-type": "application/json",
      "cache-control": "no-store",
      "x-request-id": rid,
      "x-content-type-options": "nosniff",
      ...headers,
    },
  });
}

const notFound = (rid) => envelope(rid, 404, "NOT_FOUND", "No such API route.");
const methodNotAllowed = (rid) => envelope(rid, 405, "METHOD_NOT_ALLOWED", "Method not allowed for this API route.");

/**
 * Decode one raw path segment the way Starlette sees it. Returns null when the
 * segment is empty or decodes to something containing "/" (FastAPI sees a
 * different, unmatched path). Undecodable escapes stay raw: like FastAPI, the
 * route still matches and the id simply is not found.
 */
function segment(raw) {
  if (!raw) return null;
  let s;
  try {
    s = decodeURIComponent(raw);
  } catch {
    return raw;
  }
  return s.includes("/") ? null : s;
}

/** Route table mirroring backend/main.py + backend/routes/catalog.py. */
export function matchRoute(pathname) {
  if (PROXY_ROUTES.has(pathname)) return { kind: "proxy", method: PROXY_ROUTES.get(pathname) };
  if (pathname === "/api/v1/presets") return { kind: "presets" };
  const parts = pathname.split("/"); // ["", "api", "v1", ...]
  if (parts[1] !== "api" || parts[2] !== "v1") return null;
  if (parts.length === 5 && parts[3] === "cases") {
    const id = segment(parts[4]);
    return id === null ? null : { kind: "case", id };
  }
  if (parts.length === 5 && parts[3] === "assets") {
    const id = segment(parts[4]);
    return id === null ? null : { kind: "asset", id };
  }
  if (parts.length === 6 && parts[3] === "presets" && parts[5] === "frames") {
    const id = segment(parts[4]);
    return id === null ? null : { kind: "frames", id };
  }
  return null;
}

// ------------------------------------------------------------------ catalog

let manifestPromise = null;
/** Exposed for tests. */
export function resetManifestCache() {
  manifestPromise = null;
}

function loadManifest(env) {
  if (!manifestPromise) {
    manifestPromise = env.ASSETS.fetch(new Request(`https://assets.invalid${MANIFEST_PATH}`)).then(async (r) => {
      if (!r.ok) throw new Error(`catalog manifest unavailable (${r.status})`);
      return r.json();
    });
    manifestPromise.catch(() => {
      manifestPromise = null; // retry on the next request
    });
  }
  return manifestPromise;
}

async function readAsset(env, relPath) {
  const r = await env.ASSETS.fetch(new Request(`https://assets.invalid/${relPath}`));
  if (!r.ok) return null;
  return new Uint8Array(await r.arrayBuffer());
}

async function sha256Hex(bytes) {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return Array.from(d, (b) => b.toString(16).padStart(2, "0")).join("");
}

async function jsonDocument(env, rid, relPath) {
  const data = await readAsset(env, relPath);
  if (data === null) return envelope(rid, 503, "CONTENT_UNAVAILABLE", "Bundled catalog content is unavailable.");
  return new Response(data, {
    status: 200,
    headers: {
      "content-type": "application/json",
      "cache-control": JSON_CACHE,
      "x-request-id": rid,
      "x-content-type-options": "nosniff",
    },
  });
}

async function serveCatalog(route, url, env, rid) {
  let manifest;
  try {
    manifest = await loadManifest(env);
  } catch {
    return envelope(rid, 503, "CONTENT_UNAVAILABLE", "Bundled catalog content is unavailable.");
  }
  if (route.kind === "presets") return jsonDocument(env, rid, manifest.presets_document);

  if (route.kind === "case") {
    if (!hasOwn(manifest.cases, route.id)) {
      return envelope(rid, 404, "CASE_NOT_FOUND", "Unknown case.", {
        details: { available_case_ids: manifest.case_ids },
      });
    }
    return jsonDocument(env, rid, manifest.cases[route.id]);
  }

  if (route.kind === "frames") {
    if (!hasOwn(manifest.presets, route.id)) {
      return envelope(rid, 404, "PRESET_NOT_FOUND", "Unknown preset.", {
        details: { available_preset_ids: manifest.preset_ids },
      });
    }
    const preset = manifest.presets[route.id];
    const requested = url.searchParams.getAll("case_id");
    if (requested.length === 0) return jsonDocument(env, rid, preset.frames);
    const caseId = requested[requested.length - 1]; // FastAPI/Starlette: last value wins; "" is a value
    if (!hasOwn(preset.cases, caseId)) {
      return envelope(rid, 404, "CASE_NOT_FOUND", "Unknown case for this preset.", {
        details: { available_case_ids: preset.available_case_ids },
      });
    }
    return jsonDocument(env, rid, preset.cases[caseId]);
  }

  // asset
  const entry = hasOwn(manifest.assets, route.id) ? manifest.assets[route.id] : null;
  const data = entry ? await readAsset(env, entry.path) : null;
  if (!entry || data === null || (await sha256Hex(data)) !== entry.sha256) {
    return envelope(rid, 404, "ASSET_NOT_FOUND", "Unknown or unavailable asset.");
  }
  return new Response(data, {
    status: 200,
    headers: {
      "content-type": entry.media_type,
      "cache-control": entry.canonical ? "public, max-age=31536000, immutable" : "public, max-age=300, must-revalidate",
      etag: `"${entry.sha256}"`,
      "x-content-type-options": "nosniff",
      "content-disposition": "inline",
      "x-request-id": rid,
    },
  });
}

// ------------------------------------------------------------------ proxy

class TooLarge extends Error {}

async function readCapped(body, cap) {
  if (!body) return new Uint8Array(0);
  const reader = body.getReader();
  const chunks = [];
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > cap) {
      await reader.cancel().catch(() => {});
      throw new TooLarge();
    }
    chunks.push(value);
  }
  const out = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) {
    out.set(c, off);
    off += c.byteLength;
  }
  return out;
}

async function proxy(request, pathname, rid, deps) {
  const method = request.method;
  let body;
  if (method === "POST") {
    const declared = Number(request.headers.get("content-length") || "0");
    if (declared > MAX_REQUEST_BODY_BYTES) {
      return envelope(rid, 413, "INVALID_REQUEST", "Request body too large.");
    }
    try {
      body = await readCapped(request.body, MAX_REQUEST_BODY_BYTES);
    } catch (e) {
      if (e instanceof TooLarge) return envelope(rid, 413, "INVALID_REQUEST", "Request body too large.");
      return envelope(rid, 400, "INVALID_REQUEST", "Request body could not be read.");
    }
  }
  // Fixed destination: the constant origin plus the matched fixed path. The
  // request's query string, host and every other header are dropped.
  const target = new URL(pathname, UPSTREAM_ORIGIN).toString();
  const headers = new Headers({ "x-request-id": rid, accept: "application/json", "user-agent": "perigee-cloudflare-proxy" });
  if (method === "POST") headers.set("content-type", request.headers.get("content-type") || "application/json");

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), deps.timeoutMs ?? UPSTREAM_TIMEOUT_MS);
  let upstream;
  try {
    upstream = await deps.fetch(target, { method, headers, body, redirect: "manual", signal: controller.signal });
  } catch (e) {
    clearTimeout(timer);
    console.error("perigee proxy: upstream fetch failed", pathname, e?.name, e?.message);
    if (controller.signal.aborted) {
      return envelope(rid, 504, "UPSTREAM_TIMEOUT", "The Perigee API did not answer in time.", { retryable: true });
    }
    return envelope(rid, 502, "UPSTREAM_UNAVAILABLE", "The Perigee API is unavailable right now.", { retryable: true });
  }
  try {
    if (upstream.status >= 300 && upstream.status < 400) {
      await upstream.body?.cancel().catch(() => {});
      return envelope(rid, 502, "UPSTREAM_UNAVAILABLE", "The Perigee API answered with a redirect; it was not followed.", {
        retryable: true,
      });
    }
    const ctype = (upstream.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
    if (ctype !== "application/json") {
      await upstream.body?.cancel().catch(() => {});
      return envelope(rid, 502, "UPSTREAM_UNAVAILABLE", "The Perigee API returned an unexpected response.", {
        retryable: true,
      });
    }
    let data;
    try {
      data = await readCapped(upstream.body, MAX_UPSTREAM_BODY_BYTES);
    } catch (e) {
      if (e instanceof TooLarge) {
        return envelope(rid, 502, "UPSTREAM_UNAVAILABLE", "The Perigee API response was too large.", { retryable: false });
      }
      if (controller.signal.aborted) {
        return envelope(rid, 504, "UPSTREAM_TIMEOUT", "The Perigee API did not answer in time.", { retryable: true });
      }
      return envelope(rid, 502, "UPSTREAM_UNAVAILABLE", "The Perigee API is unavailable right now.", { retryable: true });
    }
    const out = new Headers({ "x-content-type-options": "nosniff" });
    for (const h of UPSTREAM_PASS_HEADERS) {
      const v = upstream.headers.get(h);
      if (v !== null) out.set(h, v);
    }
    if (!out.has("x-request-id")) out.set("x-request-id", rid);
    return new Response(data, { status: upstream.status, headers: out });
  } finally {
    clearTimeout(timer);
  }
}

// ------------------------------------------------------------------ entry

export async function handle(request, env, deps = {}) {
  const url = new URL(request.url);
  const path = url.pathname;
  if (path !== "/api" && !path.startsWith("/api/")) return env.ASSETS.fetch(request); // not reached with run_worker_first
  const rid = requestIdFor(request);
  // Wrap the global: calling it as deps.fetch(...) would bind `this` to deps,
  // which the Workers runtime rejects ("Illegal invocation").
  const fetchImpl = deps.fetch ?? ((input, init) => fetch(input, init));

  let route = matchRoute(path);
  if (!route && path.length > 1 && path.endsWith("/") && matchRoute(path.slice(0, -1))) {
    // FastAPI redirect_slashes: 307 to the path without the trailing slash.
    return new Response(null, {
      status: 307,
      headers: { location: path.slice(0, -1) + url.search, "x-request-id": rid },
    });
  }
  if (!route) return notFound(rid);

  if (route.kind === "proxy") {
    if (request.method !== route.method) return methodNotAllowed(rid);
    return proxy(request, path, rid, { ...deps, fetch: fetchImpl });
  }
  if (request.method !== "GET") return methodNotAllowed(rid); // FastAPI GET routes answer HEAD with 405 too
  return serveCatalog(route, url, env, rid);
}

