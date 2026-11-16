import type { CaseContent, CaseFrameRef } from "../api/types";
import type { EvidenceCard, EvidenceFrame } from "./card";

const REVIEW_COMMIT = "49e6539d97823abf02889868d70998f02f7bf65b";
const reviewUrl = (path: string) => `https://github.com/sathvikloke/perigee/blob/${REVIEW_COMMIT}/${path}`;
const CONTROLS_URL = reviewUrl("science/reviews/overnight-controls/README.md");

export interface ReferenceSourceFrame {
  ref: string;
  frame_key: string;
  file_sha256: string | null;
}

export interface WiseControlEvidence {
  detector_pixel: [number, number];
  mapped_sky_shift_arcsec: number;
  predicted_sky_shift_arcsec: number;
  field_star_count: number;
  max_field_star_sky_shift_arcsec: number;
  measurement_description: string;
  source_frames: (ReferenceSourceFrame & { file_sha256: string })[];
  source_review_url: string;
}

export interface EvidenceReference {
  schema_version: 1;
  case_id: string;
  content_version: string | null;
  source_frames: ReferenceSourceFrame[];
  guide: { supported: string[]; not_supported: string[]; example_claim: string | null };
  source_review_urls: string[];
  wise_control: WiseControlEvidence | null;
}

const REVIEWED_CASES: Record<string, { version: string; refs: Record<string, string>; review: string }> = {
  moving_neighbor: {
    version: "moving_neighbor-2026-11-14b",
    refs: { A: "2025W35_1A_0008_1_D3", C: "2026W34_1A_0431_1_D3" },
    review: "science/reviews/barnard/README.md",
  },
  fair_comparison: {
    version: "fair_comparison-2026-11-15b",
    refs: { A: "2026W18_1A_0516_1_D3", B: "2026W39_2A_0597_4_D3" },
    review: "science/reviews/epsilon/README.md",
  },
  wise_0855_quality_trap: {
    version: "wise_0855_quality_trap-2026-11-15-staged1",
    refs: { A: "2025W45_2A_0278_1_D2", B: "2025W46_1A_0108_1_D2" },
    review: "science/reviews/overnight-controls/README.md",
  },
};

/** Case references identify observations; retained hashes also identify their input bytes. */
function matchesCaseFrame(expected: CaseFrameRef, frame: EvidenceFrame): boolean {
  const hash = (expected as CaseFrameRef & { sha256_of_retained_cutout?: string }).sha256_of_retained_cutout;
  return frame.ref === expected.ref && frame.frame_key === expected.frame_key &&
    frame.observation_id === expected.observation_id &&
    (expected.detector == null || frame.detector === expected.detector) &&
    (!expected.collection_id || frame.collection_id === expected.collection_id) &&
    (!expected.source_url || frame.source_url === expected.source_url) &&
    (!hash || frame.processing?.file_sha256 === hash);
}

function requiredSourceFrames(card: EvidenceCard, content: CaseContent): ReferenceSourceFrame[] | null {
  if (card.data_origin !== "api" || card.case_id !== content.case_id ||
    card.frames.length < (content.evidence_requirements?.min_selected_frames ?? 1)) return null;
  const groups = content.evidence_requirements?.must_include_refs_any_of?.length
    ? content.evidence_requirements.must_include_refs_any_of
    : [content.frames.map((f) => f.ref)];
  for (const refs of groups) {
    if (!refs.length) continue;
    const matches = refs.map((ref) => {
      const expected = content.frames.find((f) => f.ref === ref);
      return expected && card.frames.find((frame) => matchesCaseFrame(expected, frame));
    });
    if (matches.every((f) => f !== undefined)) return matches.map((f) => ({
      ref: f.ref!, frame_key: f.frame_key, file_sha256: f.processing?.file_sha256 ?? null,
    }));
  }
  return null;
}

/** Reviewed summaries and control values never transfer to a different case revision. */
export function isReviewedCasePair(card: EvidenceCard, content: CaseContent): boolean {
  const reviewed = REVIEWED_CASES[content.case_id];
  return Boolean(reviewed && reviewed.version === content.content_version && requiredSourceFrames(card, content) &&
    Object.entries(reviewed.refs).every(([ref, key]) =>
      content.frames.some((f) => f.ref === ref && f.frame_key === key) &&
      card.frames.some((f) => f.ref === ref && f.frame_key === key)));
}

// Retained result B.F1_PQ_detector_pixel, tied to the original FITS input bytes.
const WISE_SOURCE_FRAMES: WiseControlEvidence["source_frames"] = [
  { ref: "A", frame_key: "2025W45_2A_0278_1_D2", file_sha256: "fbcca340f53c5652bde70d84c23263219eb22ac0364f02a99a56acd5e26fedd0" },
  { ref: "B", frame_key: "2025W46_1A_0108_1_D2", file_sha256: "044658e75337cbd35f04b9ba77fa79e9cef96ea7a6489e33f88896506e5cd90f" },
];

function sourceFramesMatch(card: EvidenceCard, frames: ReferenceSourceFrame[]): boolean {
  return frames.length > 0 && frames.every((source) => card.frames.some((f) =>
    f.ref === source.ref && f.frame_key === source.frame_key &&
    (source.file_sha256 === null || f.processing?.file_sha256 === source.file_sha256)));
}

export function wiseControlEvidence(card: EvidenceCard, content: CaseContent): WiseControlEvidence | null {
  if (!card.reference_shown || content.case_id !== "wise_0855_quality_trap" ||
    !isReviewedCasePair(card, content) || !sourceFramesMatch(card, WISE_SOURCE_FRAMES)) return null;
  return {
    detector_pixel: [1709, 1364],
    mapped_sky_shift_arcsec: 5.36,
    predicted_sky_shift_arcsec: 5.38,
    field_star_count: 3,
    max_field_star_sky_shift_arcsec: 0.76,
    measurement_description: "The same detector pixel maps to sky positions 5.36 arcseconds apart through the two images’ coordinate solutions. This is a mapped-pixel separation, not a precision measurement of a celestial source’s motion. The 5.38-arcsecond prediction uses the field stars’ detector shifts and the first image’s coordinate solution.",
    source_frames: WISE_SOURCE_FRAMES.map((f) => ({ ...f })),
    source_review_url: CONTROLS_URL,
  };
}

/** Called only for a missing snapshot; callers preserve an existing saved reference. */
export function buildReferenceEvidence(card: EvidenceCard, content: CaseContent): EvidenceReference | null {
  if (!card.reference_shown || !content.conclusion_guide) return null;
  const sources = requiredSourceFrames(card, content);
  if (!sources) return null;
  const reviewed = REVIEWED_CASES[content.case_id];
  const urls = isReviewedCasePair(card, content)
    ? [...new Set([reviewUrl(`backend/content/cases/${content.case_id}.json`), reviewUrl(reviewed.review), CONTROLS_URL])]
    : [];
  return {
    schema_version: 1,
    case_id: content.case_id,
    content_version: content.content_version ?? null,
    source_frames: sources,
    guide: {
      supported: [...(content.conclusion_guide.supported ?? [])],
      not_supported: [...(content.conclusion_guide.not_supported ?? [])],
      example_claim: content.conclusion_guide.example_claim ?? null,
    },
    source_review_urls: urls,
    wise_control: wiseControlEvidence(card, content),
  };
}

export function referenceEvidenceMatchesCard(reference: EvidenceReference, card: EvidenceCard): boolean {
  return card.reference_shown === true && card.data_origin === "api" && reference.case_id === card.case_id &&
    sourceFramesMatch(card, reference.source_frames) &&
    (!reference.wise_control || sourceFramesMatch(card, reference.wise_control.source_frames));
}

const isObject = (v: unknown): v is Record<string, unknown> => Boolean(v && typeof v === "object" && !Array.isArray(v));
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every((s) => typeof s === "string");
const nullableString = (v: unknown) => v === null || typeof v === "string";
const finitePositive = (v: unknown) => typeof v === "number" && Number.isFinite(v) && v >= 0;
const isSourceFrame = (v: unknown): v is ReferenceSourceFrame => isObject(v) && typeof v.ref === "string" &&
  typeof v.frame_key === "string" && nullableString(v.file_sha256);

/** Validate saved shape without rewriting its guide, version, measurements or pinned URLs. */
export function normalizeReferenceEvidence(value: unknown): EvidenceReference | null {
  if (!isObject(value) || value.schema_version !== 1 || typeof value.case_id !== "string" ||
    !nullableString(value.content_version) || !Array.isArray(value.source_frames) || !value.source_frames.length ||
    !value.source_frames.every(isSourceFrame) || !isObject(value.guide) ||
    !strings(value.guide.supported) || !strings(value.guide.not_supported) || !nullableString(value.guide.example_claim) ||
    !strings(value.source_review_urls) || !value.source_review_urls.every((url) => /^https:\/\//.test(url))) return null;
  const control = value.wise_control;
  if (control !== null && (!isObject(control) || !Array.isArray(control.detector_pixel) || control.detector_pixel.length !== 2 ||
    !control.detector_pixel.every((v) => finitePositive(v) && Number.isInteger(v)) ||
    !finitePositive(control.mapped_sky_shift_arcsec) || !finitePositive(control.predicted_sky_shift_arcsec) ||
    !finitePositive(control.field_star_count) || !Number.isInteger(control.field_star_count) || control.field_star_count === 0 ||
    !finitePositive(control.max_field_star_sky_shift_arcsec) || typeof control.measurement_description !== "string" ||
    !Array.isArray(control.source_frames) || !control.source_frames.length ||
    !control.source_frames.every((f) => isSourceFrame(f) && typeof f.file_sha256 === "string") ||
    typeof control.source_review_url !== "string" || !/^https:\/\//.test(control.source_review_url))) return null;
  return value as unknown as EvidenceReference;
}
