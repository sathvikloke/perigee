// Evidence card: the contract's "Content and evidence contracts" section.
// schema_version, locally generated id, creation/update times, case ID when
// present, query coordinates, selected frame identities with
// dates/wavelengths/quality summaries, claim, observations, uncertainty,
// sources and application version. Stored in localStorage; exported as JSON.
// Never stores images, raw FITS or secrets.

import type { FrameRecord, QualityStatus, SourceLink } from "../api/types";

export const EVIDENCE_SCHEMA_VERSION = 1 as const;
export const CLAIM_MAX = 280;
export const TEXT_MAX = 2000;
export const MAX_STORED_CARDS = 50;
export const STORAGE_KEY = "perigee.evidence.v1";

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
  query: EvidenceQuery | null;
  frames: EvidenceFrame[];
  claim: string;
  observations: string;
  uncertainty: string;
  sources: SourceLink[];
  app_version: string;
  data_origin: DataOrigin;
}

export function generateId(): string {
  const c = globalThis.crypto as Crypto | undefined;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  return `ev-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createEvidenceCard(init: {
  case_id?: string | null;
  preset_id?: string | null;
  query?: EvidenceQuery | null;
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
    query: init.query ?? null,
    frames: [],
    claim: "",
    observations: "",
    uncertainty: "",
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
  "query",
  "frames",
  "claim",
  "observations",
  "uncertainty",
  "sources",
];

/** Stable, human-readable JSON for export. */
export function serializeEvidenceCard(card: EvidenceCard): string {
  const ordered: Record<string, unknown> = {};
  for (const k of CARD_KEY_ORDER) ordered[k] = card[k];
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
  return errors.length ? { ok: false, errors } : { ok: true, card: c as unknown as EvidenceCard };
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
