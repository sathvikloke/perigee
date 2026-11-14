import { useCallback, useEffect, useMemo, useState } from "react";
import type { PerigeeApi } from "../api/client";
import type { CaseContent, FrameRecord, PresetDescriptor } from "../api/types";
import { createEvidenceCard } from "../evidence/card";
import { useEvidenceCard } from "../evidence/useEvidenceCard";
import { CasePanel } from "./CasePanel";
import { ErrorBlock, useAsync } from "./common";
import { EvidencePanel } from "./EvidencePanel";
import { FrameViewer, type FrameSlot } from "./FrameViewer";

interface Loaded {
  preset: PresetDescriptor | null;
  frames: FrameRecord[];
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
      const [presets, frames] = await Promise.all([api.presets(signal), api.presetFrames(presetId, signal)]);
      const preset = presets.find((p) => p.id === presetId) ?? null;
      const caseId = preset?.case_ids[0];
      let caseContent: CaseContent | null = null;
      let caseError: unknown = null;
      if (caseId) {
        try {
          caseContent = await api.caseContent(caseId, signal);
        } catch (err) {
          // The frames are still useful without the authored case.
          caseError = err;
        }
      }
      return { preset, frames, caseContent, caseError };
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

      {slots.length === 0 ? (
        <p className="status">No curated frames are available for this preset yet.</p>
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
