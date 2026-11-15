import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { normalizeFrameRecord } from "../src/api/client";
import type { CaseContent } from "../src/api/types";
import { EvidencePreview, evidencePreviewFrame } from "../src/components/EvidencePreview";
import { Notebook } from "../src/components/Notebook";
import { attachPair, createEvidenceCard, serializeEvidenceCard } from "../src/evidence/card";

const content = JSON.parse(readFileSync(new URL("../../backend/content/cases/moving_neighbor.json", import.meta.url), "utf8")) as CaseContent;
const records = content.frames.map((ref) => ({ ref: ref.ref, frame: normalizeFrameRecord(JSON.parse(readFileSync(
  new URL(`../../backend/content/presets/barnards_star/case-moving_neighbor/${ref.frame_key}.json`, import.meta.url), "utf8"),
)) }));
const card = attachPair({
  ...createEvidenceCard({ case_id: content.case_id, title: content.title, preset_id: content.target_id, app_version: "test", data_origin: "api" }),
  observations: "The glow shifts north.\nNearby stars stay in place.",
  claim: "The comparison is consistent with motion.",
  uncertainty: "The center is saturated.",
  reviewed_step_ids: content.steps.map((step) => step.id),
}, records.filter(({ ref }) => ref === "A" || ref === "C"), records.map(({ ref }) => ref));

function renderNotebook(value = card) {
  return renderToStaticMarkup(createElement(Notebook, {
    card: value, caseContent: content, previewFrames: records.map(({ frame }) => frame),
    onChange() {}, onRemoveFrame() {}, saveState: { kind: "saved", at: "now" },
  }));
}

describe("evidence completion preview", () => {
  it("offers a preview only when the exported record has observations and all three notes", () => {
    expect(renderNotebook()).toContain("Preview your evidence card");
    expect(renderNotebook({ ...card, claim: " " })).not.toContain("Preview your evidence card");
    expect(renderNotebook({ ...card, frames: [] })).not.toContain("Preview your evidence card");
    expect(renderNotebook()).not.toContain("Reference answer (from the case)");
  });

  it("renders the same learner text and attached source identities without modifying the export", () => {
    const before = serializeEvidenceCard(card);
    const html = renderToStaticMarkup(createElement(EvidencePreview, {
      id: "test", card, frames: records.map(({ frame }) => frame), status: "Saved on this device",
      onEdit() {}, onPrint() {}, onDownload() {},
    }));
    expect(html).toContain(card.observations);
    expect(html).toContain(card.claim);
    expect(html).toContain(card.uncertainty);
    for (const frame of card.frames) {
      expect(html).toContain(frame.observation_id);
      expect(html).toContain(frame.source_url.replaceAll("&", "&amp;"));
      expect(html).toContain(`Open the archive source for Image ${frame.ref}`);
    }
    expect(html).not.toContain(records.find(({ ref }) => ref === "B")!.frame.observation_id);
    expect(html).toContain("This preview does not assess your conclusion.");
    expect(html).toContain("Print / save PDF");
    expect(html).toContain("Download evidence JSON");
    expect(serializeEvidenceCard(card)).toBe(before);
    expect(JSON.parse(before).frames[0]).not.toHaveProperty("image");
  });

  it("does not substitute another rendering or stale archive bytes with the same frame key", () => {
    const frame = card.frames[0]!;
    const matching = records.find(({ frame: record }) => record.frame_key === frame.frame_key)!.frame;
    expect(evidencePreviewFrame(frame, [matching])).toBe(matching);
    expect(evidencePreviewFrame(frame, [{ ...matching, display_scale: { mode: "per_frame" } }])).toBeUndefined();
    expect(evidencePreviewFrame(frame, [{ ...matching, provenance: { ...matching.provenance, file_sha256: "different" } }])).toBeUndefined();
    expect(evidencePreviewFrame(frame, [{ ...matching, source_url: "https://example.org/different.fits" }])).toBeUndefined();
    expect(evidencePreviewFrame(frame, [{ ...matching, provenance: { ...matching.provenance, processing_version: "different" } }])).toBeUndefined();
    expect(evidencePreviewFrame(frame, [{ ...matching, registration: { ...matching.registration, method: "different" } }])).toBeUndefined();
    expect(evidencePreviewFrame(frame, [{ ...matching, display_scale: { ...matching.display_scale!, method: "different" } }])).toBeUndefined();
    expect(evidencePreviewFrame(frame, [{ ...matching, provenance: { ...matching.provenance, processing_version: undefined } }])).toBeUndefined();
  });

  it("does not describe the Epsilon A+C products as sharing a comparison contrast", () => {
    const epsilon = JSON.parse(readFileSync(new URL("../../backend/content/cases/fair_comparison.json", import.meta.url), "utf8")) as CaseContent;
    const selected = epsilon.frames.filter(({ ref }) => ref === "A" || ref === "C").map((ref) => ({
      ref: ref.ref,
      frame: normalizeFrameRecord(JSON.parse(readFileSync(new URL(`../../backend/content/presets/epsilon_indi_b/case-fair_comparison/${ref.frame_key}.json`, import.meta.url), "utf8"))),
    }));
    const epsilonCard = attachPair({ ...card, frames: [], case_id: epsilon.case_id, title: epsilon.title }, selected, ["A", "C"]);
    expect(epsilonCard.frames.map((frame) => frame.display_scale_mode)).toEqual(["shared", "per_frame"]);
    const html = renderToStaticMarkup(createElement(EvidencePreview, {
      id: "epsilon", card: epsilonCard, frames: selected.map(({ frame }) => frame), status: "Saved on this device",
      onEdit() {}, onPrint() {}, onDownload() {},
    }));
    expect(html).toContain("Display contrast: shared-scale product.");
    expect(html).toContain("Display contrast: set for this image.");
    expect(html).toContain("It does not establish a common contrast for every image selected here.");
    expect(html).not.toContain("shared across the comparison");
  });
});
