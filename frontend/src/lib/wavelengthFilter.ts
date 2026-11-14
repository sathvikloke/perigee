// Wavelength filter for the chronological stepper and Play (worker 13).
//
// A full series mixes wavelengths, so brightness and appearance jump between
// frames for reasons unrelated to motion. The filter keeps time order and only
// narrows which frames Earlier/Later, the slider and Play visit. Each frame's
// own wavelength_um and bandwidth_um decide membership. The detector option
// groups by the record's `detector` field and reports the wavelength range of
// the frames it actually contains; no wavelength is ever inferred from a
// detector number. Frames with no wavelength at the target are left out and
// counted, never treated as zero.

import type { FrameRecord } from "../api/types";

export type WaveFilter =
  | { mode: "all" }
  /** Frames whose wavelength is within their own band width of `center_um`. */
  | { mode: "near"; center_um: number }
  /** Frames from the same detector that have a wavelength at the target. */
  | { mode: "detector"; detector: number };

export const ALL_WAVELENGTHS: WaveFilter = { mode: "all" };

interface FilterableSlot {
  status: string;
  frame: FrameRecord | null;
}

export interface FilterResult {
  /** Slot indices the stepper and Play may visit, in the slots' time order. */
  indices: number[];
  total: number;
  /** Loaded frames with no wavelength at the target (for example, position off the image). */
  noWavelength: number;
  /** Loaded frames with a wavelength but no band width, so "near" cannot be judged. */
  noBandwidth: number;
  /** Frames not processed yet or failed: their wavelength is unknown. */
  notLoaded: number;
  /** Wavelength range of the frames kept, from their own values. */
  range: [number, number] | null;
}

export function nearBand(frame: Pick<FrameRecord, "wavelength_um" | "bandwidth_um">, center_um: number): boolean {
  const w = frame.wavelength_um;
  const bw = frame.bandwidth_um;
  if (w == null || bw == null || !Number.isFinite(w) || !Number.isFinite(bw)) return false;
  // A tiny tolerance so a frame is always "near" its own wavelength.
  return Math.abs(w - center_um) <= bw + 1e-9;
}

export function applyWaveFilter(slots: readonly FilterableSlot[], filter: WaveFilter): FilterResult {
  const out: FilterResult = { indices: [], total: slots.length, noWavelength: 0, noBandwidth: 0, notLoaded: 0, range: null };
  let lo = Infinity;
  let hi = -Infinity;
  slots.forEach((s, i) => {
    const f = s.status === "ready" ? s.frame : null;
    let keep: boolean;
    if (filter.mode === "all") {
      keep = true;
    } else if (!f) {
      out.notLoaded++;
      keep = false;
    } else if (f.wavelength_um == null) {
      out.noWavelength++;
      keep = false;
    } else if (filter.mode === "near") {
      if (f.bandwidth_um == null) {
        out.noBandwidth++;
        keep = false;
      } else keep = nearBand(f, filter.center_um);
    } else {
      keep = f.detector === filter.detector;
    }
    if (!keep) return;
    out.indices.push(i);
    const w = f?.wavelength_um;
    if (w != null) {
      lo = Math.min(lo, w);
      hi = Math.max(hi, w);
    }
  });
  if (lo <= hi) out.range = [lo, hi];
  return out;
}

/** "2.01 µm": short form for labels; full precision stays in the frame details. */
export const shortMicrons = (v: number) => `${v.toFixed(2)} µm`;

export function filterOptionLabel(filter: WaveFilter): string {
  switch (filter.mode) {
    case "all":
      return "All wavelengths";
    case "near":
      return `Near ${shortMicrons(filter.center_um)} (within one band width)`;
    case "detector":
      return `Detector ${filter.detector} only`;
  }
}

/** " near 2.01 µm" / " from detector 3" / "" for spoken and visible counts. */
export function filterScope(filter: WaveFilter): string {
  if (filter.mode === "near") return ` near ${shortMicrons(filter.center_um)}`;
  if (filter.mode === "detector") return ` from detector ${filter.detector}`;
  return "";
}

const plural =(n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/**
 * Visible summary under the stepper, e.g. "3 of 34 frames near 2.01 µm".
 * Exclusions are listed separately so missing values never read as zero.
 */
export function filterSummary(filter: WaveFilter, r: FilterResult): string[] {
  if (filter.mode === "all") return [];
  const range = r.range
    ? r.range[0] === r.range[1]
      ? ` (${r.range[0].toFixed(4)} µm)`
      : ` (${r.range[0].toFixed(4)}–${r.range[1].toFixed(4)} µm)`
    : "";
  const what =
    filter.mode === "near"
      ? `near ${shortMicrons(filter.center_um)}, each within its own band width`
      : `from detector ${filter.detector}`;
  const lines = [`${r.indices.length} of ${plural(r.total, "frame", "frames")} ${what}${range}.`];
  if (r.noWavelength) {
    lines.push(`${plural(r.noWavelength, "frame has", "frames have")} no wavelength at the target, so ${r.noWavelength === 1 ? "it is" : "they are"} left out.`);
  }
  if (r.noBandwidth) {
    lines.push(`${plural(r.noBandwidth, "frame has", "frames have")} no band width, so ${r.noBandwidth === 1 ? "it is" : "they are"} left out.`);
  }
  if (r.notLoaded) {
    lines.push(`${plural(r.notLoaded, "frame is", "frames are")} not loaded, so ${r.notLoaded === 1 ? "its" : "their"} wavelength is unknown and ${r.notLoaded === 1 ? "it is" : "they are"} left out.`);
  }
  return lines;
}

/** Nearest kept index strictly before (dir -1) or after (dir +1) `from`; -1 if none. */
export function stepWithin(indices: readonly number[], from: number, dir: -1 | 1): number {
  if (dir > 0) {
    for (const i of indices) if (i > from) return i;
    return -1;
  }
  for (let k = indices.length - 1; k >= 0; k--) if (indices[k] < from) return indices[k];
  return -1;
}

/** Slider position for `index`: its place in the kept list, or the nearest earlier kept frame. */
export function sliderPosition(indices: readonly number[], index: number): number {
  let pos = 0;
  for (let k = 0; k < indices.length; k++) if (indices[k] <= index) pos = k;
  return pos;
}

/**
 * Short status tag for a frame that has no image yet, shown in the counter,
 * the slider's spoken value and the blink pair picker. Null when ready.
 */
export function slotStatusTag(slot: { status: string; error?: { code: string } | null }): string | null {
  switch (slot.status) {
    case "ready":
      return null;
    case "pending":
      return "not loaded yet";
    case "loading":
      return "loading";
    case "error":
      return slot.error?.code === "SUPERSEDED" ? "not loaded (stopped)" : "failed to load";
    default:
      return "not loaded";
  }
}
