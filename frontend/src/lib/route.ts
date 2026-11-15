// URL state. A shared link carries coordinates, field of view and an optional
// case ID (or a preset ID). It never carries private notes.

export type Route =
  | { view: "home" }
  | { view: "preset"; presetId: string }
  | { view: "query"; ra?: string; dec?: string; fov?: string; limit?: string; caseId?: string };

export function parseRoute(search: string): Route {
  const p = new URLSearchParams(search);
  const preset = p.get("preset");
  if (preset) return { view: "preset", presetId: preset };
  if (p.get("view") === "query" || p.has("ra") || p.has("dec")) {
    return {
      view: "query",
      ra: p.get("ra") ?? undefined,
      dec: p.get("dec") ?? undefined,
      fov: p.get("fov") ?? undefined,
      ...(p.has("limit") ? { limit: p.get("limit")! } : {}),
      caseId: p.get("case") ?? undefined,
    };
  }
  return { view: "home" };
}

/** Builds a query string, preserving the development-fixture flag if set. */
export function routeToSearch(route: Route, keepFixture: boolean): string {
  const p = new URLSearchParams();
  if (route.view === "preset") p.set("preset", route.presetId);
  if (route.view === "query") {
    p.set("view", "query");
    if (route.ra) p.set("ra", route.ra);
    if (route.dec) p.set("dec", route.dec);
    if (route.fov) p.set("fov", route.fov);
    if (route.limit) p.set("limit", route.limit);
    if (route.caseId) p.set("case", route.caseId);
  }
  if (keepFixture) p.set("fixtures", "1");
  const s = p.toString();
  return s ? `?${s}` : "";
}
