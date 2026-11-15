import { describe, expect, it } from "vitest";
import {
  createEvidenceCard,
  emptyStore,
  resolveDraft,
  updateEvidenceText,
  upsertCard,
  type DraftMemory,
  type EvidenceCard,
} from "../src/evidence/card";
import {
  presetContextKey,
  queryContextKey,
  reopenTarget,
  routeContextKey,
  savedContextKey,
} from "../src/evidence/reopen";
import { evidenceTitle, formatPosition, type TitleSources } from "../src/evidence/title";
import { parseRoute, routeToSearch } from "../src/lib/route";

/** Titles keep "RA"/"Dec" on the same line as their values (no-break space). */
const nb = (s: string) => s.replace(/(RA|Dec) /g, "$1\u00a0");

const NOW = new Date("2026-11-14T18:00:00.000Z");

const SOURCES: TitleSources = {
  presets: [
    { id: "epsilon_indi_b", display_name: "Epsilon Indi B", case_ids: ["fair_comparison"] },
    { id: "barnards_star", display_name: "Barnard's Star", case_ids: ["moving_neighbor"] },
    { id: "wise_0855", display_name: "WISE 0855", case_ids: [] },
  ],
  cases: {
    fair_comparison: { title: "Is this a fair comparison?", target_id: "epsilon_indi_b" },
    moving_neighbor: { title: "Follow a nearby moving star", target_id: "barnards_star" },
  },
};

function presetCard(presetId: string, caseId: string | null, origin: "api" | "fixture" = "api"): EvidenceCard {
  return createEvidenceCard({
    preset_id: presetId,
    case_id: caseId,
    query: { ra_deg: 331.0966687831005, dec_deg: -56.80064917516836, fov_arcmin: 6 },
    app_version: "test",
    data_origin: origin,
    now: NOW,
  });
}

function queryCard(ra: number, dec: number, fov = 6, caseId: string | null = null): EvidenceCard {
  return createEvidenceCard({
    case_id: caseId,
    query: { ra_deg: ra, dec_deg: dec, fov_arcmin: fov },
    app_version: "test",
    data_origin: "api",
    now: NOW,
  });
}

describe("evidence card titles", () => {
  it("combines a newer card's stored title (the case title) with the target name", () => {
    const card = { ...presetCard("epsilon_indi_b", "fair_comparison"), title: "Is this a fair comparison?" };
    expect(evidenceTitle(card, SOURCES)).toBe("Epsilon Indi B · Is this a fair comparison?");
    // Case content not loaded (or offline): the stored title still names the case.
    expect(evidenceTitle(card, { presets: SOURCES.presets })).toBe("Epsilon Indi B · Is this a fair comparison?");
    expect(evidenceTitle(card, {})).toBe("Is this a fair comparison?");
  });

  it("does not repeat a free-exploration card's stored title (the target name)", () => {
    const card = { ...presetCard("wise_0855", null), title: "WISE 0855" };
    expect(evidenceTitle(card, SOURCES)).toBe("WISE 0855");
    expect(evidenceTitle(card, {})).toBe("WISE 0855");
    const named = { ...presetCard("wise_0855", null), title: "WISE 0855 · my own card title" };
    expect(evidenceTitle(named, SOURCES)).toBe("WISE 0855 · my own card title");
  });

  it("ignores an empty or non-string own title", () => {
    const blank = { ...presetCard("epsilon_indi_b", "fair_comparison"), title: "  " };
    const nul = { ...presetCard("epsilon_indi_b", "fair_comparison"), title: null };
    expect(evidenceTitle(blank, SOURCES)).toBe("Epsilon Indi B · Is this a fair comparison?");
    expect(evidenceTitle(nul, SOURCES)).toBe("Epsilon Indi B · Is this a fair comparison?");
  });

  it("resolves an older card (no title field) from the target and case", () => {
    // A card saved before the title field existed has no `title` key at all.
    const { title: _omit, ...card } = presetCard("epsilon_indi_b", "fair_comparison");
    expect("title" in card).toBe(false);
    expect(evidenceTitle(card, SOURCES)).toBe("Epsilon Indi B · Is this a fair comparison?");
    expect(evidenceTitle(presetCard("wise_0855", null), SOURCES)).toBe("WISE 0855");
  });

  it("falls back to the target name, then the raw ID, while lookups are missing", () => {
    const card = presetCard("epsilon_indi_b", "fair_comparison");
    expect(evidenceTitle(card, { presets: SOURCES.presets })).toBe("Epsilon Indi B");
    expect(evidenceTitle(card, {})).toBe("fair_comparison");
    expect(evidenceTitle(presetCard("wise_0855", null), {})).toBe("wise_0855");
  });

  it("titles a coordinate search by its position", () => {
    expect(evidenceTitle(queryCard(83.82, -5.39), SOURCES)).toBe(nb("Coordinate search · RA 83.82°, Dec −5.39°"));
    expect(evidenceTitle(queryCard(83.82, -5.39), {})).toBe(nb("Coordinate search · RA 83.82°, Dec −5.39°"));
    expect(evidenceTitle(queryCard(331.0966687831005, -56.80064917516836, 6, "fair_comparison"), SOURCES)).toBe(
      nb("Coordinate search · RA 331.097°, Dec −56.801° · Epsilon Indi B"),
    );
  });

  it("formats positions with at most three decimals and a true minus sign", () => {
    expect(formatPosition({ ra_deg: 0, dec_deg: 4.5 })).toBe(nb("RA 0°, Dec 4.5°"));
    expect(formatPosition({ ra_deg: 269.4462585584787, dec_deg: -0.0001 })).toBe(nb("RA 269.446°, Dec 0°"));
  });
});

describe("reopening a saved card", () => {
  it("reopens a preset card at its target, keyed exactly as saved", () => {
    const card = presetCard("epsilon_indi_b", "fair_comparison");
    const key = presetContextKey("api", "epsilon_indi_b");
    const store = upsertCard(emptyStore(), key, card);
    const t = reopenTarget(card, savedContextKey(card.id, store));
    expect(t).toEqual({ route: { view: "preset", presetId: "epsilon_indi_b" }, fixtures: false, contextKey: key });
    expect(routeToSearch(t!.route, t!.fixtures)).toBe("?preset=epsilon_indi_b");
    expect(parseRoute(routeToSearch(t!.route, t!.fixtures))).toEqual(t!.route);
  });

  it("reopens a coordinate card at the same position and field of view", () => {
    const card = queryCard(83.82, -5.39, 4);
    const key = queryContextKey("api", { ra_deg: 83.82, dec_deg: -5.39, fov_arcmin: 4 });
    const store = upsertCard(emptyStore(), key, card);
    const t = reopenTarget(card, savedContextKey(card.id, store))!;
    expect(t.route).toEqual({ view: "query", ra: "83.82", dec: "-5.39", fov: "4", caseId: undefined });
    expect(t.contextKey).toBe(key);
    const search = routeToSearch(t.route, false);
    expect(search).toBe("?view=query&ra=83.82&dec=-5.39&fov=4");
    // A reload re-parses the URL and derives the same notebook key.
    expect(routeContextKey(parseRoute(search), false)).toBe(key);
  });

  it("keeps the case on a coordinate card opened from a target", () => {
    const card = queryCard(331.0966687831005, -56.80064917516836, 6, "fair_comparison");
    const key = queryContextKey("api", card.query!);
    const t = reopenTarget(card, key)!;
    expect(t.route).toMatchObject({ view: "query", caseId: "fair_comparison" });
    expect(routeContextKey(parseRoute(routeToSearch(t.route, false)), false)).toBe(key);
  });

  it("derives the saved key from an older card's fields when the context map lost it", () => {
    for (const card of [presetCard("barnards_star", "moving_neighbor"), queryCard(269.4462585584787, 4.768324486236583)]) {
      const expected = card.preset_id
        ? presetContextKey("api", card.preset_id)
        : queryContextKey("api", card.query!);
      const t = reopenTarget(card, savedContextKey(card.id, emptyStore()))!;
      expect(t.contextKey).toBe(expected);
    }
  });

  it("finds an unsaved draft's key in this tab's memory", () => {
    const card = queryCard(10, 20);
    const memory: DraftMemory = new Map([[queryContextKey("api", card.query!), card]]);
    expect(savedContextKey(card.id, emptyStore(), memory)).toBe("api:query:10,20,6");
  });

  it("keeps the development-fixture flag for fixture cards", () => {
    const card = presetCard("epsilon_indi_b", "fair_comparison", "fixture");
    const key = presetContextKey("fixture", "epsilon_indi_b");
    const t = reopenTarget(card, key)!;
    expect(t.fixtures).toBe(true);
    expect(t.contextKey).toBe(key);
    expect(routeToSearch(t.route, t.fixtures)).toBe("?preset=epsilon_indi_b&fixtures=1");
  });

  it("never puts notes in the reopen link", () => {
    let card = queryCard(83.82, -5.39);
    card = updateEvidenceText(card, "claim", "secret claim", NOW);
    card = updateEvidenceText(card, "observations", "private observation", NOW);
    const t = reopenTarget(card, null)!;
    const search = routeToSearch(t.route, false);
    expect(search).not.toMatch(/secret|private|claim|observation/);
  });

  it("restores only that card's draft and leaves other cards untouched", () => {
    const eps = updateEvidenceText(presetCard("epsilon_indi_b", "fair_comparison"), "claim", "eps note", NOW);
    const bar = updateEvidenceText(presetCard("barnards_star", "moving_neighbor"), "claim", "barnard note", NOW);
    const q = updateEvidenceText(queryCard(83.82, -5.39), "claim", "orion note", NOW);
    let store = emptyStore();
    store = upsertCard(store, presetContextKey("api", "epsilon_indi_b"), eps);
    store = upsertCard(store, presetContextKey("api", "barnards_star"), bar);
    store = upsertCard(store, queryContextKey("api", q.query!), q);
    const memory: DraftMemory = new Map();
    for (const card of [eps, bar, q]) {
      const t = reopenTarget(card, savedContextKey(card.id, store))!;
      expect(resolveDraft(t.contextKey, store, memory)?.card.claim).toBe(card.claim);
    }
    expect(store.cards.map((c) => c.claim).sort()).toEqual(["barnard note", "eps note", "orion note"]);
  });

  it("offers nothing to reopen for a card with neither target nor position", () => {
    const card = createEvidenceCard({ app_version: "test", data_origin: "api", now: NOW });
    expect(reopenTarget(card, null)).toBeNull();
    expect(reopenTarget(card, "api:query:none")).toBeNull();
  });
});
