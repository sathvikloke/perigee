import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { compareChronological, type PerigeeApi } from "../api/client";
import type { CaseContent, FrameRecord, PresetDescriptor, PresetFramesResult } from "../api/types";
import { attachPair, createEvidenceCard, type EvidenceCard } from "../evidence/card";
import { useEvidenceCard } from "../evidence/useEvidenceCard";
import { presetContextKey } from "../evidence/reopen";
import { reviewStep } from "../evidence/completion";
import { CaseBench } from "./CaseBench";
import { ErrorBlock, useAsync } from "./common";
import { FrameViewer, type FrameSlot } from "./FrameViewer";
import { Notebook, type RequiredPairRecovery } from "./Notebook";
import { useContentCue } from "../lib/contentMotion";
import "../styles/content-motion.css";
import { InvestigationSwitcher, PageHeading } from "./PageHeading";

// Short orientation for the working view. The complete authored opening is
// preserved in the context disclosure below the comparison.
const CASE_INTROS: Record<string, string> = {
  moving_neighbor: "Compare a year of observations to see how Barnard’s Star shifts against the surrounding stars.",
  fair_comparison: "Compare dates, wavelengths and image quality before deciding what changed.",
  wise_0855_quality_trap: "Check whether a jumping dot is a change in the sky or a clue in the detector.",
};

function stepPrompt(prompt: string): string {
  return prompt.replace(/\bBlink pair\b/g, "Play comparison")
    .replace(/\bBlink the three frames\b/g, "Play each image pair")
    .replace(/\bBlink A and B\b/g, "Play images A and B");
}

function focusInvestigationSection(id: string) {
  window.requestAnimationFrame(() => {
    const section = document.getElementById(id);
    section?.scrollIntoView({ block: "start", behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    section?.focus({ preventScroll: true });
  });
}

interface Loaded {
  presets: PresetDescriptor[];
  preset: PresetDescriptor | null;
  /** The preset's full `frames` set, for free stepping. */
  sequence: FrameRecord[];
  /** The case's own products; the selected pair determines stretch compatibility. */
  caseFrames: FrameRecord[];
  status: PresetFramesResult["status"];
  reason: string | null;
  warnings: string[];
  caseContent: CaseContent | null;
  caseError: unknown;
  caseFramesError: unknown;
}

export function PresetInvestigation(props: {
  api: PerigeeApi;
  presetId: string;
  caseId?: string;
  onUseFixture?: () => void;
  onQueryPosition: (preset: PresetDescriptor) => void;
  onOpenPreset: (id: string) => void;
  onOpenQuery: () => void;
  onChooseInvestigation: () => void;
}) {
  const { api, presetId } = props;
  const { state, retry } = useAsync<Loaded>(
    async (signal) => {
      const presets = await api.presets(signal);
      const preset = presets.find((p) => p.id === presetId) ?? null;
      const caseId = props.caseId === "none" ? null : props.caseId ?? preset?.case_ids[0] ?? null;
      const [all, caseSet, caseResult] = await Promise.all([
        api.presetFrames(presetId, null, signal),
        caseId ? api.presetFrames(presetId, caseId, signal).then(
          (value) => ({ value, error: null as unknown }),
          (error: unknown) => ({ value: null, error }),
        ) : Promise.resolve({ value: null, error: null }),
        caseId
          ? api.caseContent(caseId, signal).then(
              (c) => ({ c, err: null as unknown }),
              (err: unknown) => ({ c: null, err }),
            )
          : Promise.resolve({ c: null, err: null as unknown }),
      ]);
      return {
        presets,
        preset,
        sequence: all.frames,
        caseFrames: caseSet.value?.frames ?? [],
        status: all.frames.length || caseSet.value?.frames.length ? all.status : "missing",
        reason: all.reason ?? caseSet.value?.reason ?? null,
        warnings: [...all.warnings, ...(caseSet.value?.warnings ?? [])],
        caseContent: caseResult.c,
        caseError: caseResult.err,
        caseFramesError: caseSet.error,
      };
    },
    [api, presetId, props.caseId],
  );

  if (state.status === "loading") {
    return (
      <p className="status" role="status">
        Loading the investigation images…
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <ErrorBlock
        title="The images for this target could not be loaded."
        error={state.error}
        onRetry={retry}
        onChooseInvestigation={props.onChooseInvestigation}
        onUseFixture={api.mode === "api" ? props.onUseFixture : undefined}
      />
    );
  }
  return (
    <PresetLoaded
      api={api}
      presetId={presetId}
      data={state.data}
      onQueryPosition={props.onQueryPosition}
      onOpenPreset={props.onOpenPreset}
      onOpenQuery={props.onOpenQuery}
      onRetry={retry}
    />
  );
}

function PresetLoaded(props: {
  api: PerigeeApi;
  presetId: string;
  data: Loaded;
  onQueryPosition: (preset: PresetDescriptor) => void;
  onOpenPreset: (id: string) => void;
  onOpenQuery: () => void;
  onRetry: () => void;
}) {
  const { data, api, presetId } = props;
  const { preset, caseContent } = data;
  const pageArrival = useContentCue<HTMLDivElement>("heading", presetId, ".heading-copy");

  // Authored comparisons require their own products and scale. General
  // per-frame products must never silently substitute for a missing case.
  const framesByRef = useMemo(() => {
    const m = new Map<string, FrameRecord>();
    for (const cf of caseContent?.frames ?? []) {
      const f = data.caseFrames.find((x) => x.frame_key === cf.frame_key);
      if (f) m.set(cf.ref, f);
    }
    return m;
  }, [caseContent, data.caseFrames, data.sequence]);
  const caseRefs = useMemo(() => [...framesByRef.keys()].sort(), [framesByRef]);
  const firstRef = caseRefs[0] ?? null;
  const missingRefs = (caseContent?.frames ?? []).filter((cf) => !framesByRef.has(cf.ref));

  const slots: FrameSlot[] = useMemo(() => {
    const refByKey = new Map((caseContent?.frames ?? []).map((f) => [f.frame_key, f.ref]));
    const byKey = new Map(data.sequence.map((f) => [f.frame_key, f]));
    for (const f of data.caseFrames) if (!byKey.has(f.frame_key)) byKey.set(f.frame_key, f);
    return [...byKey.values()].sort(compareChronological).map((f) => ({
      key: f.frame_key,
      ref: refByKey.get(f.frame_key) ?? null,
      status: "ready" as const,
      frame: f,
      observed_at_utc: f.observed_at_utc,
      mjd: f.mjd,
      error: null,
    }));
  }, [data.sequence, data.caseFrames, caseContent]);

  const [index, setIndex] = useState(0);
  const [sequenceOpen, setSequenceOpen] = useState(false);
  useEffect(() => {
    const a = slots.findIndex((s) => s.ref === "A");
    setIndex(a >= 0 ? a : 0);
  }, [slots]);

  const contextKey = presetContextKey(api.mode, presetId, caseContent?.case_id);
  const makeCard = useCallback(
    () =>
      createEvidenceCard({
        case_id: caseContent?.case_id ?? null,
        preset_id: presetId,
        title: caseContent?.title ?? preset?.display_name ?? null,
        case_limitations: caseContent?.limitations ?? null,
        query: preset?.query_center
          ? {
              ra_deg: preset.query_center.ra_deg,
              dec_deg: preset.query_center.dec_deg,
              fov_arcmin: preset.default_fov_arcmin ?? 6,
            }
          : null,
        sources: caseContent?.sources ?? [],
        app_version: __APP_VERSION__,
        data_origin: api.mode,
      }),
    [api.mode, caseContent, preset, presetId],
  );
  const ev = useEvidenceCard(contextKey, makeCard);
  const [activeCheckIndex, setActiveCheckIndex] = useState(() => Math.max(0,
    caseContent?.steps.findIndex((step) => !ev.card.reviewed_step_ids?.includes(step.id)) ?? 0));
  const overviewRef = useRef<HTMLDetailsElement>(null);

  // The pair partner of the first case frame. Restore it from the saved card.
  const defaultOther = (() => {
    const restored = ev.card.frames.find((f) => f.ref && f.ref !== firstRef && framesByRef.has(f.ref))?.ref;
    if (restored) return restored;
    const req = caseContent?.evidence_requirements?.must_include_refs_any_of?.[0];
    const fromReq = req?.find((r) => r !== firstRef && framesByRef.has(r));
    return fromReq ?? caseRefs[1] ?? null;
  })();
  const [otherRef, setOtherRef] = useState<string | null>(defaultOther);
  useEffect(() => {
    if (!otherRef || !framesByRef.has(otherRef)) setOtherRef(defaultOther);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [framesByRef]);

  const pair = useMemo(() => {
    if (!firstRef || !otherRef) return [];
    return [firstRef, otherRef].flatMap((ref) => {
      const frame = framesByRef.get(ref);
      return frame ? [{ frame, ref }] : [];
    });
  }, [firstRef, otherRef, framesByRef]);

  const withPair = useCallback(
    (card: EvidenceCard) => (pair.length === 2 ? attachPair(card, pair, caseRefs) : card),
    [pair, caseRefs],
  );
  const exportCard = useMemo(() => withPair(ev.card), [withPair, ev.card]);
  const selected = useMemo(() => new Set(exportCard.frames.map((f) => f.frame_key)), [exportCard.frames]);
  const hasCase = Boolean(caseContent && caseRefs.length >= 2);

  const choosePair = (ref: string) => {
    if (!framesByRef.has(ref)) return;
    setOtherRef(ref);
    const nextPair = [firstRef, ref].flatMap((r) => {
      const frame = r ? framesByRef.get(r) : undefined;
      return frame && r ? [{ frame, ref: r }] : [];
    });
    if (nextPair.length === 2) ev.update(attachPair(ev.card, nextPair, caseRefs));
  };
  const requiredGroups = caseContent?.evidence_requirements?.must_include_refs_any_of ?? [];
  const requiredRefs = requiredGroups.find((group) => group.length === 2 && group.includes(firstRef ?? "") && group.every((ref) => framesByRef.has(ref)))
    ?? requiredGroups[0];
  const requiredOther = requiredRefs?.find((ref) => ref !== firstRef);
  const canRestorePair = Boolean(requiredRefs?.length === 2 && requiredRefs.includes(firstRef ?? "") && requiredRefs.every((ref) => framesByRef.has(ref)));
  const requiredPair: RequiredPairRecovery | undefined = requiredRefs ? {
    refs: requiredRefs,
    reason: caseContent?.case_id === "moving_neighbor"
      ? "The final question compares the first and last images to examine a year of change."
      : caseContent?.case_id === "wise_0855_quality_trap"
        ? "The final question uses the images taken three days apart at nearly the same wavelength."
        : caseContent?.case_id === "fair_comparison"
          ? "The final question uses images taken at nearly the same wavelength to check for a change over time."
          : "The reference answer is based on this pair. Other pairs help you check alternative explanations.",
    onSelect: canRestorePair && requiredOther ? () => choosePair(requiredOther) : undefined,
  } : undefined;
  const checkCount = caseContent?.steps.length ?? 0;
  const checkIndex = Math.min(activeCheckIndex, Math.max(0, checkCount - 1));
  const currentCheck = caseContent?.steps[checkIndex];
  const checkArrival = useContentCue<HTMLDivElement>("step", currentCheck?.id ?? "");
  const reviewedCount = caseContent?.steps.filter((step) => ev.card.reviewed_step_ids?.includes(step.id)).length ?? 0;
  const currentReviewed = Boolean(currentCheck && ev.card.reviewed_step_ids?.includes(currentCheck.id));
  const openCheck = (index: number) => {
    setActiveCheckIndex(index);
    if (overviewRef.current) overviewRef.current.open = false;
    focusInvestigationSection("investigation-steps");
  };
  const continueChecks = () => {
    const next = caseContent?.steps.findIndex((step) => !ev.card.reviewed_step_ids?.includes(step.id)) ?? 0;
    openCheck(Math.max(0, next));
  };

  const stepsCard =
    caseContent && currentCheck ? (
            <section className="case-steps guided-check" aria-labelledby="investigation-steps">
              <div className="case-steps-heading">
                <h3 id="investigation-steps" tabIndex={-1}>Check what you noticed</h3>
                <span>{reviewedCount} of {checkCount} reviewed</span>
              </div>
              <div className="check-route" aria-hidden="true">
                {caseContent.steps.map((step, index) => <span key={step.id} data-current={index === checkIndex} data-reviewed={Boolean(ev.card.reviewed_step_ids?.includes(step.id))} />)}
              </div>
              <div className="active-check" ref={checkArrival} key={currentCheck.id} aria-live="polite" aria-atomic="true">
                <p className="check-position">Check {checkIndex + 1} of {checkCount}{currentReviewed ? " · Reviewed" : ""}</p>
                <p className="check-prompt">{stepPrompt(currentCheck.prompt)}</p>
              </div>
              {currentCheck.hint && <details className="check-help" key={`help-${currentCheck.id}`}>
                <summary>Help with this check</summary>
                <p>{currentCheck.hint}</p>
              </details>}
              <div className="check-actions">
                <button type="button" className="check-continue" onClick={() => {
                  if (!currentReviewed) ev.update(withPair(reviewStep(ev.card, currentCheck.id, true)));
                  if (checkIndex + 1 < checkCount) openCheck(checkIndex + 1);
                  else focusInvestigationSection("notebook");
                }}>{currentReviewed ? checkIndex + 1 < checkCount ? "Next check" : "Record what you found" : checkIndex + 1 < checkCount ? "Mark reviewed and continue" : "Mark reviewed and record"}</button>
                {checkIndex > 0 && <button type="button" className="link" onClick={() => openCheck(checkIndex - 1)}>Previous check</button>}
              </div>
              <p className="check-progress-note">Reviewed means you looked at the check, not that your answer was graded.</p>
              <details className="check-overview" ref={overviewRef}>
                <summary>All {checkCount} checks and your progress</summary>
                <ol>
                {caseContent.steps.map((s, i) => (
                  <li key={s.id}>
                    <button type="button" className="link" onClick={() => openCheck(i)}>Open check {i + 1}</button>
                    <p>{stepPrompt(s.prompt)}</p>
                    <label className="step-review">
                      <input type="checkbox" checked={Boolean(ev.card.reviewed_step_ids?.includes(s.id))}
                        aria-label={`Reviewed step ${i + 1}`}
                        onChange={(e) => ev.update(withPair(reviewStep(ev.card, s.id, e.target.checked)))} />
                      <span>Reviewed</span>
                    </label>
                  </li>
                ))}
                </ol>
              </details>
            </section>
          ) : null;

  // Authored background, closed by default so the plates reach the first viewport.
  const backgroundPanel =
    caseContent?.opening_question || caseContent?.background?.short || caseContent?.background?.details?.length ? (
      <details className="panel">
        <summary>
          <span>
            <span className="section-icon" aria-hidden="true">
              ?
            </span>
            About {preset?.display_name ?? "this target"} and this investigation
          </span>
          <span className="expand" aria-hidden="true">
            +
          </span>
        </summary>
        <div className="details-body">
          {caseContent?.opening_question && <p>{caseContent.opening_question}</p>}
          {preset?.object_type && <p className="context-target">{preset.display_name} · {preset.object_type}</p>}
          {caseContent?.background?.short && <p>{caseContent.background.short}</p>}
          {caseContent?.background?.details?.length ? (
            <ul className="plain-list">
              {caseContent.background.details.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          ) : null}
        </div>
      </details>
    ) : null;
  const fullSequence = (slots.length === 0 ? (
            <div className="status">
              <p>No processed frames are published for this target yet. Nothing is shown in their place.</p>
              {data.reason && <p className="muted">{data.reason}</p>}
            </div>
          ) : (
            <FrameViewer
              title={hasCase ? `All ${slots.length} observations` : "Observations in date order"}
              description={hasCase ? "Optional: look beyond the guided pair. Each image keeps its own date, wavelength and quality." : "Use Earlier and Later to explore. Each image keeps its own date, wavelength and quality."}
              slots={slots}
              index={Math.min(index, slots.length - 1)}
              onIndexChange={setIndex}
              selectedKeys={selected}
              requiredKeys={new Set(pair.map(({ frame }) => frame.frame_key))}
              onToggleEvidence={(frame, ref) => ev.toggleFrame(frame, hasCase ? null : ref)}
              guideLine={Boolean(caseContent?.display_requirements?.reference_line)}
              blinkTool={!hasCase}
            />
          ));

  return (
    <>
      <div className="content-page-arrival" ref={pageArrival}>
      <PageHeading
        eyebrow="SPHEREx investigation"
        eyebrowDetail={caseContent ? preset?.display_name ?? presetId : "Free exploration"}
        title={caseContent?.title ?? preset?.display_name ?? presetId}
        intro={caseContent ? CASE_INTROS[caseContent.case_id] ?? caseContent.opening_question : preset?.one_line}
        mode={api.mode}
        controls={<InvestigationSwitcher
          presets={data.presets}
          currentId={presetId}
          onOpenPreset={props.onOpenPreset}
          onOpenQuery={props.onOpenQuery}
        />}
      />
      </div>
      <div className="workspace investigation-workspace">
        <section className="bench" id="observations" tabIndex={-1} aria-label="Observation comparison">
          {hasCase && <h2 className="visually-hidden">Compare observations</h2>}
          {!hasCase && <div className="target-line">
            <div>
              <span className="eyebrow">Your target</span>
              <h2>
                {preset?.display_name ?? presetId}
                {preset?.object_type && <span className="tag">{preset.object_type}</span>}
              </h2>
            </div>
            <p>
              {slots.length} processed frame{slots.length === 1 ? "" : "s"}
              {preset?.query_center && (
                <>
                  <br />
                  <button type="button" className="link" onClick={() => props.onQueryPosition(preset)}>
                    Search the archive here
                  </button>
                </>
              )}
            </p>
          </div>}

          {data.caseError != null && !caseContent && (
            <ErrorBlock title="The investigation text could not be loaded. The frames below still work." error={data.caseError} onRetry={props.onRetry} />
          )}
          {data.caseFramesError != null && <ErrorBlock title="The guided comparison could not be loaded. General frames below use their own display scales." error={data.caseFramesError} onRetry={props.onRetry} />}

          {hasCase && caseContent && otherRef && (
            <CaseBench
              caseContent={caseContent}
              framesByRef={framesByRef}
              otherRef={otherRef}
              afterShell={stepsCard}
              onOtherRefChange={choosePair}
            />
          )}
          {!hasCase && caseContent && data.caseFramesError == null && stepsCard}
          {missingRefs.length > 0 && data.caseFramesError == null && (
            <p className="notice" role="note">
              Case frame{missingRefs.length > 1 ? "s" : ""} {missingRefs.map((m) => `${m.ref} (${m.frame_key})`).join(", ")}{" "}
              {missingRefs.length > 1 ? "are" : "is"} not available in this comparison.
            </p>
          )}
          {data.status === "partial" && (
            <p className="notice" role="note">
              Some processed frames for this target could not be used.
            </p>
          )}
          {!hasCase && fullSequence}
        </section>

        <Notebook
          card={ev.card}
          exportCard={exportCard}
          onChange={(c) => ev.update(withPair(c))}
          onRemoveFrame={ev.removeFrame}
          saveState={ev.saveState}
          caseContent={caseContent}
          attachedLabel={hasCase && firstRef && otherRef ? `${firstRef} + ${otherRef}` : null}
          requiredPair={requiredPair}
          onReviewSteps={continueChecks}
        />

        <section className="investigation-extras" aria-label="Background and optional exploration">
          {backgroundPanel}
          {data.warnings.length > 0 && (
            <details className="inline-disclosure">
              <summary>More about these data ({data.warnings.length} warnings)</summary>
              <ul className="plain-list background-short">{data.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
            </details>
          )}
          {hasCase && (
            <details className="panel sequence-disclosure" onToggle={(event) => setSequenceOpen(event.currentTarget.open)}>
              <summary><span>Explore all {slots.length} observations (optional)</span><span className="expand" aria-hidden="true">+</span></summary>
              <div className="details-body">{sequenceOpen && fullSequence}</div>
            </details>
          )}
          {hasCase && preset?.query_center && (
            <div className="archive-action">
              <span>Choose your own patch of sky</span>
              <button type="button" onClick={() => props.onQueryPosition(preset)}>Search around this target</button>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
