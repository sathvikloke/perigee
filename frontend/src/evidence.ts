import type { FrameRecord } from './api/types';
import { qualityStatus, releaseLabel } from './format';

export const APP_VERSION = 'perigee-frontend-b/0.2.0';
export const NOTE_FIELDS = ['claim', 'observations', 'uncertainty'] as const;
export type NoteField = (typeof NOTE_FIELDS)[number];
export type Notes = Record<NoteField, string>;
export const EMPTY_NOTES: Notes = { claim: '', observations: '', uncertainty: '' };

export interface SelectedFrame {
  ref: string;
  frame: FrameRecord;
}

export interface EvidenceContext {
  investigationKey: string;
  caseId: string | null;
  presetId: string | null;
  query: { ra_deg: number; dec_deg: number; fov_arcmin: number } | null;
  comparison: string;
  selected: SelectedFrame[];
  sources: { label: string; url: string }[];
  limitations: string[];
}

export interface EvidenceCard {
  schema_version: 1;
  kind: 'perigee-evidence-card';
  id: string;
  created_at: string;
  updated_at: string;
  app_version: string;
  case_id: string | null;
  preset_id: string | null;
  query: EvidenceContext['query'];
  comparison: string;
  selected_frames: ReturnType<typeof frameSummary>[];
  notes: Notes;
  sources: { label: string; url: string }[];
  limitations: string[];
}

export function frameSummary({ ref, frame: f }: SelectedFrame) {
  return {
    ref,
    frame_id: f.frame_id,
    observation_id: f.observation_id,
    detector: f.detector ?? null,
    collection_id: f.collection_id,
    release: releaseLabel(f.collection_id),
    pipeline_version: f.provenance?.pipeline_version ?? null,
    observed_at_utc: f.observed_at_utc,
    mjd: f.mjd,
    wavelength_um: f.wavelength_um,
    bandwidth_um: f.bandwidth_um,
    wavelength_location: f.wavelength_location ?? null,
    quality: {
      status: qualityStatus(f),
      covered: f.quality?.covered ?? null,
      adverse_aperture_pixels: f.quality?.adverse_aperture_pixels ?? null,
      flag_names: f.quality?.flag_names ?? [],
    },
    source_url: f.source_url,
    cutout_url: f.provenance?.cutout_url ?? null,
    source_sha256: f.provenance?.sha256 ?? null,
    processing: {
      processing_version: f.provenance?.processing_version ?? null,
      registration_method: f.registration?.method ?? null,
      scale_arcsec_per_px: f.registration?.scale_arcsec_per_px ?? null,
      grid_id: f.registration?.grid_id ?? null,
      orientation: f.registration?.orientation ?? null,
      display_scale: f.display_scale?.mode ?? null,
      display_basis: f.display_scale?.basis ?? null,
    },
    marker: f.marker ? { kind: f.marker.kind, x: f.marker.x, y: f.marker.y } : null,
  };
}

/** Returns the first blank field, or null when every note has content. */
export function firstMissingNote(notes: Notes): NoteField | null {
  return NOTE_FIELDS.find((k) => !notes[k].trim()) ?? null;
}

export function buildEvidenceCard(ctx: EvidenceContext, notes: Notes, now = new Date(), id?: string): EvidenceCard {
  const stamp = now.toISOString();
  return {
    schema_version: 1,
    kind: 'perigee-evidence-card',
    id: id ?? `ev-${now.getTime().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    created_at: stamp,
    updated_at: stamp,
    app_version: APP_VERSION,
    case_id: ctx.caseId,
    preset_id: ctx.presetId,
    query: ctx.query,
    comparison: ctx.comparison,
    selected_frames: ctx.selected.map(frameSummary),
    notes: { claim: notes.claim.trim(), observations: notes.observations.trim(), uncertainty: notes.uncertainty.trim() },
    sources: ctx.sources,
    limitations: ctx.limitations,
  };
}

export const serializeCard = (card: EvidenceCard) => JSON.stringify(card, null, 2);

// ---- browser storage (notes per investigation, saved cards) ----

const NOTES_KEY = 'perigee.b.notes.v1';
const CARDS_KEY = 'perigee.b.cards.v1';
const MAX_CARDS = 30;

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function loadNotes(investigationKey: string): Notes | null {
  const all = readJson<Record<string, Partial<Notes>>>(NOTES_KEY, {});
  const n = all[investigationKey];
  if (!n) return null;
  return {
    claim: typeof n.claim === 'string' ? n.claim : '',
    observations: typeof n.observations === 'string' ? n.observations : '',
    uncertainty: typeof n.uncertainty === 'string' ? n.uncertainty : '',
  };
}

/** Returns false when browser storage is unavailable. */
export function saveNotes(investigationKey: string, notes: Notes): boolean {
  try {
    const all = readJson<Record<string, Notes>>(NOTES_KEY, {});
    all[investigationKey] = notes;
    localStorage.setItem(NOTES_KEY, JSON.stringify(all));
    return true;
  } catch {
    return false;
  }
}

export function savedCards(): EvidenceCard[] {
  const cards = readJson<EvidenceCard[]>(CARDS_KEY, []);
  return Array.isArray(cards) ? cards : [];
}

export function storeCard(card: EvidenceCard): number | null {
  try {
    const cards = [card, ...savedCards().filter((c) => c.id !== card.id)].slice(0, MAX_CARDS);
    localStorage.setItem(CARDS_KEY, JSON.stringify(cards));
    return cards.length;
  } catch {
    return null;
  }
}

export function downloadCard(card: EvidenceCard) {
  const url = URL.createObjectURL(new Blob([serializeCard(card)], { type: 'application/json' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `perigee-evidence-${card.case_id ?? card.preset_id ?? 'coordinates'}-${card.created_at.slice(0, 10)}.json`;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}
