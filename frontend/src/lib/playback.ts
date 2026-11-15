// Series playback ("like a little video") over the chronological stepper.
// Pure helpers so the cadence, ordering and caveats are unit-tested; the
// timer itself lives in FrameViewer next to the two-frame blink timer.

import type { FrameRecord } from "../api/types";
import { filterScope, type WaveFilter } from "./wavelengthFilter";

/** About 2 frames per second; reduced-motion visitors get a slower cadence. */
export const PLAY_MS = 500;
export const PLAY_MS_REDUCED = 1500;

export function playCadenceMs(reducedMotion: boolean): number {
  return reducedMotion ? PLAY_MS_REDUCED : PLAY_MS;
}

interface PlayableSlot {
  status: string;
  frame: FrameRecord | null;
}

const playable = (s: PlayableSlot | undefined) => Boolean(s && s.status === "ready" && s.frame);

/** `allowed` (slot indices kept by the wavelength filter) narrows what can play. */
export function playableCount(slots: readonly PlayableSlot[], allowed?: readonly number[]): number {
  if (!allowed) return slots.filter(playable).length;
  return allowed.filter((i) => playable(slots[i])).length;
}

/**
 * The next ready frame after `from`, in the slots' chronological order,
 * wrapping to the earliest. Pending, loading and failed frames are skipped,
 * never reordered. Returns -1 when no other frame is ready. With `allowed`,
 * only those slot indices are visited (frames outside the wavelength filter
 * are skipped the same way).
 */
export function nextPlayableIndex(slots: readonly PlayableSlot[], from: number, allowed?: readonly number[]): number {
  const n = slots.length;
  const ok = allowed ? new Set(allowed) : null;
  for (let step = 1; step <= n; step++) {
    const i = (((from + step) % n) + n) % n;
    if (i === from) break;
    if (playable(slots[i]) && (!ok || ok.has(i))) return i;
  }
  return -1;
}

/**
 * Honest caveats shown while the series plays. Each wording matches the
 * existing per-frame notes (FrameDetails, compare.ts) rather than inventing
 * a new claim.
 */
export function playbackCaveats(
  slots: readonly PlayableSlot[],
  allowed?: readonly number[],
  filter: WaveFilter = { mode: "all" },
): string[] {
  const kept = allowed ? allowed.map((i) => slots[i]) : slots;
  const frames = kept.filter(playable).map((s) => s.frame as FrameRecord);
  const out: string[] = [];
  if (frames.some((f) => f.display_scale?.mode === "per_frame")) {
    out.push("Each frame has its own contrast stretch, so brightness is not directly comparable.");
  }
  const waves = frames.map((f) => f.wavelength_um).filter((w): w is number => w != null);
  const lo = Math.min(...waves);
  const hi = Math.max(...waves);
  // The near filter's count and range are already stated beside the select,
  // so no extra wavelength line is added for it while playing.
  if (filter.mode === "near") return out;
  if (filter.mode === "detector") {
    if (hi > lo) out.push(`These detector ${filter.detector} frames still differ in wavelength by up to ${(hi - lo).toFixed(2)} µm; each is labeled.`);
  } else if (new Set(waves).size > 1) {
    out.push("The wavelength also changes from frame to frame; it is labeled on each one.");
  }
  return out;
}

export function playAnnouncement(count: number, filter: WaveFilter = { mode: "all" }): string {
  return `Playing ${count} frames${filterScope(filter)} in time order. Use Pause to stop.`;
}
