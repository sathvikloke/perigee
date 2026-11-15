import { useEffect, useRef } from "react";

export type ContentCue = "heading" | "step" | "notebook" | "reference" | "ready" | "instruction";

const cues: Record<ContentCue, { frames: Keyframe[]; duration: number }> = {
  heading: { frames: [
    { clipPath: "inset(0 0 65% 0)", transform: "translateY(12px)", opacity: .65 },
    { clipPath: "inset(0 0 0% 0)", transform: "none", opacity: 1 },
  ], duration: 440 },
  step: { frames: [
    { transform: "translateX(14px)", opacity: .55 },
    { transform: "none", opacity: 1 },
  ], duration: 300 },
  notebook: { frames: [
    { backgroundColor: "#263016", borderBottomColor: "#d6f59a" },
    { backgroundColor: "transparent", borderBottomColor: "var(--lavender-line)" },
  ], duration: 560 },
  reference: { frames: [
    { transform: "translateY(12px)", opacity: .55 },
    { transform: "none", opacity: 1 },
  ], duration: 380 },
  ready: { frames: [
    { color: "#d6f59a", transform: "translateY(4px)" },
    { color: "var(--ink)", transform: "none" },
  ], duration: 360 },
  instruction: { frames: [
    { backgroundColor: "#263016" },
    { backgroundColor: "transparent" },
  ], duration: 420 },
};

/** One finite cue on text/chrome only. The resting DOM is always fully visible.
 * Offscreen entry waits for visibility; departure/interruption settles instead
 * of replaying old feedback. Nothing owns image pixels or delays an action. */
export function playContentCue(element: HTMLElement, kind: ContentCue): () => void {
  const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (preference.matches || document.hidden || typeof element.animate !== "function") return () => {};
  let animation: Animation | null = null;
  let observer: IntersectionObserver | null = null;
  let settled = false;

  const dispose = () => {
    if (settled) return;
    settled = true;
    observer?.disconnect();
    document.removeEventListener("visibilitychange", onVisibility);
    window.removeEventListener("beforeprint", dispose);
    preference.removeEventListener("change", onPreference);
    element.removeEventListener("pointerdown", dispose);
    element.removeEventListener("keydown", dispose);
    if (animation) {
      animation.onfinish = null;
      animation.cancel();
    }
  };
  const onVisibility = () => { if (document.hidden) dispose(); };
  const onPreference = () => { if (preference.matches) dispose(); };
  const start = () => {
    if (settled || animation) return;
    const cue = cues[kind];
    animation = element.animate(cue.frames, { duration: cue.duration, easing: "cubic-bezier(.16,1,.3,1)" });
    animation.onfinish = dispose;
  };
  document.addEventListener("visibilitychange", onVisibility);
  window.addEventListener("beforeprint", dispose);
  preference.addEventListener("change", onPreference);
  element.addEventListener("pointerdown", dispose);
  element.addEventListener("keydown", dispose);
  if (typeof IntersectionObserver === "function") {
    observer = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting) start();
      else if (animation) dispose();
    }, { threshold: .1 });
    observer.observe(element);
  } else start();
  return dispose;
}

/** Only a semantic state key restarts a cue, never keystrokes or autosave. */
export function useContentCue<T extends HTMLElement>(kind: ContentCue, stateKey: string | number | boolean, selector?: string) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const element = selector ? ref.current?.querySelector<HTMLElement>(selector) : ref.current;
    if (element) return playContentCue(element, kind);
  }, [kind, stateKey, selector]);
  return ref;
}
