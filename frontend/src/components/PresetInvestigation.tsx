import { useCallback, useEffect, useMemo, useState } from "react";
import { compareChronological, type PerigeeApi } from "../api/client";
import type { CaseContent, FrameRecord, PresetDescriptor, PresetFramesResult } from "../api/types";
import { attachPair, createEvidenceCard, type EvidenceCard } from "../evidence/card";
import { useEvidenceCard } from "../evidence/useEvidenceCard";
import { CaseBench } from "./CaseBench";
import { ErrorBlock, useAsync } from "./common";
import { FrameViewer, type FrameSlot } from "./FrameViewer";
import { Notebook } from "./Notebook";
import { PageHeading, WorkflowStrip } from "./PageHeading";

interface Loaded {
  preset: PresetDescriptor | null;
  /** The preset's full `frames` set, for free stepping. */
  sequence: FrameRecord[];
  /** The case's own product set (shared stretch), for the comparison plates. */
  caseFrames: FrameRecord[];
  status: PresetFramesResult["status"];
  reason: string | null;
  warnings: string[];
  caseContent: CaseContent | null;
  caseError: unknown;
}

export function PresetInvestigation(props: {
  api: PerigeeApi;
  presetId: string;
  onUseFixture?: () => void;
  onQueryPosition: (preset: PresetDescriptor) => void;
}) {
  const { api, presetId } = props;
  const { state, retry } = useAsync<Loaded>(
    async (signal) => {
      const presets = await api.presets(signal);
      const preset = presets.find((p) => p.id === presetId) ?? null;
      const caseId = preset?.case_ids[0] ?? null;
      const [all, caseSet, caseResult] = await Promise.all([
        api.presetFrames(presetId, null, signal),
        caseId ? api.presetFrames(presetId, caseId, signal).catch(() => null) : Promise.resolve(null),
        caseId
          ? api.caseContent(caseId, signal).then(
              (c) => ({ c, err: null as unknown }),
              (err: unknown) => ({ c: null, err }),
            )
          : Promise.resolve({ c: null, err: null as unknown }),
      ]);
      return {
        preset,
        sequence: all.frames,
        caseFrames: caseSet?.frames ?? [],
        status: all.frames.length || caseSet?.frames.length ? all.status : "missing",
        reason: all.reason ?? caseSet?.reason ?? null,
        warnings: [...all.warnings, ...(caseSet?.warnings ?? [])],
        caseContent: caseResult.c,
        caseError: caseResult.err,
      };
    },
    [api, presetId],
  );

  if (state.status === "loading") {
    return (
      <p className="status" role="status">
        Loading curated frames…
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <ErrorBlock
        title="The curated frames for this target could not be loaded."
        error={state.error}
        onRetry={retry}
        onUseFixture={api.mode === "api" ? props.onUseFixture : undefined}
      />
    );
  }
  return <PresetLoaded api={api} presetId={presetId} data={state.data} onQueryPosition={props.onQueryPosition} />;
}

function PresetLoaded(props: {
  api: PerigeeApi;
  presetId: string;
  data: Loaded;
  onQueryPosition: (preset: PresetDescriptor) => void;
}) {
  const { data, api, presetId } = props;
  const { preset, caseContent } = data;

  // Comparison plates use the case product set (shared stretch); fall back to
  // the preset set only for a frame the case set lacks.
  const framesByRef = useMemo(() => {
    const m = new Map<string, FrameRecord>();
    for (const cf of caseContent?.frames ?? []) {
      const f =
        data.caseFrames.find((x) => x.frame_key === cf.frame_key) ??
        data.sequence.find((x) => x.frame_key === cf.frame_key);
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
  useEffect(() => {
    const a = slots.findIndex((s) => s.ref === "A");
    setIndex(a >= 0 ? a : 0);
  }, [slots]);

  const contextKey = `${api.mode}:preset:${presetId}`;
  const makeCard = useCallback(
    () =>
      createEvidenceCard({
        case_id: caseContent?.case_id ?? null,
        preset_id: presetId,
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

  const stepsCard =
    caseContent && caseContent.steps.length > 0 ? (
            <div className="case-steps">
              <h3>Your steps</h3>
              <ol>
                {caseContent.steps.map((s) => (
                  <li key={s.id}>
                    {s.prompt}
                    {s.hint && (
                      <details>
                        <summary>Hint</summary>
                        <p>{s.hint}</p>
                      </details>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          ) : null;

  return (
    <>
      <PageHeading
        eyebrow="SPHEREx investigation"
        eyebrowDetail={caseContent ? preset?.display_name ?? presetId : "Free exploration"}
        title={caseContent?.title ?? preset?.display_name ?? presetId}
        intro={caseContent?.opening_question ?? preset?.one_line}
        mode={api.mode}
      />
      <div className="workspace">
        <section className="bench" aria-label="Observation comparison">
          {hasCase && <WorkflowStrip />}
          <div className="target-line">
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
                    Search the archive here ↗
                  </button>
                </>
              )}
            </p>
          </div>

          {caseContent?.background?.short && (
            <p className="background-short wide-only">{caseContent.background.short}</p>
          )}
          {caseContent?.background?.short || caseContent?.background?.details?.length ? (
            <details className="inline-disclosure">
              <summary>
                <span className="wide-only">More background</span>
                <span className="phone-only">About this target</span>
              </summary>
              {caseContent?.background?.short && (
                <p className="background-short phone-only">{caseContent.background.short}</p>
              )}
              <ul className="plain-list background-short">
                {(caseContent?.background?.details ?? []).map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </details>
          ) : null}
          {data.caseError != null && !caseContent && (
            <ErrorBlock title="The investigation text could not be loaded. The frames below still work." error={data.caseError} />
          )}

          {hasCase && caseContent && otherRef && (
            <CaseBench
              caseContent={caseContent}
              framesByRef={framesByRef}
              otherRef={otherRef}
              afterShell={stepsCard}
              onOtherRefChange={(r) => {
                setOtherRef(r);
                const nextPair = [firstRef, r].flatMap((ref) => {
                  const frame = ref ? framesByRef.get(ref) : undefined;
                  return frame && ref ? [{ frame, ref }] : [];
                });
                if (nextPair.length === 2) ev.update(attachPair(ev.card, nextPair, caseRefs));
              }}
            />
          )}
          {missingRefs.length > 0 && (
            <p className="notice" role="note">
              Case frame{missingRefs.length > 1 ? "s" : ""} {missingRefs.map((m) => `${m.ref} (${m.frame_key})`).join(", ")}{" "}
              {missingRefs.length > 1 ? "are" : "is"} not among the published frames yet.
            </p>
          )}
          {data.status === "partial" && (
            <p className="notice" role="note">
              Some processed frames for this target could not be used.
            </p>
          )}
          {data.warnings.length > 0 && (
            <details className="inline-disclosure">
              <summary>Catalog warnings ({data.warnings.length})</summary>
              <ul className="plain-list background-short">
                {data.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </details>
          )}

          {slots.length === 0 ? (
            <div className="status">
              <p>No processed frames are published for this target yet. Nothing is shown in their place.</p>
              {data.reason && <p className="muted">{data.reason}</p>}
            </div>
          ) : (
            <FrameViewer
              title={hasCase ? `All ${slots.length} frames in time order` : "Frames in time order"}
              description="Use ← → to step. Each frame keeps its own date, wavelength and quality."
              slots={slots}
              index={Math.min(index, slots.length - 1)}
              onIndexChange={setIndex}
              selectedKeys={selected}
              onToggleEvidence={(frame, ref) => ev.toggleFrame(frame, hasCase ? null : ref)}
              guideLine={Boolean(caseContent?.display_requirements?.reference_line)}
              blinkTool={!hasCase}
            />
          )}
        </section>

        <Notebook
          card={ev.card}
          exportCard={exportCard}
          onChange={(c) => ev.update(withPair(c))}
          onRemoveFrame={ev.removeFrame}
          saveState={ev.saveState}
          caseContent={caseContent}
          attachedLabel={hasCase && firstRef && otherRef ? `${firstRef} + ${otherRef}` : null}
        />
      </div>
    </>
  );
}
