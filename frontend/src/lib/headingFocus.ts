// Focus management on view changes: keyboard and screen reader users land on
// the new view's heading. Views that load data first (a preset) render their
// heading later, so focus moves when the heading actually mounts, not after a
// guessed delay. If the user has already moved focus somewhere (for example
// into the target switcher while frames load), focus is left alone.

interface FocusableHeading {
  setAttribute(name: string, value: string): void;
  focus(options?: FocusOptions): void;
}

export interface HeadingFocusEnv {
  /** The view container (`<main>`). */
  container: { querySelector(selector: string): FocusableHeading | null };
  /** Returns the currently focused element. */
  activeElement: () => unknown;
  /** The page body: focus there means nothing is focused. */
  body: unknown;
  /** Calls `onChange` whenever the container's subtree changes; returns a stop function. */
  observe: (onChange: () => void) => () => void;
}

/** Focuses the container's h1 now, or when it mounts. Returns a cleanup function. */
export function focusHeadingWhenReady(env: HeadingFocusEnv): () => void {
  const tryFocus = () => {
    const h1 = env.container.querySelector("h1");
    if (!h1) return false;
    h1.setAttribute("tabindex", "-1");
    h1.focus({ preventScroll: true });
    return true;
  };
  if (tryFocus()) return () => {};
  let stop: (() => void) | null = null;
  stop = env.observe(() => {
    const active = env.activeElement();
    // The user moved focus to a real control while the view loaded: respect it.
    const userMoved = active != null && active !== env.body && active !== env.container;
    if (userMoved || tryFocus()) {
      stop?.();
      stop = null;
    }
  });
  return () => stop?.();
}

/** Browser wiring for `focusHeadingWhenReady`. */
export function focusHeadingIn(main: HTMLElement): () => void {
  return focusHeadingWhenReady({
    container: main,
    activeElement: () => document.activeElement,
    body: document.body,
    observe: (onChange) => {
      const observer = new MutationObserver(onChange);
      observer.observe(main, { childList: true, subtree: true });
      return () => observer.disconnect();
    },
  });
}
