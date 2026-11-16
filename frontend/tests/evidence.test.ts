import { describe, expect, it } from "vitest";
import { normalizeFrameRecord } from "../src/api/client";
import {
  CLAIM_MAX,
  STORAGE_KEY,
  checkCaseRequirements,
  createEvidenceCard,
  exportFilename,
  loadStore,
  persistStore,
  serializeEvidenceCard,
  toggleEvidenceFrame,
  updateEvidenceText,
  upsertCard,
  validateEvidenceCard,
} from "../src/evidence/card";
import { validateQuery } from "../src/lib/coords";

const NOW = new Date("2026-11-14T18:00:00.000Z");

function frame(obs: string, detector: number, mjd: number, status = "clear") {
  return normalizeFrameRecord({
    frame_id: `${obs}_D${detector}`,
    observation_id: obs,
    detector,
    collection_id: "spherex_dr1",
    observed_at_utc: "2026-04-29T12:05:47.874",
    mjd,
    source_url: `https://irsa.ipac.caltech.edu/${obs}.fits`,
    wavelength_um: 2.3232,
    bandwidth_um: 0.0577,
    wavelength_location: "Catalog-predicted position",
    image: null,
    quality: { status, covered: true, valid_aperture_pixels: null, adverse_aperture_pixels: null, flag_names: ["OVERFLOW"], notes: null },
    display_scale: { mode: "shared" },
    limitations: [],
  });
}

class MemoryStorage {
  data = new Map<string, string>();
  getItem(k: string) {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string) {
    this.data.set(k, v);
  }
}

function baseCard() {
  return createEvidenceCard({
    id: "11111111-2222-3333-4444-555555555555",
    case_id: "fair_comparison",
    preset_id: "epsilon_indi_b",
    query: { ra_deg: 331.0966687831005, dec_deg: -56.80064917516836, fov_arcmin: 6 },
    sources: [{ label: "IRSA", url: "https://irsa.ipac.caltech.edu/Missions/spherex.html" }],
    app_version: "0.1.0",
    data_origin: "api",
    now: NOW,
  });
}

describe("evidence card", () => {
  it("has every contract field with stable key order", () => {
    let card = baseCard();
    card = toggleEvidenceFrame(card, frame("2026W39_2A_0597_4", 3, 61310.32), "B", NOW);
    card = toggleEvidenceFrame(card, frame("2026W18_1A_0516_1", 3, 61159.5), "A", NOW);
    card = updateEvidenceText(card, "claim", "A and B are a fair pair.", NOW);
    const json = serializeEvidenceCard(card);
    const parsed = JSON.parse(json);
    expect(Object.keys(parsed)).toEqual([
      "schema_version",
      "id",
      "created_at_utc",
      "updated_at_utc",
      "app_version",
      "data_origin",
      "case_id",
      "preset_id",
      "title",
      "query",
      "frames",
      "claim",
      "observations",
      "uncertainty",
      "case_limitations",
      "sources",
      "reviewed_step_ids",
      "reference_shown",
      "reference_evidence",
    ]);
    expect(parsed.schema_version).toBe(1);
    // Chronological, with per-frame identity, date, wavelength, quality and source.
    expect(parsed.frames.map((f: { ref: string }) => f.ref)).toEqual(["A", "B"]);
    expect(parsed.frames[0]).toMatchObject({
      frame_key: "2026W18_1A_0516_1_D3",
      observation_id: "2026W18_1A_0516_1",
      detector: 3,
      collection_id: "spherex_dr1",
      observed_at_utc: "2026-04-29T12:05:47.874",
      wavelength_um: 2.3232,
      quality_status: "clear",
      source_url: "https://irsa.ipac.caltech.edu/2026W18_1A_0516_1.fits",
    });
    expect(json.endsWith("\n")).toBe(true);
    expect(validateEvidenceCard(parsed).ok).toBe(true);
  });

  it("round-trips through serialization without loss", () => {
    const card = toggleEvidenceFrame(baseCard(), frame("X", 1, 1, "flagged"), null, NOW);
    expect(JSON.parse(serializeEvidenceCard(card))).toEqual(card);
  });

  it("toggling a frame twice removes it", () => {
    const f = frame("X", 1, 1);
    const card = toggleEvidenceFrame(toggleEvidenceFrame(baseCard(), f, null, NOW), f, null, NOW);
    expect(card.frames).toEqual([]);
  });

  it("limits the claim length", () => {
    const card = updateEvidenceText(baseCard(), "claim", "x".repeat(CLAIM_MAX + 50), NOW);
    expect(card.claim.length).toBe(CLAIM_MAX);
  });

  it("rejects malformed cards", () => {
    const bad = { ...baseCard(), schema_version: 2, frames: [{ frame_key: 1 }] };
    const v = validateEvidenceCard(bad);
    expect(v.ok).toBe(false);
    if (!v.ok) {
      expect(v.errors).toContain("schema_version must be 1");
      expect(v.errors).toContain("frames[0] is malformed");
    }
  });

  it("names exports by subject, date and id", () => {
    expect(exportFilename(baseCard())).toBe("perigee-evidence-fair_comparison-2026-11-14-11111111.json");
  });

  it("checks case requirements without blocking", () => {
    const req = { min_selected_frames: 2, must_include_refs_any_of: [["A", "B"]] };
    expect(checkCaseRequirements(baseCard(), req)).toEqual([
      "Add at least 2 frames to the card.",
      "Include frames A and B.",
      "Write a short claim.",
    ]);
    let card = toggleEvidenceFrame(baseCard(), frame("a", 3, 1), "A", NOW);
    card = toggleEvidenceFrame(card, frame("b", 3, 2), "B", NOW);
    card = updateEvidenceText(card, "claim", "Fair pair.", NOW);
    expect(checkCaseRequirements(card, req)).toEqual([]);
  });
});

describe("evidence storage", () => {
  it("persists and reloads by context, discarding invalid cards", () => {
    const storage = new MemoryStorage();
    const card = baseCard();
    expect(persistStore(storage, upsertCard(loadStore(storage), "api:preset:epsilon_indi_b", card))).toBe(true);
    const raw = JSON.parse(storage.getItem(STORAGE_KEY) as string);
    raw.cards.push({ junk: true });
    storage.setItem(STORAGE_KEY, JSON.stringify(raw));
    const store = loadStore(storage);
    expect(store.cards).toHaveLength(1);
    expect(store.contexts["api:preset:epsilon_indi_b"]).toBe(card.id);
  });

  it("survives corrupt or unavailable storage", () => {
    const storage = new MemoryStorage();
    storage.setItem(STORAGE_KEY, "{not json");
    expect(loadStore(storage).cards).toEqual([]);
    expect(loadStore(null).cards).toEqual([]);
    const throwing = {
      getItem: () => null,
      setItem: () => {
        throw new Error("QuotaExceededError");
      },
    };
    expect(persistStore(throwing, loadStore(null))).toBe(false);
  });
});

describe("coordinate validation", () => {
  const ok = { ra: "330.84", dec: "-56.786", fov: "6", limit: "24" };
  it("accepts a valid query", () => {
    expect(validateQuery(ok)).toEqual({
      ok: true,
      value: { ra_deg: 330.84, dec_deg: -56.786, fov_arcmin: 6, limit: 24 },
      notices: [],
    });
  });
  it("rejects partial parses, NaN, infinity and out-of-range values without clipping", () => {
    for (const ra of ["12abc", "NaN", "Infinity", "", "400", "-1", "1e999"]) {
      expect(validateQuery({ ...ok, ra }).ok).toBe(false);
    }
    expect(validateQuery({ ...ok, dec: "90.0001" }).ok).toBe(false);
    expect(validateQuery({ ...ok, fov: "1.9" }).ok).toBe(false);
    expect(validateQuery({ ...ok, fov: "10.5" }).ok).toBe(false);
    expect(validateQuery({ ...ok, limit: "49" }).ok).toBe(false);
    expect(validateQuery({ ...ok, limit: "2.5" }).ok).toBe(false);
  });
  it("normalizes exactly 360 to 0 with a visible notice", () => {
    const v = validateQuery({ ...ok, ra: "360" });
    expect(v.ok && v.value.ra_deg).toBe(0);
    expect(v.ok && v.notices.length).toBe(1);
  });
  it("applies frontend defaults for blank FOV and limit", () => {
    const v = validateQuery({ ...ok, fov: "", limit: "" });
    expect(v.ok && v.value).toMatchObject({ fov_arcmin: 6, limit: 12 });
  });
});
