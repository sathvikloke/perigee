// Regression checks (worker 23) for behaviour near confirmed fixes that the
// existing tests do not pin. Inputs are real processor-A products committed in
// backend/content (perigee-processor-a/0.1.2), not hand-written fixtures.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { normalizeFrameRecord, runWithConcurrency } from "../src/api/client";
import {
  CLAIM_MAX,
  TEXT_MAX,
  createEvidenceCard,
  serializeEvidenceCard,
  toggleEvidenceFrame,
  updateEvidenceText,
  validateEvidenceCard,
} from "../src/evidence/card";
import { formatDateShort } from "../src/lib/format";

const product = (rel: string): unknown =>
  JSON.parse(readFileSync(new URL(`../../backend/content/presets/${rel}`, import.meta.url), "utf8"));

describe("evidence export from real processor-A records", () => {
  it("carries identity, detector/release, UTC time, wavelength, source, processing and the full notes", () => {
    const a = normalizeFrameRecord(product("epsilon_indi_b/case-fair_comparison/2026W18_1A_0516_1_D3.json"));
    const c = normalizeFrameRecord(product("epsilon_indi_b/case-fair_comparison/2026W18_1A_0516_1_D6.json"));
    let card = createEvidenceCard({ case_id: "fair_comparison", preset_id: "epsilon_indi_b", app_version: "t", data_origin: "api" });
    card = toggleEvidenceFrame(card, c, "C");
    card = toggleEvidenceFrame(card, a, "A");
    const claim = "c".repeat(CLAIM_MAX);
    const obs = `${"o".repeat(TEXT_MAX - 2)}\n¶`;
    const unc = `${"u".repeat(TEXT_MAX - 1)}✓`;
    card = updateEvidenceText(card, "claim", claim);
    card = updateEvidenceText(card, "observations", obs);
    card = updateEvidenceText(card, "uncertainty", unc);

    const parsed = JSON.parse(serializeEvidenceCard(card));
    expect(validateEvidenceCard(parsed).ok).toBe(true);
    expect(parsed.claim).toBe(claim);
    expect(parsed.observations).toBe(obs);
    expect(parsed.uncertainty).toBe(unc);

    expect(parsed.frames.map((f: { frame_key: string }) => f.frame_key).sort()).toEqual([
      "2026W18_1A_0516_1_D3",
      "2026W18_1A_0516_1_D6",
    ]);
    for (const f of parsed.frames) {
      expect(f.frame_id).toBe(f.frame_key);
      expect([3, 6]).toContain(f.detector);
      expect(f.collection_id).toBe("spherex_dr1");
      expect(f.observed_at_utc).toMatch(/^2026-04-29T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/);
      expect(typeof f.wavelength_um).toBe("number");
      expect(f.source_url).toMatch(/^https:\/\/irsa\.ipac\.caltech\.edu\/ibe\/data\/spherex\/dr1\/.+\.fits$/);
      expect(f.processing.processing_version).toBe("perigee-processor-a/0.1.2");
      expect(f.processing.file_sha256).toMatch(/^[0-9a-f]{64}$/);
      expect(f.processing.registration_method).toEqual(expect.any(String));
      expect(f.processing.display_scale_method).toEqual(expect.any(String));
      expect(f.processing.marker_kind).toBe("catalog_prediction");
    }
    const d3 = parsed.frames.find((f: { detector: number }) => f.detector === 3);
    expect(d3.wavelength_um).toBeCloseTo(2.3232, 4); // case JSON value, tolerance 1e-4
  });
});

describe("timestamps are parsed as UTC whether or not they carry Z", () => {
  // Processor A writes a trailing Z; case JSON and processor B do not. Times
  // near midnight show the bug in any non-UTC local zone.
  it.each([
    ["2026-04-29T00:30:00.000", "2026-04-29T00:30:00.000Z"],
    ["2026-04-29T23:30:00.000", "2026-04-29T23:30:00.000Z"],
  ])("%s and %s give the same UTC date", (bare, zulu) => {
    expect(formatDateShort(bare)).toBe("29 Apr 2026");
    expect(formatDateShort(zulu)).toBe("29 Apr 2026");
  });
});

describe("a failed frame does not move the others", () => {
  it("each result lands in its own index slot regardless of failures and finish order", async () => {
    const keys = ["a", "b", "c", "d", "e"];
    const slots: (string | null)[] = keys.map(() => null);
    await runWithConcurrency(keys, 2, async (k, i) => {
      await new Promise((r) => setTimeout(r, (5 - i) * 3));
      if (k === "b") throw new Error("UPSTREAM_UNAVAILABLE");
      slots[i] = k;
    });
    expect(slots).toEqual(["a", null, "c", "d", "e"]);
  });
});
