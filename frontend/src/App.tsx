import { useCallback, useEffect, useMemo, useState } from 'react';
import { ApiError, api } from './api/client';
import type { FrameRecord, PresetDescriptor } from './api/types';
import { Notebook } from './components/Notebook';
import { Picker } from './components/Picker';
import { Plate, PlatePlaceholder } from './components/Plate';
import type { EvidenceContext } from './evidence';
import {
  QUALITY_TEXT,
  classifyPair,
  detectorLabel,
  formatDate,
  formatWavelength,
  pairInsight,
  qualityStatus,
  releaseLabel,
} from './format';
import { sourceFromSearch, sourceToSearch, type Source } from './source';
import { useInvestigation, type View } from './useInvestigation';

type Pair = [number, number];
type Blink = 'off' | 'playing' | 'paused';

const CASE_EYEBROW: Record<string, string> = { fair_comparison: '01 / Fair comparisons', moving_neighbor: '02 / Moving neighbor' };
const PAIR_SUBLABEL = { same_time: 'Different wavelengths', fair_time: 'Different dates', mixed: 'Dates and wavelengths', unknown: 'Check metadata' };
const ARCHIVE = { label: 'SPHEREx data at NASA/IPAC IRSA', url: 'https://irsa.ipac.caltech.edu/Missions/spherex.html' };

const mq = (q: string) => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(q) : null);

function defaultPair(view: View | null): Pair | null {
  if (!view) return null;
  if (view.pairs?.length) return view.pairs[0];
  const ready = view.slots.map((s, i) => (s.status === 'ready' ? i : -1)).filter((i) => i >= 0);
  if (ready.length < 2) return null;
  // Prefer the longest-baseline pair at matching wavelength, favouring frames that pass the flag screen.
  let best: Pair | null = null;
  let bestScore = -1;
  for (const i of ready)
    for (const j of ready) {
      if (j <= i) continue;
      const fi = view.slots[i].frame!;
      const fj = view.slots[j].frame!;
      if (classifyPair(fi, fj) !== 'fair_time') continue;
      const clear = (qualityStatus(fi) === 'clear' ? 1 : 0) + (qualityStatus(fj) === 'clear' ? 1 : 0);
      const score = clear * 1e6 + Math.abs((fj.mjd ?? 0) - (fi.mjd ?? 0));
      if (score > bestScore) [best, bestScore] = [[i, j], score];
    }
  return best ?? [ready[0], ready[ready.length - 1]];
}

function frameHeading(f: FrameRecord, other: FrameRecord): string {
  const kind = classifyPair(f, other);
  if (kind === 'same_time') {
    if (f.wavelength_um == null || other.wavelength_um == null) return 'Same moment';
    return f.wavelength_um <= other.wavelength_um ? 'Shorter wavelength' : 'Longer wavelength';
  }
  if (f.mjd == null || other.mjd == null) return 'Observation';
  return f.mjd <= other.mjd ? 'Earlier observation' : 'Later observation';
}

function optionLabel(f: FrameRecord, i: number): string {
  return `#${i + 1} · ${formatDate(f.observed_at_utc) ?? 'date n/a'} · ${formatWavelength(f.wavelength_um) ?? 'λ n/a'} · ${releaseLabel(f.collection_id)} D${f.detector ?? '?'} · ${QUALITY_TEXT[qualityStatus(f)].label}`;
}

export default function App() {
  const [source, setSource] = useState<Source>(() => sourceFromSearch(window.location.search));
  const [presets, setPresets] = useState<PresetDescriptor[]>([]);
  const [presetsError, setPresetsError] = useState<string | null>(null);
  const { view, request, load, retrySlot } = useInvestigation();

  const [pairChoice, setPairChoice] = useState<{ key: string; pair: Pair } | null>(null);
  const [shown, setShown] = useState<0 | 1>(0);
  const [blink, setBlink] = useState<Blink>('off');
  const [showMarker, setShowMarker] = useState(true);
  const [flagsChoice, setFlagsChoice] = useState<boolean | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    api
      .presets(ctl.signal)
      .then((r) => setPresets(r.presets))
      .catch((e) => {
        if (e instanceof ApiError) setPresetsError(`Target list unavailable: ${e.message}`);
      });
    return () => ctl.abort();
  }, []);

  useEffect(() => {
    load(source);
  }, [source, load]);

  useEffect(() => {
    const onPop = () => setSource(sourceFromSearch(window.location.search));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const pick = useCallback((s: Source) => {
    window.history.pushState(null, '', sourceToSearch(s));
    setSource(s);
  }, []);

  const pair = (pairChoice && view && pairChoice.key === view.key ? pairChoice.pair : null) ?? defaultPair(view);
  const left = pair ? view!.slots[pair[0]] : null;
  const right = pair ? view!.slots[pair[1]] : null;
  const a = left?.status === 'ready' ? left.frame! : null;
  const b = right?.status === 'ready' ? right.frame! : null;
  const isCase = !!view?.caseData;
  const letters: [string, string] = isCase && left && right ? [left.ref, right.ref] : ['A', 'B'];

  // Leaving a pair, an investigation or the phone breakpoint stops blinking.
  const pairKey = `${view?.key}|${pair?.join(',')}`;
  useEffect(() => {
    setBlink('off');
    setShown(0);
  }, [pairKey]);

  useEffect(() => {
    if (blink !== 'playing') return;
    const reduced = mq('(prefers-reduced-motion: reduce)')?.matches;
    const id = window.setInterval(() => setShown((s) => (s === 0 ? 1 : 0)), reduced ? 1500 : 1000);
    return () => window.clearInterval(id);
  }, [blink]);

  useEffect(() => {
    const pause = () => document.hidden && setBlink((b) => (b === 'playing' ? 'paused' : b));
    const stop = () => setBlink('off');
    const small = mq('(max-width: 560px)');
    document.addEventListener('visibilitychange', pause);
    window.addEventListener('beforeprint', stop);
    small?.addEventListener('change', stop);
    return () => {
      document.removeEventListener('visibilitychange', pause);
      window.removeEventListener('beforeprint', stop);
      small?.removeEventListener('change', stop);
    };
  }, []);

  const startBlink = () => {
    setShown(0);
    setBlink(mq('(prefers-reduced-motion: reduce)')?.matches ? 'paused' : 'playing');
  };

  const choose = (side: 0 | 1, index: number) => {
    if (!view || !pair) return;
    const next: Pair = side === 0 ? [index, pair[1]] : [pair[0], index];
    setPairChoice({ key: view.key, pair: next });
  };

  // ----- derived content -----
  const caseData = view?.caseData ?? null;
  const presetId = caseData?.target_id ?? (view?.source.kind === 'preset' ? view.source.presetId : null);
  const preset = presets.find((p) => p.id === presetId) ?? null;
  const targetName = !view ? 'Loading…' : preset?.display_name ?? (presetId ? presetId : 'Sky position');
  const vs = view?.source;

  let eyebrow = 'SPHEREx investigation';
  let accent = '';
  let title = 'Loading investigation…';
  let intro = '';
  if (vs?.kind === 'case' && caseData) {
    accent = CASE_EYEBROW[caseData.case_id] ?? caseData.case_id;
    title = caseData.title;
    intro = caseData.opening_question;
  } else if (vs?.kind === 'preset') {
    eyebrow = 'Named target';
    accent = `${view!.slots.length} retained frames`;
    title = `Compare two observations of ${targetName}`;
    intro = preset?.one_line ?? 'Pick any two retained frames. Check their dates, wavelengths and quality before deciding what changed.';
  } else if (vs?.kind === 'coords') {
    eyebrow = 'Live coordinates';
    accent = 'NASA/IPAC IRSA';
    title = `Compare observations at RA\u00a0${vs.ra.toFixed(4)}°, Dec\u00a0${vs.dec.toFixed(4).replace('-', '−')}°`;
    intro = `A ${vs.fov} arcmin field searched live in SPHEREx DR1 and QR3. Pick two processed frames and check whether the comparison is fair.`;
  }

  const insight = a && b ? pairInsight(a, b, letters[0], letters[1]) : null;
  const guideY = useMemo(() => {
    if (!caseData?.display_requirements?.reference_line) return null;
    const first = view?.slots[0]?.frame;
    return first?.marker ? (first.marker.y / (first.image.height || 256)) * 100 : null;
  }, [caseData, view]);

  const evidence: EvidenceContext | null = useMemo(() => {
    if (!view) return null;
    const selected = a && b ? [{ ref: letters[0], frame: a }, { ref: letters[1], frame: b }] : [];
    const lim = new Set<string>([...(caseData?.limitations ?? []), ...selected.flatMap((s) => s.frame.limitations ?? [])]);
    return {
      investigationKey: view.key,
      caseId: caseData?.case_id ?? null,
      presetId,
      query:
        view.source.kind === 'coords'
          ? { ra_deg: view.source.ra, dec_deg: view.source.dec, fov_arcmin: view.source.fov }
          : null,
      comparison: insight ? `${letters[0]} + ${letters[1]}: ${insight.title}` : 'No pair selected',
      selected,
      sources: caseData?.sources ?? [ARCHIVE],
      limitations: [...lim],
    };
  }, [view, a, b, letters[0], letters[1], caseData, presetId, insight?.title]);

  const busy = request.phase === 'loading';
  const readyCount = view?.slots.filter((s) => s.status === 'ready').length ?? 0;
  const loadingCount = view?.slots.filter((s) => s.status === 'loading').length ?? 0;
  const failed = view ? view.slots.map((s, i) => ({ s, i })).filter(({ s }) => s.status === 'failed') : [];
  const search = view?.search ?? null;
  const plates: { slot: typeof left; frame: FrameRecord | null; other: FrameRecord | null }[] = [
    { slot: left, frame: a, other: b },
    { slot: right, frame: b, other: a },
  ];
  const blinking = blink !== 'off';
  const anyFlagged = [a, b].some((f) => f && qualityStatus(f) === 'flagged');
  const showFlags = flagsChoice ?? anyFlagged;
  const legend = showFlags ? flagLegend([a, b]) : [];
  const notClear = a && b ? ([[letters[0], a], [letters[1], b]] as const).filter(([, f]) => qualityStatus(f) !== 'clear') : [];
  const qualityNote = notClear.length
    ? `Quality: ${notClear.map(([r, f]) => `${r} is ${QUALITY_TEXT[qualityStatus(f)].label.toLowerCase()}`).join('; ')}. Open the quality details before reading anything into brightness at the target.`
    : null;

  return (
    <>
      <a className="skip" href="#investigation">
        Skip to investigation
      </a>
      <header className="topbar">
        <a href="#investigation" className="brand" aria-label="Perigee home">
          <svg viewBox="0 0 36 36" aria-hidden="true">
            <circle cx="18" cy="18" r="10" />
            <ellipse cx="18" cy="18" rx="17" ry="6" transform="rotate(-36 18 18)" />
            <circle className="satellite" cx="29" cy="9" r="3" />
          </svg>
          perigee<span className="brand-divider" />
          <span className="brand-caption">
            A closer look at
            <br />
            our infrared sky
          </span>
        </a>
        <nav aria-label="Page navigation">
          <a href="#investigation" className="active">
            Investigation
          </a>
          <a href="#notebook">My evidence</a>
          <a href="#sources">
            Sources <span aria-hidden="true">↗</span>
          </a>
        </nav>
      </header>

      <main id="investigation" aria-busy={busy}>
        <Picker source={source} presets={presets} presetsError={presetsError} busy={busy} onPick={pick} key={sourceToSearch(source)} />

        <div className="heading-row">
          <div>
            <p className="eyebrow">
              {eyebrow} {accent ? <span>{accent}</span> : null}
            </p>
            <h1>{title}</h1>
            {intro ? <p className="intro">{intro}</p> : null}
          </div>
          {readyCount > 0 ? (
            <span className="real-data">
              <span aria-hidden="true">✦</span> Real NASA / IPAC observations
            </span>
          ) : null}
        </div>

        <div className="workspace">
          <section className="bench" aria-label="Observation comparison">
            <ol className="steps">
              <li>
                <span className="step-num">1</span>
                <div>
                  <strong>Compare</strong>
                  <span>Time and wavelength</span>
                </div>
              </li>
              <li>
                <span className="step-num">2</span>
                <div>
                  <strong>Check</strong>
                  <span>Quality and context</span>
                </div>
              </li>
              <li>
                <span className="step-num">3</span>
                <div>
                  <strong>Explain</strong>
                  <span>What the evidence says</span>
                </div>
              </li>
            </ol>

            <div className="target-line">
              <div>
                <span className="eyebrow">Your target</span>
                <h2>
                  {targetName} {preset?.object_type ? <span className="tag">{shortType(preset.object_type)}</span> : null}
                </h2>
              </div>
              {vs?.kind === 'coords' ? (
                <p>
                  {vs.fov} arcmin field
                  <br />
                  <span>ICRS decimal degrees</span>
                </p>
              ) : view ? (
                <p>
                  {view.slots.length} frames loaded
                  <br />
                  <span>Curated, verified products</span>
                </p>
              ) : null}
            </div>

            <RequestBanner request={request} hasView={!!view} viewTitle={title} onRetry={() => load(source)} />

            {search ? (
              <div className={`search-status${search.status === 'partial' ? ' warn' : ''}`} role="status">
                {search.status === 'empty' ? (
                  <p>
                    <strong>No SPHEREx observations matched.</strong> The archive answered: DR1 and QR3 have no image covering this
                    position and field. That says nothing about other collections or missions.
                  </p>
                ) : (
                  <p>
                    <strong>
                      {search.returned_count} observation{search.returned_count === 1 ? '' : 's'} found
                      {search.total_matches != null && search.truncated ? ` (of ${search.total_matches})` : ''}
                    </strong>{' '}
                    · {readyCount} ready{loadingCount ? ` · ${loadingCount} still loading` : ''}
                    {failed.length ? ` · ${failed.length} could not be processed` : ''}
                  </p>
                )}
                {search.status === 'partial' && search.collections_failed?.length ? (
                  <p>Some collections did not answer ({search.collections_failed.join(', ')}). Results from the others are shown.</p>
                ) : null}
                {search.warnings.map((w) => (
                  <p key={w}>{w}</p>
                ))}
              </div>
            ) : null}

            <div className="comparison-shell">
              <div className="comparison-toolbar">
                {isCase && view?.pairs ? (
                  <div className="segmented pair-control" role="group" aria-label="Choose comparison">
                    {view.pairs.map((p) => {
                      const fa = view.slots[p[0]].frame;
                      const fb = view.slots[p[1]].frame;
                      const kind = fa && fb ? classifyPair(fa, fb) : 'unknown';
                      const pressed = pair?.[0] === p[0] && pair?.[1] === p[1];
                      return (
                        <button key={p.join()} type="button" aria-pressed={pressed} onClick={() => setPairChoice({ key: view.key, pair: p })}>
                          {view.slots[p[0]].ref} + {view.slots[p[1]].ref} <span>{PAIR_SUBLABEL[kind]}</span>
                        </button>
                      );
                    })}
                  </div>
                ) : view && readyCount >= 2 && pair ? (
                  <div className="frame-selects">
                    {([0, 1] as const).map((side) => (
                      <label key={side}>
                        <span>Plate {side === 0 ? 'A' : 'B'}</span>
                        <select value={pair[side]} onChange={(e) => choose(side, Number(e.target.value))}>
                          {view.slots.map((s, i) =>
                            s.status === 'ready' ? (
                              <option key={i} value={i}>
                                {optionLabel(s.frame!, i)}
                              </option>
                            ) : null,
                          )}
                        </select>
                      </label>
                    ))}
                  </div>
                ) : (
                  <span />
                )}
                {a && b ? (
                  blinking ? (
                    <div className="blink-controls">
                      <button type="button" className="quiet" aria-pressed={blink === 'playing'} onClick={() => setBlink(blink === 'playing' ? 'paused' : 'playing')}>
                        {blink === 'playing' ? 'Ⅱ Pause blink' : '▷ Play blink'}
                      </button>
                      <button type="button" className="quiet" onClick={() => setBlink('off')}>
                        Side by side
                      </button>
                    </div>
                  ) : (
                    <button type="button" className="quiet" onClick={startBlink}>
                      ▷ Blink pair
                    </button>
                  )
                ) : null}
              </div>

              {failed.length ? (
                <div className="frame-failures" role="alert">
                  {failed.map(({ s, i }) => (
                    <p key={i}>
                      <span>
                        Frame #{i + 1}
                        {s.descriptor?.frame_key ? ` (${s.descriptor.frame_key})` : ''}: {s.error?.message ?? 'could not be processed.'}
                      </span>
                      {s.error?.code === 'TOKEN_EXPIRED' ? (
                        <button type="button" onClick={() => load(source)}>
                          Search again
                        </button>
                      ) : s.descriptor && s.error?.retryable !== false ? (
                        <button type="button" onClick={() => retrySlot(i)}>
                          Retry frame
                        </button>
                      ) : null}
                    </p>
                  ))}
                </div>
              ) : null}

              {a && b ? (
                <div className="mobile-frame-control" role="group" aria-label="Visible observation">
                  {([0, 1] as const).map((i) => (
                    <button key={i} type="button" aria-pressed={shown === i} onClick={() => setShown(i)}>
                      Observation {letters[i]}
                    </button>
                  ))}
                </div>
              ) : null}

              <div className={`plates${blinking ? ' blinking' : ''}${!showMarker ? ' markers-hidden' : ''}`}>
                {plates.map(({ slot, frame, other }, i) => {
                  const hidden = shown !== i;
                  if (frame && other)
                    return (
                      <Plate
                        key={i}
                        letter={letters[i]}
                        heading={frameHeading(frame, other)}
                        frame={frame}
                        targetName={targetName}
                        showMarker={showMarker}
                        showFlags={showFlags}
                        guideY={guideY}
                        hidden={hidden}
                      />
                    );
                  if (frame)
                    return <Plate key={i} letter={letters[i]} heading="Observation" frame={frame} targetName={targetName} showMarker={showMarker} showFlags={showFlags} hidden={hidden && i !== 0} />;
                  const msg =
                    search?.status === 'empty'
                      ? 'No archive image to show for this position.'
                      : slot?.status === 'failed'
                        ? slot.error?.message ?? 'This observation could not be processed.'
                        : loadingCount > 0 || busy
                          ? 'Processing an observation…'
                          : !view && request.phase === 'error'
                            ? 'Nothing loaded yet.'
                            : view && readyCount < 2
                              ? 'Fewer than two observations could be processed for a comparison.'
                              : 'Loading…';
                  return <PlatePlaceholder key={i} letter={letters[i]} title={i === 0 ? 'First observation' : 'Second observation'} message={msg} />;
                })}
              </div>

              <div className="view-controls">
                <div className="toggles">
                  <label>
                    <input type="checkbox" checked={showMarker} onChange={(e) => setShowMarker(e.target.checked)} /> Show predicted position
                  </label>
                  <label>
                    <input type="checkbox" checked={showFlags} onChange={(e) => setFlagsChoice(e.target.checked)} /> Show flagged pixels
                  </label>
                </div>
                <span>Same sky grid · north up, east left{guideY != null ? ' · guide line at A’s prediction' : ''}</span>
              </div>
              <p className="flag-legend">
                <span className="no-data-key">
                  <i aria-hidden="true" /> Hatched: no usable data (outside the cutout, or saturated / non-finite pixels)
                </span>
                {legend.map((l) => (
                  <span key={l.name}>
                    <i aria-hidden="true" style={{ background: l.css }} /> {l.label}
                  </span>
                ))}
              </p>

              {insight ? (
                <div className={`comparison-insight${insight.warn ? ' different' : ''}`} aria-live="polite">
                  <span className="insight-icon" aria-hidden="true">
                    ↔
                  </span>
                  <div>
                    <strong>{insight.title}</strong>
                    <p>{insight.body}</p>
                    {qualityNote ? <p>{qualityNote}</p> : null}
                    {a?.display_scale?.mode !== b?.display_scale?.mode || a?.display_scale?.mode === 'per_frame' ? (
                      <p>Brightness is scaled separately for at least one frame, so grey levels are not directly comparable.</p>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>

            <QualityDetails frames={a && b ? [[letters[0], a], [letters[1], b]] : []} />
            <SourceDetails frames={a && b ? [[letters[0], a], [letters[1], b]] : []} sources={evidence?.sources ?? [ARCHIVE]} />
            {caseData ? (
              <details className="source-details">
                <summary>
                  <span>
                    <span className="section-icon" aria-hidden="true">?</span> About this investigation
                  </span>
                  <span className="expand" aria-hidden="true">+</span>
                </summary>
                <div className="details-body">
                  {caseData.background?.short ? <p>{caseData.background.short}</p> : null}
                  <ol className="case-steps">
                    {caseData.steps.map((s) => (
                      <li key={s.id}>{s.prompt}</li>
                    ))}
                  </ol>
                  {caseData.background?.details?.length ? (
                    <ul className="case-details">
                      {caseData.background.details.map((d) => (
                        <li key={d}>{d}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </details>
            ) : null}
          </section>

          <Notebook context={evidence} claimHint={caseData?.claim_prompt} attached={a && b ? `${letters[0]} + ${letters[1]}` : 'None yet'} />
        </div>

        <PrintProvenance frames={a && b ? [[letters[0], a], [letters[1], b]] : []} title={title} />

        <footer>
          <span>
            PERIGEE <span className="footer-dot">·</span> Explore what the evidence supports
          </span>
          <a href={ARCHIVE.url} target="_blank" rel="noopener">
            Explore the SPHEREx archive ↗
          </a>
        </footer>
      </main>
    </>
  );
}

const LEGEND_LABELS: Record<string, string> = { adverse_flag: 'Problem flag', non_finite: 'Non-finite value' };

/** Overlay colours come from each record's legend; nothing is hard-coded. */
function flagLegend(frames: (FrameRecord | null)[]) {
  const seen = new Map<string, { name: string; label: string; css: string }>();
  for (const f of frames) {
    for (const [name, rgba] of Object.entries(f?.flag_image?.legend ?? {})) {
      if (!Array.isArray(rgba) || rgba.length < 3) continue;
      const [r, g, b, alpha = 255] = rgba;
      const css = `rgba(${r}, ${g}, ${b}, ${Math.max(alpha / 255, 0.6).toFixed(2)})`;
      const key = `${name}|${css}`;
      if (!seen.has(key)) seen.set(key, { name: key, label: LEGEND_LABELS[name] ?? name.replace(/_/g, ' '), css });
    }
  }
  return [...seen.values()];
}

function shortType(t: string): string {
  return t.replace(/\s*\(.*?\)\s*/g, ' ').replace(/,.*$/, '').trim();
}

function RequestBanner({ request, hasView, viewTitle, onRetry }: { request: ReturnType<typeof useInvestigation>['request']; hasView: boolean; viewTitle: string; onRetry: () => void }) {
  if (request.phase === 'loading') {
    const what = request.source.kind === 'coords' ? 'Searching the NASA/IPAC archive…' : 'Loading observations…';
    return (
      <div className="banner" role="status">
        {what}
      </div>
    );
  }
  if (request.phase === 'error') {
    const e = request.error;
    const archive = e.code.startsWith('UPSTREAM') || e.code === 'RATE_LIMITED';
    return (
      <div className="banner error" role="alert">
        <p>
          <strong>{archive ? 'The archive request did not complete.' : 'This request failed.'}</strong> {e.message}
          {hasView ? ` The images from “${viewTitle}” are still shown, and your notes are kept.` : ' Your notes are kept.'}
        </p>
        {e.retryable || e.code === 'NETWORK' || e.code === 'BAD_RESPONSE' ? (
          <button type="button" onClick={onRetry}>
            Try again
          </button>
        ) : null}
      </div>
    );
  }
  return null;
}

function QualityDetails({ frames }: { frames: [string, FrameRecord][] }) {
  return (
    <details className="quality-details">
      <summary>
        <span>
          <span className="section-icon" aria-hidden="true">✓</span> What does the flag screen mean?
        </span>
        <span className="expand" aria-hidden="true">+</span>
      </summary>
      <div className="details-body">
        <p>
          Each frame is screened for problem flags (saturation, cosmic-ray hits, detector defects) in a small circle around the predicted target
          position, or the search center for live coordinates. Passing means no problem flags were found there. It does not prove a detection or measure
          brightness. Missing quality data is shown as unknown, never as clear.
        </p>
        <div className="quality-grid">
          {frames.map(([ref, f]) => {
            const q = qualityStatus(f);
            return (
              <div key={ref}>
                <strong>
                  {ref} · {QUALITY_TEXT[q].label}
                </strong>
                <p>
                  Covered: {f.quality?.covered == null ? 'unknown' : f.quality.covered ? 'yes' : 'no'} · Valid pixels:{' '}
                  {f.quality?.valid_aperture_pixels ?? 'unknown'} · Flagged pixels: {f.quality?.adverse_aperture_pixels ?? 'unknown'}
                </p>
                {f.quality?.flag_names?.length ? <p>Flags: {f.quality.flag_names.join(', ')}</p> : null}
                {(f.quality?.notes ?? []).map((n) => (
                  <p key={n}>{n}</p>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </details>
  );
}

function SourceDetails({ frames, sources }: { frames: [string, FrameRecord][]; sources: { label: string; url: string }[] }) {
  const f0 = frames[0]?.[1];
  return (
    <details className="source-details" id="sources">
      <summary>
        <span>
          <span className="section-icon" aria-hidden="true">≡</span> Observation sources & processing
        </span>
        <span className="expand" aria-hidden="true">+</span>
      </summary>
      <div className="details-body">
        <p className="source-intro">Each image can be traced back to its original SPHEREx observation.</p>
        <div className="table-scroll">
          <table>
            <caption className="sr-only">Selected observation provenance</caption>
            <thead>
              <tr>
                <th>Frame</th>
                <th>Date (UTC)</th>
                <th>Wavelength</th>
                <th>Quality</th>
                <th>Original data</th>
              </tr>
            </thead>
            <tbody>
              {frames.map(([ref, f]) => (
                <tr key={ref}>
                  <td>{ref}</td>
                  <td>{f.observed_at_utc ?? 'not provided'}</td>
                  <td>{formatWavelength(f.wavelength_um) ?? 'not provided'}</td>
                  <td>{QUALITY_TEXT[qualityStatus(f)].label}</td>
                  <td>
                    <a href={f.source_url} target="_blank" rel="noopener">
                      {releaseLabel(f.collection_id)} / D{f.detector ?? '?'} FITS ↗
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {f0 ? (
          <p className="processing">
            Fixed {f0.registration?.width ?? f0.image.width} × {f0.registration?.height ?? f0.image.height} grid at{' '}
            {f0.registration?.scale_arcsec_per_px?.toFixed(3) ?? '?'} arcsec/pixel (native ≈{' '}
            {f0.registration?.native_scale_arcsec_per_px?.toFixed(2) ?? '?'}″; resampling adds no resolution),{' '}
            {f0.registration?.orientation?.replace(/_/g, ' ') ?? 'orientation not stated'}, {f0.registration?.method?.replace(/_/g, ' ') ?? 'method not stated'}.{' '}
            {f0.display_scale?.basis ?? ''} Processing {f0.provenance?.processing_version ?? 'version not stated'}.
          </p>
        ) : null}
        {frames.map(([ref, f]) =>
          f.wavelength_location ? (
            <p className="processing" key={ref}>
              {ref} wavelength: {f.wavelength_location}
            </p>
          ) : null,
        )}
        <ul className="source-links">
          {sources.map((s) => (
            <li key={s.url}>
              <a href={s.url} target="_blank" rel="noopener">
                {s.label} ↗
              </a>
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}

function PrintProvenance({ frames, title }: { frames: [string, FrameRecord][]; title: string }) {
  return (
    <section className="print-provenance" aria-label="Printed observation provenance">
      <h2>Selected observation provenance · {title}</h2>
      {frames.map(([ref, f]) => (
        <div key={ref}>
          <h3>
            Observation {ref} · {f.frame_id}
          </h3>
          <p>
            Observation ID: {f.observation_id} | {detectorLabel(f)} | Collection: {f.collection_id} ({releaseLabel(f.collection_id)}
            {f.provenance?.pipeline_version ? `, ${f.provenance.pipeline_version}` : ''})
          </p>
          <p>
            UTC: {f.observed_at_utc ?? 'not provided'} | MJD: {f.mjd ?? 'not provided'} | Wavelength: {formatWavelength(f.wavelength_um) ?? 'not provided'}
            {f.bandwidth_um != null ? ` (band ${f.bandwidth_um.toFixed(4)} µm)` : ''} | Flag screen: {QUALITY_TEXT[qualityStatus(f)].label}
          </p>
          <p>Source: {f.source_url}</p>
          {f.provenance?.sha256 ? <p>Source SHA-256: {f.provenance.sha256}</p> : null}
          <p>
            Processing: {f.provenance?.processing_version ?? 'not stated'}; {f.registration?.method ?? ''} onto grid {f.registration?.grid_id ?? ''} at{' '}
            {f.registration?.scale_arcsec_per_px ?? '?'} arcsec/px; {f.display_scale?.mode ?? '?'} {f.display_scale?.method ?? ''} stretch.
          </p>
        </div>
      ))}
      <p>Markers are catalog predictions, not detections. A passed flag screen is not a detection or brightness measurement.</p>
    </section>
  );
}
