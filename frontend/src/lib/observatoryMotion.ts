export interface ObservatoryController {
  setPaused: (paused: boolean) => void;
  skip: () => void;
  replay: () => void;
  dispose: () => void;
}

/** The one-shot approach settles on departure; only ambient drift pauses and resumes. */
export function createObservatoryMotion(host: HTMLElement, driftHost: HTMLElement, options: {
  paused: boolean; enter?: boolean; onEnter: () => void; onRest: () => void;
}): ObservatoryController {
  let paused = options.paused, visible = true, disposed = false, entering = options.enter !== false;
  const entrance = host.animate([
    { transform: "translate3d(28%, 12%, 0) rotate(12deg) scale(.85)", opacity: 0 },
    { transform: "none", opacity: 1 },
  ], { duration: 1100, easing: "cubic-bezier(.16, 1, .3, 1)", fill: "backwards" });
  const drift = driftHost.animate([
    { transform: "translate3d(0, 0, 0) rotate(0deg)" },
    { transform: "translate3d(-14px, -22px, 0) rotate(-3deg)" },
    { transform: "translate3d(0, 0, 0) rotate(0deg)" },
  ], { duration: 6800, iterations: Infinity, easing: "ease-in-out" });
  entrance.currentTime = 0; entrance.pause(); drift.currentTime = 0; drift.pause();
  const rest = () => {
    if (disposed || !entering) return;
    entering = false;
    entrance.onfinish = null;
    entrance.cancel();
    options.onRest();
    sync();
  };
  const sync = () => {
    if (disposed) return;
    const active = visible && !document.hidden && !paused;
    if (entering) {
      drift.pause();
      // Never resume an opacity-zero/partial entrance when the reader scrolls back.
      if (active) entrance.play(); else rest();
    } else {
      if (active) drift.play(); else drift.pause();
    }
  };
  entrance.onfinish = rest;
  const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(([entry]) => {
    if (disposed) return;
    visible = entry.isIntersecting;
    sync();
  });
  observer?.observe(host);
  document.addEventListener("visibilitychange", sync);
  if (entering) options.onEnter(); else { entrance.onfinish = null; entrance.cancel(); }
  sync();
  return {
    setPaused(value) { paused = value; sync(); },
    skip: rest,
    replay() {
      if (disposed) return;
      drift.pause(); drift.currentTime = 0;
      entering = true; entrance.currentTime = 0; entrance.onfinish = rest;
      options.onEnter(); sync();
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      observer?.disconnect(); document.removeEventListener("visibilitychange", sync);
      entrance.onfinish = null; entrance.cancel(); drift.cancel();
    },
  };
}
