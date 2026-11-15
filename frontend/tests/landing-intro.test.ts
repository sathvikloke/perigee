import { afterEach, describe, expect, it, vi } from "vitest";
import { createLandingIntroMotion, INTRO_HERO_AT_MS, INTRO_TOTAL_MS, introEligible } from "../src/lib/landingIntroMotion";

class MotionDouble {
  onfinish: (() => void) | null = null;
  cancel = vi.fn();
}
class DocumentDouble extends EventTarget { hidden = false; }

function scene() {
  vi.useFakeTimers();
  vi.stubGlobal("window", { setTimeout, clearTimeout });
  const doc = new DocumentDouble();
  vi.stubGlobal("document", doc);
  const cover = new MotionDouble(), flight = new MotionDouble();
  const curtain = { animate: vi.fn(() => cover) } as unknown as HTMLElement;
  const rocket = { animate: vi.fn(() => flight) } as unknown as HTMLElement;
  const onReveal = vi.fn(), onFinish = vi.fn();
  const controller = createLandingIntroMotion(curtain, rocket, { onReveal, onFinish });
  return { doc, cover, flight, onReveal, onFinish, controller };
}
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

describe("bounded opening flight", () => {
  it("reveals during the cover travel, then settles once", () => {
    const s = scene();
    vi.advanceTimersByTime(INTRO_HERO_AT_MS - 1);
    expect(s.onReveal).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(s.onReveal).toHaveBeenCalledOnce();
    s.cover.onfinish?.();
    s.cover.onfinish?.();
    vi.advanceTimersByTime(INTRO_TOTAL_MS);
    expect(s.onFinish).toHaveBeenCalledOnce();
    s.controller.dispose();
  });

  it("skip reveals immediately and cancels pending callbacks on disposal", () => {
    const s = scene();
    s.controller.skip();
    expect(s.onReveal).toHaveBeenCalledOnce();
    expect(s.onFinish).toHaveBeenCalledOnce();
    s.controller.dispose();
    vi.runAllTimers();
    expect(s.onFinish).toHaveBeenCalledOnce();
    expect(s.cover.cancel).toHaveBeenCalledOnce();
    expect(s.flight.cancel).toHaveBeenCalledOnce();
  });

  it("opens the page when animation-end events never arrive", () => {
    const s = scene();
    vi.advanceTimersByTime(INTRO_TOTAL_MS + 200);
    expect(s.onFinish).toHaveBeenCalledOnce();
    s.controller.dispose();
  });

  it("settles if the document is hidden instead of trapping a returning visitor", () => {
    const s = scene();
    s.doc.hidden = true;
    s.doc.dispatchEvent(new Event("visibilitychange"));
    expect(s.onReveal).toHaveBeenCalledOnce();
    expect(s.onFinish).toHaveBeenCalledOnce();
    s.controller.dispose();
  });

  it("does not let stale timers or events finish a disposed scene", () => {
    const s = scene();
    const stale = s.cover.onfinish;
    s.controller.dispose();
    stale?.();
    s.controller.skip();
    s.doc.hidden = true;
    s.doc.dispatchEvent(new Event("visibilitychange"));
    vi.runAllTimers();
    expect(s.onReveal).not.toHaveBeenCalled();
    expect(s.onFinish).not.toHaveBeenCalled();
  });
});

describe("opening eligibility", () => {
  it("uses the first homepage load while preserving deep links", () => {
    expect(introEligible("", "")).toBe(true);
    expect(introEligible("?fixtures=1", "")).toBe(true);
    expect(introEligible("", "#investigations")).toBe(false);
    expect(introEligible("?preset=barnards_star", "")).toBe(false);
    expect(introEligible("?view=query", "")).toBe(false);
    expect(introEligible("?ra=258&dec=0", "")).toBe(false);
    expect(introEligible("?ra=258", "")).toBe(false);
    expect(introEligible("?dec=0", "")).toBe(false);
  });
});
