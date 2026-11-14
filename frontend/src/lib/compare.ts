// Pair comparison helpers. Every statement is computed from the two
// FrameRecords; nothing is hardcoded to a particular case.

import type { FrameRecord, Marker, QualityStatus } from "../api/types";
import { formatDuration } from "./format";

const RELEASE: Record<string, string> = { spherex_dr1: "DR1", spherex_qr3: "QR3" };
export function releaseLabel(collectionId: string): string {
  return RELEASE[collectionId] ?? collectionId;
}

export function markerXY(m: Marker | null): { x: number; y: number } | null {
  if (!m) return null;
  const pixel = m.pixel as { x?: number; y?: number } | undefined;
  const x = m.x ?? m.x_px ?? pixel?.x;
  const y = m.y ?? m.y_px ?? pixel?.y;
  return typeof x === "number" && typeof y === "number" ? { x, y } : null;
}

/** Short chip text for the flag screen. Status words stay explicit; never hardcoded. */
export const QUALITY_CHIP: Record<QualityStatus, string> = {
  clear: "Flag screen passed",
  flagged: "Flagged near target",
  not_covered: "Target not covered",
  unknown: "Flag screen not run",
};

export type PairKind = "time" | "wavelength" | "both" | "unknown";

export interface PairAnalysis {
  kind: PairKind;
  /** Segmented-control subtitle. */
  subtitle: string;
  title: string;
  body: string;
  caveats: string[];
  sameTime: boolean;
}

const ONE_HOUR_DAYS = 1 / 24;

export function analyzePair(a: FrameRecord, b: FrameRecord): PairAnalysis {
  const dt = Math.abs(b.mjd - a.mjd);
  const sameTime = dt < ONE_HOUR_DAYS;
  const dl =
    a.wavelength_um != null && b.wavelength_um != null ? Math.abs(a.wavelength_um - b.wavelength_um) : null;
  const bandwidths = [a.bandwidth_um, b.bandwidth_um].filter((v): v is number => v != null);
  const bw = bandwidths.length ? Math.min(...bandwidths) : null;
  const sameColor = dl != null && bw != null && dl < bw / 2;
  const bothClear = a.quality.status === "clear" && b.quality.status === "clear";

  const caveats: string[] = [];
  if (a.quality.status !== "clear" || b.quality.status !== "clear") {
    caveats.push("At least one frame did not pass the flag screen near the target: look, but don't measure.");
  }
  if (a.display_scale?.mode === "per_frame" || b.display_scale?.mode === "per_frame") {
    caveats.push("Each frame has its own contrast stretch, so brightness is not directly comparable.");
  }
  if (a.collection_id !== b.collection_id) {
    caveats.push(
      `The frames come from different data releases (${releaseLabel(a.collection_id)} and ${releaseLabel(b.collection_id)}).`,
    );
  }

  if (dl == null) {
    return {
      kind: "unknown",
      subtitle: sameTime ? "Same time" : "Different dates",
      title: "Wavelength not available for one frame",
      body: "Without both wavelengths you can't tell whether a difference comes from time or from color.",
      caveats,
      sameTime,
    };
  }
  const dlText = `${dl.toFixed(4)} µm`;
  if (sameTime && !sameColor) {
    return {
      kind: "wavelength",
      subtitle: "Different wavelengths",
      title: "Same moment, a different infrared color",
      body: `These were taken at the same time, ${dlText} apart in wavelength. This pair compares wavelengths, not change over time. A different appearance is not evidence that time changed the object.`,
      caveats,
      sameTime,
    };
  }
  if (!sameTime && sameColor) {
    return {
      kind: "time",
      subtitle: "Different dates",
      title: "Different dates, nearly the same wavelength",
      body: `${capitalize(formatDuration(dt))}. The wavelengths differ by ${dlText}, well inside one band's width, so ${
        bothClear
          ? "this pair passes the first checks for a fair comparison of change over time."
          : "the colors match; the quality screen still needs a look."
      }`,
      caveats,
      sameTime,
    };
  }
  if (sameTime && sameColor) {
    return {
      kind: "unknown",
      subtitle: "Same time and wavelength",
      title: "Same moment, same color",
      body: "These two frames record the same time and nearly the same wavelength.",
      caveats,
      sameTime,
    };
  }
  return {
    kind: "both",
    subtitle: "Different dates and wavelengths",
    title: "Both the date and the wavelength differ",
    body: `${capitalize(formatDuration(dt))} and ${dlText} apart in wavelength. A difference could come from time or from color; this pair can't separate them.`,
    caveats,
    sameTime,
  };
}

function capitalize(s: string): string {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}
