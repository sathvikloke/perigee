// Human titles for saved evidence cards ("My evidence" on the home view):
// "<target> · <case title>", "<target>", or "Coordinate search · RA …, Dec …".
// Resolved from the target list and case content already served by the API,
// then the card's own stored `title`, then the raw ID.

import type { EvidenceCard, EvidenceQuery } from "./card";

export interface TitleSources {
  /** Targets from /api/v1/presets. */
  presets?: readonly { id: string; display_name: string; case_ids: readonly string[] }[] | null;
  /** Case content from /api/v1/cases/<id>, keyed by case ID. */
  cases?: Readonly<Record<string, { title?: string | null; target_id?: string | null } | undefined>> | null;
}

const SEP = " · ";

/** "RA 83.82°, Dec −5.39°": at most three decimals, true minus sign. */
export function formatPosition(q: Pick<EvidenceQuery, "ra_deg" | "dec_deg">): string {
  const deg = (v: number) => {
    const s = String(Number(v.toFixed(3)));
    return `${s.startsWith("-") ? `−${s.slice(1)}` : s}°`;
  };
  // No-break spaces keep each label with its value when the title wraps.
  return `RA\u00a0${deg(q.ra_deg)}, Dec\u00a0${deg(q.dec_deg)}`;
}

function nonEmpty(s: string | null | undefined): string | null {
  return typeof s === "string" && s.trim() ? s.trim() : null;
}

export function evidenceTitle(card: EvidenceCard, src: TitleSources = {}): string {
  // A card's stored title (QA-F1) is the case title, else the target name;
  // older cards have none until reopened. It stands in for the case title
  // and is combined with the target name so every row reads the same way.
  const own = nonEmpty(card.title);
  const presets = src.presets ?? [];
  const caseInfo = card.case_id ? src.cases?.[card.case_id] : undefined;
  const caseTitle = nonEmpty(caseInfo?.title) ?? own;
  const targetName = (id: string | null | undefined) =>
    id ? nonEmpty(presets.find((p) => p.id === id)?.display_name) : null;
  const caseTarget =
    targetName(caseInfo?.target_id) ??
    (card.case_id ? nonEmpty(presets.find((p) => p.case_ids.includes(card.case_id as string))?.display_name) : null);

  if (card.preset_id) {
    const name = targetName(card.preset_id) ?? caseTarget;
    // A free-exploration card's stored title is the target name itself; a
    // title that already names the target is shown as it is.
    if (name && caseTitle?.includes(name)) return caseTitle;
    const parts = [name, caseTitle].filter(Boolean) as string[];
    return parts.length ? parts.join(SEP) : (card.case_id ?? card.preset_id);
  }

  if (card.query) {
    const parts = ["Coordinate search", formatPosition(card.query)];
    const context = caseTarget ?? caseTitle;
    if (context) parts.push(context);
    return parts.join(SEP);
  }

  return caseTarget && caseTitle ? `${caseTarget}${SEP}${caseTitle}` : (caseTitle ?? card.case_id ?? "Evidence card");
}
