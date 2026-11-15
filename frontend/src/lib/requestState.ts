// Pure helpers for the live coordinate search's loading, partial and recovery
// states (docs/INTEGRATION_CONTRACT.md "Error and loading behavior"). Kept out
// of the components so the wording and the rules are unit-tested.

import type { SearchResponse } from "../api/types";
import type { ValidQuery } from "./coords";

/** Describes the processing lifecycle without tying announcements to frame playback. */
export function frameProcessingAnnouncement(counts: { pending: number; loading: number; ready: number; error: number }): string {
  const working = counts.pending + counts.loading;
  const ready = `${counts.ready} frame${counts.ready === 1 ? "" : "s"} ready`;
  const failed = counts.error ? `; ${counts.error} could not be processed` : "";
  return working
    ? `${ready}; ${working} still processing${failed}.`
    : `Frame processing finished: ${ready}${failed}.`;
}

export function sameQuery(a: ValidQuery, b: ValidQuery): boolean {
  return a.ra_deg === b.ra_deg && a.dec_deg === b.dec_deg && a.fov_arcmin === b.fov_arcmin && a.limit === b.limit;
}

/**
 * True when a submit would only repeat the search already in flight (a fast
 * double-click, a held Enter key, a double-tapped retry). A different query
 * is never a duplicate: it supersedes and aborts the one in flight.
 */
export function isDuplicateSubmit(inFlight: ValidQuery | null, next: ValidQuery): boolean {
  return inFlight !== null && sameQuery(inFlight, next);
}

/** "8 s", "1 min 05 s". Whole seconds; never negative. */
export function formatElapsed(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s} s`;
  return `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, "0")} s`;
}

/** After this long a search is "slow" and the UI says the archive may be busy. */
export const SLOW_SEARCH_MS = 8_000;

/** Collections that answered and those that could not be searched. */
export function searchScope(r: Pick<SearchResponse, "collections_queried" | "collections_failed">): {
  answered: string[];
  failed: string[];
} {
  const failed = r.collections_failed ?? [];
  return { answered: r.collections_queried.filter((c) => !failed.includes(c)), failed };
}

interface SlotLike {
  status: string;
  error: { code: string; retryable: boolean } | null;
}

/**
 * Frames worth retrying, in result order. An expired search token is not
 * retryable frame by frame (the whole search must run again), and neither is
 * a non-retryable processing failure.
 */
export function retryableFailedIndices(slots: readonly SlotLike[]): number[] {
  const out: number[] = [];
  slots.forEach((s, i) => {
    if (s.status === "error" && s.error?.retryable && s.error.code !== "TOKEN_EXPIRED") out.push(i);
  });
  return out;
}

/** Frames that were stopped (not failed) because a newer search started. */
export function stoppedCount(slots: readonly SlotLike[]): number {
  return slots.filter((s) => s.status === "error" && s.error?.code === "SUPERSEDED").length;
}

/** Label for the bulk retry: stopped frames were never tried, so they are "loaded", not "retried". */
export function retryActionLabel(slots: readonly SlotLike[], indices: readonly number[]): string {
  const n = indices.length;
  const stopped = indices.filter((i) => slots[i]?.error?.code === "SUPERSEDED").length;
  const s = n === 1 ? "" : "s";
  if (stopped === 0) return `Retry ${n} failed frame${s}`;
  if (stopped === n) return `Load ${n} stopped frame${s}`;
  return `Retry ${n} unfinished frames`;
}

/** Failures before any archive answer: the browser or the Perigee API, not IRSA. */
const CONNECTION_CODES = new Set(["NETWORK_ERROR", "CLIENT_TIMEOUT", "NON_JSON_RESPONSE"]);

/** Heading for a failed search. Neither wording claims anything about the sky. */
export function searchFailureTitle(code: string | null): string {
  return code && CONNECTION_CODES.has(code)
    ? "The search couldn’t connect. Try again when your connection is ready."
    : "The archive search couldn’t finish. You can try again.";
}
