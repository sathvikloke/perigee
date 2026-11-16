import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { normalizeFrameRecord } from "../src/api/client";
import type { CaseContent } from "../src/api/types";
import { ReferenceReview, hasWiseControlEvidence, referenceFinding } from "../src/components/ReferenceReview";
import { createEvidenceCard, frameToEvidence, type EvidenceCard } from "../src/evidence/card";
import { buildReferenceEvidence, normalizeReferenceEvidence, referenceEvidenceMatchesCard } from "../src/evidence/referenceEvidence";

function publishedCase(id: string) {
  const content = JSON.parse(readFileSync(new URL(`../../backend/content/cases/${id}.json`, import.meta.url), "utf8")) as CaseContent;
  const required = content.evidence_requirements!.must_include_refs_any_of![0];
  const card = createEvidenceCard({ case_id: id, preset_id: content.target_id, app_version: "test", data_origin: "api" });
  card.frames = content.frames.filter((f) => required.includes(f.ref)).map((f) => frameToEvidence(normalizeFrameRecord(JSON.parse(readFileSync(
    new URL(`../../backend/content/presets/${content.target_id}/case-${id}/${f.frame_key}.json`, import.meta.url), "utf8",
  ))), f.ref));
  card.claim = "My own explanation stays editable.";
  card.reference_shown = true;
  return { content, card };
}

const wise = publishedCase("wise_0855_quality_trap");
const render = (content = wise.content, card = wise.card) => renderToStaticMarkup(createElement(ReferenceReview, { id: "test", caseContent: content, card }));
const escaped = (text: string) => renderToStaticMarkup(createElement("span", null, text)).slice(6, -7);

describe("compact reference review", () => {
  it.each(["moving_neighbor", "fair_comparison", "wise_0855_quality_trap"])("shows a supported takeaway for the published %s pair", (id) => {
    const { content, card } = publishedCase(id);
    const finding = referenceFinding(content, card);
    expect(finding).not.toBeNull();
    expect(render(content, card)).toContain(escaped(finding!.title));
  });

  it("keeps every scientific statement and the example in a closed disclosure", () => {
    const html = render();
    expect(html).toContain('<details class="reference-details"><summary>Full reference and scientific limits');
    expect(html).not.toMatch(/<details[^>]*\sopen(?:[=>\s])/);
    for (const text of [...wise.content.conclusion_guide!.supported!, ...wise.content.conclusion_guide!.not_supported!, wise.content.conclusion_guide!.example_claim!]) {
      expect(html).toContain(escaped(text));
    }
    expect(html.indexOf("The jumping dot is unreliable evidence of motion")).toBeLessThan(html.indexOf("Full reference and scientific limits"));
    expect(html).toContain("does not grade your answer");
    expect(html).toContain('tabindex="-1" aria-labelledby="test-reference-title"');
  });

  it("restricts measured WISE controls to the actual retained source bytes", () => {
    expect(hasWiseControlEvidence(wise.content, wise.card)).toBe(true);
    const html = render();
    expect(html).toContain("5.36 arcsec");
    expect(html).toContain("5.38 arcsec");
    const replaced: EvidenceCard = { ...wise.card, frames: wise.card.frames.map((frame, i) => i ? frame : {
      ...frame, processing: { ...frame.processing!, file_sha256: "different-source-bytes" },
    }) };
    expect(hasWiseControlEvidence(wise.content, replaced)).toBe(false);
    expect(render(wise.content, replaced)).not.toContain("5.36 arcsec");
  });

  it("does not apply an archived finding to another pair, revision, or fixture", () => {
    const wrongPair = { ...wise.card, frames: wise.card.frames.map((f) => f.ref === "B" ? { ...f, frame_key: "another-observation" } : f) };
    const revisedCase = { ...wise.content, content_version: "future-revision" };
    expect(referenceFinding(wise.content, wrongPair)).toBeNull();
    expect(referenceFinding(revisedCase, wise.card)).toBeNull();
    expect(referenceFinding(wise.content, { ...wise.card, data_origin: "fixture" })).toBeNull();
    expect(render(wise.content, wrongPair)).not.toContain("5.36 arcsec");
    expect(render(revisedCase)).toContain(escaped(wise.content.conclusion_guide!.supported![0]));
  });

  it("retains future case guidance without inventing a result", () => {
    const future: CaseContent = { ...wise.content, case_id: "future-case", conclusion_guide: { supported: ["The observations support this new finding."], not_supported: ["Keep this important limit."], example_claim: "An example for the new case." } };
    const html = render(future, { ...wise.card, case_id: "future-case" });
    expect(html).toContain("The observations support this new finding.");
    expect(html).toContain("Keep this important limit.");
    expect(html).not.toContain("jumping dot");
    expect(html).not.toContain("5.36 arcsec");
  });

  it("withholds reference content and snapshots until the learner requests them", () => {
    const unrevealed = { ...wise.card, reference_shown: false };
    expect(buildReferenceEvidence(unrevealed, wise.content)).toBeNull();
    expect(hasWiseControlEvidence(wise.content, unrevealed)).toBe(false);
    expect(render(wise.content, unrevealed)).toBe("");
  });

  it("snapshots the complete reference, pinned sources and qualified detector control", () => {
    const snapshot = buildReferenceEvidence(wise.card, wise.content)!;
    expect(snapshot.case_id).toBe(wise.content.case_id);
    expect(snapshot.content_version).toBe(wise.content.content_version);
    expect(snapshot.guide).toEqual(wise.content.conclusion_guide);
    expect(snapshot.guide.supported).not.toBe(wise.content.conclusion_guide!.supported);
    expect(snapshot.source_review_urls.length).toBeGreaterThan(0);
    for (const url of snapshot.source_review_urls) expect(url).toMatch(/\/blob\/[a-f0-9]{40}\//);
    expect(snapshot.wise_control).toMatchObject({
      detector_pixel: [1709, 1364], mapped_sky_shift_arcsec: 5.36, predicted_sky_shift_arcsec: 5.38,
      field_star_count: 3, max_field_star_sky_shift_arcsec: 0.76,
    });
    expect(snapshot.wise_control!.measurement_description).toContain("mapped-pixel separation");
    expect(snapshot.wise_control!.measurement_description).toContain("not a precision measurement");
    expect(snapshot.wise_control!.source_frames).toHaveLength(2);
    expect(render()).toContain("Same pixel, mapped sky separation");
    expect(render()).not.toContain("Measured sky-position shift");
  });

  it("rejects snapshots for another case, observation, source bytes or fixture", () => {
    expect(buildReferenceEvidence({ ...wise.card, case_id: "another-case" }, wise.content)).toBeNull();
    expect(buildReferenceEvidence({ ...wise.card, data_origin: "fixture" }, wise.content)).toBeNull();
    for (const changed of [{ observation_id: "wrong-observation" }, { source_url: "https://example.com/wrong.fits" }, { processing: { ...wise.card.frames[0].processing!, file_sha256: "wrong-bytes" } }]) {
      const card = { ...wise.card, frames: [{ ...wise.card.frames[0], ...changed }, ...wise.card.frames.slice(1)] };
      expect(buildReferenceEvidence(card, wise.content)).toBeNull();
    }
  });

  it("keeps the saved guide when a later case revision supplies another answer", () => {
    const snapshot = buildReferenceEvidence(wise.card, wise.content)!;
    const card = { ...wise.card, reference_evidence: snapshot };
    const updated = { ...wise.content, content_version: "next-version", conclusion_guide: { supported: ["A later reference answer."] } };
    expect(normalizeReferenceEvidence(JSON.parse(JSON.stringify(snapshot)))).toEqual(snapshot);
    const html = render(updated, card);
    expect(html).toContain(escaped(snapshot.guide.example_claim!));
    expect(html).not.toContain("A later reference answer.");
    expect(html).toContain("5.36 arcsec");
    expect(referenceEvidenceMatchesCard(snapshot, { ...card, frames: card.frames.slice(0, 1) })).toBe(false);
  });

  it("rejects malformed saved references without changing valid historical values", () => {
    const snapshot = buildReferenceEvidence(wise.card, wise.content)!;
    expect(normalizeReferenceEvidence({ ...snapshot, guide: { ...snapshot.guide, supported: [3] } })).toBeNull();
    expect(normalizeReferenceEvidence({ ...snapshot, source_review_urls: ["javascript:bad"] })).toBeNull();
    expect(normalizeReferenceEvidence({ ...snapshot, wise_control: { ...snapshot.wise_control, mapped_sky_shift_arcsec: NaN } })).toBeNull();
    const historical = { ...snapshot, content_version: "older-reviewed-version", wise_control: { ...snapshot.wise_control!, mapped_sky_shift_arcsec: 5.35 } };
    expect(normalizeReferenceEvidence(historical)).toBe(historical);
  });
});
