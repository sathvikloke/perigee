// Series playback ("like a little video") over the chronological stepper.
// Pure helpers so the cadence, ordering and caveats are unit-tested; the
// timer itself lives in FrameViewer next to the two-frame blink timer.

import type { FrameRecord } from "../api/types";

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

export function playableCount(slots: readonly PlayableSlot[]): number {
  return slots.filter(playable).length;
}

/**
 * The next ready frame after `from`, in the slots' chronological order,
 * wrapping to the earliest. Pending, loading and failed frames are skipped,
 * never reordered. Returns -1 when no other frame is ready.
 */
export function nextPlayableIndex(slots: readonly PlayableSlot[], from: number): number {
  const n = slots.length;
  for (let step = 1; step <= n; step++) {
    const i = (((from + step) % n) + n) % n;
    if (i === from) break;
    if (playable(slots[i])) return i;
  }
  return -1;
}

/**
 * Honest caveats shown while the series plays. Each wording matches the
 * existing per-frame notes (FrameDetails, compare.ts) rather than inventing
 * a new claim.
 */
export function playbackCaveats(slots: readonly PlayableSlot[]): string[] {
  const frames = slots.filter(playable).map((s) => s.frame as FrameRecord);
  const out: string[] = [];
  if (frames.some((f) => f.display_scale?.mode === "per_frame")) {
    out.push("Each frame has its own contrast stretch, so brightness is not directly comparable.");
  }
  const waves = new Set(frames.map((f) => f.wavelength_um).filter((w): w is number => w != null));
  if (waves.size > 1) out.push("The wavelength also changes from frame to frame; it is labeled on each one.");
  return out;
}

export function playAnnouncement(count: number): string {
  return `Playing ${count} frames in time order. Use Pause to stop.`;
}
