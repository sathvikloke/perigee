import { useEffect, useRef, useState } from "react";
import { OrbitField } from "./OrbitField";
import { CartoonOutline } from "./CartoonOutline";
import { createObservatoryMotion, type ObservatoryController } from "../lib/observatoryMotion";

/** Reference-informed artistic illustration, never a mission photograph or live orbit. */
export function LandingObservatory({ active = true, onReplayIntro }: { active?: boolean; onReplayIntro?: () => void } = {}) {
  const host=useRef<HTMLDivElement>(null);
  const driftHost=useRef<HTMLDivElement>(null);
  const illustration=useRef<HTMLImageElement>(null);
  const controller=useRef<ObservatoryController|null>(null);
  const [reduced,setReduced]=useState(()=>typeof window!=="undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [paused,setPaused]=useState(false);
  const [ready,setReady]=useState(false);
  const [failed,setFailed]=useState(false);
  const [entering,setEntering]=useState(false);
  const pauseRef=useRef(paused);
  pauseRef.current=paused;

  useEffect(()=>{
    const query=window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync=()=>setReduced(query.matches);
    query.addEventListener("change",sync);
    if(illustration.current?.complete && illustration.current.naturalWidth) setReady(true);
    return()=>query.removeEventListener("change",sync);
  },[]);
  useEffect(()=>{
    setEntering(false);
    if(!active || reduced || !ready || !host.current || !driftHost.current || typeof host.current.animate!=="function") return;
    controller.current=createObservatoryMotion(host.current,driftHost.current,{
      paused:pauseRef.current,onEnter:()=>setEntering(true),onRest:()=>setEntering(false),
    });
    return()=>{controller.current?.dispose();controller.current=null;};
  },[active,reduced,ready]);
  useEffect(()=>{controller.current?.setPaused(paused);},[paused]);

  return <>
    <CartoonOutline id="satellite-sticker-outline" radius={14} />
    <OrbitField externallyPaused={!active || paused || reduced} hideControl />
    <figure className="observatory-stage" data-motion={entering ? "entering" : paused ? "paused" : "drifting"} aria-label="Cartoon space telescope">
      <div className="observatory-model" ref={host} aria-hidden="true">
        <div className="observatory-drift" ref={driftHost}>
          {!failed && <img ref={illustration} className="observatory-art" src="/illustrations/perigee-satellite-cartoon.webp"
            alt="" width={1254} height={1254} fetchPriority="high"
            onLoad={()=>setReady(true)} onError={()=>{setFailed(true);setReady(false);}} />}
        </div>
      </div>
      <figcaption>{failed ? "Space telescope illustration unavailable" : <>Space telescope<span className="observatory-illustration">AI illustration</span></>}</figcaption>
    </figure>
    <div className="landing-motion-controls">
      {!reduced && <button type="button" className="landing-replay"
        onClick={()=>{setPaused(false);onReplayIntro?.();}}>
        Replay intro <span aria-hidden="true">↗</span>
      </button>}
      <button type="button" className="landing-pause" aria-pressed={paused || reduced} disabled={reduced}
        aria-label={reduced ? "Animation off for reduced motion" : paused ? "Resume animation" : "Pause animation"}
        onClick={()=>setPaused(value=>!value)}>
        <span aria-hidden="true">{paused || reduced ? "▷" : "Ⅱ"}</span>
        {reduced ? "Motion reduced" : paused ? "Animation paused" : "Pause animation"}
      </button>
    </div>
  </>;
}
