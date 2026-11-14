import { useCallback, useRef, useState } from 'react';
import { ApiError, api, createLatest, isAbort, loadFrames } from './api/client';
import type { CaseContent, FrameRecord, ObservationDescriptor, SearchResponse } from './api/types';
import { sourceKey, type Source } from './source';

export interface Slot {
  ref: string;
  status: 'loading' | 'ready' | 'failed';
  frame?: FrameRecord;
  error?: ApiError;
  descriptor?: ObservationDescriptor;
}

/** Everything currently on screen. Replaced only by a successful request. */
export interface View {
  ticket: number;
  key: string;
  source: Source;
  caseData: CaseContent | null;
  slots: Slot[];
  /** Curated pairings (case only), as slot indices. */
  pairs: [number, number][] | null;
  search: SearchResponse | null;
}

export type Request =
  | { phase: 'idle' }
  | { phase: 'loading'; source: Source }
  | { phase: 'error'; source: Source; error: ApiError };

const letter = (i: number) => (i < 26 ? String.fromCharCode(65 + i) : `F${i + 1}`);

export function useInvestigation() {
  const [view, setView] = useState<View | null>(null);
  const [request, setRequest] = useState<Request>({ phase: 'idle' });
  const latest = useRef(createLatest());

  const load = useCallback(
    async (source: Source) => {
      const { ticket, signal, isCurrent } = latest.current.next();
      setRequest({ phase: 'loading', source });
      try {
        const base = { ticket, key: sourceKey(source), source, caseData: null, pairs: null, search: null };
        if (source.kind === 'case') {
          const caseData = await api.case(source.caseId, signal);
          const res = await api.presetFrames(caseData.target_id, source.caseId, signal);
          if (!isCurrent()) return;
          const byKey = new Map(res.frames.map((f) => [f.frame_key ?? f.frame_id, f]));
          const slots: Slot[] = caseData.frames.map((ref) => {
            const frame = byKey.get(ref.frame_key);
            return frame
              ? { ref: ref.ref, status: 'ready', frame }
              : { ref: ref.ref, status: 'failed', error: new ApiError('NOT_FOUND', `Curated frame ${ref.frame_key} is not available yet.`, false, 404) };
          });
          const pairs = slots.slice(1).map((_, i) => [0, i + 1] as [number, number]);
          setView({ ...base, caseData, slots, pairs });
        } else if (source.kind === 'preset') {
          const res = await api.presetFrames(source.presetId, null, signal);
          if (!isCurrent()) return;
          const slots: Slot[] = res.frames.map((frame, i) => ({ ref: letter(i), status: 'ready', frame }));
          setView({ ...base, slots });
        } else {
          const search = await api.search({ ra_deg: source.ra, dec_deg: source.dec, fov_arcmin: source.fov, limit: 12 }, signal);
          if (!isCurrent()) return;
          const slots: Slot[] = search.observations.map((descriptor, i) => ({ ref: letter(i), status: 'loading', descriptor }));
          setView({ ...base, slots, search });
          setRequest({ phase: 'idle' });
          await loadFrames(
            search.observations,
            (out) =>
              setView((v) => {
                if (!v || v.ticket !== ticket) return v; // stale guard at the state boundary too
                const slots = v.slots.slice();
                slots[out.index] = out.ok
                  ? { ...slots[out.index], status: 'ready', frame: out.frame }
                  : { ...slots[out.index], status: 'failed', error: out.error };
                return { ...v, slots };
              }),
            { signal, isCurrent, concurrency: 2 },
          );
          return;
        }
        setRequest({ phase: 'idle' });
      } catch (e) {
        if (isAbort(e) || !isCurrent()) return;
        const error = e instanceof ApiError ? e : new ApiError('UNKNOWN', String(e), true, null);
        setRequest({ phase: 'error', source, error });
      }
    },
    [],
  );

  /** Retry one failed live frame without disturbing the others. */
  const retrySlot = useCallback(async (index: number) => {
    const v = viewRef.current;
    const descriptor = v?.slots[index]?.descriptor;
    if (!v || !descriptor) return;
    const ticket = v.ticket;
    const patch = (s: Partial<Slot>) =>
      setView((cur) => {
        if (!cur || cur.ticket !== ticket) return cur;
        const slots = cur.slots.slice();
        slots[index] = { ...slots[index], ...s };
        return { ...cur, slots };
      });
    patch({ status: 'loading', error: undefined });
    try {
      const { frame } = await api.frame(descriptor.frame_token);
      patch({ status: 'ready', frame });
    } catch (e) {
      patch({ status: 'failed', error: e instanceof ApiError ? e : new ApiError('PROCESSING_FAILED', String(e), true, null) });
    }
  }, []);

  const viewRef = useRef(view);
  viewRef.current = view;

  return { view, request, load, retrySlot };
}
