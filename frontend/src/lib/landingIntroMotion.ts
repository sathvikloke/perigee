export interface LandingIntroController {
  skip: () => void;
  dispose: () => void;
}

export const INTRO_FLIGHT_MS = 1450;
export const INTRO_REVEAL_AT_MS = 650;
export const INTRO_HERO_AT_MS = 1480;
export const INTRO_TOTAL_MS = 2050;

/** One decorative leftward flight followed by a matching reveal. No loading claims. */
export function createLandingIntroMotion(curtain: HTMLElement, rocket: HTMLElement, callbacks: {
  onReveal: () => void;
  onFinish: () => void;
}): LandingIntroController {
  let disposed = false, finished = false, revealed = false;
  const reveal = () => {
    if (disposed || revealed) return;
    revealed = true;
    callbacks.onReveal();
  };
  const flight = rocket.animate([
    { transform: "translate3d(110vw, -34%, 0) rotate(5deg)", offset: 0 },
    { transform: "translate3d(45vw, -55%, 0) rotate(-4deg)", offset: .52 },
    { transform: "translate3d(-130%, -72%, 0) rotate(-8deg)", offset: 1 },
  ], { duration: INTRO_FLIGHT_MS, easing: "cubic-bezier(.4, 0, .7, 1)", fill: "both" });
  const cover = curtain.animate([
    { transform: "translate3d(0, 0, 0)" },
    { transform: "translate3d(-100%, 0, 0)" },
  ], { delay: INTRO_REVEAL_AT_MS, duration: INTRO_TOTAL_MS - INTRO_REVEAL_AT_MS, easing: "cubic-bezier(.76, 0, .24, 1)", fill: "both" });
  const revealTimer = window.setTimeout(reveal, INTRO_HERO_AT_MS);
  let failSafe: number;
  const finish = () => {
    if (disposed || finished) return;
    finished = true;
    window.clearTimeout(revealTimer);
    window.clearTimeout(failSafe);
    reveal();
    callbacks.onFinish();
  };
  cover.onfinish = finish;
  // If animation events are interrupted, never leave a cover over the app.
  failSafe = window.setTimeout(finish, INTRO_TOTAL_MS + 200);
  const onVisibility = () => { if (document.hidden) finish(); };
  document.addEventListener("visibilitychange", onVisibility);
  if (document.hidden) finish();
  return {
    skip: finish,
    dispose() {
      disposed = true;
      window.clearTimeout(revealTimer);
      window.clearTimeout(failSafe);
      document.removeEventListener("visibilitychange", onVisibility);
      cover.onfinish = null;
      cover.cancel();
      flight.cancel();
    },
  };
}

/** Deep links and returns from the workbench must never trigger the first-load intro. */
export function introEligible(search: string, hash: string): boolean {
  const query = new URLSearchParams(search);
  return !hash && !query.has("preset") && !query.has("ra") && !query.has("dec") && query.get("view") !== "query";
}
