// Contract checks against the API owner's example payloads, copied verbatim
// from backend/tests/api/examples/ on origin/claude/perigee-integration
// (worker 03, commit 8bcaf49). Re-copy them when the API changes.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { createHttpApi, errorFromResponse, normalizeFrameResponse, normalizeSearchResponse } from "../src/api/client";
import { createEvidenceCard, serializeEvidenceCard, toggleEvidenceFrame, validateEvidenceCard } from "../src/evidence/card";

const example = (name: string): unknown =>
  JSON.parse(readFileSync(new URL(`./contract-examples/${name}`, import.meta.url), "utf8"));

describe("API example payloads", () => {
  it("reads the live ready search response in contract order", () => {
    const res = normalizeSearchResponse(example("search_response.ready.live.json"));
    expect(res.status).toBe("ready");
    expect(res.observations.length).toBeGreaterThan(0);
    for (let i = 1; i < res.observations.length; i++) {
      expect((res.observations[i - 1].mjd ?? 0) <= (res.observations[i].mjd ?? 0)).toBe(true);
    }
    expect(res.observations[0].frame_key).toMatch(/_D\d$/);
    expect(res.observations[0].frame_token.length).toBeGreaterThan(10);
  });

  it("distinguishes partial and empty search results", () => {
    expect(normalizeSearchResponse(example("search_response.partial.fixture.json")).status).toBe("partial");
    const empty = normalizeSearchResponse(example("search_response.empty.fixture.json"));
    expect(empty.status).toBe("empty");
    expect(empty.observations).toEqual([]);
  });

  it("reads a frame response and carries it into a valid evidence card", () => {
    const frame = normalizeFrameResponse(example("frame_response.fixture.json"));
    expect(frame.frame_key).toBe("2026W18_1A_0516_1_D3");
    expect(frame.image?.src.startsWith("data:image/png")).toBe(true);
    const card = toggleEvidenceFrame(
      createEvidenceCard({ app_version: "test", data_origin: "api", query: { ra_deg: 1, dec_deg: 2, fov_arcmin: 6 } }),
      frame,
      null,
    );
    const parsed = JSON.parse(serializeEvidenceCard(card));
    expect(validateEvidenceCard(parsed).ok).toBe(true);
    expect(parsed.frames[0].source_url).toBe(frame.source_url);
  });

  it("maps the error examples through the client", async () => {
    const expired = example("error.token_expired.json");
    const api = createHttpApi({
      base: "/api/v1",
      fetchImpl: async () =>
        new Response(JSON.stringify(expired), { status: 410, headers: { "content-type": "application/json" } }),
    });
    await expect(api.frame("t")).rejects.toMatchObject({ code: "TOKEN_EXPIRED", retryable: false });
    const upstream = errorFromResponse(
      502,
      "application/json",
      JSON.stringify(example("error.upstream_unavailable.json")),
    );
    expect(upstream.code).toBe("UPSTREAM_UNAVAILABLE");
  });
});
