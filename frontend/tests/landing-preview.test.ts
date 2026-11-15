import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { CaseContent, FrameRecord } from "../src/api/types";
import { landingPreview } from "../src/lib/landingPreview";

function caseData(id: string) {
  const content: CaseContent = JSON.parse(readFileSync(new URL(`../../backend/content/cases/${id}.json`, import.meta.url), "utf8"));
  const frames: FrameRecord[] = content.frames.map(frame => JSON.parse(readFileSync(new URL(`../../backend/content/presets/${content.target_id}/case-${id}/${frame.frame_key}.json`, import.meta.url), "utf8")));
  return { content, frames };
}

describe("landing previews match authored initial comparisons", () => {
  it.each([
    ["fair_comparison", "B"],
    ["moving_neighbor", "C"],
    ["wise_0855_quality_trap", "B"],
  ])("uses %s's intended pair even when response order changes", (id, otherRef) => {
    const { content, frames } = caseData(id);
    const [first, other] = landingPreview([...frames].reverse(), content);
    expect(first?.frame_key).toBe(content.frames.find(frame => frame.ref === "A")?.frame_key);
    expect(other?.frame_key).toBe(content.frames.find(frame => frame.ref === otherRef)?.frame_key);
  });
  it("does not replace a missing Epsilon B with the different-wavelength C", () => {
    const { content, frames } = caseData("fair_comparison");
    const b = content.frames.find(frame => frame.ref === "B")!.frame_key;
    expect(landingPreview(frames.filter(frame => frame.frame_key !== b), content)[1]).toBeUndefined();
  });
});
