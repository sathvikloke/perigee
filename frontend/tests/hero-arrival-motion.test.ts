import { afterEach, describe, expect, it, vi } from "vitest";
import { createHeroArrivalMotion } from "../src/lib/heroArrivalMotion";

function setup({ hidden = false, reduced = false } = {}) {
  vi.useFakeTimers();
  const doc = Object.assign(new EventTarget(), { hidden });
  const preference = Object.assign(new EventTarget(), { matches: reduced });
  const win = Object.assign(new EventTarget(), { matchMedia: () => preference, setTimeout, clearTimeout });
  const animations = [0,1,2].map(() => ({ cancel: vi.fn(), onfinish: null as (() => void) | null }));
  const targets = animations.map(animation => ({ animate: vi.fn(() => animation) }));
  const host = Object.assign(new EventTarget(), {
    animate: vi.fn(), querySelector: (selector: string) => targets[["h1", ".hero-description", ".hero-cta"].indexOf(selector)],
  });
  const disconnect = vi.fn();
  let notify: IntersectionObserverCallback | undefined;
  vi.stubGlobal("window", win); vi.stubGlobal("document", doc);
  vi.stubGlobal("IntersectionObserver", class {
    constructor(callback: IntersectionObserverCallback) { notify = callback; }
    observe = vi.fn(); disconnect = disconnect;
  });
  const onRest = vi.fn();
  const dispose = createHeroArrivalMotion(host as unknown as HTMLElement, onRest);
  const intersect = (isIntersecting: boolean) => notify?.([{ isIntersecting } as IntersectionObserverEntry], {} as IntersectionObserver);
  return { doc, win, preference, host, animations, targets, onRest, dispose, intersect, disconnect };
}
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

describe("one-shot hero arrival", () => {
  it("releases masks and opacity effects after the complete entrance", () => {
    const x = setup();
    x.animations.forEach(animation => animation.onfinish?.());
    x.animations.forEach(animation => { expect(animation.cancel).toHaveBeenCalledOnce(); expect(animation.onfinish).toBeNull(); });
    expect(x.onRest).toHaveBeenCalledOnce();
    x.intersect(false); x.intersect(true);
    x.targets.forEach(target => expect(target.animate).toHaveBeenCalledOnce());
    expect(x.onRest).toHaveBeenCalledOnce();
  });
  it("scrolling away mid-arrival settles all text and never restarts it on return", () => {
    const x = setup();
    vi.advanceTimersByTime(180);
    x.intersect(false);
    x.animations.forEach(animation => expect(animation.cancel).toHaveBeenCalledOnce());
    expect(x.onRest).toHaveBeenCalledOnce();
    x.intersect(true);
    vi.runAllTimers();
    x.targets.forEach(target => expect(target.animate).toHaveBeenCalledOnce());
    expect(x.onRest).toHaveBeenCalledOnce();
  });
  it.each(["focusin", "pointerdown", "keydown"])("settles immediately on %s instead of concealing a control", (event) => {
    const x = setup();
    x.host.dispatchEvent(new Event(event));
    x.animations.forEach(animation => expect(animation.cancel).toHaveBeenCalledOnce());
    expect(x.onRest).toHaveBeenCalledOnce();
  });
  it.each([{ hidden: true }, { reduced: true }])("keeps static content for %j", (options) => {
    const x = setup(options);
    x.targets.forEach(target => expect(target.animate).not.toHaveBeenCalled());
    expect(x.onRest).toHaveBeenCalledOnce();
  });
  it("settles when the tab is hidden or reduced motion changes", () => {
    const x = setup();
    x.doc.hidden = true; x.doc.dispatchEvent(new Event("visibilitychange"));
    x.preference.matches = true; x.preference.dispatchEvent(new Event("change"));
    x.animations.forEach(animation => expect(animation.cancel).toHaveBeenCalledOnce());
    expect(x.onRest).toHaveBeenCalledOnce();
  });
  it("opens fully even when finish events are missing", () => {
    const x = setup();
    vi.advanceTimersByTime(1050);
    expect(x.onRest).toHaveBeenCalledOnce();
    x.animations.forEach(animation => expect(animation.cancel).toHaveBeenCalledOnce());
  });
  it("cancels an old sequence without settling a newly mounted/replayed one", () => {
    const x = setup();
    const stale = x.animations[0].onfinish;
    x.dispose(); stale?.(); x.intersect(true); vi.runAllTimers();
    expect(x.onRest).not.toHaveBeenCalled();
    x.animations.forEach(animation => expect(animation.cancel).toHaveBeenCalledOnce());
  });
});
