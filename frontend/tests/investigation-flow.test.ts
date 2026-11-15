import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { CaseContent } from "../src/api/types";
import { normalizeFrameRecord } from "../src/api/client";
import { comparisonSwipe, CaseBench } from "../src/components/CaseBench";
import { Notebook } from "../src/components/Notebook";
import { FrameViewer, type FrameSlot } from "../src/components/FrameViewer";
import { attachPair, createEvidenceCard } from "../src/evidence/card";
import { completionIssues } from "../src/evidence/completion";

function investigation(caseId: string) {
  const content = JSON.parse(readFileSync(new URL(`../../backend/content/cases/${caseId}.json`, import.meta.url), "utf8")) as CaseContent;
  const frames = content.frames.map((ref) => ({ ref: ref.ref, frame: normalizeFrameRecord(JSON.parse(readFileSync(
    new URL(`../../backend/content/presets/${content.target_id}/case-${caseId}/${ref.frame_key}.json`, import.meta.url), "utf8"),
  )) }));
  return { content, frames, framesByRef: new Map(frames.map(({ ref, frame }) => [ref, frame])) };
}

describe("intentional comparison gestures", () => {
  it("changes images only for deliberate horizontal swipes", () => {
    expect(comparisonSwipe({ x: 200, y: 100 }, { x: 100, y: 106 })).toBe("second");
    expect(comparisonSwipe({ x: 100, y: 100 }, { x: 200, y: 106 })).toBe("first");
    expect(comparisonSwipe({ x: 200, y: 100 }, { x: 185, y: 260 })).toBeNull();
    expect(comparisonSwipe({ x: 200, y: 100 }, { x: 100, y: 150 })).toBeNull();
    expect(comparisonSwipe({ x: 200, y: 100 }, { x: 175, y: 102 })).toBeNull();
  });
});

describe("required comparison recovery", () => {
  for (const [caseId, wrongOther, requiredOther] of [["wise_0855_quality_trap", "C", "B"], ["fair_comparison", "C", "B"], ["moving_neighbor", "B", "C"]]) {
    it(`${caseId} names its required pair without unlocking the reference`, () => {
      const { content, frames } = investigation(caseId);
      const pair = (other: string) => frames.filter(({ ref }) => ref === "A" || ref === other);
      const draft = createEvidenceCard({ case_id: content.case_id, preset_id: content.target_id, app_version: "test", data_origin: "api" });
      const notes = { ...draft, observations: "My own observation", claim: "My own explanation", uncertainty: "My own uncertainty", reviewed_step_ids: content.steps.map((step) => step.id) };
      const card = attachPair(notes, pair(wrongOther), frames.map(({ ref }) => ref));
      const render = (record = card) => renderToStaticMarkup(createElement(Notebook, {
        card: record, caseContent: content, saveState: { kind: "saved", at: "now" }, onChange() {}, onRemoveFrame() {},
        requiredPair: { refs: ["A", requiredOther], reason: "This pair answers the final question.", onSelect() {} },
      }));
      const html = render();
      expect(html).toContain(`Use images A + ${requiredOther} for the final question`);
      expect(html).toContain(`>Use images A + ${requiredOther}</button>`);
      expect(html).not.toContain("Reference answer (from the case)");
      expect(completionIssues(card, content, true)).toContain(`Include frames A and ${requiredOther}.`);
      const restored = attachPair(card, pair(requiredOther), frames.map(({ ref }) => ref));
      expect(restored.claim).toBe(notes.claim);
      expect(restored.observations).toBe(notes.observations);
      expect(restored.uncertainty).toBe(notes.uncertainty);
      expect(completionIssues(restored, content, true)).toEqual([]);
      expect(render(restored)).not.toContain("required-pair-note");
      expect(html.indexOf("What did you notice?")).toBeLessThan(html.indexOf("What do you think the images show?"));
    });
  }
});

describe("image-first quality defaults", () => {
  it("keeps the quality warning while the guided overlay starts off", () => {
    const { content, framesByRef } = investigation("wise_0855_quality_trap");
    const html = renderToStaticMarkup(createElement(CaseBench, { caseContent: content, framesByRef, otherRef: "B", onOtherRefChange() {} }));
    expect(html).toContain("Flagged near target");
    expect(html).toContain("You can check whether a changing dot overlaps flagged pixels");
    expect(html).not.toContain('class="flag-overlay"');
  });
  it("also starts the optional explorer overlay off without hiding its warning", () => {
    const { frames } = investigation("wise_0855_quality_trap");
    const slots: FrameSlot[] = frames.map(({ frame, ref }) => ({ key: frame.frame_key, ref, frame, status: "ready", observed_at_utc: frame.observed_at_utc, mjd: frame.mjd, error: null }));
    const html = renderToStaticMarkup(createElement(FrameViewer, { slots, index: 1, onIndexChange() {}, selectedKeys: new Set<string>(), onToggleEvidence() {}, title: "Optional observations" }));
    expect(html).toContain("Flagged near target");
    expect(html).toContain("This image needs a quality check");
    expect(html).not.toContain('class="flag-overlay"');
  });
});
