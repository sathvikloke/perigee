import { useEffect, useLayoutEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import type { PerigeeApi } from "../api/client";
import type { PresetDescriptor } from "../api/types";
import {
  browserStorage,
  forgetDraft,
  listCards,
  loadStore,
  persistStore,
  removeCard,
  sessionDrafts,
  type EvidenceStore,
} from "../evidence/card";
import { reopenTarget, savedContextKey, type ReopenTarget } from "../evidence/reopen";
import { readSavedList } from "../evidence/savedList";
import { evidenceTitle, type TitleSources } from "../evidence/title";
import { formatDateShort, formatMicrons } from "../lib/format";
import { landingPreview } from "../lib/landingPreview";
import { routeToSearch, type Route } from "../lib/route";
import { ErrorBlock, useAsync } from "./common";
import { resolveAssetSrc } from "../api/client";
import { LandingObservatory } from "./LandingObservatory";
import { LandingIntro } from "./LandingIntro";
import { introEligible } from "../lib/landingIntroMotion";
import { useLandingContentMotion } from "../lib/useLandingContentMotion";
import { createHeroArrivalMotion } from "../lib/heroArrivalMotion";
import { downloadEvidence } from "./Notebook";

const initialHomeVisit = typeof window !== "undefined" && introEligible(window.location.search, window.location.hash);
let introSeen = false;

export function Home(props: {
  api: PerigeeApi;
  onOpenPreset: (id: string) => void;
  onOpenQuery: () => void;
  /** Opens a saved card's investigation; `fixtures` is the card's data origin. */
  onOpenRoute: (route: Route, fixtures: boolean) => void;
  onUseFixture?: () => void;
}) {
  const { state, retry } = useAsync((signal) => props.api.presets(signal), [props.api]);
  const ready = state.status === "ready" ? state.data : [];
  const guided = ready.filter((p) => p.case_ids.length > 0);
  const open = ready.filter((p) => p.case_ids.length === 0);
  const content = useRef<HTMLDivElement>(null);
  useLandingContentMotion(content, ready.length);
  const [introActive, setIntroActive] = useState(() => initialHomeVisit && !introSeen && !window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [heroRevealed, setHeroRevealed] = useState(!introActive);
  const [arrival, setArrival] = useState(false);
  const [introKey, setIntroKey] = useState(0);
  const heroCopy = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (!arrival || !heroCopy.current) return;
    return createHeroArrivalMotion(heroCopy.current, () => setArrival(false));
  }, [arrival]);
  useEffect(() => { introSeen = true; }, []);
  const revealHero = () => { setHeroRevealed(true); setArrival(true); };
  const finishIntro = () => {
    setIntroActive(false);
    window.requestAnimationFrame(() => document.getElementById("hero-title")?.focus({ preventScroll: true }));
  };
  const replayIntro = () => {
    window.scrollTo({ top: 0, behavior: "instant" });
    setHeroRevealed(false); setArrival(false); setIntroKey((key) => key + 1); setIntroActive(true);
  };
  return (
    <div className="home" data-hero-revealed={heroRevealed} data-hero-arrival={arrival}>
      {introActive && <LandingIntro key={introKey} onReveal={revealHero} onFinish={finishIntro} />}
      <section className="landing-hero" aria-labelledby="hero-title">
        <LandingObservatory active={heroRevealed} animateEntrance={arrival} onReplayIntro={replayIntro} />
        <div className="hero-copy" ref={heroCopy}>
          <h1 id="hero-title" tabIndex={-1}>A closer look at<br /><span>a changing sky</span></h1>
          <p className="hero-description">Compare infrared images from NASA’s SPHEREx mission, check what changed, and record what the evidence supports.</p>
          <button className="primary hero-cta" type="button" onClick={() => props.onOpenPreset("barnards_star")}>Start investigating <span className="hero-cta-arrow" aria-hidden="true">↗</span></button>
          {props.api.mode === "fixture" && <p className="hero-source">Development fixture. Not NASA observations.</p>}
        </div>
      </section>

      <div className="home-content" ref={content}>
        <section className="investigations-section" id="investigations" aria-labelledby="presets-h">
          <div className="section-head editorial-heading">
            <div><p className="section-label">Your first investigation</p><h2 id="presets-h">Choose an investigation</h2></div>
            <p>Start with a guided question and real observations you can inspect for yourself.</p>
          </div>
          {state.status === "loading" && <p className="status" role="status">Loading targets…</p>}
          {state.status === "error" && <ErrorBlock title="The target list could not be loaded." error={state.error} onRetry={retry} onUseFixture={props.api.mode === "api" ? props.onUseFixture : undefined} />}
          {state.status === "ready" && (ready.length === 0 ? <p className="status">No targets are published yet.</p> : <>
            <ul className="investigation-grid">
              {guided.map((p) => <PresetItem key={p.id} api={props.api} preset={p} onOpen={() => props.onOpenPreset(p.id)} />)}
            </ul>
            <p className="preview-note">Processed SPHEREx previews. Striped pixels have no usable value; inspect quality flags inside each investigation.</p>
            <div className="open-targets-heading"><h3>Keep exploring</h3><p>Choose a field and follow your own question.</p></div>
            <ul className="open-targets">{open.map((p) => <PresetItem key={p.id} api={props.api} preset={p} onOpen={() => props.onOpenPreset(p.id)} compact />)}</ul>
          </>)}
        </section>

        <section className="evidence-intro" aria-labelledby="evidence-intro-title">
          <div><p className="section-label">Compare, check, explain</p><h2 id="evidence-intro-title">Check what the images support</h2><p>A different wavelength, a flagged pixel, or the way an image is displayed can change what you see. Check those clues, write what the evidence supports, and take your sources with you.</p><a href="#my-evidence" className="text-action">Find your saved evidence</a></div>
          <article className="example-evidence" aria-label="Example reasoning about Barnard's Star">
            <p className="example-heading"><span>Example reasoning</span><span>Barnard’s Star</span></p>
            <h3>The glow shifts north</h3>
            <p>Against the surrounding stars, the bright glow shifts between the two dates.</p>
            <div className="example-observations"><span><b>A</b>25 Aug 2025<small>2.0062 µm</small></span><span><b>C</b>19 Aug 2026<small>2.0284 µm</small></span></div>
            <div className="example-uncertainty"><span>What I still can’t tell</span><p>The core is saturated. These images don’t measure the star’s exact speed or brightness.</p></div>
            <button type="button" className="link" onClick={() => props.onOpenPreset("barnards_star")}>Inspect the source observations</button>
          </article>
        </section>

        <section className="coordinate-invitation" aria-labelledby="query-h">
          <div><p className="section-label">Your object, your question</p><h2 id="query-h">Have a patch of sky in mind?</h2><p>Find SPHEREx observations by object name or sky coordinates.</p></div>
          <button type="button" className="primary" onClick={props.onOpenQuery}>Search archive <span className="home-action-arrow" aria-hidden="true">↗</span></button>
        </section>
        <SavedEvidence api={props.api} presets={state.status === "ready" ? state.data : null} onOpenRoute={props.onOpenRoute} />
      </div>
    </div>
  );
}

const INVESTIGATION_COPY: Record<string, { question: string; description: string }> = {
  barnards_star: { question: "Can you see a star move?", description: "Follow Barnard’s Star across the sky, using the surrounding stars as your reference." },
  epsilon_indi_b: { question: "Is this a fair comparison?", description: "Look at Epsilon Indi B through different infrared wavelengths and separate a change in view from a change in the sky." },
  wise_0855: { question: "A dot that jumps", description: "A bright dot seems to move. Follow the image flags to find out whether the sky really changed." },
};

function PresetItem({ api, preset, onOpen, compact = false }: { api: PerigeeApi; preset: PresetDescriptor; onOpen: () => void; compact?: boolean }) {
  const caseId = preset.case_ids[0] ?? null;
  const { state } = useAsync(async (signal) => {
    const [result, caseContent] = await Promise.all([
      api.presetFrames(preset.id, caseId, signal),
      caseId ? api.caseContent(caseId, signal) : Promise.resolve(null),
    ]);
    return { ...result, caseContent };
  }, [api, preset.id, caseId]);
  const frames = state.status === "ready" ? state.data.frames.filter((f) => f.image) : [];
  const [first, last] = landingPreview(frames, state.status === "ready" ? state.data.caseContent : null);
  const copy = INVESTIGATION_COPY[preset.id];
  return <li className={compact ? "open-target" : "investigation-card"}>
    <button type="button" className="target-link" onClick={onOpen}
      aria-label={copy ? `${preset.display_name}: ${copy.question}` : `Explore ${preset.display_name}`}>
      <span className="target-preview" aria-hidden="true">
        {first?.image ? <img src={resolveAssetSrc(first.image.src)} alt="" loading="lazy" width={256} height={256} /> : <span className="preview-fallback">{state.status === "loading" ? "Loading observation" : "Preview unavailable"}</span>}
        {!compact && last?.image && <img src={resolveAssetSrc(last.image.src)} alt="" loading="lazy" width={256} height={256} />}
        {!compact && first && last && <span className="preview-labels"><span>{formatDateShort(first.observed_at_utc)}<small>{formatMicrons(first.wavelength_um)}</small></span><span>{formatDateShort(last.observed_at_utc)}<small>{formatMicrons(last.wavelength_um)}</small></span></span>}
      </span>
      <span className="target-copy">
        <span className="target-overline">{preset.display_name}</span>
        <span className="target-title">{copy?.question ?? preset.display_name}</span>
        <span className="target-description">{copy?.description ?? preset.one_line}</span>
        <span className="target-footer"><span>{compact ? "Open exploration" : "Guided investigation"}<span className="home-action-arrow" aria-hidden="true">↗</span></span><span>{preset.frame_count ? `${preset.frame_count} observations` : "Explore target"}</span></span>
      </span>
    </button>
  </li>;
}

function SavedEvidence(props: {
  api: PerigeeApi;
  presets: PresetDescriptor[] | null;
  onOpenRoute: (route: Route, fixtures: boolean) => void;
}) {
  const [store, setStore] = useState<EvidenceStore>(() => readSavedList(browserStorage()).store);
  // Read again once mounted: the investigation just left saves its last
  // edit in its unmount cleanup, after this list first rendered (see savedList.ts).
  useEffect(() => setStore(readSavedList(browserStorage()).store), []);
  const cards = useMemo(() => listCards(store), [store]);
  const [failed, setFailed] = useState(false);
  const caseIds = useMemo(
    () => [...new Set(cards.map(({ card }) => card.case_id).filter((id): id is string => Boolean(id)))].sort(),
    [cards],
  );
  // Case titles for the card headings. A failed lookup only costs the
  // case title; the target name or coordinates still identify the card.
  const { state: caseState } = useAsync(
    async (signal) =>
      Object.fromEntries(
        (
          await Promise.all(
            caseIds.map((id) =>
              props.api.caseContent(id, signal).then(
                (c) => [[id, { title: c.title, target_id: c.target_id }]] as const,
                () => [],
              ),
            ),
          )
        ).flat(),
      ),
    [props.api, caseIds.join("|")],
  );
  const sources: TitleSources = {
    presets: props.presets,
    cases: caseState.status === "ready" ? caseState.data : null,
  };
  const remove = (id: string) => {
    if (!window.confirm("Delete this evidence card from this browser? This cannot be undone; export it first to keep a copy.")) {
      return;
    }
    const storage = browserStorage();
    forgetDraft(id);
    const next = removeCard(loadStore(storage), id);
    setFailed(!persistStore(storage, next));
    setStore(next);
  };
  return (
    <section className="card" id="my-evidence" aria-labelledby="saved-h">
      <div className="section-head">
        <h2 id="saved-h" tabIndex={-1}>My evidence</h2>
        <p>Cards are saved only in this browser. Reopen one to keep working, or export it to keep or share it.</p>
      </div>
      {cards.length === 0 ? (
        <p className="status">No evidence cards yet. Open a target and write in its notebook.</p>
      ) : (
        <ul className="saved-list">
          {cards.map(({ card: c, unsaved }) => {
            const title = evidenceTitle(c, sources);
            const target = reopenTarget(c, savedContextKey(c.id, store, sessionDrafts));
            return (
              <li key={c.id}>
                <span className="saved-summary">
                  <strong className="saved-title">{title}</strong>
                  {c.data_origin === "fixture" && <span className="fixture-tag"> (development fixture)</span>}
                  {unsaved && <span className="fixture-tag"> (not saved on this device; export to keep it)</span>}
                  <span className="muted block">
                    Updated {formatDateShort(c.updated_at_utc)}. {c.frames.length} observation
                    {c.frames.length === 1 ? "" : "s"}
                    {c.claim ? `. “${c.claim.slice(0, 80)}${c.claim.length > 80 ? "…" : ""}”` : ". No claim yet."}
                  </span>
                </span>
                <span className="actions">
                  {target && <ReopenLink target={target} title={title} onOpen={props.onOpenRoute} />}
                  <button type="button" onClick={() => downloadEvidence(c)}>
                    Export JSON
                  </button>
                  <button type="button" className="link" onClick={() => remove(c.id)}>
                    Delete from this browser
                  </button>
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {failed && <p role="alert">This browser would not update its saved evidence.</p>}
    </section>
  );
}

/**
 * A real link (it can be opened in a new tab and its URL shared): the URL
 * carries only the target or coordinates, never the notes, which stay in
 * this browser and come back through the notebook's own context key.
 */
function ReopenLink(props: {
  target: ReopenTarget;
  title: string;
  onOpen: (route: Route, fixtures: boolean) => void;
}) {
  const { route, fixtures } = props.target;
  const href = `${window.location.pathname}${routeToSearch(route, fixtures)}`;
  const onClick = (e: MouseEvent<HTMLAnchorElement>) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    props.onOpen(route, fixtures);
  };
  return (
    // The accessible name starts with the visible word, then names the card.
    <a className="reopen" href={href} onClick={onClick} aria-label={`Reopen ${props.title}`}>
      Reopen
    </a>
  );
}
