export interface ObservatoryController {
  setPaused: (paused: boolean) => void;
  skip: () => void;
  replay: () => void;
  dispose: () => void;
}

/** A fixed-view spacecraft illustration: bounded approach and drift, no simulated orbit. */
export function createObservatoryMotion(host: HTMLElement, driftHost: HTMLElement, options: {
  paused: boolean; onEnter: () => void; onRest: () => void;
}): ObservatoryController {
  let paused=options.paused, visible=true, disposed=false, entering=true;
  const entrance=host.animate([
    { transform:"translate3d(28%, 12%, 0) rotate(12deg) scale(.85)", opacity: 0 },
    { transform:"translate3d(0, 0, 0) rotate(0deg) scale(1)", opacity: 1 },
  ], {duration:1100,easing:"cubic-bezier(.16, 1, .3, 1)",fill:"both"});
  const drift=driftHost.animate([
    {transform:"translate3d(0, 0, 0) rotate(0deg)"},
    {transform:"translate3d(-14px, -22px, 0) rotate(-3deg)"},
    {transform:"translate3d(0, 0, 0) rotate(0deg)"},
  ], {duration:6800,iterations:Infinity,easing:"ease-in-out"});
  entrance.currentTime=0; entrance.pause(); drift.currentTime=0; drift.pause();
  const sync=()=>{
    if(disposed) return;
    const active=visible && !document.hidden && !paused;
    if(entering) { drift.pause(); active ? entrance.play() : entrance.pause(); }
    else { active ? drift.play() : drift.pause(); }
  };
  const rest=()=>{ if(disposed || !entering) return; entering=false; options.onRest(); sync(); };
  entrance.onfinish=rest;
  const observer=new IntersectionObserver(([entry])=>{visible=entry.isIntersecting;sync();});
  observer.observe(host); document.addEventListener("visibilitychange",sync);
  options.onEnter(); sync();
  return {
    setPaused(value){paused=value;sync();},
    skip(){entrance.finish();rest();},
    replay(){if(disposed)return;drift.pause();drift.currentTime=0;entering=true;entrance.currentTime=0;options.onEnter();sync();},
    dispose(){disposed=true;observer.disconnect();document.removeEventListener("visibilitychange",sync);entrance.onfinish=null;entrance.cancel();drift.cancel();},
  };
}
