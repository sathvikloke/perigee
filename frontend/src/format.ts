import type { FrameRecord, QualityStatus } from './api/types';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "29 Apr 2026" in UTC, or null when the archive did not supply a time. */
export function formatDate(utc: string | null | undefined): string | null {
  if (!utc) return null;
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(utc) ? utc : `${utc}Z`);
  if (Number.isNaN(d.getTime())) return null;
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export function isoDate(utc: string | null | undefined): string | undefined {
  return utc ? utc.slice(0, 10) : undefined;
}

export function formatWavelength(um: number | null | undefined): string | null {
  return typeof um === 'number' && Number.isFinite(um) ? `${um.toFixed(4)} µm` : null;
}

export function releaseLabel(collectionId: string): string {
  const m = /spherex_(\w+)/i.exec(collectionId);
  return m ? m[1].toUpperCase() : collectionId;
}

export function detectorLabel(f: FrameRecord): string {
  return typeof f.detector === 'number' ? `Detector ${f.detector}` : 'Detector not stated';
}

/** Missing quality is unknown, never clear. */
export function qualityStatus(f: FrameRecord): QualityStatus {
  const s = f.quality?.status;
  return s === 'clear' || s === 'flagged' || s === 'not_covered' ? s : 'unknown';
}

export const QUALITY_TEXT: Record<QualityStatus, { icon: string; label: string }> = {
  clear: { icon: '✓', label: 'Flag screen passed' },
  flagged: { icon: '⚑', label: 'Flagged near target' },
  not_covered: { icon: '○', label: 'Position just outside image' },
  unknown: { icon: '?', label: 'Quality unknown' },
};

export function daysBetween(a: FrameRecord, b: FrameRecord): number | null {
  if (a.mjd == null || b.mjd == null) return null;
  return Math.abs(b.mjd - a.mjd);
}

export function describeSpan(days: number): string {
  if (days < 0.01) return 'the same moment';
  if (days < 1.5) return `${Math.round(days * 24)} hours apart`;
  if (days < 60) return `${Math.round(days)} days apart`;
  const months = Math.round(days / 30.44);
  if (months < 18) return `about ${months} months apart`;
  return `about ${(days / 365.25).toFixed(1)} years apart`;
}

export type PairKind = 'same_time' | 'fair_time' | 'mixed' | 'unknown';

/** Classify a pair from its documented fields only. */
export function classifyPair(a: FrameRecord, b: FrameRecord): PairKind {
  const days = daysBetween(a, b);
  if (days == null) return 'unknown';
  if (days < 0.01) return 'same_time';
  if (a.wavelength_um == null || b.wavelength_um == null) return 'unknown';
  const band = Math.min(a.bandwidth_um ?? Infinity, b.bandwidth_um ?? Infinity);
  const dl = Math.abs(a.wavelength_um - b.wavelength_um);
  const tolerance = Number.isFinite(band) ? band / 2 : 0.01;
  return dl <= tolerance ? 'fair_time' : 'mixed';
}

export function pairInsight(a: FrameRecord, b: FrameRecord, la: string, lb: string): { title: string; body: string; warn: boolean } {
  const kind = classifyPair(a, b);
  const days = daysBetween(a, b);
  const dl = a.wavelength_um != null && b.wavelength_um != null ? Math.abs(a.wavelength_um - b.wavelength_um) : null;
  switch (kind) {
    case 'same_time':
      return {
        title: 'Same moment, a different infrared color',
        body: `${la} and ${lb} were taken at the same time. This pair compares wavelengths, not change over time. A different appearance is not evidence that time changed the object.`,
        warn: true,
      };
    case 'fair_time':
      return {
        title: 'Different dates, nearly the same wavelength',
        body: `${capital(describeSpan(days!))}. The wavelengths differ by ${dl!.toFixed(4)} µm, less than half of each band's width, so ${la} + ${lb} passes the first check for a fair comparison over time.`,
        warn: false,
      };
    case 'mixed':
      return {
        title: 'Both the date and the wavelength changed',
        body: `${capital(describeSpan(days!))} and ${dl!.toFixed(3)} µm apart in wavelength. A difference here could come from time or from infrared color, so it cannot be blamed on time alone.`,
        warn: true,
      };
    default:
      return {
        title: 'Check dates and wavelengths before comparing',
        body: 'A date or wavelength is missing for one of these frames, so Perigee cannot say whether this pair isolates change over time.',
        warn: true,
      };
  }
}

const capital = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
