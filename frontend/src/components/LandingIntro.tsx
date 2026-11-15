import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createLandingIntroMotion, type LandingIntroController } from "../lib/landingIntroMotion";
import { CartoonOutline } from "./CartoonOutline";

export function LandingIntro({ onReveal, onFinish }: { onReveal: () => void; onFinish: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const curtain = useRef<HTMLDivElement>(null);
  const rocket = useRef<HTMLDivElement>(null);
  const art = useRef<HTMLImageElement>(null);
  const flameArt = useRef<HTMLImageElement>(null);
  const motion = useRef<LandingIntroController | null>(null);
  const [ready, setReady] = useState(false);
  const latest = useRef({ onReveal, onFinish });
  latest.current = { onReveal, onFinish };
  const artworkReady = () => Boolean(art.current?.complete && art.current.naturalWidth && flameArt.current?.complete && flameArt.current.naturalWidth);
  const checkArtwork = () => { if (artworkReady()) setReady(true); };

  useLayoutEffect(() => {
    const node = dialog.current;
    if (!node) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const finish = () => { latest.current.onReveal(); latest.current.onFinish(); };
    const sync = () => { if (reduced.matches) finish(); };
    if (reduced.matches || typeof node.showModal !== "function") { finish(); return; }
    try { node.showModal(); } catch { finish(); return; }
    const priorOverflow = document.documentElement.style.overflow;
    document.documentElement.style.overflow = "hidden";
    reduced.addEventListener("change", sync);
    const assetTimeout = window.setTimeout(() => {
      if (!artworkReady()) finish();
    }, 1200);
    checkArtwork();
    return () => {
      window.clearTimeout(assetTimeout);
      reduced.removeEventListener("change", sync);
      node.close();
      document.documentElement.style.overflow = priorOverflow;
    };
  }, []);

  useEffect(() => {
    if (!ready || !curtain.current || !rocket.current) return;
    if (typeof curtain.current.animate !== "function") { latest.current.onReveal(); latest.current.onFinish(); return; }
    motion.current = createLandingIntroMotion(curtain.current, rocket.current, {
      onReveal: () => latest.current.onReveal(),
      onFinish: () => latest.current.onFinish(),
    });
    return () => { motion.current?.dispose(); motion.current = null; };
  }, [ready]);

  const skip = () => {
    if (motion.current) motion.current.skip();
    else { latest.current.onReveal(); latest.current.onFinish(); }
  };

  return <dialog className="landing-intro" ref={dialog} aria-label="Perigee opening animation"
    onCancel={(event) => { event.preventDefault(); skip(); }}>
    <CartoonOutline id="rocket-sticker-outline" radius={7} />
    <CartoonOutline id="flame-sticker-outline" radius={4} />
    <div className="intro-curtain" ref={curtain} aria-hidden="true">
      <div className="intro-wordmark">perigee<span>Explore the infrared sky</span></div>
    </div>
    <div className="intro-rocket" ref={rocket} aria-hidden="true">
      <div className="intro-exhaust">
        <img ref={flameArt} className="intro-flame" src="/illustrations/perigee-flame-cartoon.webp" alt="" width={1254} height={1254}
          fetchPriority="high" onLoad={checkArtwork} onError={skip} />
        <span className="exhaust-ember" /><span className="exhaust-ember" /><span className="exhaust-ember" />
      </div>
      <img className="intro-rocket-body" ref={art} src="/illustrations/perigee-rocket-cartoon.webp" alt="" width={1254} height={1254}
        fetchPriority="high" onLoad={checkArtwork} onError={skip} />
    </div>
    <p className="intro-art-label">AI illustration</p>
    <button type="button" className="intro-skip" autoFocus onClick={skip}>Skip intro <span aria-hidden="true">↗</span></button>
  </dialog>;
}
