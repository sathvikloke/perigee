import { useEffect, useRef, useState } from "react";
import { resolveAssetSrc, type PerigeeApi } from "../api/client";
import type { FrameRecord } from "../api/types";
import { markerXY } from "../lib/compare";
import { formatDateShort, formatMicrons, HATCH_EXPLANATION } from "../lib/format";
import { landingPreview } from "../lib/landingPreview";
import { useAsync } from "./common";
import "../styles/featured-investigation.css";

/** A user-controlled look at the real A/C case images, before the notebook. */
export function FeaturedInvestigation({ api, onOpen }: { api: PerigeeApi; onOpen: () => void }) {
  const { state, retry } = useAsync(async (signal) => {
    const [result, content] = await Promise.all([
      api.presetFrames("barnards_star", "moving_neighbor", signal),
      api.caseContent("moving_neighbor", signal),
    ]);
    return landingPreview(result.frames, content);
  }, [api]);
  const [first, last] = state.status === "ready" ? state.data : [];
  return <article className="featured-investigation" aria-labelledby="featured-title">
    <div className="featured-story">
      <p className="featured-target">Start here. Barnard’s Star</p>
      <h3 id="featured-title">Watch a star move</h3>
      <p className="featured-lead">Two observations, almost a year apart. Watch the bright glow near the ring and use the smaller stars as your reference.</p>
      <p className="featured-next">Then open the investigation to check the evidence and explain what you see.</p>
      <button type="button" className="featured-open" onClick={onOpen} aria-label="Open Barnard’s Star investigation">Investigate this star <span aria-hidden="true">↗</span></button>
    </div>
    {first?.image && last?.image
      ? <FeaturedComparison key={`${api.mode}:${first.frame_key}:${last.frame_key}`} frames={[first, last]} />
      : <div className="featured-unavailable" role="status">
        <p>{state.status === "loading" ? "Loading the two observations…" : "The preview couldn’t load. You can retry or open the investigation."}</p>
        {state.status !== "loading" && <button type="button" onClick={retry}>Retry preview</button>}
      </div>}
  </article>;
}

function FeaturedComparison({ frames }: { frames: [FrameRecord, FrameRecord] }) {
  const root = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [loaded, setLoaded] = useState<boolean[]>([false, false]);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [reduced, setReduced] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const ready = loaded.every(Boolean) && !failed;
  const reference = markerXY(frames[0].marker);
  const firstImage = frames[0].image!;
  const current = frames[visible];

  useEffect(() => {
    if (!playing || !ready) return;
    const id = window.setInterval(() => setVisible((index) => 1 - index), reduced ? 1500 : 1000);
    return () => window.clearInterval(id);
  }, [playing, ready, reduced]);

  useEffect(() => {
    const stop = () => setPlaying(false);
    const onVisibility = () => { if (document.hidden) stop(); };
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onPreference = () => { stop(); setReduced(query.matches); };
    const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) stop();
    }, { threshold: 0 });
    if (root.current) observer?.observe(root.current);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("beforeprint", stop);
    query.addEventListener("change", onPreference);
    return () => {
      observer?.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("beforeprint", stop);
      query.removeEventListener("change", onPreference);
    };
  }, []);

  return <div className="featured-comparison" ref={root}>
    <div className="featured-image" aria-label="Barnard’s Star comparison" aria-describedby="featured-image-help">
      {frames.map((frame, index) => <img
        key={`${frame.frame_key}:${attempt}`}
        src={resolveAssetSrc(frame.image!.src)} width={frame.image!.width} height={frame.image!.height}
        alt={`SPHEREx observation of Barnard’s Star, ${formatDateShort(frame.observed_at_utc)}, ${formatMicrons(frame.wavelength_um)}. ${HATCH_EXPLANATION}`}
        aria-hidden={visible !== index} data-visible={visible === index} draggable={false}
        onLoad={() => setLoaded((previous) => previous.map((value, i) => i === index ? true : value))}
        onError={() => { setFailed(true); setPlaying(false); }}
      />)}
      {reference && <span className="featured-reference" aria-hidden="true" style={{ left: `${reference.x / firstImage.width * 100}%`, top: `${reference.y / firstImage.height * 100}%` }} />}
      <span className="featured-compass" aria-hidden="true">N ↑</span>
      <span className="featured-date">{formatDateShort(current.observed_at_utc)}</span>
      {(!ready || failed) && <div className="featured-image-status" role="status">
        {failed ? <><p>An observation image couldn’t load.</p><button type="button" onClick={() => { setFailed(false); setLoaded([false, false]); setAttempt((value) => value + 1); }}>Retry images</button></> : "Loading images…"}
      </div>}
    </div>
    <div className="featured-playback">
      <button type="button" className="primary featured-play" aria-pressed={playing} disabled={!ready} onClick={() => setPlaying((value) => !value)}>
        <span aria-hidden="true">{playing ? "Ⅱ" : "▷"}</span>{playing ? "Pause comparison" : "Play comparison"}
      </button>
      <span>Almost one year apart</span>
    </div>
    <div className="featured-dates" role="group" aria-label="Choose an observation">
      {frames.map((frame, index) => <button type="button" key={frame.frame_key} aria-pressed={visible === index} disabled={!ready} onClick={() => { setPlaying(false); setVisible(index); }}>
        <span>{index === 0 ? "Earlier" : "Later"} <time dateTime={frame.observed_at_utc}>{formatDateShort(frame.observed_at_utc)}</time></span>
        <small>{formatMicrons(frame.wavelength_um)}</small>
      </button>)}
    </div>
    <p className="featured-image-help" id="featured-image-help">The ring stays at the first date’s catalog-predicted position. Both images are flagged near the saturated core; compare the glow’s position. Stripes mark pixels with no usable value.</p>
    {frames.some((frame) => frame._fixture) && <p className="featured-image-help">Development fixture. Not NASA observations.</p>}
  </div>;
}
