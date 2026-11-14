// The single API client module for Perigee. Every network call the UI makes
// goes through here. Base: same-origin `/api/v1`, or VITE_API_BASE at build
// time (a public origin, never a secret). See docs/INTEGRATION_CONTRACT.md.

import {
  SCHEMA_VERSION,
  type CaseContent,
  type ErrorEnvelope,
  type FrameRecord,
  type HealthResponse,
  type ObservationDescriptor,
  type PresetDescriptor,
  type PresetFramesResult,
  type Provenance,
  type Quality,
  type QualityStatus,
  type SearchRequest,
  type SearchResponse,
} from "./types";

export const API_PREFIX = "/api/v1";

/** Browser frame concurrency limit fixed by the contract. */
export const FRAME_CONCURRENCY = 2;

/** Browser-side wait for /search; the UI quotes it while a search is slow. */
export const SEARCH_TIMEOUT_MS = 45_000;
const FRAME_TIMEOUT_MS = 90_000;
const DEFAULT_TIMEOUT_MS = 20_000;

// ---------------------------------------------------------------------------
// Errors

/** Client-side codes for failures that never reached a JSON API response. */
export type ClientErrorCode =
  | "NETWORK_ERROR"
  | "NON_JSON_RESPONSE"
  | "MALFORMED_RESPONSE"
  | "CLIENT_TIMEOUT";

export class ApiError extends Error {
  readonly code: string;
  readonly httpStatus: number | null;
  readonly retryable: boolean;
  readonly requestId: string | null;
  readonly details: unknown;

  constructor(init: {
    code: string;
    message: string;
    httpStatus?: number | null;
    retryable?: boolean;
    requestId?: string | null;
    details?: unknown;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.code = init.code;
    this.httpStatus = init.httpStatus ?? null;
    this.retryable = init.retryable ?? false;
    this.requestId = init.requestId ?? null;
    this.details = init.details;
  }
}

export function isAbortError(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "name" in err &&
    (err as { name: unknown }).name === "AbortError"
  );
}

/** Returns the envelope if `body` has the contract's error shape, else null. */
export function parseErrorEnvelope(body: unknown): ErrorEnvelope | null {
  if (typeof body !== "object" || body === null) return null;
  const b = body as Record<string, unknown>;
  const e = b.error;
  if (typeof e !== "object" || e === null) return null;
  const err = e as Record<string, unknown>;
  if (typeof err.code !== "string" || typeof err.message !== "string") return null;
  return {
    schema_version: typeof b.schema_version === "number" ? b.schema_version : SCHEMA_VERSION,
    request_id: typeof b.request_id === "string" ? b.request_id : null,
    error: {
      code: err.code,
      message: err.message,
      retryable: err.retryable === true,
      details: err.details,
    },
  };
}

/**
 * Converts a non-2xx (or non-JSON) HTTP outcome into an ApiError. Pure: takes
 * the status, content type and raw text so it can be unit tested.
 */
export function errorFromResponse(
  status: number,
  contentType: string | null,
  bodyText: string,
): ApiError {
  const isJson = (contentType ?? "").toLowerCase().includes("json");
  if (isJson) {
    let parsed: unknown = null;
    try {
      parsed = JSON.parse(bodyText);
    } catch {
      parsed = null;
    }
    const env = parseErrorEnvelope(parsed);
    if (env) {
      return new ApiError({
        code: env.error.code,
        message: env.error.message,
        httpStatus: status,
        retryable: env.error.retryable,
        requestId: env.request_id,
        details: env.error.details,
      });
    }
    // FastAPI's default validation error shape: {"detail": [...]}
    if (parsed && typeof parsed === "object" && "detail" in parsed) {
      return new ApiError({
        code: status === 404 ? "NOT_FOUND" : "INVALID_REQUEST",
        message: describeFastApiDetail((parsed as { detail: unknown }).detail),
        httpStatus: status,
        retryable: false,
      });
    }
  }
  if (!isJson) {
    // An HTML body here usually means the SPA fallback or an upstream proxy
    // page answered instead of the API. Never treat it as success.
    return new ApiError({
      code: "NON_JSON_RESPONSE",
      message: `The Perigee API did not answer normally (HTTP ${status}, ${contentType || "unknown content"} instead of JSON). It may be down or misrouted.`,
      httpStatus: status,
      retryable: status >= 500,
    });
  }
  return new ApiError({
    code: "MALFORMED_RESPONSE",
    message: `The API returned HTTP ${status} without a readable error.`,
    httpStatus: status,
    retryable: status >= 500 || status === 429,
  });
}

function describeFastApiDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown; loc?: unknown };
    const loc = Array.isArray(first.loc) ? first.loc.join(".") : "";
    return `${typeof first.msg === "string" ? first.msg : "Invalid request"}${loc ? ` (${loc})` : ""}`;
  }
  return "The request was rejected.";
}

// ---------------------------------------------------------------------------
// Request identity: ignore stale responses and cancel superseded work.

export interface RequestTicket {
  id: number;
  signal: AbortSignal;
}

export interface RequestGate {
  /** Starts a new request generation, aborting the previous one. */
  begin(): RequestTicket;
  /** True only for the most recent generation. */
  isCurrent(id: number): boolean;
  /** Aborts the current generation; nothing in flight remains current. */
  cancel(): void;
  /** The live ticket, for follow-up work (e.g. a retry) in the same generation. */
  active(): RequestTicket | null;
}

export function createRequestGate(): RequestGate {
  let current = 0;
  let controller: AbortController | null = null;
  return {
    begin() {
      controller?.abort();
      controller = new AbortController();
      current += 1;
      return { id: current, signal: controller.signal };
    },
    isCurrent(id) {
      return id === current;
    },
    active() {
      return controller && !controller.signal.aborted ? { id: current, signal: controller.signal } : null;
    },
    cancel() {
      controller?.abort();
      controller = null;
      current += 1;
    },
  };
}

/**
 * Runs `worker` over `items` with at most `limit` in flight, starting items in
 * index order. Worker failures are the worker's responsibility; one failure
 * never stops or reorders the rest. Stops scheduling when `signal` aborts.
 */
export async function runWithConcurrency<T>(
  items: readonly T[],
  limit: number,
  worker: (item: T, index: number) => Promise<void>,
  signal?: AbortSignal,
): Promise<void> {
  let next = 0;
  const lane = async () => {
    while (next < items.length) {
      if (signal?.aborted) return;
      const index = next;
      next += 1;
      try {
        await worker(items[index], index);
      } catch {
        // Swallowed deliberately: per-item state is reported by the worker.
      }
    }
  };
  const lanes = Array.from({ length: Math.max(1, Math.min(limit, items.length)) }, lane);
  await Promise.all(lanes);
}

export interface Limiter {
  /**
   * Runs `fn` once fewer than `limit` calls are in flight, in call order.
   * Aborting `signal` while queued rejects with an AbortError and never runs `fn`.
   */
  run<T>(fn: () => Promise<T>, signal?: AbortSignal): Promise<T>;
  inFlight(): number;
}

/**
 * One concurrency budget shared by every frame request on a page: the first
 * pass, single-frame retries and "retry all failed" together stay within
 * FRAME_CONCURRENCY, however fast the learner clicks.
 */
export function createLimiter(limit: number): Limiter {
  let active = 0;
  const queue: Array<() => void> = [];
  const release = () => {
    active -= 1;
    queue.shift()?.();
  };
  return {
    inFlight: () => active,
    run<T>(fn: () => Promise<T>, signal?: AbortSignal): Promise<T> {
      return new Promise<T>((resolve, reject) => {
        const abortError = () => new DOMException("Aborted while queued", "AbortError");
        if (signal?.aborted) return reject(abortError());
        const start = () => {
          signal?.removeEventListener("abort", onAbort);
          active += 1;
          let p: Promise<T>;
          try {
            p = fn();
          } catch (err) {
            p = Promise.reject(err);
          }
          p.then(resolve, reject).finally(release);
        };
        const onAbort = () => {
          const i = queue.indexOf(start);
          if (i >= 0) queue.splice(i, 1);
          reject(abortError());
        };
        if (active < limit) start();
        else {
          queue.push(start);
          signal?.addEventListener("abort", onAbort, { once: true });
        }
      });
    },
  };
}

// ---------------------------------------------------------------------------
// Normalizers. They accept small shape variations from the backend workers
// without inventing values: absent numbers become null, never 0.

function asArray(body: unknown, keys: string[]): unknown[] {
  if (Array.isArray(body)) return body;
  if (body && typeof body === "object") {
    for (const k of keys) {
      const v = (body as Record<string, unknown>)[k];
      if (Array.isArray(v)) return v;
    }
  }
  throw new ApiError({
    code: "MALFORMED_RESPONSE",
    message: `Expected a list (${keys.join(" or ")}) in the API response.`,
  });
}

const numOrNull = (v: unknown): number | null =>
  typeof v === "number" && Number.isFinite(v) ? v : null;
const strOrNull = (v: unknown): string | null => (typeof v === "string" && v ? v : null);

export function makeFrameKey(observationId: string, detector: number | null | undefined): string {
  return detector == null ? observationId : `${observationId}_D${detector}`;
}

const QUALITY_STATUSES: QualityStatus[] = ["clear", "flagged", "not_covered", "unknown"];

function normalizeQuality(raw: unknown): Quality {
  const q = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const status = QUALITY_STATUSES.includes(q.status as QualityStatus)
    ? (q.status as QualityStatus)
    : "unknown";
  return {
    status,
    covered: typeof q.covered === "boolean" ? q.covered : null,
    valid_aperture_pixels: numOrNull(q.valid_aperture_pixels),
    adverse_aperture_pixels: numOrNull(q.adverse_aperture_pixels),
    flag_names: Array.isArray(q.flag_names) ? q.flag_names.filter((f) => typeof f === "string") : [],
    notes: Array.isArray(q.notes) || typeof q.notes === "string" ? (q.notes as string[] | string) : null,
  };
}

// The processor (05) writes `retrieved_at` and `sha256`; the contract text says
// "retrieval time" and "file hash". Accept both spellings, invent neither.
function normalizeProvenance(raw: unknown): Provenance | null {
  if (!raw || typeof raw !== "object") return null;
  const p = raw as Record<string, unknown>;
  return {
    ...p,
    retrieved_at_utc: strOrNull(p.retrieved_at_utc) ?? strOrNull(p.retrieved_at),
    original_url: strOrNull(p.original_url),
    file_sha256: strOrNull(p.file_sha256) ?? strOrNull(p.sha256),
    processing_version: strOrNull(p.processing_version),
    acknowledgments: (p.acknowledgments as Provenance["acknowledgments"]) ?? null,
  };
}

export function normalizeFrameRecord(raw: unknown): FrameRecord {
  if (!raw || typeof raw !== "object") {
    throw new ApiError({ code: "MALFORMED_RESPONSE", message: "Frame record is not an object." });
  }
  const r = raw as Record<string, unknown>;
  const observationId = strOrNull(r.observation_id);
  const observedAt = strOrNull(r.observed_at_utc);
  const mjd = numOrNull(r.mjd);
  if (!observationId || !observedAt || mjd === null) {
    throw new ApiError({
      code: "MALFORMED_RESPONSE",
      message: "Frame record is missing observation_id, observed_at_utc or mjd.",
    });
  }
  const detector = numOrNull(r.detector);
  const frameKey = strOrNull(r.frame_key) ?? makeFrameKey(observationId, detector);
  return {
    frame_id: strOrNull(r.frame_id) ?? frameKey,
    frame_key: frameKey,
    observation_id: observationId,
    detector,
    collection_id: strOrNull(r.collection_id) ?? "unknown",
    observed_at_utc: observedAt,
    mjd,
    source_url: strOrNull(r.source_url) ?? "",
    wavelength_um: numOrNull(r.wavelength_um),
    bandwidth_um: numOrNull(r.bandwidth_um),
    wavelength_location: strOrNull(r.wavelength_location),
    image: (r.image as FrameRecord["image"]) ?? null,
    flag_image: (r.flag_image as FrameRecord["flag_image"]) ?? null,
    registration: (r.registration as FrameRecord["registration"]) ?? null,
    quality: normalizeQuality(r.quality),
    display_scale: (r.display_scale as FrameRecord["display_scale"]) ?? null,
    marker: (r.marker as FrameRecord["marker"]) ?? null,
    provenance: normalizeProvenance(r.provenance),
    limitations: Array.isArray(r.limitations)
      ? r.limitations.filter((l): l is string => typeof l === "string")
      : [],
    ...(r._fixture === true ? { _fixture: true as const } : {}),
  };
}

/** Contract order: numeric observation time, then frame_key as tie breaker. */
export function compareChronological(
  a: { mjd: number | null; frame_key?: string; observation_id: string },
  b: { mjd: number | null; frame_key?: string; observation_id: string },
): number {
  const am = a.mjd ?? Number.POSITIVE_INFINITY;
  const bm = b.mjd ?? Number.POSITIVE_INFINITY;
  if (am !== bm) return am < bm ? -1 : 1;
  const ak = a.frame_key ?? a.observation_id;
  const bk = b.frame_key ?? b.observation_id;
  return ak < bk ? -1 : ak > bk ? 1 : 0;
}

export function normalizePresets(body: unknown): PresetDescriptor[] {
  return asArray(body, ["presets", "targets"]).map((p) => {
    const r = p as Record<string, unknown>;
    const id = strOrNull(r.id) ?? strOrNull(r.preset_id);
    if (!id) throw new ApiError({ code: "MALFORMED_RESPONSE", message: "Preset without an id." });
    return {
      ...(r as object),
      id,
      display_name: strOrNull(r.display_name) ?? id,
      case_ids: Array.isArray(r.case_ids) ? (r.case_ids as string[]) : [],
    } as PresetDescriptor;
  });
}

export function normalizeFrameList(body: unknown): FrameRecord[] {
  return asArray(body, ["frames"]).map(normalizeFrameRecord).sort(compareChronological);
}

export function normalizePresetFrames(body: unknown): PresetFramesResult {
  const frames = normalizeFrameList(body);
  const r = (body && typeof body === "object" && !Array.isArray(body) ? body : {}) as Record<string, unknown>;
  const status =
    r.status === "ready" || r.status === "partial" || r.status === "missing"
      ? r.status
      : frames.length
        ? "ready"
        : "missing";
  return {
    status,
    frames,
    reason: strOrNull(r.reason),
    warnings: Array.isArray(r.warnings) ? r.warnings.filter((w): w is string => typeof w === "string") : [],
  };
}

export function normalizeFrameResponse(body: unknown): FrameRecord {
  if (body && typeof body === "object" && "frame" in body) {
    return normalizeFrameRecord((body as { frame: unknown }).frame);
  }
  return normalizeFrameRecord(body);
}

export function normalizeSearchResponse(body: unknown): SearchResponse {
  if (!body || typeof body !== "object") {
    throw new ApiError({ code: "MALFORMED_RESPONSE", message: "Search response is not an object." });
  }
  const r = body as Record<string, unknown>;
  const status = r.status;
  if (status !== "ready" && status !== "partial" && status !== "empty") {
    throw new ApiError({ code: "MALFORMED_RESPONSE", message: "Search response has no valid status." });
  }
  const observations = asArray(r, ["observations"]).map((o) => {
    const d = o as Record<string, unknown>;
    const observationId = strOrNull(d.observation_id);
    const token = strOrNull(d.frame_token);
    if (!observationId || !token) {
      throw new ApiError({
        code: "MALFORMED_RESPONSE",
        message: "Observation descriptor without observation_id or frame_token.",
      });
    }
    const detector = numOrNull(d.detector);
    const descriptor: ObservationDescriptor = {
      observation_id: observationId,
      frame_key: strOrNull(d.frame_key) ?? makeFrameKey(observationId, detector),
      detector,
      collection_id: strOrNull(d.collection_id) ?? "unknown",
      observed_at_utc: strOrNull(d.observed_at_utc),
      mjd: numOrNull(d.mjd),
      source_url: strOrNull(d.source_url),
      frame_token: token,
    };
    return descriptor;
  });
  observations.sort(compareChronological);
  return {
    schema_version: numOrNull(r.schema_version) ?? SCHEMA_VERSION,
    request_id: strOrNull(r.request_id) ?? "",
    query: r.query as SearchResponse["query"],
    status,
    observations,
    returned_count: numOrNull(r.returned_count) ?? observations.length,
    total_matches: numOrNull(r.total_matches),
    truncated: r.truncated === true,
    warnings: Array.isArray(r.warnings) ? (r.warnings as string[]) : [],
    collections_queried: Array.isArray(r.collections_queried) ? (r.collections_queried as string[]) : [],
    collections_failed: Array.isArray(r.collections_failed)
      ? r.collections_failed.filter((c): c is string => typeof c === "string")
      : [],
    queried_at_utc: strOrNull(r.queried_at_utc) ?? "",
  };
}

// ---------------------------------------------------------------------------
// Transport

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

/** Resolves the API base. `override` is VITE_API_BASE (an origin or origin+prefix). */
export function resolveApiBase(override?: string | null): string {
  const trimmed = (override ?? "").trim().replace(/\/+$/, "");
  if (!trimmed) return API_PREFIX;
  return trimmed.endsWith(API_PREFIX) ? trimmed : `${trimmed}${API_PREFIX}`;
}

/**
 * Resolves an image `src` from a FrameRecord. Data URLs and absolute URLs pass
 * through; same-origin asset paths are rebased when VITE_API_BASE points at
 * another origin.
 */
export function resolveAssetSrc(src: string, apiBase: string = defaultBase()): string {
  if (/^(data:|https?:|blob:)/i.test(src)) return src;
  if (src.startsWith(API_PREFIX) && apiBase !== API_PREFIX) {
    return apiBase.slice(0, -API_PREFIX.length) + src;
  }
  return src;
}

function defaultBase(): string {
  return resolveApiBase(import.meta.env?.VITE_API_BASE as string | undefined);
}

function withTimeout(signal: AbortSignal | undefined, ms: number): {
  signal: AbortSignal;
  timedOut: () => boolean;
  clear: () => void;
} {
  const controller = new AbortController();
  let didTimeout = false;
  const timer = setTimeout(() => {
    didTimeout = true;
    controller.abort();
  }, ms);
  const onAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", onAbort, { once: true });
  }
  return {
    signal: controller.signal,
    timedOut: () => didTimeout,
    clear: () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
    },
  };
}

export interface PerigeeApi {
  readonly mode: "api" | "fixture";
  health(signal?: AbortSignal): Promise<HealthResponse>;
  presets(signal?: AbortSignal): Promise<PresetDescriptor[]>;
  caseContent(caseId: string, signal?: AbortSignal): Promise<CaseContent>;
  /** Curated frames; `caseId` restricts to that case's product set (catalog `?case_id=`). */
  presetFrames(presetId: string, caseId?: string | null, signal?: AbortSignal): Promise<PresetFramesResult>;
  search(req: Omit<SearchRequest, "schema_version">, signal?: AbortSignal): Promise<SearchResponse>;
  frame(frameToken: string, signal?: AbortSignal): Promise<FrameRecord>;
}

export function createHttpApi(options: { base?: string; fetchImpl?: FetchLike } = {}): PerigeeApi {
  const base = options.base ?? defaultBase();
  const fetchImpl: FetchLike = options.fetchImpl ?? ((i, init) => fetch(i, init));

  async function requestJson(
    method: "GET" | "POST",
    path: string,
    body: unknown,
    signal: AbortSignal | undefined,
    timeoutMs: number,
  ): Promise<unknown> {
    const t = withTimeout(signal, timeoutMs);
    let response: Response;
    try {
      response = await fetchImpl(`${base}${path}`, {
        method,
        headers: body === undefined ? { Accept: "application/json" } : {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: t.signal,
      });
    } catch (err) {
      t.clear();
      if (isAbortError(err) && t.timedOut()) {
        throw new ApiError({
          code: "CLIENT_TIMEOUT",
          message: `No response from the API within ${Math.round(timeoutMs / 1000)} seconds.`,
          retryable: true,
        });
      }
      if (isAbortError(err)) throw err;
      throw new ApiError({
        code: "NETWORK_ERROR",
        message: "Could not reach the Perigee API. Check your connection and try again.",
        retryable: true,
      });
    }
    try {
      const contentType = response.headers.get("content-type");
      const text = await response.text();
      if (!response.ok || !(contentType ?? "").toLowerCase().includes("json")) {
        throw errorFromResponse(response.status, contentType, text);
      }
      try {
        return JSON.parse(text) as unknown;
      } catch {
        throw new ApiError({
          code: "MALFORMED_RESPONSE",
          message: "The API response was not valid JSON.",
          httpStatus: response.status,
        });
      }
    } finally {
      t.clear();
    }
  }

  const enc = encodeURIComponent;
  return {
    mode: "api",
    health: async (signal) =>
      (await requestJson("GET", "/health", undefined, signal, DEFAULT_TIMEOUT_MS)) as HealthResponse,
    presets: async (signal) =>
      normalizePresets(await requestJson("GET", "/presets", undefined, signal, DEFAULT_TIMEOUT_MS)),
    caseContent: async (caseId, signal) => {
      const body = await requestJson("GET", `/cases/${enc(caseId)}`, undefined, signal, DEFAULT_TIMEOUT_MS);
      const c = (body && typeof body === "object" && "case" in body ? (body as { case: unknown }).case : body) as CaseContent;
      if (!c || typeof c !== "object" || !Array.isArray(c.steps) || !Array.isArray(c.frames)) {
        throw new ApiError({ code: "MALFORMED_RESPONSE", message: "Case content is missing steps or frames." });
      }
      return c;
    },
    presetFrames: async (presetId, caseId, signal) =>
      normalizePresetFrames(
        await requestJson(
          "GET",
          `/presets/${enc(presetId)}/frames${caseId ? `?case_id=${enc(caseId)}` : ""}`,
          undefined,
          signal,
          DEFAULT_TIMEOUT_MS,
        ),
      ),
    search: async (req, signal) =>
      normalizeSearchResponse(
        await requestJson("POST", "/search", { schema_version: SCHEMA_VERSION, ...req }, signal, SEARCH_TIMEOUT_MS),
      ),
    frame: async (frameToken, signal) =>
      normalizeFrameResponse(
        await requestJson(
          "POST",
          "/frame",
          { schema_version: SCHEMA_VERSION, frame_token: frameToken },
          signal,
          FRAME_TIMEOUT_MS,
        ),
      ),
  };
}
