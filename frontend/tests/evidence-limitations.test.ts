import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import { normalizeFrameRecord } from "../src/api/client";
import type { CaseContent } from "../src/api/types";
import { Notebook } from "../src/components/Notebook";
import {
  STORAGE_KEY,
  printedLimitations,
  attachPair,
  createEvidenceCard,
  fillCardContext,
  loadStore,
  serializeEvidenceCard,
  toggleEvidenceFrame,
  updateEvidenceText,
  validateEvidenceCard,
  withCaseContext,
} from "../src/evidence/card";

const NOW = new Date("2026-11-14T18:00:00.000Z");

// Verbatim strings from backend/content/cases/fair_comparison.json.
const CASE_LIMS = [
  "The quality screen checks for problem flags in a small circle around the predicted position. It is not a detection test or a brightness measurement.",
  "Display images are resampled and contrast-stretched for viewing; they are not used to measure brightness.",
];
const FRAME_LIMS = ["Display image only; not for photometry.", "Marker is a catalog prediction, not a measured position."];

function frame(obs: string, detector: number, mjd: number, limitations: string[] = []) {
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
    quality: { status: "clear", covered: true, valid_aperture_pixels: null, adverse_aperture_pixels: null, flag_names: [], notes: null },
    display_scale: { mode: "shared" },
    limitations,
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

/** A card exactly as an earlier build stored it: schema_version 1, no title or limitations. */
function legacyV1Card() {
  return {
    schema_version: 1,
    id: "legacy00-1111-4222-8333-444444444444",
    created_at_utc: "2026-11-13T09:00:00.000Z",
    updated_at_utc: "2026-11-13T09:30:00.000Z",
    app_version: "0.1.0",
    data_origin: "api",
    case_id: "fair_comparison",
    preset_id: "epsilon_indi_b",
    query: { ra_deg: 331.0966687831005, dec_deg: -56.80064917516836, fov_arcmin: 6 },
    frames: [
      {
        ref: "A",
        frame_key: "2026W18_1A_0516_1_D3",
        frame_id: "2026W18_1A_0516_1_D3",
        observation_id: "2026W18_1A_0516_1",
        detector: 3,
        collection_id: "spherex_dr1",
        observed_at_utc: "2026-04-29T12:05:47.874",
        mjd: 61159.5,
        wavelength_um: 2.3232,
        bandwidth_um: 0.0577,
        wavelength_location: "Catalog-predicted position",
        quality_status: "clear",
        quality_flag_names: [],
        display_scale_mode: "shared",
        source_url: "https://irsa.ipac.caltech.edu/a.fits",
        processing: {
          processing_version: "perigee-processor 0.3.0",
          file_sha256: "abc",
          registration_method: "wcs",
          display_scale_method: "asinh",
          marker_kind: "catalog_prediction",
        },
      },
    ],
    claim: "A and B are a fair pair — same detector, ±0.001 µm.",
    observations: "Line one\nLine two with “quotes”.",
    uncertainty: "Quick release may be reprocessed.",
    sources: [{ label: "IRSA", url: "https://irsa.ipac.caltech.edu/Missions/spherex.html" }],
  };
}

function caseCard() {
  return createEvidenceCard({
    case_id: "fair_comparison",
    preset_id: "epsilon_indi_b",
    title: "Is this a fair comparison?",
    case_limitations: CASE_LIMS,
    app_version: "t",
    data_origin: "api",
    now: NOW,
  });
}

describe("evidence card limitations and title: construction", () => {
  it("copies case and frame limitations verbatim, dropping only exact duplicates", () => {
    let card = createEvidenceCard({
      case_id: "fair_comparison",
      preset_id: "epsilon_indi_b",
      title: "Is this a fair comparison?",
      case_limitations: [CASE_LIMS[0]!, CASE_LIMS[1]!, CASE_LIMS[0]!, ` ${CASE_LIMS[1]}`],
      app_version: "t",
      data_origin: "api",
      now: NOW,
    });
    card = toggleEvidenceFrame(card, frame("A1", 3, 1, [FRAME_LIMS[0]!, FRAME_LIMS[0]!, FRAME_LIMS[1]!]), "A", NOW);
    // A near-duplicate (leading space) is different wording: kept as is.
    expect(card.case_limitations).toEqual([CASE_LIMS[0], CASE_LIMS[1], ` ${CASE_LIMS[1]}`]);
    expect(card.title).toBe("Is this a fair comparison?");
    expect(card.frames[0]?.limitations).toEqual(FRAME_LIMS);
  });

  it("records an empty list when the API reports no frame limitations", () => {
    const card = toggleEvidenceFrame(caseCard(), frame("A1", 3, 1, []), "A", NOW);
    expect(card.frames[0]?.limitations).toEqual([]);
  });

  it("gives coordinate-search cards frame limitations only and a null title", () => {
    let card = createEvidenceCard({
      query: { ra_deg: 83.82, dec_deg: -5.39, fov_arcmin: 6 },
      case_limitations: CASE_LIMS,
      app_version: "t",
      data_origin: "api",
      now: NOW,
    });
    card = toggleEvidenceFrame(card, frame("Q1", 2, 5, FRAME_LIMS), null, NOW);
    const out = JSON.parse(serializeEvidenceCard(card));
    expect(out.title).toBeNull();
    expect(out.case_limitations).toBeNull();
    expect(out.frames[0].limitations).toEqual(FRAME_LIMS);
    expect(printedLimitations(card)).toEqual(FRAME_LIMS);
  });
});

describe("evidence card limitations and title: export serialization", () => {
  it("exports case limitations after the learner's uncertainty, and per-frame lists", () => {
    let card = toggleEvidenceFrame(caseCard(), frame("A1", 3, 1, [CASE_LIMS[1]!, FRAME_LIMS[0]!]), "A", NOW);
    card = updateEvidenceText(card, "uncertainty", "Mine.", NOW);
    const json = serializeEvidenceCard(card);
    const out = JSON.parse(json);
    const keys = Object.keys(out);
    expect(keys.indexOf("title")).toBe(keys.indexOf("preset_id") + 1);
    expect(keys.indexOf("case_limitations")).toBe(keys.indexOf("uncertainty") + 1);
    expect(out.uncertainty).toBe("Mine.");
    expect(out.title).toBe("Is this a fair comparison?");
    expect(out.case_limitations).toEqual(CASE_LIMS);
    expect(out.frames[0].limitations).toEqual([CASE_LIMS[1], FRAME_LIMS[0]]);
    expect(printedLimitations(card)).toEqual(CASE_LIMS);
    expect(json).not.toMatch(/data:image|base64|\.png"/i);
    expect(out).toEqual(card);
    expect(validateEvidenceCard(out).ok).toBe(true);
  });

  it("adds the case's limitations at export time when the card was made without them", () => {
    const legacy = validateEvidenceCard(legacyV1Card());
    if (!legacy.ok) throw new Error("legacy card invalid");
    const content = { case_id: "fair_comparison", title: "Is this a fair comparison?", limitations: CASE_LIMS };
    const out = withCaseContext(legacy.card, content);
    expect(out.case_limitations).toEqual(CASE_LIMS);
    expect(out.title).toBe("Is this a fair comparison?");
    expect(withCaseContext(out, content)).toBe(out);
    expect(withCaseContext(legacy.card, { ...content, case_id: "moving_neighbor" })).toBe(legacy.card);
    const query = createEvidenceCard({ app_version: "t", data_origin: "api" });
    expect(withCaseContext(query, content)).toBe(query);
  });

  const printSection = (card: ReturnType<typeof caseCard>) => {
    const html = renderToStaticMarkup(
      createElement(Notebook, {
        card,
        onChange: () => {},
        onRemoveFrame: () => {},
        saveState: { kind: "idle" },
        caseContent: null,
      }),
    );
    return html.slice(html.indexOf("print-provenance"));
  };

  it("prints the case's limitations once each for a case card, beside the provenance", () => {
    const card = toggleEvidenceFrame(caseCard(), frame("A1", 3, 1, [CASE_LIMS[1]!, FRAME_LIMS[0]!]), "A", NOW);
    const section = printSection(card);
    expect(section).toContain("Stated limitations");
    expect(section).toContain("(from the case)");
    for (const l of CASE_LIMS) expect(section.split(l).length - 1).toBe(1);
    // Frame-only wording stays in the JSON, not the short printed list.
    expect(section).not.toContain(FRAME_LIMS[0]!);
    // Existing print provenance is still there.
    expect(section).toContain("Observation ID: A1");
    expect(section).toContain("Source: https://irsa.ipac.caltech.edu/A1.fits");
  });

  it("prints frame limitations once each for a coordinate-search card", () => {
    let card = createEvidenceCard({ query: { ra_deg: 83.82, dec_deg: -5.39, fov_arcmin: 6 }, app_version: "t", data_origin: "api", now: NOW });
    card = toggleEvidenceFrame(card, frame("Q1", 2, 5, FRAME_LIMS), null, NOW);
    card = toggleEvidenceFrame(card, frame("Q2", 2, 6, [FRAME_LIMS[1]!]), null, NOW);
    const section = printSection(card);
    expect(section).toContain("(from the observation records)");
    for (const l of FRAME_LIMS) expect(section.split(l).length - 1).toBe(1);
  });

  it("prints nothing extra when no limitations are known", () => {
    const card = toggleEvidenceFrame(createEvidenceCard({ app_version: "t", data_origin: "api" }), frame("Q1", 2, 5), null, NOW);
    expect(printSection(card)).not.toContain("Stated limitations");
  });

  it("prints case limitations from case content for an older card", () => {
    const legacy = validateEvidenceCard(legacyV1Card());
    if (!legacy.ok) throw new Error("legacy card invalid");
    const content = { case_id: "fair_comparison", title: "Fair", limitations: CASE_LIMS, frames: [], steps: [] } as unknown as CaseContent;
    const html = renderToStaticMarkup(
      createElement(Notebook, {
        card: legacy.card,
        onChange: () => {},
        onRemoveFrame: () => {},
        saveState: { kind: "restored" },
        caseContent: content,
      }),
    );
    expect(html).toContain(CASE_LIMS[0]!);
  });
});

describe("evidence card limitations and title: v1 cards", () => {
  it("loads a stored v1 card without the new fields, keeping every existing field unchanged", () => {
    const legacy = legacyV1Card();
    const storage = new MemoryStorage();
    storage.setItem(
      STORAGE_KEY,
      JSON.stringify({ version: 1, cards: [legacy], contexts: { "api:preset:epsilon_indi_b": legacy.id } }),
    );
    const store = loadStore(storage);
    expect(store.cards).toHaveLength(1);
    expect(store.contexts["api:preset:epsilon_indi_b"]).toBe(legacy.id);
    const card = store.cards[0]!;
    for (const [k, v] of Object.entries(legacy)) {
      if (k !== "frames") expect(card[k as keyof typeof card]).toEqual(v);
    }
    const { limitations, rendering, ...frameRest } = card.frames[0]!;
    expect(frameRest).toEqual(legacy.frames[0]);
    expect(limitations).toBeNull();
    expect(rendering).toBeNull();
    expect(card.title).toBeNull();
    expect(card.case_limitations).toBeNull();
    expect(card.schema_version).toBe(1);

    const out = JSON.parse(serializeEvidenceCard(card));
    expect(out.claim).toBe(legacy.claim);
    expect(out.observations).toBe(legacy.observations);
    expect(out.title).toBeNull();
    expect(out.case_limitations).toBeNull();
    expect(out.frames[0].limitations).toBeNull();
    expect(validateEvidenceCard(out).ok).toBe(true);
    // A raw legacy object (e.g. a session draft) serializes with the new keys too.
    expect(JSON.parse(serializeEvidenceCard(legacy as never)).case_limitations).toBeNull();
  });

  it("keeps a card whose new fields are malformed, nulling only those fields", () => {
    const bad = { ...legacyV1Card(), title: 42, case_limitations: "nope" };
    bad.frames[0] = { ...bad.frames[0]!, limitations: { x: 1 } } as never;
    const v = validateEvidenceCard(bad);
    expect(v.ok).toBe(true);
    if (v.ok) {
      expect(v.card.title).toBeNull();
      expect(v.card.case_limitations).toBeNull();
      expect(v.card.frames[0]?.limitations).toBeNull();
      expect(v.card.claim).toBe(bad.claim);
    }
  });

  it("fills a reopened card's missing title and limitations without touching learner text", () => {
    const legacy = validateEvidenceCard(legacyV1Card());
    if (!legacy.ok) throw new Error("legacy card invalid");
    const fresh = createEvidenceCard({
      case_id: "fair_comparison",
      preset_id: "epsilon_indi_b",
      title: "Is this a fair comparison?",
      case_limitations: CASE_LIMS,
      app_version: "0.2.0",
      data_origin: "api",
    });
    const filled = fillCardContext(legacy.card, fresh);
    expect(filled.title).toBe("Is this a fair comparison?");
    expect(filled.case_limitations).toEqual(CASE_LIMS);
    expect({ ...filled, title: null, case_limitations: null }).toEqual(legacy.card);
    // Idempotent, and existing values win.
    expect(fillCardContext(filled, { ...fresh, title: "Other" })).toBe(filled);
    // Never borrows another investigation's limitations.
    expect(fillCardContext(legacy.card, { ...fresh, case_id: "moving_neighbor" })).toBe(legacy.card);

    // Pair frames attached before the field gain limitations when the same pair is re-attached.
    const a = frame("2026W18_1A_0516_1", 3, 61159.5, FRAME_LIMS);
    const withFrames = attachPair(filled, [{ frame: a, ref: "A" }], ["A", "B"], NOW);
    expect(withFrames.frames[0]?.limitations).toEqual(FRAME_LIMS);
    expect(withFrames.updated_at_utc).toBe(legacy.card.updated_at_utc);
    expect(withFrames.claim).toBe(legacy.card.claim);
    expect(attachPair(withFrames, [{ frame: a, ref: "A" }], ["A", "B"], NOW)).toBe(withFrames);
  });
});
