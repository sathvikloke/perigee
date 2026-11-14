// Evidence card: the contract's "Content and evidence contracts" section.
// schema_version, locally generated id, creation/update times, case ID when
// present, query coordinates, selected frame identities with
// dates/wavelengths/quality summaries, claim, observations, uncertainty,
// sources and application version. Stored in localStorage; exported as JSON.
// Never stores images, raw FITS or secrets.
//
// Additive fields (still schema_version 1; older cards lack them and are
// normalized on load, see normalizeEvidenceCard):
//   title             human name of the investigation (case title, else the
//                     preset display name); null for a coordinate search or an
//                     older card that has not been reopened yet.
//   case_limitations  the case's `limitations`, copied verbatim from the API;
//                     null when no case is active or the card predates the field.
//   frames[].limitations  the FrameRecord's `limitations`, verbatim; [] when the
//                     API reported none, null when the frame was attached before
//                     the field existed.

import type { FrameRecord, QualityStatus, SourceLink } from "../api/types";

export const EVIDENCE_SCHEMA_VERSION = 1 as const;
export const CLAIM_MAX = 280;
export const TEXT_MAX = 2000;
export const MAX_STORED_CARDS = 50;
export const STORAGE_KEY = "perigee.evidence.v1";
/** Defensive bounds for API-supplied limitation lists. Items are never shortened or reworded. */
export const MAX_LIMITATIONS = 20;

export type DataOrigin = "api" | "fixture";

export interface EvidenceFrame {
  ref: string | null;
  frame_key: string;
  frame_id: string;
  observation_id: string;
  detector: number | null;
  collection_id: string;
  observed_at_utc: string;
  mjd: number;
  wavelength_um: number | null;
  bandwidth_um: number | null;
  wavelength_location: string | null;
  quality_status: QualityStatus;
  quality_flag_names: string[];
  display_scale_mode: "shared" | "per_frame" | null;
  source_url: string;
  /** The frame's limitations, verbatim from the API. Null: attached before this field existed. */
  limitations?: string[] | null;
  /** How the display image was made (from the FrameRecord). Null when not reported. */
  processing?: EvidenceProcessing;
}

export interface EvidenceProcessing {
  processing_version: string | null;
  /** Archive pipeline version of the source file (e.g. "l2b-v27-2026-230"), when the API reports it. */
  pipeline_version?: string | null;
  file_sha256: string | null;
  registration_method: string | null;
  display_scale_method: string | null;
  marker_kind: string | null;
}

export interface EvidenceQuery {
  ra_deg: number;
  dec_deg: number;
  fov_arcmin: number;
}

export interface EvidenceCard {
  schema_version: typeof EVIDENCE_SCHEMA_VERSION;
  id: string;
  created_at_utc: string;
  updated_at_utc: string;
  case_id: string | null;
  preset_id: string | null;
  /** Case title, else the preset display name; null for a coordinate search or an older card. */
  title?: string | null;
  query: EvidenceQuery | null;
  frames: EvidenceFrame[];
  claim: string;
  observations: string;
  uncertainty: string;
  /** The active case's limitations, verbatim from the API; null without a case or on an older card. */
  case_limitations?: string[] | null;
  sources: SourceLink[];
  app_version: string;
  data_origin: DataOrigin;
}

/**
 * API limitation strings as stored: strings only, exact duplicates removed,
 * order and wording kept. Anything that is not a list becomes null (unknown).
 */
export function cleanLimitations(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  const out: string[] = [];
  for (const v of value) {
    if (typeof v !== "string" || !v.trim() || v.length > TEXT_MAX || out.includes(v)) continue;
    out.push(v);
    if (out.length >= MAX_LIMITATIONS) break;
  }
  return out;
}

const cleanTitle = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v.slice(0, CLAIM_MAX) : null);

export function generateId(): string {
  const c = globalThis.crypto as Crypto | undefined;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  return `ev-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createEvidenceCard(init: {
  case_id?: string | null;
  preset_id?: string | null;
  query?: EvidenceQuery | null;
  /** Case title, else preset display name. Omit for a coordinate search. */
  title?: string | null;
  /** The active case's `limitations` from the API. Ignored without a case_id. */
  case_limitations?: string[] | null;
  sources?: SourceLink[];
  app_version: string;
  data_origin: DataOrigin;
  now?: Date;
  id?: string;
}): EvidenceCard {
  const ts = (init.now ?? new Date()).toISOString();
  return {
    schema_version: EVIDENCE_SCHEMA_VERSION,
    id: init.id ?? generateId(),
    created_at_utc: ts,
    updated_at_utc: ts,
    case_id: init.case_id ?? null,
    preset_id: init.preset_id ?? null,
    title: cleanTitle(init.title),
    query: init.query ?? null,
    frames: [],
    claim: "",
    observations: "",
    uncertainty: "",
    case_limitations: init.case_id ? cleanLimitations(init.case_limitations) : null,
    sources: init.sources ?? [],
    app_version: init.app_version,
    data_origin: init.data_origin,
  };
}

export function frameToEvidence(frame: FrameRecord, ref: string | null): EvidenceFrame {
  return {
    ref,
    frame_key: frame.frame_key,
    frame_id: frame.frame_id,
    observation_id: frame.observation_id,
    detector: frame.detector,
    collection_id: frame.collection_id,
    observed_at_utc: frame.observed_at_utc,
    mjd: frame.mjd,
    wavelength_um: frame.wavelength_um,
    bandwidth_um: frame.bandwidth_um,
    wavelength_location: frame.wavelength_location,
    quality_status: frame.quality.status,
    quality_flag_names: [...frame.quality.flag_names],
    display_scale_mode: frame.display_scale?.mode ?? null,
    source_url: frame.source_url,
    limitations: cleanLimitations(frame.limitations) ?? [],
    processing: {
      processing_version: frame.provenance?.processing_version ?? null,
      pipeline_version: typeof frame.provenance?.pipeline_version === "string" ? frame.provenance.pipeline_version : null,
      file_sha256: frame.provenance?.file_sha256 ?? null,
      registration_method: typeof frame.registration?.method === "string" ? frame.registration.method : null,
      display_scale_method: typeof frame.display_scale?.method === "string" ? frame.display_scale.method : null,
      marker_kind: frame.marker?.kind ?? null,
    },
  };
}

/** Adds or removes a frame, keeping the list in chronological order. */
export function toggleEvidenceFrame(
  card: EvidenceCard,
  frame: FrameRecord,
  ref: string | null,
  now: Date = new Date(),
): EvidenceCard {
  const exists = card.frames.some((f) => f.frame_key === frame.frame_key);
  const frames = exists
    ? card.frames.filter((f) => f.frame_key !== frame.frame_key)
    : [...card.frames, frameToEvidence(frame, ref)].sort(
        (a, b) => a.mjd - b.mjd || (a.frame_key < b.frame_key ? -1 : a.frame_key > b.frame_key ? 1 : 0),
      );
  return { ...card, frames, updated_at_utc: now.toISOString() };
}

/**
 * Replaces the case-pair frames (any frame carrying one of `pairRefs`) with
 * the currently compared pair, keeping extra frames the learner added from
 * the full sequence. Returns the same object when nothing changes.
 */
export function attachPair(
  card: EvidenceCard,
  pair: { frame: FrameRecord; ref: string }[],
  pairRefs: string[],
  now: Date = new Date(),
): EvidenceCard {
  const want = pair.map((p) => p.frame.frame_key).sort().join("|");
  const have = card.frames
    .filter((f) => f.ref && pairRefs.includes(f.ref))
    .map((f) => f.frame_key)
    .sort()
    .join("|");
  if (want === have) return fillFrameLimitations(card, pair.map((p) => p.frame));
  const pairKeys = new Set(pair.map((p) => p.frame.frame_key));
  const extras = card.frames.filter((f) => !(f.ref && pairRefs.includes(f.ref)) && !pairKeys.has(f.frame_key));
  const frames = [...extras, ...pair.map((p) => frameToEvidence(p.frame, p.ref))].sort(
    (a, b) => a.mjd - b.mjd || (a.frame_key < b.frame_key ? -1 : a.frame_key > b.frame_key ? 1 : 0),
  );
  return { ...card, frames, updated_at_utc: now.toISOString() };
}

/**
 * Fills `limitations` on attached frames that predate the field, from the
 * matching FrameRecords. Never touches learner text or updated_at_utc.
 * Returns the same object when nothing changes.
 */
export function fillFrameLimitations(card: EvidenceCard, records: FrameRecord[]): EvidenceCard {
  let changed = false;
  const frames = card.frames.map((f) => {
    if (f.limitations != null) return f;
    const rec = records.find((r) => r.frame_key === f.frame_key);
    if (!rec) return f;
    changed = true;
    return { ...f, limitations: cleanLimitations(rec.limitations) ?? [] };
  });
  return changed ? { ...card, frames } : card;
}

/**
 * Fills a reopened card's missing title and case limitations from a freshly
 * made card for the same investigation (same case and preset). Existing
 * values and all learner text are kept; updated_at_utc is unchanged.
 * Returns the same object when nothing changes.
 */
export function fillCardContext(card: EvidenceCard, fresh: EvidenceCard): EvidenceCard {
  if (card.case_id !== fresh.case_id || card.preset_id !== fresh.preset_id) return card;
  const title = card.title ?? fresh.title ?? null;
  const case_limitations = card.case_limitations ?? fresh.case_limitations ?? null;
  if (title === (card.title ?? null) && case_limitations === (card.case_limitations ?? null)) return card;
  return { ...card, title, case_limitations };
}

/**
 * Export-time guarantee: a case card carries its case's title and
 * limitations when the case content is at hand, even if the card was made
 * before they were known. Existing values win. Same object when unchanged.
 */
export function withCaseContext(
  card: EvidenceCard,
  content: { case_id: string; title?: string; limitations?: string[] } | null | undefined,
): EvidenceCard {
  if (!content || !card.case_id || card.case_id !== content.case_id) return card;
  const title = card.title ?? cleanTitle(content.title);
  const case_limitations = card.case_limitations ?? cleanLimitations(content.limitations);
  if (title === (card.title ?? null) && case_limitations === (card.case_limitations ?? null)) return card;
  return { ...card, title, case_limitations };
}

/**
 * The short list for print: the case's limitations when a case is active
 * (they are written for the pair), otherwise the attached frames'
 * limitations with exact duplicates removed. The exported JSON always keeps
 * the full case and per-frame lists.
 */
export function printedLimitations(card: EvidenceCard): string[] {
  if (card.case_limitations?.length) return card.case_limitations;
  return [...new Set(card.frames.flatMap((f) => f.limitations ?? []))];
}

export function updateEvidenceText(
  card: EvidenceCard,
  field: "claim" | "observations" | "uncertainty",
  value: string,
  now: Date = new Date(),
): EvidenceCard {
  const max = field === "claim" ? CLAIM_MAX : TEXT_MAX;
  return { ...card, [field]: value.slice(0, max), updated_at_utc: now.toISOString() };
}

const CARD_KEY_ORDER: (keyof EvidenceCard)[] = [
  "schema_version",
  "id",
  "created_at_utc",
  "updated_at_utc",
  "app_version",
  "data_origin",
  "case_id",
  "preset_id",
  "title",
  "query",
  "frames",
  "claim",
  "observations",
  "uncertainty",
  "case_limitations",
  "sources",
];

/** Stable, human-readable JSON for export. Older cards export the new keys as null. */
export function serializeEvidenceCard(card: EvidenceCard): string {
  const c = normalizeEvidenceCard(card);
  const ordered: Record<string, unknown> = {};
  for (const k of CARD_KEY_ORDER) ordered[k] = c[k];
  return `${JSON.stringify(ordered, null, 2)}\n`;
}

export function exportFilename(card: EvidenceCard): string {
  const subject = (card.case_id ?? card.preset_id ?? "query").replace(/[^a-z0-9_-]/gi, "_");
  const date = card.updated_at_utc.slice(0, 10);
  return `perigee-evidence-${subject}-${date}-${card.id.slice(0, 8)}.json`;
}

// ---------------------------------------------------------------------------
// Validation (used for stored data and any future import)

const isStr = (v: unknown): v is string => typeof v === "string";
const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const isNumOrNull = (v: unknown) => v === null || isNum(v);
const isStrOrNull = (v: unknown) => v === null || isStr(v);
const STATUSES = ["clear", "flagged", "not_covered", "unknown"];

export function validateEvidenceCard(
  value: unknown,
): { ok: true; card: EvidenceCard } | { ok: false; errors: string[] } {
  const errors: string[] = [];
  if (!value || typeof value !== "object") return { ok: false, errors: ["not an object"] };
  const c = value as Record<string, unknown>;
  if (c.schema_version !== EVIDENCE_SCHEMA_VERSION) errors.push("schema_version must be 1");
  for (const k of ["id", "created_at_utc", "updated_at_utc", "app_version"]) {
    if (!isStr(c[k]) || !(c[k] as string)) errors.push(`${k} must be a non-empty string`);
  }
  if (c.data_origin !== "api" && c.data_origin !== "fixture") errors.push("data_origin must be api or fixture");
  if (!isStrOrNull(c.case_id)) errors.push("case_id must be a string or null");
  if (!isStrOrNull(c.preset_id)) errors.push("preset_id must be a string or null");
  if (c.query !== null) {
    const q = c.query as Record<string, unknown> | undefined;
    if (!q || !isNum(q.ra_deg) || !isNum(q.dec_deg) || !isNum(q.fov_arcmin)) {
      errors.push("query must be null or {ra_deg, dec_deg, fov_arcmin}");
    }
  }
  for (const k of ["claim", "observations", "uncertainty"]) {
    if (!isStr(c[k])) errors.push(`${k} must be a string`);
  }
  if (isStr(c.claim) && c.claim.length > CLAIM_MAX) errors.push(`claim exceeds ${CLAIM_MAX} characters`);
  if (!Array.isArray(c.sources) || !c.sources.every((s) => s && isStr(s.label) && isStr(s.url))) {
    errors.push("sources must be [{label, url}]");
  }
  if (!Array.isArray(c.frames)) {
    errors.push("frames must be an array");
  } else {
    c.frames.forEach((f: unknown, i: number) => {
      const fr = f as Record<string, unknown>;
      const ok =
        fr &&
        isStr(fr.frame_key) &&
        isStr(fr.frame_id) &&
        isStr(fr.observation_id) &&
        isNumOrNull(fr.detector) &&
        isStr(fr.collection_id) &&
        isStr(fr.observed_at_utc) &&
        isNum(fr.mjd) &&
        isNumOrNull(fr.wavelength_um) &&
        isNumOrNull(fr.bandwidth_um) &&
        isStrOrNull(fr.wavelength_location) &&
        STATUSES.includes(fr.quality_status as string) &&
        Array.isArray(fr.quality_flag_names) &&
        isStr(fr.source_url) &&
        isStrOrNull(fr.ref);
      if (!ok) errors.push(`frames[${i}] is malformed`);
    });
  }
  return errors.length ? { ok: false, errors } : { ok: true, card: normalizeEvidenceCard(c as unknown as EvidenceCard) };
}

/**
 * Brings a stored card (possibly written before title/limitations existed)
 * to the current shape: missing or malformed additive fields become null.
 * Every other field, including all learner text and provenance, is kept as
 * is. Returns the same object when nothing needs to change.
 */
export function normalizeEvidenceCard(card: EvidenceCard): EvidenceCard {
  const title = cleanTitle(card.title);
  const raw = card.case_limitations;
  const caseLims = raw == null ? null : cleanLimitations(raw);
  let framesChanged = false;
  const frames = card.frames.map((f) => {
    const lims = f.limitations == null ? null : cleanLimitations(f.limitations);
    if (f.limitations !== undefined && sameList(lims, f.limitations)) return f;
    framesChanged = true;
    return { ...f, limitations: lims };
  });
  if (card.title === title && sameList(caseLims, raw) && !framesChanged) return card;
  return { ...card, title, case_limitations: caseLims, frames: framesChanged ? frames : card.frames };
}

function sameList(a: string[] | null, b: unknown): boolean {
  if (a === null) return b === null;
  return Array.isArray(b) && a.length === b.length && a.every((v, i) => v === b[i]);
}

// ---------------------------------------------------------------------------
// Local storage. All access is wrapped: storage can be unavailable or full.

export interface EvidenceStore {
  version: 1;
  cards: EvidenceCard[];
  /** Maps an investigation context (preset/case or query) to its draft card. */
  contexts: Record<string, string>;
}

type StorageLike = Pick<Storage, "getItem" | "setItem">;

export function emptyStore(): EvidenceStore {
  return { version: 1, cards: [], contexts: {} };
}

export function loadStore(storage: StorageLike | null): EvidenceStore {
  if (!storage) return emptyStore();
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return emptyStore();
    const parsed = JSON.parse(raw) as Partial<EvidenceStore>;
    const cards = Array.isArray(parsed.cards)
      ? parsed.cards.flatMap((c) => {
          const v = validateEvidenceCard(c);
          return v.ok ? [v.card] : [];
        })
      : [];
    const contexts =
      parsed.contexts && typeof parsed.contexts === "object" ? (parsed.contexts as Record<string, string>) : {};
    return { version: 1, cards, contexts };
  } catch {
    return emptyStore();
  }
}

export function upsertCard(store: EvidenceStore, contextKey: string | null, card: EvidenceCard): EvidenceStore {
  const others = store.cards.filter((c) => c.id !== card.id);
  const cards = [card, ...others]
    .sort((a, b) => (a.updated_at_utc < b.updated_at_utc ? 1 : -1))
    .slice(0, MAX_STORED_CARDS);
  const kept = new Set(cards.map((c) => c.id));
  const contexts = Object.fromEntries(
    Object.entries({ ...store.contexts, ...(contextKey ? { [contextKey]: card.id } : {}) }).filter(([, id]) =>
      kept.has(id),
    ),
  );
  return { version: 1, cards, contexts };
}

export function removeCard(store: EvidenceStore, id: string): EvidenceStore {
  return {
    version: 1,
    cards: store.cards.filter((c) => c.id !== id),
    contexts: Object.fromEntries(Object.entries(store.contexts).filter(([, v]) => v !== id)),
  };
}

/** Returns false when the browser refused the write (private mode, quota). */
export function persistStore(storage: StorageLike | null, store: EvidenceStore): boolean {
  if (!storage) return false;
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(store));
    return true;
  } catch {
    return false;
  }
}

/**
 * In-memory drafts for this page session, keyed like `store.contexts`. When
 * storage refuses a write (quota, private mode, blocked), leaving a target
 * and coming back must not lose notes: the session copy wins over an older
 * or missing stored copy. It never leaves the tab.
 */
export type DraftMemory = Map<string, EvidenceCard>;
export const sessionDrafts: DraftMemory = new Map();

export function resolveDraft(
  contextKey: string,
  store: EvidenceStore,
  memory: DraftMemory = sessionDrafts,
): { card: EvidenceCard; source: "memory" | "storage" } | null {
  const id = store.contexts[contextKey];
  const stored = id ? store.cards.find((c) => c.id === id) : undefined;
  const mem = memory.get(contextKey);
  if (mem && (!stored || mem.updated_at_utc >= stored.updated_at_utc)) {
    // Equal timestamps mean the stored copy is the same save.
    return { card: mem, source: stored && stored.updated_at_utc === mem.updated_at_utc ? "storage" : "memory" };
  }
  return stored ? { card: stored, source: "storage" } : null;
}

/**
 * Saved cards plus session drafts the browser refused to store, newest
 * first. `unsaved` marks a draft that exists only in this tab.
 */
export function listCards(
  store: EvidenceStore,
  memory: DraftMemory = sessionDrafts,
): { card: EvidenceCard; unsaved: boolean }[] {
  const byId = new Map(store.cards.map((c) => [c.id, { card: c, unsaved: false }]));
  for (const m of memory.values()) {
    const s = byId.get(m.id);
    if (s && s.card.updated_at_utc >= m.updated_at_utc) continue;
    const touched = m.frames.length > 0 || Boolean(m.claim || m.observations || m.uncertainty);
    if (s || touched) byId.set(m.id, { card: m, unsaved: true });
  }
  return [...byId.values()].sort((a, b) => (a.card.updated_at_utc < b.card.updated_at_utc ? 1 : -1));
}

/** Drops a deleted card's session copy so it cannot reappear. */
export function forgetDraft(id: string, memory: DraftMemory = sessionDrafts): void {
  for (const [k, c] of memory) if (c.id === id) memory.delete(k);
}

export function browserStorage(): StorageLike | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Case evidence requirements (from the case JSON). Advisory, not blocking.

export function checkCaseRequirements(
  card: EvidenceCard,
  req: { min_selected_frames?: number; must_include_refs_any_of?: string[][] } | undefined,
): string[] {
  if (!req) return [];
  const issues: string[] = [];
  if (req.min_selected_frames && card.frames.length < req.min_selected_frames) {
    issues.push(`Add at least ${req.min_selected_frames} frames to the card.`);
  }
  const refs = new Set(card.frames.map((f) => f.ref).filter(Boolean) as string[]);
  const groups = req.must_include_refs_any_of ?? [];
  if (groups.length && !groups.some((g) => g.every((r) => refs.has(r)))) {
    issues.push(`Include frames ${groups.map((g) => g.join(" and ")).join(", or ")}.`);
  }
  if (!card.claim.trim()) issues.push("Write a short claim.");
  return issues;
}
