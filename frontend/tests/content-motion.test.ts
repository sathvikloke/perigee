import { afterEach, describe, expect, it, vi } from "vitest";
import { playContentCue } from "../src/lib/contentMotion";

// Exercise lifecycle policy; interpolation and visible timing need a browser.
function setup({ reduced = false, hidden = false, observer = true, animationApi = true } = {}) {
  const document = Object.assign(new EventTarget(), { hidden });
  const preference = Object.assign(new EventTarget(), { matches: reduced });
  const window = Object.assign(new EventTarget(), { matchMedia: () => preference });
  const animation = { cancel: vi.fn(), onfinish: null as (() => void) | null };
  const animate = vi.fn(() => animation);
  const element = Object.assign(new EventTarget(), { animate: animationApi ? animate : undefined });
  const disconnect = vi.fn();
  let notify: IntersectionObserverCallback | undefined;
  vi.stubGlobal("document", document);
  vi.stubGlobal("window", window);
  vi.stubGlobal("IntersectionObserver", observer ? class {
    constructor(callback: IntersectionObserverCallback) { notify = callback; }
    observe = vi.fn();
    disconnect = disconnect;
  } : undefined);
  const dispose = playContentCue(element as unknown as HTMLElement, "step");
  const intersect = (isIntersecting: boolean) => notify?.([{ isIntersecting } as IntersectionObserverEntry], {} as IntersectionObserver);
  return { document, preference, window, animation, animate, element, disconnect, dispose, intersect };
}

afterEach(() => vi.unstubAllGlobals());

describe("content cue lifecycle", () => {
  it.each([{ reduced: true }, { hidden: true }, { animationApi: false }])("keeps the default visible state without starting under %j", (options) => {
    const x = setup(options);
    x.intersect(true);
    expect(x.animate).not.toHaveBeenCalled();
    x.dispose();
  });

  it("waits for the content, runs once, and cleans up its completed effect", () => {
    const x = setup();
    x.intersect(false);
    expect(x.animate).not.toHaveBeenCalled();
    x.intersect(true);
    x.intersect(true);
    expect(x.animate).toHaveBeenCalledOnce();
    x.animation.onfinish?.();
    expect(x.animation.cancel).toHaveBeenCalledOnce();
    expect(x.disconnect).toHaveBeenCalledOnce();
    x.intersect(true);
    expect(x.animate).toHaveBeenCalledOnce();
  });

  it("settles on leaving the viewport instead of replaying a stale state on return", () => {
    const x = setup();
    x.intersect(true);
    x.intersect(false);
    x.intersect(true);
    expect(x.animate).toHaveBeenCalledOnce();
    expect(x.animation.cancel).toHaveBeenCalledOnce();
  });

  it("discards a pending cue when the tab is hidden", () => {
    const x = setup();
    x.document.hidden = true;
    x.document.dispatchEvent(new Event("visibilitychange"));
    x.document.hidden = false;
    x.intersect(true);
    expect(x.animate).not.toHaveBeenCalled();
    expect(x.disconnect).toHaveBeenCalledOnce();
  });

  it("settles immediately when reduced motion is enabled mid-cue", () => {
    const x = setup();
    x.intersect(true);
    x.preference.matches = true;
    x.preference.dispatchEvent(new Event("change"));
    expect(x.animation.cancel).toHaveBeenCalledOnce();
    x.preference.matches = false;
    x.intersect(true);
    expect(x.animate).toHaveBeenCalledOnce();
  });

  it.each(["pointerdown", "keydown"])("interaction %s interrupts without waiting", (event) => {
    const x = setup();
    x.intersect(true);
    x.element.dispatchEvent(new Event(event));
    expect(x.animation.cancel).toHaveBeenCalledOnce();
  });

  it("cleans up on state replacement/unmount, including pending starts", () => {
    const x = setup();
    x.dispose();
    x.intersect(true);
    expect(x.animate).not.toHaveBeenCalled();
    expect(x.disconnect).toHaveBeenCalledOnce();
    x.dispose();
    expect(x.disconnect).toHaveBeenCalledOnce();
  });

  it("supports the observer fallback and settles before printing", () => {
    const x = setup({ observer: false });
    expect(x.animate).toHaveBeenCalledOnce();
    x.window.dispatchEvent(new Event("beforeprint"));
    expect(x.animation.cancel).toHaveBeenCalledOnce();
    expect(x.animation.onfinish).toBeNull();
  });
});
