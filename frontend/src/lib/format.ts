import type { FrameRecord, QualityStatus } from "../api/types";

/** "2026-04-29T12:05:47.874" → "2026-04-29 12:05:47 UTC". Uses the string as given. */
export function formatUtc(iso: string | null | undefined): string {
  if (!iso) return "Not available";
  const m = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/.exec(iso);
  return m ? `${m[1]} ${m[2]} UTC` : iso;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Short human date, always in UTC so it matches the archive timestamp. */
export function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return "Unknown date";
  const withZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(withZone);
  if (Number.isNaN(d.getTime())) return iso;
  // Fixed "29 Apr 2026" form (design reference); UTC so it matches the archive.
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
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
    "The predicted position is just outside this image, so this frame can't show the object there. That is not evidence the object is absent.",
  unknown:
    "The flag screen was not run or could not be completed for this frame, so its quality is unknown. Treat it as unchecked, not as clear.",
};

/**
 * Quality explanation for one frame. Curated frames screen the catalog
 * prediction; live search frames without a marker screen the query center.
 */
export function qualityExplanation(frame: Pick<FrameRecord, "quality" | "marker">): string {
  const text = QUALITY_EXPLANATION[frame.quality.status];
  return frame.marker ? text : text.replace(/the predicted position/g, "the searched position");
}

/**
 * Problem-flag list for one frame. An empty list only means "none" when the
 * screen actually ran; unknown and not-covered frames were never screened.
 */
export function formatFlagNames(q: Pick<FrameRecord["quality"], "status" | "flag_names">): string {
  if (q.flag_names.length) return q.flag_names.join(", ");
  if (q.status === "unknown") return "not checked";
  if (q.status === "not_covered") return "not checked (the position is off this image)";
  return "none reported";
}

export function formatPixelCount(v: number | null): string {
  return v == null ? "not available" : String(v);
}

export function qualityNotes(notes: string[] | string | null): string[] {
  if (!notes) return [];
  return Array.isArray(notes) ? notes : [notes];
}
