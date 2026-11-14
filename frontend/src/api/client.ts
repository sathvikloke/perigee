// The one API client. Same-origin `/api/v1` by default; a fallback deployment
// may set VITE_PERIGEE_API_ORIGIN (a public origin, never a secret).
import type {
  CaseContent,
  ErrorEnvelope,
  FrameRecord,
  FrameResponse,
  ObservationDescriptor,
  PresetFramesResponse,
  PresetsResponse,
  SearchRequest,
  SearchResponse,
} from './types';

const origin = (import.meta.env?.VITE_PERIGEE_API_ORIGIN as string | undefined)?.replace(/\/$/, '') ?? '';
export const API_BASE = `${origin}/api/v1`;

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly retryable: boolean,
    readonly status: number | null,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const isAbort = (e: unknown) => e instanceof DOMException && e.name === 'AbortError';

type FetchLike = typeof fetch;
let fetcher: FetchLike = (...args) => fetch(...args);
/** Test seam: replace the network function. */
export function setFetch(f: FetchLike) {
  fetcher = f;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetcher(`${API_BASE}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}) },
    });
  } catch (e) {
    if (isAbort(e)) throw e;
    throw new ApiError('NETWORK', 'Perigee could not reach its server. Check the connection and try again.', true, null);
  }
  const type = res.headers.get('content-type') ?? '';
  if (!type.includes('json')) {
    // An SPA fallback must never turn a broken API route into success.
    throw new ApiError('BAD_RESPONSE', `The server answered ${res.status} without JSON.`, res.status >= 500, res.status);
  }
  const body = (await res.json()) as T | ErrorEnvelope;
  if (!res.ok || (body && typeof body === 'object' && 'error' in body && (body as ErrorEnvelope).error)) {
    const err = (body as ErrorEnvelope).error;
    throw new ApiError(
      err?.code ?? 'HTTP_' + res.status,
      err?.message ?? `Request failed (${res.status}).`,
      err?.retryable ?? res.status >= 500,
      res.status,
      err?.details,
    );
  }
  return body as T;
}

export const api = {
  presets: (signal?: AbortSignal) => request<PresetsResponse>('/presets', { signal }),
  case: (caseId: string, signal?: AbortSignal) => request<CaseContent>(`/cases/${encodeURIComponent(caseId)}`, { signal }),
  presetFrames: (presetId: string, caseId?: string | null, signal?: AbortSignal) =>
    request<PresetFramesResponse>(
      `/presets/${encodeURIComponent(presetId)}/frames${caseId ? `?case_id=${encodeURIComponent(caseId)}` : ''}`,
      { signal },
    ),
  search: (body: Omit<SearchRequest, 'schema_version'>, signal?: AbortSignal) =>
    request<SearchResponse>('/search', { method: 'POST', body: JSON.stringify({ schema_version: 1, ...body }), signal }),
  frame: (frameToken: string, signal?: AbortSignal) =>
    request<FrameResponse>('/frame', { method: 'POST', body: JSON.stringify({ schema_version: 1, frame_token: frameToken }), signal }),
};

/**
 * Stale-response guard. Each new query takes a ticket; anything resolving for
 * an older ticket is dropped, so an earlier query never paints the new viewer.
 */
export function createLatest() {
  let current = 0;
  let controller: AbortController | null = null;
  return {
    next() {
      controller?.abort();
      controller = new AbortController();
      const ticket = ++current;
      return { ticket, signal: controller.signal, isCurrent: () => ticket === current };
    },
    cancel() {
      controller?.abort();
      current++;
    },
  };
}

export type FrameOutcome =
  | { index: number; ok: true; frame: FrameRecord }
  | { index: number; ok: false; error: ApiError };

/**
 * Request processed frames with bounded concurrency (2 by contract). Results are
 * reported by descriptor index so a failure never reorders completed frames.
 */
export async function loadFrames(
  observations: ObservationDescriptor[],
  onResult: (outcome: FrameOutcome) => void,
  opts: { signal?: AbortSignal; concurrency?: number; isCurrent?: () => boolean } = {},
) {
  const { signal, concurrency = 2, isCurrent = () => true } = opts;
  let next = 0;
  const worker = async () => {
    while (next < observations.length) {
      const index = next++;
      if (signal?.aborted || !isCurrent()) return;
      try {
        const { frame } = await api.frame(observations[index].frame_token, signal);
        if (isCurrent()) onResult({ index, ok: true, frame });
      } catch (e) {
        if (isAbort(e) || !isCurrent()) return;
        const error = e instanceof ApiError ? e : new ApiError('PROCESSING_FAILED', String(e), true, null);
        onResult({ index, ok: false, error });
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(concurrency, observations.length) }, worker));
}
