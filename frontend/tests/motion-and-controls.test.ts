// Initial-render checks for motion and keyboard behavior (worker 17).
// Rendered with react-dom/server: effects do not run, so this is exactly the
// state a learner sees before interacting. Browser checks live in qa/mobile.
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { FrameRecord } from "../src/api/types";
import { CaseBench } from "../src/components/CaseBench";
import { FrameViewer, type FrameSlot } from "../src/components/FrameViewer";
import { createFixtureApi } from "../src/fixtures/devFixture";

const g = globalThis as { window?: unknown };
const hadWindow = "window" in g;

beforeAll(() => {
  // A reduced-motion visitor: every media query reports `matches: true`.
  g.window = {
    matchMedia: (query: string) => ({
      matches: true,
      media: query,
      addEventListener() {},
      removeEventListener() {},
    }),
  };
});
afterAll(() => {
  if (!hadWindow) delete g.window;
});

async function fairComparison() {
  const api = createFixtureApi();
  const [caseContent, set] = await Promise.all([
    api.caseContent("fair_comparison"),
    api.presetFrames("epsilon_indi_b", "fair_comparison"),
  ]);
  const framesByRef = new Map<string, FrameRecord>();
  for (const cf of caseContent.frames) {
    const f = set.frames.find((x) => x.frame_key === cf.frame_key);
    if (f) framesByRef.set(cf.ref, f);
  }
  return { caseContent, framesByRef, frames: set.frames };
}

describe("case comparison under reduced motion", () => {
  it("starts paused with nothing auto-animating", async () => {
    const { caseContent, framesByRef } = await fairComparison();
    expect(framesByRef.size).toBeGreaterThanOrEqual(2);
    const html = renderToStaticMarkup(
      createElement(CaseBench, { caseContent, framesByRef, otherRef: "B", onOtherRefChange: () => {} }),
    );
    const playButton = html.match(/<button\b[^>]*class="[^"]*\bblink-toggle\b[^"]*"[^>]*>[\s\S]*?<\/button>/)?.[0];
    expect(playButton).toBeDefined();
    expect(playButton).toContain('aria-pressed="false"');
    expect(playButton?.replace(/<[^>]*>/g, "").trim()).toBe("Play comparison");
    expect(html).not.toContain("Pause comparison");
    expect(html).not.toMatch(/class="[^"]*\bplates\b[^"]*\bblinking\b[^"]*"/);
  });

  it("keeps the phone A/B choice and blink in one control row, in reading order", async () => {
    const { caseContent, framesByRef } = await fairComparison();
    const html = renderToStaticMarkup(
      createElement(CaseBench, { caseContent, framesByRef, otherRef: "B", onOtherRefChange: () => {} }),
    );
    const row = html.slice(html.indexOf('class="view-switch"'));
    const a = row.indexOf("Image A");
    const b = row.indexOf("Image B");
    const blink = row.indexOf("Play comparison");
    expect(a).toBeGreaterThan(0);
    expect(b).toBeGreaterThan(a);
    expect(blink).toBeGreaterThan(b);
  });
});

describe("frame stepper", () => {
  it("does not blink on load and keeps the end buttons focusable", async () => {
    const { frames } = await fairComparison();
    const slots: FrameSlot[] = frames.map((f) => ({
      key: f.frame_key,
      ref: null,
      status: "ready",
      frame: f,
      observed_at_utc: f.observed_at_utc,
      mjd: f.mjd,
      error: null,
    }));
    const html = renderToStaticMarkup(
      createElement(FrameViewer, {
        slots,
        index: 0,
        onIndexChange: () => {},
        selectedKeys: new Set<string>(),
        onToggleEvidence: () => {},
        title: "Frames in time order",
        blinkTool: true,
      }),
    );
    // At the first frame "Earlier" is aria-disabled, not disabled, so focus is not lost.
    expect(html).toMatch(/<button[^>]*aria-disabled="true"[^>]*aria-label="Earlier frame"/);
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*aria-label="Earlier frame"/);
    // The live region describes the current frame, not a running blink.
    expect(html).toContain("Frame 1 of");
    expect(html).not.toContain("Blinking two frames");
  });
});

describe("reduced-motion stylesheet", () => {
  it("removes smooth scrolling and transitions", () => {
    const css = readFileSync(new URL("../src/styles/app.css", import.meta.url), "utf8");
    const block = css.slice(css.indexOf("@media (prefers-reduced-motion: reduce)"));
    expect(block).toMatch(/scroll-behavior:\s*auto/);
    expect(block).toMatch(/transition:\s*none\s*!important/);
  });
});
