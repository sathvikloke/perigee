/** First arrival only: rest is plain, visible DOM with no retained animation effect. */
export function createHeroArrivalMotion(host: HTMLElement, onRest: () => void) {
  const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (preference.matches || document.hidden || typeof host.animate !== "function") {
    onRest();
    return () => {};
  }
  let disposed = false;
  const active = new Set<Animation>();
  let observer: IntersectionObserver | undefined;
  let deadline: number | undefined;
  const cleanup = () => {
    if (disposed) return;
    disposed = true;
    window.clearTimeout(deadline);
    observer?.disconnect();
    document.removeEventListener("visibilitychange", visibility);
    preference.removeEventListener("change", reduced);
    window.removeEventListener("resize", settle);
    window.removeEventListener("beforeprint", settle);
    host.removeEventListener("focusin", settle);
    host.removeEventListener("pointerdown", settle);
    host.removeEventListener("keydown", settle);
    active.forEach((animation) => { animation.onfinish = null; animation.cancel(); });
    active.clear();
  };
  const settle = () => { if (disposed) return; cleanup(); onRest(); };
  const visibility = () => { if (document.hidden) settle(); };
  const reduced = () => { if (preference.matches) settle(); };
  const play = (selector: string, frames: Keyframe[], duration: number, delay = 0) => {
    const target = host.querySelector<HTMLElement>(selector);
    if (!target || typeof target.animate !== "function") return;
    const animation = target.animate(frames, { duration, delay, easing: "cubic-bezier(.16,1,.3,1)", fill: "backwards" });
    active.add(animation);
    animation.onfinish = () => {
      if (disposed) return;
      animation.onfinish = null;
      animation.cancel();
      active.delete(animation);
      if (active.size === 0) settle();
    };
  };
  play("h1", [
    { opacity: 0, transform: "translate3d(0,35px,0)", clipPath: "inset(0 0 100% 0)" },
    { opacity: 1, transform: "none", clipPath: "inset(-5% 0 -5% 0)" },
  ], 800);
  const copy = [{ opacity: 0, transform: "translate3d(0,16px,0)" }, { opacity: 1, transform: "none" }];
  play(".hero-description", copy, 650, 100);
  play(".hero-cta", copy, 650, 160);
  if (!active.size) { settle(); return cleanup; }
  if (typeof IntersectionObserver !== "undefined") {
    observer = new IntersectionObserver(([entry]) => { if (!entry.isIntersecting) settle(); });
    observer.observe(host);
  }
  document.addEventListener("visibilitychange", visibility);
  preference.addEventListener("change", reduced);
  window.addEventListener("resize", settle);
  window.addEventListener("beforeprint", settle);
  host.addEventListener("focusin", settle);
  host.addEventListener("pointerdown", settle, { passive: true });
  host.addEventListener("keydown", settle);
  // Browser scheduling must never hold the first, transparent keyframe indefinitely.
  deadline = window.setTimeout(settle, 1050);
  return cleanup;
}
