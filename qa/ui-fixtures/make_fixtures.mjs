// UI failure-state fixtures for Codex (N4), produced by the REAL Worker code
// (cloudflare/src/app.js) against fault-injected static assets, plus real shipped
// records and existing API examples. Nothing here is hand-written response JSON.
//
//   .venv/bin/python cloudflare/build.py      # build/public must match this checkout
//   node qa/ui-fixtures/make_fixtures.mjs      # writes qa/ui-fixtures/*.json
//
// Each fixture: { scenario, requests: [{method, path, status, headers, body}], expected_ui }
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { handle, resetManifestCache } from "../../cloudflare/src/app.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..", "..");
const PUBLIC = path.join(REPO, "cloudflare", "build", "public");
const RID = "ui-fixture-0001";

function assets(missing = new Set()) {
  return {
    async fetch(req) {
      const p = decodeURIComponent(new URL(req.url).pathname);
      const f = path.join(PUBLIC, p);
      if (missing.has(p) || !f.startsWith(PUBLIC) || !existsSync(f)) return new Response("not found", { status: 404 });
      return new Response(readFileSync(f), { status: 200 });
    },
  };
}

async function call(method, p, env, deps = {}) {
  resetManifestCache();
  const r = await handle(new Request(`https://perigee.example${p}`, { method, headers: { "x-request-id": RID } }), env, deps);
  const ct = r.headers.get("content-type") || "";
  const raw = new Uint8Array(await r.arrayBuffer());
  const body = ct.startsWith("application/json") ? JSON.parse(new TextDecoder().decode(raw)) : `<${raw.length} bytes ${ct}>`;
  const keep = ["content-type", "cache-control", "x-request-id", "x-perigee-worker", "retry-after", "etag"];
  return { method, path: p, status: r.status, headers: Object.fromEntries(keep.filter((h) => r.headers.has(h)).map((h) => [h, r.headers.get(h)])), body };
}

const manifest = JSON.parse(readFileSync(path.join(PUBLIC, "api/__perigee/catalog-manifest.json"), "utf8"));
const fairFrames = JSON.parse(readFileSync(path.join(PUBLIC, manifest.presets.epsilon_indi_b.cases.fair_comparison), "utf8"));
const caseA = fairFrames.frames.find((f) => f.case_ref === "A" || f.frame_key === "2026W18_1A_0516_1_D3");
const overlayId = caseA.flag_image.src.split("/").pop();
const out = {};

// 1. Missing overlay: the record says flags exist; the overlay PNG cannot be fetched.
out.missing_overlay = {
  scenario: "Quality overlay asset unavailable for a frame whose record is fine",
  requests: [
    await call("GET", `/api/v1/assets/${overlayId}`, { ASSETS: assets(new Set([`/${manifest.assets[overlayId].path}`])) }),
  ],
  frame_record_quality: caseA.quality,
  expected_ui: [
    "Keep the frame's quality status from the record (here " + caseA.quality.status + "); do NOT change it to 'clear' or 'no flags'.",
    "Disable the 'Show flagged pixels' control for this frame and say the overlay could not be loaded (F3).",
    "Do not show a legend that implies an overlay is drawn.",
  ],
};

// 2. Case product set unavailable (catalog content failure) -> JSON 503, not HTML.
const caseRel = `/${manifest.presets.epsilon_indi_b.cases.fair_comparison}`;
out.case_unavailable = {
  scenario: "Authored case frames cannot be served (bundled content unusable)",
  requests: [await call("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id=fair_comparison", { ASSETS: assets(new Set([caseRel])) })],
  expected_ui: [
    "Show that the investigation's case images are unavailable and offer retry.",
    "Do NOT silently fall back to the general per-frame-stretch sequence for the comparison plates (F4): the case relies on its shared stretch.",
  ],
};

// 3. Unknown case for a preset (stale URL / renamed case).
out.unknown_case = {
  scenario: "case_id not valid for this preset",
  requests: [await call("GET", "/api/v1/presets/epsilon_indi_b/frames?case_id=moving_neighbor", { ASSETS: assets() })],
  expected_ui: ["Treat as 'investigation not found'; list available_case_ids from details; keep notes."],
};

// 4. Live origin down: curated routes still work; proxied routes return the envelope.
const down = async () => {
  throw new TypeError("fetch failed (fixture: origin unreachable)");
};
out.live_origin_unavailable = {
  scenario: "Python API origin unreachable while curated content is fine",
  requests: [
    await call("GET", "/api/v1/presets", { ASSETS: assets() }, { fetch: down }),
    await call("GET", "/api/v1/health", { ASSETS: assets() }, { fetch: down }),
  ],
  expected_ui: [
    "Curated investigations keep working (presets 200).",
    "Live search/frame show 'archive service unavailable, retry' (502 UPSTREAM_UNAVAILABLE, retryable) — never an empty result.",
  ],
};
if (out.live_origin_unavailable.requests[0].body && out.live_origin_unavailable.requests[0].body.presets) {
  out.live_origin_unavailable.requests[0].body = `<presets document: ${out.live_origin_unavailable.requests[0].body.count} presets>`;
}

// 5-7. Existing API examples (real recorded/fixture responses), referenced not copied.
out.reused_api_examples = {
  partial_search: "backend/tests/api/examples/search_response.partial.fixture.json",
  empty_search: "backend/tests/api/examples/search_response.empty.fixture.json",
  token_expired: "backend/tests/api/examples/error.token_expired.json",
  upstream_unavailable: "backend/tests/api/examples/error.upstream_unavailable.json",
  invalid_coordinates: "backend/tests/api/examples/error.invalid_coordinates.json",
  invalid_field_of_view: "backend/tests/api/examples/error.invalid_field_of_view.json",
};

// 8. No coverage: a real shipped record whose target is off the image.
const nc = JSON.parse(readFileSync(path.join(PUBLIC, manifest.presets.epsilon_indi_b.frames), "utf8")).frames.find(
  (f) => f.quality.status === "not_covered",
);
out.no_coverage = {
  scenario: "Target position not covered by this image (real shipped record)",
  frame_key: nc.frame_key,
  record_excerpt: { quality: nc.quality, wavelength_um: nc.wavelength_um, wavelength_location: nc.wavelength_location, marker: nc.marker },
  expected_ui: ["Say the target is outside this image; show no wavelength at target; do not call it 'flagged' or 'clear'."],
};

for (const [name, fx] of Object.entries(out)) {
  writeFileSync(path.join(HERE, `${name}.json`), JSON.stringify(fx, null, 1) + "\n");
}
console.log(`wrote ${Object.keys(out).length} fixtures to qa/ui-fixtures/`);
