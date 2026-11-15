import { afterEach, describe, expect, it, vi } from "vitest";
import { observeLandingArrival } from "../src/lib/landingContentMotion";

function setup({ reduced = false, hidden = false, focused = false } = {}) {
  const doc = Object.assign(new EventTarget(), { hidden, activeElement: null });
  const preference = Object.assign(new EventTarget(), { matches: reduced });
  const win = Object.assign(new EventTarget(), { matchMedia: () => preference });
  const element = Object.assign(new EventTarget(), { classList: { remove: vi.fn() }, contains: () => focused });
  const animations = [0, 1].map(() => ({ cancel: vi.fn(), onfinish: null as (() => void) | null }));
  const start = vi.fn(() => animations as unknown as Animation[]);
  const disconnect = vi.fn();
  let notify: IntersectionObserverCallback | undefined;
  vi.stubGlobal("document", doc);
  vi.stubGlobal("window", win);
  vi.stubGlobal("IntersectionObserver", class {
    constructor(callback: IntersectionObserverCallback) { notify = callback; }
    observe = vi.fn();
    disconnect = disconnect;
  });
  const seen = new WeakSet<Element>();
  const dispose = observeLandingArrival(element as unknown as HTMLElement, start, seen);
  const intersect = (isIntersecting: boolean) => notify?.([{ isIntersecting } as IntersectionObserverEntry], {} as IntersectionObserver);
  return { doc, preference, win, element, animations, start, disconnect, seen, dispose, intersect };
}
afterEach(() => vi.unstubAllGlobals());

describe("landing section lifecycle", () => {
  it.each([{ hidden: true }, { reduced: true }, { focused: true }])("retains readable content without starting under %j", (options) => {
    const s = setup(options);
    s.intersect(true);
    expect(s.start).not.toHaveBeenCalled();
    s.dispose();
  });
  it("waits for visibility, starts once, and releases all completed effects", () => {
    const s = setup();
    s.intersect(false);
    expect(s.start).not.toHaveBeenCalled();
    s.intersect(true);
    s.intersect(true);
    expect(s.start).toHaveBeenCalledOnce();
    s.animations[0].onfinish?.();
    expect(s.disconnect).not.toHaveBeenCalled();
    s.animations[1].onfinish?.();
    expect(s.disconnect).toHaveBeenCalledOnce();
    s.animations.forEach((animation) => expect(animation.cancel).toHaveBeenCalledOnce());
  });
  it("settles all card effects when their section leaves the viewport", () => {
    const s = setup();
    s.intersect(true);
    s.intersect(false);
    s.intersect(true);
    expect(s.start).toHaveBeenCalledOnce();
    s.animations.forEach((animation) => expect(animation.cancel).toHaveBeenCalledOnce());
  });
  it.each(["focusin", "pointerdown", "keydown"])("settles immediately on %s", (type) => {
    const s = setup();
    s.intersect(true);
    s.element.dispatchEvent(new Event(type));
    s.animations.forEach((animation) => expect(animation.cancel).toHaveBeenCalledOnce());
    s.intersect(true);
    expect(s.start).toHaveBeenCalledOnce();
  });
  it("discards a pending arrival when the document is hidden", () => {
    const s = setup();
    s.doc.hidden = true;
    s.doc.dispatchEvent(new Event("visibilitychange"));
    s.doc.hidden = false;
    s.intersect(true);
    expect(s.start).not.toHaveBeenCalled();
    expect(s.disconnect).toHaveBeenCalledOnce();
  });
  it("settles running effects when reduced motion is enabled", () => {
    const s = setup();
    s.intersect(true);
    s.preference.matches = true;
    s.preference.dispatchEvent(new Event("change"));
    s.animations.forEach((animation) => expect(animation.cancel).toHaveBeenCalledOnce());
  });
  it("settles before printing and cancels callbacks on cleanup", () => {
    const s = setup();
    s.intersect(true);
    s.win.dispatchEvent(new Event("beforeprint"));
    s.dispose();
    s.animations.forEach((animation) => { expect(animation.cancel).toHaveBeenCalledOnce(); expect(animation.onfinish).toBeNull(); });
    expect(s.disconnect).toHaveBeenCalledOnce();
  });
  it("disposal cancels pending arrivals without consuming a future mount", () => {
    const s = setup();
    s.dispose();
    s.intersect(true);
    expect(s.start).not.toHaveBeenCalled();
    expect(s.seen.has(s.element as unknown as Element)).toBe(false);
  });
});
