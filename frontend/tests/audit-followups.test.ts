import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { normalizeFrameRecord } from "../src/api/client";
import type { CaseContent, FrameRecord } from "../src/api/types";
import { ProcessingNote } from "../src/components/CaseBench";
import { Plate } from "../src/components/Plate";
import { analyzePair, hasSharedStretch } from "../src/lib/compare";
import { frameProcessingAnnouncement } from "../src/lib/requestState";

function caseFrames(caseId: string) {
  const content = JSON.parse(readFileSync(new URL(`../../backend/content/cases/${caseId}.json`, import.meta.url), "utf8")) as CaseContent;
  return Object.fromEntries(content.frames.map((ref) => [ref.ref, normalizeFrameRecord(JSON.parse(readFileSync(
    new URL(`../../backend/content/presets/${content.target_id}/case-${caseId}/${ref.frame_key}.json`, import.meta.url), "utf8"),
  ))])) as Record<string, FrameRecord>;
}

describe("pair processing claims follow the selected scientific records", () => {
  for (const caseId of ["fair_comparison", "wise_0855_quality_trap"]) {
    it(`${caseId}: describes A+B as shared and A+C as separate`, () => {
      const { A, B, C } = caseFrames(caseId);
      const note = (other: FrameRecord) => renderToStaticMarkup(createElement(ProcessingNote, { frame: A, comparedWith: other }));
      expect(hasSharedStretch(A, B)).toBe(true);
      expect(note(B)).toContain("one shared contrast stretch");
      expect(hasSharedStretch(A, C)).toBe(false);
      expect(note(C)).toContain("separate contrast stretches");
      expect(note(C)).toContain("Grey levels cannot establish a brightness change");
      expect(note(C)).not.toContain("one shared");
      expect(analyzePair(A, C).caveats).toContain("The selected images use separate contrast stretches. Grey levels cannot establish a brightness change.");
    });
  }

  it("retains both genuinely shared Barnard pairs", () => {
    const { A, B, C } = caseFrames("moving_neighbor");
    expect(hasSharedStretch(A, B)).toBe(true);
    expect(hasSharedStretch(A, C)).toBe(true);
  });

  it("does not trust matching shared labels with different groups or mapping parameters", () => {
    const { A, B } = caseFrames("moving_neighbor");
    for (const patch of [{ basis: "another group" }, { high: 100 }, { method: "linear" }, { asinh_softening: 2 }, { unit: "counts" }]) {
      expect(hasSharedStretch(A, { ...B, display_scale: { ...B.display_scale!, ...patch } })).toBe(false);
    }
  });

  it("does not infer a common mapping from missing or invalid metadata", () => {
    const { A, B } = caseFrames("moving_neighbor");
    expect(hasSharedStretch(A, { ...B, display_scale: null })).toBe(false);
    for (const value of [undefined, Number.NaN, Number.POSITIVE_INFINITY]) {
      const scale = { ...A.display_scale!, high: value };
      expect(hasSharedStretch({ ...A, display_scale: scale }, { ...B, display_scale: scale })).toBe(false);
    }
  });
});

it("describes unusable covered pixels as well as absent coverage in image alt text", () => {
  const { A } = caseFrames("moving_neighbor");
  const html = renderToStaticMarkup(createElement(Plate, { frame: A, heading: "Observation A", letter: "A", showMarker: true, showFlags: true }));
  const alt = html.match(/alt="([^"]+)"/)?.[1];
  expect(alt).toContain("outside image coverage or saturated/non-finite pixels");
  expect(alt).toContain("does not represent dark sky");
  expect(html).not.toContain("Hatched areas are outside the image.");
});

describe("search announcements finish with processing", () => {
  it("includes both queued and active frames while processing", () => {
    expect(frameProcessingAnnouncement({ pending: 1, loading: 1, ready: 0, error: 0 })).toBe("0 frames ready; 2 still processing.");
  });
  it("announces successful completion instead of a stale processing message", () => {
    expect(frameProcessingAnnouncement({ pending: 0, loading: 0, ready: 2, error: 0 })).toBe("Frame processing finished: 2 frames ready.");
  });
  it("does not describe failed frames as ready, and updates when a retry completes", () => {
    expect(frameProcessingAnnouncement({ pending: 0, loading: 0, ready: 1, error: 1 })).toBe("Frame processing finished: 1 frame ready; 1 could not be processed.");
    expect(frameProcessingAnnouncement({ pending: 0, loading: 1, ready: 1, error: 0 })).toBe("1 frame ready; 1 still processing.");
    expect(frameProcessingAnnouncement({ pending: 0, loading: 0, ready: 2, error: 0 })).toContain("finished: 2 frames ready");
  });
});
