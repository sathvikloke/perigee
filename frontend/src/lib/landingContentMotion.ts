/** Bounded scroll cue that settles before interaction or leaving the viewing context. */
export function observeLandingArrival(element: HTMLElement, start: () => Animation[], seen: WeakSet<Element> = new WeakSet()) {
  if (seen.has(element)) return () => {};
  const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (preference.matches || document.hidden || typeof IntersectionObserver === "undefined") {
    seen.add(element);
    return () => {};
  }
  let disposed = false, started = false;
  const active = new Set<Animation>();
  const cleanup = () => {
    if (disposed) return;
    disposed = true;
    observer.disconnect();
    document.removeEventListener("visibilitychange", visibility);
    preference.removeEventListener("change", reduced);
    window.removeEventListener("beforeprint", settle);
    element.removeEventListener("focusin", settle);
    element.removeEventListener("pointerdown", settle);
    element.removeEventListener("keydown", settle);
    element.classList.remove("landing-section-entered");
    active.forEach((animation) => { animation.onfinish = null; animation.cancel(); });
    active.clear();
  };
  const settle = () => { seen.add(element); cleanup(); };
  const visibility = () => { if (document.hidden) settle(); };
  const reduced = () => { if (preference.matches) settle(); };
  const observer = new IntersectionObserver((entries) => {
    if (disposed) return;
    for (const entry of entries) {
      if (!entry.isIntersecting) { if (started) settle(); continue; }
      if (started) continue;
      if (document.hidden || preference.matches || element.contains(document.activeElement)) { settle(); return; }
      started = true;
      seen.add(element);
      for (const animation of start()) {
        active.add(animation);
        animation.onfinish = () => {
          animation.onfinish = null;
          animation.cancel();
          active.delete(animation);
          if (active.size === 0) cleanup();
        };
      }
      if (active.size === 0) cleanup();
    }
  }, { threshold: .12, rootMargin: "0px 0px -36px 0px" });
  document.addEventListener("visibilitychange", visibility);
  preference.addEventListener("change", reduced);
  window.addEventListener("beforeprint", settle);
  element.addEventListener("focusin", settle);
  element.addEventListener("pointerdown", settle, { passive: true });
  element.addEventListener("keydown", settle);
  observer.observe(element);
  return cleanup;
}
