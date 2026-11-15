import { test } from "node:test";
import assert from "node:assert/strict";
import { handle, matchRoute, UPSTREAM_ORIGIN } from "../src/app.js";

test("object lookup proxies only its fixed POST path, not caller query or cookies", async () => {
  let captured;
  const response = await handle(new Request("https://perigee.example/api/v1/resolve?url=https://evil.test", {
    method: "POST", headers: { "content-type": "application/json", cookie: "private=1" },
    body: JSON.stringify({ name: "Barnard's Star" }),
  }), {}, { fetch: async (url, init) => {
    captured = { url, init };
    return Response.json({ name: "Barnard's Star", source: "SIMBAD via CDS Sesame" });
  }});
  assert.equal(response.status, 200);
  assert.equal(captured.url, UPSTREAM_ORIGIN + "/api/v1/resolve");
  assert.equal(captured.init.redirect, "manual");
  assert.equal(captured.init.headers.has("cookie"), false);
  assert.equal(JSON.parse(new TextDecoder().decode(captured.init.body)).name, "Barnard's Star");
  assert.deepEqual(matchRoute("/api/v1/resolve"), { kind: "proxy", method: "POST" });
});

test("resolver GET and arbitrary resolver paths never proxy", async () => {
  for (const path of ["/api/v1/resolve", "/api/v1/resolve/evil"]) {
    let fetched = false;
    const r = await handle(new Request("https://perigee.example" + path), {}, { fetch: async () => { fetched = true; } });
    assert.equal(fetched, false);
    assert.equal(r.status, path.endsWith("evil") ? 404 : 405);
  }
});
