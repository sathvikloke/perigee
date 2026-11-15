import { describe, expect, it } from "vitest";
import { focusHeadingWhenReady } from "../src/lib/headingFocus";

/** A tiny stand-in for <main>: a heading may be mounted later, and changes notify an observer. */
function harness() {
  const body = { name: "body" };
  let active: unknown = body;
  let h1: { focused: number; tabindex?: string; setAttribute(n: string, v: string): void; focus(): void } | null = null;
  let listener: (() => void) | null = null;
  let observing = false;
  const container = { querySelector: (s: string) => (s === "h1" ? h1 : null) };
  const env = {
    container,
    body,
    activeElement: () => active,
    observe: (cb: () => void) => {
      listener = cb;
      observing = true;
      return () => {
        observing = false;
        listener = null;
      };
    },
  };
  const mountHeading = () => {
    h1 = {
      focused: 0,
      setAttribute(n, v) {
        if (n === "tabindex") this.tabindex = v;
      },
      focus() {
        this.focused += 1;
        active = this;
      },
    };
    listener?.();
    return h1;
  };
  return {
    env,
    mountHeading,
    mutate: () => listener?.(),
    setActive: (a: unknown) => (active = a),
    isObserving: () => observing,
  };
}

describe("focus moves to the view heading", () => {
  it("focuses a heading that is already there, without observing", () => {
    const h = harness();
    const heading = h.mountHeading();
    focusHeadingWhenReady(h.env);
    expect(heading.focused).toBe(1);
    expect(heading.tabindex).toBe("-1");
    expect(h.isObserving()).toBe(false);
  });

  it("waits for a loading view's heading, focuses it once, then stops observing", () => {
    const h = harness();
    focusHeadingWhenReady(h.env);
    expect(h.isObserving()).toBe(true);
    h.mutate(); // a loading message appears: still no heading
    expect(h.isObserving()).toBe(true);
    const heading = h.mountHeading();
    expect(heading.focused).toBe(1);
    expect(h.isObserving()).toBe(false);
    h.mutate(); // later re-renders never steal focus again
    expect(heading.focused).toBe(1);
  });

  it("leaves focus alone if the user moved it while the view loaded", () => {
    const h = harness();
    focusHeadingWhenReady(h.env);
    h.setActive({ name: "switcher button" });
    const heading = h.mountHeading();
    expect(heading.focused).toBe(0);
    expect(h.isObserving()).toBe(false);
  });

  it("stops waiting when the route changes first (cleanup)", () => {
    const h = harness();
    const cleanup = focusHeadingWhenReady(h.env);
    cleanup();
    expect(h.isObserving()).toBe(false);
  });
});
