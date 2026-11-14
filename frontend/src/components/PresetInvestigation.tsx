import { useCallback, useEffect, useMemo, useState } from "react";
import { compareChronological, type PerigeeApi } from "../api/client";
import type { CaseContent, FrameRecord, PresetDescriptor, PresetFramesResult } from "../api/types";
import { createEvidenceCard } from "../evidence/card";
import { useEvidenceCard } from "../evidence/useEvidenceCard";
import { CasePanel } from "./CasePanel";
import { ErrorBlock, useAsync } from "./common";
import { EvidencePanel } from "./EvidencePanel";
import { FrameViewer, type FrameSlot } from "./FrameViewer";

interface Loaded {
  preset: PresetDescriptor | null;
  frames: FrameRecord[];
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
      // The preset's full sequence, plus the case's own product set when one
      // exists. A missing case set is not fatal; the preset set still works.
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
      const byKey = new Map<string, FrameRecord>();
      for (const f of [...all.frames, ...(caseSet?.frames ?? [])]) if (!byKey.has(f.frame_key)) byKey.set(f.frame_key, f);
      const frames = [...byKey.values()].sort(compareChronological);
      return {
        preset,
        frames,
        status: frames.length ? all.status : "missing",
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
        title="The curated frames for this preset could not be loaded."
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
  const { preset, frames, caseContent } = data;

  const slots: FrameSlot[] = useMemo(() => {
    const refByKey = new Map((caseContent?.frames ?? []).map((f) => [f.frame_key, f.ref]));
    return frames.map((f) => ({
      key: f.frame_key,
      ref: refByKey.get(f.frame_key) ?? null,
      status: "ready" as const,
      frame: f,
      observed_at_utc: f.observed_at_utc,
      mjd: f.mjd,
      error: null,
    }));
  }, [frames, caseContent]);

  const missingRefs = (caseContent?.frames ?? []).filter((cf) => !frames.some((f) => f.frame_key === cf.frame_key));

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
  const selected = useMemo(() => new Set(ev.card.frames.map((f) => f.frame_key)), [ev.card.frames]);

  const pairRefs = caseContent?.evidence_requirements?.must_include_refs_any_of?.[0];
  const defaultPair: [string, string] | undefined =
    pairRefs && pairRefs.length >= 2 ? [pairRefs[0], pairRefs[1]] : undefined;

  return (
    <div className="investigation">
      <header className="investigation-head">
        <h1>{preset?.display_name ?? presetId}</h1>
        {preset?.object_type && <p className="muted">{preset.object_type}</p>}
        {preset?.one_line && <p>{preset.one_line}</p>}
        {preset?.quality_summary && <p className="muted">{preset.quality_summary}</p>}
        {preset?.query_center && (
          <button type="button" className="link" onClick={() => props.onQueryPosition(preset)}>
            Search the archive live at this position
          </button>
        )}
      </header>

      {caseContent ? (
        <CasePanel content={caseContent} />
      ) : data.caseError ? (
        <ErrorBlock title="The investigation text could not be loaded. The frames below still work." error={data.caseError} />
      ) : null}
      {missingRefs.length > 0 && (
        <p className="notice" role="note">
          Case frame{missingRefs.length > 1 ? "s" : ""} {missingRefs.map((m) => m.ref).join(", ")} (
          {missingRefs.map((m) => m.frame_key).join(", ")}) {missingRefs.length > 1 ? "are" : "is"} not among the
          served frames for this preset.
        </p>
      )}

      {data.status === "partial" && (
        <p className="notice" role="note">
          Some curated frames for this preset could not be used.
        </p>
      )}
      {data.warnings.length > 0 && (
        <details className="disclosure">
          <summary>Catalog warnings ({data.warnings.length})</summary>
          <ul className="plain-list">
            {data.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </details>
      )}

      {slots.length === 0 ? (
        <div className="status">
          <p>No processed frames are published for this preset yet. Nothing is shown in their place.</p>
          {data.reason && <p className="muted">{data.reason}</p>}
        </div>
      ) : (
        <FrameViewer
          label={`${preset?.display_name ?? presetId} frames in time order`}
          slots={slots}
          index={Math.min(index, slots.length - 1)}
          onIndexChange={setIndex}
          selectedKeys={selected}
          onToggleEvidence={ev.toggleFrame}
          guideLine={Boolean(caseContent?.display_requirements?.reference_line)}
          defaultPair={defaultPair}
        />
      )}

      <EvidencePanel
        card={ev.card}
        onChange={ev.update}
        onRemoveFrame={ev.removeFrame}
        saveState={ev.saveState}
        caseContent={caseContent}
      />
    </div>
  );
}
