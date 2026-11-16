import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { normalizeFrameRecord } from "../src/api/client";
import type { CaseContent } from "../src/api/types";
import { evidencePreviewFrame } from "../src/components/EvidencePreview";
import {
  attachPair, createEvidenceCard, fillFrameRendering, frameToEvidence, normalizeEvidenceCard,
  serializeEvidenceCard, snapshotFrameRendering, validateEvidenceCard, withReferenceEvidence,
} from "../src/evidence/card";

const content = JSON.parse(readFileSync(new URL("../../backend/content/cases/moving_neighbor.json", import.meta.url), "utf8")) as CaseContent;
const selected = content.frames.filter(({ ref }) => ref === "A" || ref === "C").map((ref) => ({
  ref: ref.ref,
  frame: normalizeFrameRecord(JSON.parse(readFileSync(new URL(`../../backend/content/presets/barnards_star/case-moving_neighbor/${ref.frame_key}.json`, import.meta.url), "utf8"))),
}));
const record = selected[0]!.frame;
const card = attachPair({
  ...createEvidenceCard({ case_id: content.case_id, preset_id: content.target_id, app_version: "test", data_origin: "api" }),
  claim: "My explanation, not the reference.", observations: "A glow moves.\nThe field stars stay close.",
  uncertainty: "The bright center is saturated.",
}, selected, ["A", "B", "C"]);

describe("exported rendering snapshots", () => {
  it("round-trips the full supplied stretch, grid, image references and actual cutout URL", () => {
    const out = JSON.parse(serializeEvidenceCard(card));
    const saved = out.frames[0].rendering;
    expect(saved.display_scale).toEqual(record.display_scale);
    expect(saved.registration).toEqual(record.registration);
    expect(saved.image).toEqual(record.image);
    expect(saved.flag_image).toEqual(record.flag_image);
    expect(saved.cutout_url).toBe(record.provenance?.cutout_url);
    expect(saved.display_scale.low).toBeTypeOf("number");
    expect(saved.display_scale.asinh_softening).toBeTypeOf("number");
    expect(saved.registration.scale_arcsec_per_px).toBeTypeOf("number");
    expect(validateEvidenceCard(out)).toEqual({ ok: true, card: out });
    expect(JSON.parse(serializeEvidenceCard(out))).toEqual(out);
    expect(saved.display_scale).not.toBe(record.display_scale);
    expect(saved.registration).not.toBe(record.registration);
    expect(out.claim).toBe(card.claim);
  });

  it("resolves portable asset URLs using the active API base and never invents a cutout URL", () => {
    const available = snapshotFrameRendering(record, { baseUrl: "https://viewer.example/investigation", apiBase: "https://api.example/api/v1" });
    expect(available.image_url).toBe(`https://api.example${record.image!.src}`);
    expect(available.flag_image_url).toBe(`https://api.example${record.flag_image!.src}`);
    expect(available.image?.src).toBe(record.image!.src);
    const missing = snapshotFrameRendering({ ...record, provenance: { original_url: record.source_url } }, { baseUrl: "https://viewer.example/investigation", apiBase: "/api/v1" });
    expect(missing.image_url).toBe(`https://viewer.example${record.image!.src}`);
    expect(missing.cutout_url).toBeNull();
    expect(snapshotFrameRendering({ ...record, image: { ...record.image!, src: "data:image/png;base64,AAAA" } }).image).toBeNull();
  });

  it("loads older cards with unknown snapshots without changing notes, identities or dates", () => {
    const legacy = { ...card, frames: card.frames.map(({ rendering: _rendering, ...frame }) => frame) };
    const { reference_evidence: _reference, ...older } = legacy;
    const normalized = normalizeEvidenceCard(older);
    expect(normalized.reference_evidence).toBeNull();
    for (const [index, frame] of normalized.frames.entries()) {
      const { rendering, ...unchanged } = frame;
      expect(rendering).toBeNull();
      expect(unchanged).toEqual(legacy.frames[index]);
    }
    expect(normalized.claim).toBe(legacy.claim);
    expect(normalized.observations).toBe(legacy.observations);
    expect(normalized.uncertainty).toBe(legacy.uncertainty);
    expect(normalized.updated_at_utc).toBe(legacy.updated_at_utc);
  });

  it("keeps legacy rendering unknown even when source bytes and processing identity match", () => {
    const legacy = { ...card, frames: [{ ...card.frames[0]!, rendering: null }] };
    expect(fillFrameRendering(legacy, [record])).toBe(legacy);
    expect(evidencePreviewFrame(legacy.frames[0]!, [record])).toBeUndefined();
    const mismatches = [
      { ...record, source_url: "https://example.test/different.fits" },
      { ...record, provenance: { ...record.provenance, file_sha256: "different" } },
      { ...record, provenance: { ...record.provenance, processing_version: "different" } },
      { ...record, registration: { ...record.registration, method: "different" } },
      { ...record, display_scale: { ...record.display_scale!, method: "different" } },
    ];
    for (const changed of mismatches) expect(fillFrameRendering(legacy, [changed])).toBe(legacy);
    const withoutHash = { ...legacy, frames: [{ ...legacy.frames[0]!, processing: { ...legacy.frames[0]!.processing!, file_sha256: null } }] };
    expect(fillFrameRendering(withoutHash, [record])).toBe(withoutHash);
    expect(evidencePreviewFrame(withoutHash.frames[0]!, [record])).toBeUndefined();
  });

  it("never backfills changed numeric settings as a legacy card's original rendering", () => {
    const { rendering: _rendering, ...oldFrame } = card.frames[0]!;
    const legacy = { ...card, frames: [oldFrame] };
    const changes = [
      { ...record, display_scale: { ...record.display_scale!, low: Number(record.display_scale!.low) + 1, high: Number(record.display_scale!.high) + 5 } },
      { ...record, registration: { ...record.registration, scale_arcsec_per_px: Number(record.registration!.scale_arcsec_per_px) + 1 } },
    ];
    for (const changed of changes) {
      expect(changed.provenance?.file_sha256).toBe(oldFrame.processing?.file_sha256);
      expect(changed.provenance?.processing_version).toBe(oldFrame.processing?.processing_version);
      expect(changed.display_scale?.method).toBe(oldFrame.processing?.display_scale_method);
      expect(changed.registration?.method).toBe(oldFrame.processing?.registration_method);
      const reopened = fillFrameRendering(normalizeEvidenceCard(legacy), [changed]);
      const exported = JSON.parse(serializeEvidenceCard(reopened));
      expect(exported.frames[0].rendering).toBeNull();
      expect(exported.frames[0].source_url).toBe(oldFrame.source_url);
      expect(exported.claim).toBe(legacy.claim);
      expect(exported.observations).toBe(legacy.observations);
      expect(exported.uncertainty).toBe(legacy.uncertainty);
      expect(exported.updated_at_utc).toBe(legacy.updated_at_utc);
      expect(evidencePreviewFrame(reopened.frames[0]!, [changed])).toBeUndefined();
    }
  });

  it("rejects changed numeric display limits or grid despite identical hash and method names", () => {
    const frame = frameToEvidence(record, "A");
    expect(evidencePreviewFrame(frame, [record])).toBe(record);
    const mismatches = [
      { ...record, display_scale: { ...record.display_scale!, low: Number(record.display_scale!.low) + 1 } },
      { ...record, display_scale: { ...record.display_scale!, asinh_softening: Number(record.display_scale!.asinh_softening) + 1 } },
      { ...record, registration: { ...record.registration, center_ra_deg: Number(record.registration!.center_ra_deg) + 1 } },
      { ...record, registration: { ...record.registration, scale_arcsec_per_px: Number(record.registration!.scale_arcsec_per_px) + 1 } },
      { ...record, image: { ...record.image!, src: "/api/v1/different-rendering.png" } },
      { ...record, flag_image: { ...record.flag_image!, src: "/api/v1/different-flags.png" } },
    ];
    for (const changed of mismatches) {
      expect(evidencePreviewFrame(frame, [changed])).toBeUndefined();
      expect(fillFrameRendering(card, [changed])).toBe(card);
    }
  });

  it("keeps old malformed optional metadata unknown without discarding a learner's card", () => {
    const raw = { ...card, frames: [{ ...card.frames[0], rendering: "not a snapshot" }], reference_evidence: { guide: "broken" } };
    const result = validateEvidenceCard(raw);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.card.frames[0]!.rendering).toBeNull();
    expect(result.card.reference_evidence).toBeNull();
    expect(result.card.claim).toBe(card.claim);
  });
});

describe("revealed reference export", () => {
  it("exports no unseen guide, then preserves the revealed reference after later content changes", () => {
    expect(withReferenceEvidence(card, content)).toBe(card);
    expect(JSON.parse(serializeEvidenceCard(card)).reference_evidence).toBeNull();
    const revealed = withReferenceEvidence({ ...card, reference_shown: true }, content);
    expect(revealed.reference_evidence?.guide).toEqual(content.conclusion_guide);
    const saved = JSON.parse(serializeEvidenceCard(revealed));
    expect(validateEvidenceCard(saved).ok).toBe(true);
    expect(saved.reference_evidence.content_version).toBe(content.content_version);
    expect(saved.reference_evidence.source_frames.map((frame: { ref: string }) => frame.ref)).toEqual(["A", "C"]);
    expect(saved.claim).toBe(card.claim);
    expect(withReferenceEvidence(saved, { ...content, content_version: "later", conclusion_guide: { supported: ["A revised guide"] } })).toBe(saved);
    expect(JSON.parse(serializeEvidenceCard(saved)).reference_evidence).toEqual(revealed.reference_evidence);
  });
});
