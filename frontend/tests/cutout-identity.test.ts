import { describe, expect, it } from "vitest";
import { frameCacheKey, rememberFrame } from "../src/lib/frameCache";
import { parseRoute, routeToSearch } from "../src/lib/route";

describe("cutout identity", () => {
  const query = { ra_deg: 83.8, dec_deg: -5.4, fov_arcmin: 2, limit: 8 };
  it("never reuses a frame for another field, position, source, or signed release", () => {
    const original = frameCacheKey("api", "same-observation", "release-a", query);
    const others = [
      frameCacheKey("api", "same-observation", "release-a", { ...query, fov_arcmin: 10 }),
      frameCacheKey("api", "same-observation", "release-a", { ...query, ra_deg: 83.9 }),
      frameCacheKey("api", "same-observation", "release-a", { ...query, dec_deg: -5.5 }),
      frameCacheKey("api", "same-observation", "release-b", query),
      frameCacheKey("fixture", "same-observation", "release-a", query),
    ];
    const cache = new Map([[original, "old pixels"]]);
    for (const key of others) expect(cache.get(key)).toBeUndefined();
    expect(cache.get(frameCacheKey("api", "same-observation", "release-a", { ...query, limit: 24 }))).toBe("old pixels");
  });
  it("bounds long-session memory without discarding the newly processed frame", () => {
    const cache = new Map<string, string>();
    for (let i = 0; i < 160; i++) rememberFrame(cache, `${i}`, `pixels-${i}`);
    expect(cache.size).toBe(128);
    expect(cache.has("0")).toBe(false);
    expect(cache.get("159")).toBe("pixels-159");
  });
  it("round-trips the requested result limit in a shared query", () => {
    const route = { view: "query" as const, ra: "83.8", dec: "-5.4", fov: "10", limit: "8" };
    expect(parseRoute(routeToSearch(route, false))).toEqual({ ...route, caseId: undefined });
  });
});
