import type { FrameRecord, QualityStatus } from "../api/types";

/** "2026-04-29T12:05:47.874" → "2026-04-29 12:05:47 UTC". Uses the string as given. */
export function formatUtc(iso: string | null | undefined): string {
  if (!iso) return "Not available";
  const m = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/.exec(iso);
  return m ? `${m[1]} ${m[2]} UTC` : iso;
}

/** Short human date, always in UTC so it matches the archive timestamp. */
export function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return "Unknown date";
  const withZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(withZone);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(d);
}

export function formatMicrons(v: number | null | undefined, digits = 4): string {
  return v == null ? "Not available" : `${v.toFixed(digits)} µm`;
}

export function formatWavelength(frame: Pick<FrameRecord, "wavelength_um" | "bandwidth_um" | "quality">): string {
  if (frame.wavelength_um == null) {
    return frame.quality.status === "not_covered"
      ? "Not available — the position is off this image"
      : "Not available";
  }
  const bw = frame.bandwidth_um != null ? ` (band width ${frame.bandwidth_um.toFixed(4)} µm)` : "";
  return `${frame.wavelength_um.toFixed(4)} µm${bw}`;
}

export function daysBetween(mjdA: number, mjdB: number): number {
  return Math.abs(mjdB - mjdA);
}

export function formatDuration(days: number): string {
  if (days < 1 / 24) return "under an hour apart";
  if (days < 1) return `${Math.round(days * 24)} hours apart`;
  if (days < 60) return `${Math.round(days)} days apart`;
  return `${Math.round(days)} days (about ${(days / 30.44).toFixed(1)} months) apart`;
}

export const QUALITY_LABEL: Record<QualityStatus, string> = {
  clear: "Passes the flag screen",
  flagged: "Flagged",
  not_covered: "Not covered",
  unknown: "Not checked",
};

export const QUALITY_EXPLANATION: Record<QualityStatus, string> = {
  clear:
    "No problem flags were found in a small circle around the predicted position. The frame is usable for a visual comparison. This is not a detection and not a brightness measurement.",
  flagged:
    "Problem flags or missing pixels were found near the predicted position. You can look, but brightness and exact position here are not reliable.",
  not_covered:
    "The predicted position is outside this image. Absence here says nothing about the object.",
  unknown:
    "The quality screen could not be completed for this frame. Treat it as unchecked.",
};

export function formatPixelCount(v: number | null): string {
  return v == null ? "not available" : String(v);
}

export function qualityNotes(notes: string[] | string | null): string[] {
  if (!notes) return [];
  return Array.isArray(notes) ? notes : [notes];
}
