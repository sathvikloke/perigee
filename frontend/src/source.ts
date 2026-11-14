// What the learner is looking at. The URL is the single source of truth, so a
// shared link reproduces coordinates, field of view and case, never private notes.

export type Source =
  | { kind: 'case'; caseId: string }
  | { kind: 'preset'; presetId: string }
  | { kind: 'coords'; ra: number; dec: number; fov: number };

export const DEFAULT_SOURCE: Source = { kind: 'case', caseId: 'fair_comparison' };
export const CASE_IDS = ['fair_comparison', 'moving_neighbor'] as const;
export const FOV_MIN = 2;
export const FOV_MAX = 10;

export function sourceKey(s: Source): string {
  if (s.kind === 'case') return `case:${s.caseId}`;
  if (s.kind === 'preset') return `preset:${s.presetId}`;
  return `coords:${s.ra.toFixed(4)},${s.dec.toFixed(4)},${s.fov}`;
}

export function sourceFromSearch(search: string): Source {
  const p = new URLSearchParams(search);
  const c = p.get('case');
  if (c && /^[a-z0-9_]{1,64}$/.test(c)) return { kind: 'case', caseId: c };
  const pr = p.get('preset');
  if (pr && /^[a-z0-9_]{1,64}$/.test(pr)) return { kind: 'preset', presetId: pr };
  if (p.has('ra') && p.has('dec')) {
    const ra = parseCoordinate(p.get('ra') ?? '', 'ra');
    const dec = parseCoordinate(p.get('dec') ?? '', 'dec');
    const fov = parseCoordinate(p.get('fov') ?? '6', 'fov');
    if (ra.ok && dec.ok && fov.ok) return { kind: 'coords', ra: ra.value, dec: dec.value, fov: fov.value };
  }
  return DEFAULT_SOURCE;
}

export function sourceToSearch(s: Source): string {
  if (s.kind === 'case') return `?case=${s.caseId}`;
  if (s.kind === 'preset') return `?preset=${s.presetId}`;
  return `?ra=${s.ra}&dec=${s.dec}&fov=${s.fov}`;
}

type Parsed = { ok: true; value: number } | { ok: false; message: string };

/** Strict parse: rejects partial numbers, NaN, infinity and out-of-range values (no silent clipping). */
export function parseCoordinate(raw: string, field: 'ra' | 'dec' | 'fov'): Parsed {
  const text = raw.trim().replace(/^−/, '-');
  if (!/^[-+]?(\d+(\.\d*)?|\.\d+)$/.test(text)) {
    return { ok: false, message: field === 'fov' ? 'Enter the field size as a number of arcminutes.' : 'Enter decimal degrees, for example 330.84.' };
  }
  const value = Number(text);
  if (!Number.isFinite(value)) return { ok: false, message: 'Enter a finite number.' };
  if (field === 'ra' && (value < 0 || value >= 360)) return { ok: false, message: 'Right ascension must be at least 0 and less than 360 degrees.' };
  if (field === 'dec' && (value < -90 || value > 90)) return { ok: false, message: 'Declination must be between −90 and 90 degrees.' };
  if (field === 'fov' && (value < FOV_MIN || value > FOV_MAX)) return { ok: false, message: `Field size must be ${FOV_MIN} to ${FOV_MAX} arcminutes.` };
  return { ok: true, value };
}
