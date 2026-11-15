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

function setup({ paused = false, hidden = false, enter = true } = {}) {
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
  const controller = createObservatoryMotion(host, driftHost, { paused, enter, onEnter, onRest });
  const intersect = (isIntersecting: boolean) => notifyIntersection(
    [{ isIntersecting } as IntersectionObserverEntry],
    {} as IntersectionObserver,
  );
  return { controller, entrance, drift, document, intersect, onEnter, onRest, observe, disconnect, host };
}

afterEach(() => vi.unstubAllGlobals());

describe("observatory motion lifecycle", () => {
  it("settles an incomplete entrance on scroll departure and returns directly to ambient drift", () => {
    const x = setup();
    expect(x.observe).toHaveBeenCalledWith(x.host);
    expect(x.entrance.playState).toBe("running");
    x.entrance.currentTime = 200;
    x.intersect(false);
    expect(x.entrance.playState).toBe("idle");
    expect(x.entrance.currentTime).toBeNull();
    expect(x.onRest).toHaveBeenCalledOnce();
    expect(x.drift.playState).toBe("paused");
    const plays = x.entrance.play.mock.calls.length;
    x.intersect(true);
    expect(x.entrance.play.mock.calls.length).toBe(plays);
    expect(x.drift.playState).toBe("running");
    x.controller.dispose();
  });

  it("releases the completed entrance effect and never reapplies it on scroll return", () => {
    const x = setup();
    x.entrance.complete();
    expect(x.onRest).toHaveBeenCalledOnce();
    expect(x.entrance.playState).toBe("idle");
    expect(x.entrance.cancel).toHaveBeenCalledOnce();
    expect(x.entrance.onfinish).toBeNull();
    const plays = x.entrance.play.mock.calls.length;
    x.intersect(false);
    expect(x.drift.playState).toBe("paused");
    x.intersect(true);
    x.intersect(false);
    x.intersect(true);
    expect(x.drift.playState).toBe("running");
    expect(x.entrance.play.mock.calls.length).toBe(plays);
    expect(x.onEnter).toHaveBeenCalledOnce();
    x.controller.dispose();
  });

  it("settles the entrance when the tab is hidden and resumes only ambient motion", () => {
    const x = setup();
    x.document.setHidden(true);
    expect(x.entrance.playState).toBe("idle");
    expect(x.onRest).toHaveBeenCalledOnce();
    x.document.setHidden(false);
    expect(x.drift.playState).toBe("running");
    expect(x.entrance.play).toHaveBeenCalledOnce();
    x.controller.dispose();
  });

  it("starts in a visible resting state when already paused or hidden", () => {
    const x = setup({ paused: true, hidden: true });
    expect(x.entrance.playState).toBe("idle");
    expect(x.drift.playState).toBe("paused");
    x.controller.setPaused(false);
    expect(x.drift.playState).toBe("paused");
    x.document.setHidden(false);
    expect(x.drift.playState).toBe("running");
    expect(x.entrance.play).not.toHaveBeenCalled();
    x.controller.dispose();
  });

  it("preserves manual pause across viewport and tab changes after completion", () => {
    const x = setup();
    x.entrance.complete();
    x.controller.setPaused(true);
    x.intersect(false); x.intersect(true);
    x.document.setHidden(true); x.document.setHidden(false);
    expect(x.drift.playState).toBe("paused");
    x.controller.setPaused(false);
    expect(x.drift.playState).toBe("running");
    x.controller.dispose();
  });

  it("only an explicit replay restarts the canceled approach", () => {
    const x = setup();
    x.controller.skip();
    expect(x.onRest).toHaveBeenCalledOnce();
    expect(x.entrance.playState).toBe("idle");
    x.drift.currentTime = 900;
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

  it("can create ambient motion without a new entrance when already read", () => {
    const x = setup({ enter: false });
    expect(x.entrance.playState).toBe("idle");
    expect(x.entrance.play).not.toHaveBeenCalled();
    expect(x.onEnter).not.toHaveBeenCalled();
    expect(x.drift.playState).toBe("running");
    x.controller.dispose();
  });

  it("prevents queued visibility and finish callbacks after disposal", () => {
    const x = setup();
    const pendingFinish = x.entrance.onfinish;
    const plays = x.entrance.play.mock.calls.length;
    x.controller.dispose();
    x.document.setHidden(true); x.document.setHidden(false);
    x.intersect(true); pendingFinish?.();
    x.controller.setPaused(false); x.controller.replay();
    expect(x.entrance.play.mock.calls.length).toBe(plays);
    expect(x.entrance.playState).toBe("idle");
    expect(x.drift.playState).toBe("idle");
    expect(x.onRest).not.toHaveBeenCalled();
    expect(x.disconnect).toHaveBeenCalledOnce();
  });
});
