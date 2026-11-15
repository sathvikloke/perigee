import { useEffect, useRef, type RefObject } from "react";
import { observeLandingArrival } from "./landingContentMotion";

/** Section-specific arrivals; actual observations stay fixed inside their frames. */
export function useLandingContentMotion(root: RefObject<HTMLDivElement | null>, contentVersion: number) {
  const seen = useRef(new WeakSet<Element>());
  useEffect(() => {
    const host = root.current;
    if (!host) return;
    const cleanup: Array<() => void> = [];
    host.querySelectorAll<HTMLElement>(".editorial-heading,.investigation-card,.open-targets,.evidence-intro,.coordinate-invitation").forEach((element) => {
      cleanup.push(observeLandingArrival(element, () => {
        const running: Animation[] = [];
        const play = (target: Element | null, frames: Keyframe[], delay = 0, duration = 650) => {
          if (!(target instanceof HTMLElement) || typeof target.animate !== "function") return;
          running.push(target.animate(frames, { duration, delay, easing: "cubic-bezier(.16,1,.3,1)", fill: "backwards" }));
        };
        const revealTitle = (section: Element) => play(section.querySelector("h2,h3"), [
          { transform: "translateY(22px)", clipPath: "inset(0 0 100% 0)" },
          { transform: "translateY(0)", clipPath: "inset(-5% 0 -5% 0)" },
        ], 0, 700);
        element.classList.add("landing-section-entered");
        if (element.matches(".investigation-card")) {
          const index = Array.from(element.parentElement?.children ?? []).indexOf(element);
          play(element, [{ transform: "translateY(36px)" }, { transform: "translateY(0)" }], index * 80, 720);
          play(element.querySelector(".target-preview"), [{ clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0 0 0)" }], index * 80, 800);
          play(element.querySelector(".target-copy"), [{ opacity: 0, transform: "translateY(14px)" }, { opacity: 1, transform: "translateY(0)" }], index * 80 + 100);
        } else if (element.matches(".evidence-intro")) {
          revealTitle(element);
          play(element.querySelector(".example-evidence"), [
            { opacity: .3, transform: "translateX(-32px) rotate(-2deg)", transformOrigin: "50% 100%" },
            { opacity: 1, transform: "translateX(0) rotate(0deg)", transformOrigin: "50% 100%" },
          ], 60, 800);
          play(element.querySelector(".example-uncertainty"), [{ opacity: 0, transform: "translateY(10px)" }, { opacity: 1, transform: "translateY(0)" }], 260, 550);
        } else if (element.matches(".open-targets")) {
          element.querySelectorAll(".target-link").forEach((target, index) => play(target,
            [{ opacity: 0, transform: "translateX(26px)" }, { opacity: 1, transform: "translateX(0)" }], index * 90));
        } else {
          revealTitle(element);
        }
        return running;
      }, seen.current));
    });
    return () => cleanup.forEach((dispose) => dispose());
  }, [root, contentVersion]);
}
