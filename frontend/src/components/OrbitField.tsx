import { useEffect, useRef, useState } from "react";

/** Decorative stars, not a sky map. The visible lower arc travels leftward. */
export function OrbitField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const phaseRef = useRef(0);
  const [paused, setPaused] = useState(false);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduced(preference.matches);
    sync();
    preference.addEventListener("change", sync);
    return () => preference.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let width = 1, height = 1, frame = 0, last = 0, elapsed = phaseRef.current;
    let visible = true;
    let seed = 707;
    const random = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
    const stars = Array.from({ length: 1000 }, () => ({
      radius: Math.sqrt(random()), angle: random() * Math.PI * 2,
      size: .45 + random() ** 3 * 1.3, opacity: .2 + random() * .66,
      speed: .0025 + random() * .002,
    }));
    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      const cx = width * .57, cy = -height * .42;
      const extent = Math.hypot(width * .8, height * 1.7);
      for (const star of stars) {
        const a = star.angle + elapsed * star.speed;
        const r = 90 + star.radius * extent;
        const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
        if (x < -4 || x > width + 4 || y < -4 || y > height + 4) continue;
        // Keep the reading column calm without drawing a visible panel.
        const distance = Math.hypot((x - width / 2) / (width * .32), (y - height * .46) / (height * .38));
        const quiet = .22 + Math.min(1, distance) * .78;
        ctx.fillStyle = `rgba(255,255,255,${star.opacity * quiet})`;
        ctx.beginPath(); ctx.arc(x, y, star.size, 0, Math.PI * 2); ctx.fill();
        if (star.size > 1.55) {
          ctx.fillStyle = `rgba(255,255,255,${.1 * quiet})`;
          ctx.beginPath(); ctx.arc(x, y, star.size * 2.6, 0, Math.PI * 2); ctx.fill();
        }
      }
    };
    const tick = (time: number) => {
      if (last && time - last < 30) { frame = requestAnimationFrame(tick); return; }
      if (last) elapsed += Math.min((time - last) / 1000, .1);
      last = time;
      draw(); frame = requestAnimationFrame(tick);
    };
    const sync = () => {
      cancelAnimationFrame(frame); last = 0; draw();
      if (visible && !document.hidden && !paused && !reduced) frame = requestAnimationFrame(tick);
    };
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width; height = rect.height;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); sync();
    };
    const observer = new ResizeObserver(resize);
    const visibility = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); });
    observer.observe(canvas); visibility.observe(canvas);
    document.addEventListener("visibilitychange", sync);
    resize();
    return () => { phaseRef.current = elapsed; cancelAnimationFrame(frame); observer.disconnect(); visibility.disconnect(); document.removeEventListener("visibilitychange", sync); };
  }, [paused, reduced]);

  return <>
    <canvas ref={canvasRef} className="orbit-field" aria-hidden="true" />
    <button type="button" className="orbit-toggle" aria-pressed={paused || reduced}
      onClick={() => setPaused(!paused)} disabled={reduced}
      aria-label={reduced ? "Star motion off for reduced motion" : paused ? "Resume star motion" : "Pause star motion"}>
      <span aria-hidden="true">{paused || reduced ? "▷" : "Ⅱ"}</span>
      {reduced ? "Motion reduced" : paused ? "Stars paused" : "Pause stars"}
    </button>
  </>;
}
