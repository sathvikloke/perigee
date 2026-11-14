// Reopening a saved evidence card from "My evidence".
//
// The notebook finds its draft by a context key (see useEvidenceCard's
// resolveDraft). The keys are built in PresetInvestigation and
// QueryInvestigation as:
//   preset: `${mode}:preset:${presetId}`
//   query:  `${mode}:query:${ra_deg},${dec_deg},${fov_arcmin}`
// where mode is "api" or "fixture" and the numbers are the validated query.
// Reopening must land on a route whose investigation derives exactly the key
// the card is saved under, so its own notes come back and no other card is
// touched. The route never carries notes: only IDs and coordinates.

import { validateQuery } from "../lib/coords";
import type { Route } from "../lib/route";
import type { DataOrigin, DraftMemory, EvidenceCard, EvidenceStore } from "./card";

export function presetContextKey(mode: DataOrigin, presetId: string): string {
  return `${mode}:preset:${presetId}`;
}

export function queryContextKey(mode: DataOrigin, q: { ra_deg: number; dec_deg: number; fov_arcmin: number }): string {
  return `${mode}:query:${q.ra_deg},${q.dec_deg},${q.fov_arcmin}`;
}

/** The context key a card is saved under: the stored map first, then this tab's unsaved drafts. */
export function savedContextKey(cardId: string, store: EvidenceStore, memory?: DraftMemory): string | null {
  for (const [key, id] of Object.entries(store.contexts)) if (id === cardId) return key;
  if (memory) for (const [key, c] of memory) if (c.id === cardId) return key;
  return null;
}

export interface ReopenTarget {
  route: Route;
  /** Whether the card came from the development fixture (the link keeps ?fixtures=1). */
  fixtures: boolean;
  /** The context key the reopened investigation will derive. */
  contextKey: string;
}

const PRESET_KEY = /^(api|fixture):preset:(.+)$/;
const QUERY_KEY = /^(api|fixture):query:([^,]+),([^,]+),([^,]+)$/;

/**
 * Where to reopen a card. Uses the saved context key when there is one (it
 * is what the notebook looks up), else the card's own preset or query
 * fields, which are set from the same values when the card is created.
 * Returns null when the card has nothing to reopen.
 */
export function reopenTarget(card: EvidenceCard, contextKey: string | null): ReopenTarget | null {
  const caseId = card.case_id ?? undefined;
  const preset = contextKey?.match(PRESET_KEY);
  if (preset) return finish({ view: "preset", presetId: preset[2] }, preset[1] === "fixture");
  const query = contextKey?.match(QUERY_KEY);
  if (query) {
    return finish({ view: "query", ra: query[2], dec: query[3], fov: query[4], caseId }, query[1] === "fixture");
  }
  const fixtures = card.data_origin === "fixture";
  if (card.preset_id) return finish({ view: "preset", presetId: card.preset_id }, fixtures);
  if (card.query) {
    const { ra_deg, dec_deg, fov_arcmin } = card.query;
    return finish({ view: "query", ra: String(ra_deg), dec: String(dec_deg), fov: String(fov_arcmin), caseId }, fixtures);
  }
  return null;
}

function finish(route: Route, fixtures: boolean): ReopenTarget | null {
  const key = routeContextKey(route, fixtures);
  return key ? { route, fixtures, contextKey: key } : null;
}

/**
 * The context key an investigation opened at `route` derives, mirroring
 * PresetInvestigation and QueryInvestigation (the query view validates the
 * link's coordinates the same way before keying its notebook).
 */
export function routeContextKey(route: Route, fixtures: boolean): string | null {
  const mode: DataOrigin = fixtures ? "fixture" : "api";
  if (route.view === "preset") return presetContextKey(mode, route.presetId);
  if (route.view === "query" && route.ra && route.dec) {
    const v = validateQuery({ ra: route.ra, dec: route.dec, fov: route.fov ?? "", limit: "" });
    return v.ok ? queryContextKey(mode, v.value) : null;
  }
  return null;
}
