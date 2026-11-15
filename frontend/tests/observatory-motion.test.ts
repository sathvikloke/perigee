import { afterEach, describe, expect, it, vi } from "vitest";
import { createObservatoryMotion } from "../src/lib/observatoryMotion";

// Small platform doubles let us exercise lifecycle policy without a DOM or
// pretending to verify interpolation, rendering, or browser frame scheduling.
class AnimationDouble {
  currentTime: number | null = 0;
  playState: AnimationPlayState = "running";
  onfinish: (() => void) | null = null;
  play = vi.fn(() => { this.playState = "running"; });
  pause = vi.fn(() => { this.playState = "paused"; });
  cancel = vi.fn(() => { this.playState = "idle"; this.currentTime = null; });
  finish = vi.fn(() => { this.playState = "finished"; });

  complete() {
    this.playState = "finished";
    this.onfinish?.();
  }
}

class DocumentDouble extends EventTarget {
  hidden = false;

  setHidden(hidden: boolean) {
    this.hidden = hidden;
    this.dispatchEvent(new Event("visibilitychange"));
  }
}

function setup({ paused = false, hidden = false } = {}) {
  const document = new DocumentDouble();
  document.hidden = hidden;
  const entrance = new AnimationDouble();
  const drift = new AnimationDouble();
  const host = { animate: () => entrance } as unknown as HTMLElement;
  const driftHost = { animate: () => drift } as unknown as HTMLElement;
  let notifyIntersection: IntersectionObserverCallback;
  const observe = vi.fn();
  const disconnect = vi.fn();

  vi.stubGlobal("document", document);
  vi.stubGlobal("IntersectionObserver", class {
    constructor(callback: IntersectionObserverCallback) { notifyIntersection = callback; }
    observe = observe;
    disconnect = disconnect;
  });

  const onEnter = vi.fn();
  const onRest = vi.fn();
  const controller = createObservatoryMotion(host, driftHost, { paused, onEnter, onRest });
  const intersect = (isIntersecting: boolean) => notifyIntersection(
    [{ isIntersecting } as IntersectionObserverEntry],
    {} as IntersectionObserver,
  );
  return { controller, entrance, drift, document, intersect, onEnter, onRest, observe, disconnect, host };
}

afterEach(() => vi.unstubAllGlobals());

describe("observatory motion lifecycle", () => {
  it("runs the entrance only while on screen, visible, and not manually paused", () => {
    const x = setup();
    expect(x.observe).toHaveBeenCalledWith(x.host);
    expect(x.onEnter).toHaveBeenCalledOnce();
    expect(x.entrance.playState).toBe("running");
    expect(x.drift.playState).toBe("paused");

    x.intersect(false);
    expect(x.entrance.playState).toBe("paused");
    x.document.setHidden(true);
    x.intersect(true);
    expect(x.entrance.playState).toBe("paused");
    x.document.setHidden(false);
    expect(x.entrance.playState).toBe("running");

    x.controller.setPaused(true);
    x.intersect(false);
    x.document.setHidden(true);
    x.intersect(true);
    x.document.setHidden(false);
    expect(x.entrance.playState).toBe("paused");
    expect(x.drift.playState).toBe("paused");
    x.controller.setPaused(false);
    expect(x.entrance.playState).toBe("running");
    x.controller.dispose();
  });

  it("respects pause and hidden-document state before the first frame", () => {
    const x = setup({ paused: true, hidden: true });
    expect(x.entrance.playState).toBe("paused");
    expect(x.drift.playState).toBe("paused");
    x.controller.setPaused(false);
    expect(x.entrance.playState).toBe("paused");
    x.document.setHidden(false);
    expect(x.entrance.playState).toBe("running");
    x.controller.dispose();
  });

  it("hands off to drift once and applies the same visibility policy after entrance", () => {
    const x = setup();
    x.entrance.complete();
    x.entrance.complete();
    expect(x.onRest).toHaveBeenCalledOnce();
    expect(x.entrance.playState).toBe("finished");
    expect(x.drift.playState).toBe("running");

    x.intersect(false);
    expect(x.drift.playState).toBe("paused");
    x.intersect(true);
    expect(x.drift.playState).toBe("running");
    x.document.setHidden(true);
    expect(x.drift.playState).toBe("paused");
    x.controller.setPaused(true);
    x.document.setHidden(false);
    expect(x.drift.playState).toBe("paused");
    x.controller.setPaused(false);
    expect(x.drift.playState).toBe("running");
    x.controller.dispose();
  });

  it("skips to rest, ignores a duplicate finish notification, and replays from the start", () => {
    const x = setup();
    x.controller.skip();
    // WAAPI finish notification can be delivered after finish() returns.
    x.entrance.complete();
    expect(x.entrance.finish).toHaveBeenCalledOnce();
    expect(x.onRest).toHaveBeenCalledOnce();
    expect(x.drift.playState).toBe("running");

    x.drift.currentTime = 900;
    x.entrance.currentTime = 1200;
    x.controller.replay();
    expect(x.onEnter).toHaveBeenCalledTimes(2);
    expect(x.entrance.currentTime).toBe(0);
    expect(x.drift.currentTime).toBe(0);
    expect(x.entrance.playState).toBe("running");
    expect(x.drift.playState).toBe("paused");
    x.entrance.complete();
    expect(x.onRest).toHaveBeenCalledTimes(2);
    expect(x.drift.playState).toBe("running");
    x.controller.dispose();
  });

  it("preserves an explicit pause across skip and replay", () => {
    const x = setup({ paused: true });
    x.controller.skip();
    expect(x.onRest).toHaveBeenCalledOnce();
    expect(x.drift.playState).toBe("paused");
    x.controller.replay();
    expect(x.entrance.playState).toBe("paused");
    expect(x.drift.playState).toBe("paused");
    x.controller.setPaused(false);
    expect(x.entrance.playState).toBe("running");
    expect(x.drift.playState).toBe("paused");
    x.controller.dispose();
  });

  it("cancels animations and prevents stale visibility and finish callbacks after disposal", () => {
    const x = setup();
    const removeListener = vi.spyOn(x.document, "removeEventListener");
    const pendingFinish = x.entrance.onfinish;
    x.controller.dispose();
    expect(x.disconnect).toHaveBeenCalledOnce();
    expect(removeListener).toHaveBeenCalledWith("visibilitychange", expect.any(Function));
    expect(x.entrance.cancel).toHaveBeenCalledOnce();
    expect(x.drift.cancel).toHaveBeenCalledOnce();
    expect(x.entrance.onfinish).toBeNull();

    const entrancePlays = x.entrance.play.mock.calls.length;
    const driftPlays = x.drift.play.mock.calls.length;
    x.document.setHidden(true);
    x.document.setHidden(false);
    x.intersect(true); // Already queued observer callback, despite disconnect.
    pendingFinish?.();
    x.controller.setPaused(false);
    x.controller.replay();
    expect(x.entrance.play.mock.calls.length).toBe(entrancePlays);
    expect(x.drift.play.mock.calls.length).toBe(driftPlays);
    expect(x.entrance.playState).toBe("idle");
    expect(x.drift.playState).toBe("idle");
    expect(x.onRest).not.toHaveBeenCalled();
    expect(x.onEnter).toHaveBeenCalledOnce();
  });
});
