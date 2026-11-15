import type { CaseContent } from "../api/types";
import { checkCaseRequirements, type EvidenceCard } from "./card";

/** Self-reported progress, never a grade of the learner's answer. */
export function reviewStep(card: EvidenceCard, stepId: string, reviewed: boolean): EvidenceCard {
  const ids = new Set(card.reviewed_step_ids ?? []);
  if (reviewed) ids.add(stepId); else ids.delete(stepId);
  return { ...card, reviewed_step_ids: [...ids], reference_shown: false, updated_at_utc: new Date().toISOString() };
}

export function completionIssues(card: EvidenceCard, content: CaseContent, saved: boolean): string[] {
  const issues = checkCaseRequirements(card, { min_selected_frames: 2, ...content.evidence_requirements });
  if (card.case_id !== content.case_id) issues.push("Open the evidence card for this investigation.");
  if (!card.observations.trim()) issues.push("Record what you noticed.");
  if (!card.uncertainty.trim()) issues.push("Record what remains uncertain.");
  const reviewed = new Set(card.reviewed_step_ids ?? []);
  const remaining = content.steps.filter((s) => !reviewed.has(s.id)).length;
  if (remaining) issues.push(`Review the remaining ${remaining} step${remaining === 1 ? "" : "s"} below the images.`);
  if (!saved) issues.push("Save this card on your device.");
  return issues;
}
