import type { Ref } from "react";
import type { CaseContent } from "../api/types";
import type { EvidenceCard } from "../evidence/card";
import {
  buildReferenceEvidence, isReviewedCasePair, normalizeReferenceEvidence,
  referenceEvidenceMatchesCard, wiseControlEvidence,
} from "../evidence/referenceEvidence";
import "../styles/reference-review.css";

interface CaseFinding {
  title: string;
  evidence: string;
  limit: string;
}

// These summaries belong to the reviewed case revisions, not arbitrary archive
// results. A changed case or selected observation falls back to its own guide.
const FINDINGS: Record<string, CaseFinding> = {
  moving_neighbor: {
    title: "The glow shifts against the surrounding stars",
    evidence: "Images A and C are about a year apart at similar infrared wavelengths. The bright glow shifts north while the nearby stars remain nearly fixed, consistent with Barnard’s Star’s predicted motion.",
    limit: "The saturated center prevents a precise position or speed measurement. The ring shows a catalog prediction.",
  },
  fair_comparison: {
    title: "A time comparison and a wavelength comparison",
    evidence: "Epsilon Indi B looks similar in A and B, taken five months apart near 2.323 µm. A and C capture the same moment at different wavelengths and have different appearances. They compare views of the same exposure, not change over time.",
    limit: "A and C also use different detectors and contrast scales. Their gray levels cannot establish a brightness change over time.",
  },
  wise_0855_quality_trap: {
    title: "The jumping dot is unreliable evidence of motion",
    evidence: "The feature stays at the same detector position in A and B, even though it shifts on the sky display. Both observations flag that pixel as unreliable.",
    limit: "These checks do not establish the pixel’s physical cause. The ring is a catalog prediction, and WISE 0855 is not identified in these images.",
  },
};

/** Return a specific takeaway only for its reviewed observations and revision. */
export function referenceFinding(caseContent: CaseContent, card: EvidenceCard): CaseFinding | null {
  const finding = FINDINGS[caseContent.case_id];
  return finding && isReviewedCasePair(card, caseContent) ? finding : null;
}

export function hasWiseControlEvidence(caseContent: CaseContent, card: EvidenceCard): boolean {
  return Boolean(wiseControlEvidence(card, caseContent));
}

export function ReferenceReview({ id, card, caseContent, reviewRef }: {
  id: string;
  card: EvidenceCard;
  caseContent: CaseContent;
  reviewRef?: Ref<HTMLElement>;
}) {
  if (!card.reference_shown || card.case_id !== caseContent.case_id) return null;
  const saved = normalizeReferenceEvidence(card.reference_evidence);
  const reference = saved
    ? referenceEvidenceMatchesCard(saved, card) ? saved : null
    : buildReferenceEvidence(card, caseContent);
  const guide = reference?.guide ?? caseContent.conclusion_guide;
  if (!guide) return null;
  const finding = !saved || saved.content_version === caseContent.content_version
    ? referenceFinding(caseContent, card) : null;
  const controls = reference?.wise_control;
  return (
    <section className="reference-review reference-review-compact" ref={reviewRef} tabIndex={-1} aria-labelledby={`${id}-reference-title`}>
      <h3 id={`${id}-reference-title`}>Compare your reasoning</h3>
      <p className="reference-context">Reference answer (from the case)</p>
      <div className="reference-takeaway">
        {finding ? <>
          <h4>{finding.title}</h4>
          <p>{finding.evidence}</p>
          <p className="reference-boundary">{finding.limit}</p>
        </> : <p>{guide.supported?.[0] ?? guide.example_claim ?? "Use the case reference below to review your explanation."}</p>}
      </div>
      <p className="reference-reflection">Compare this with your explanation above. You can revise your notes; Perigee does not grade your answer.</p>

      {controls && <details className="reference-details reference-controls">
        <summary>How we checked the jumping dot<span aria-hidden="true" className="reference-disclosure-icon">+</span></summary>
        <div className="reference-detail-body">
          <p>The raw files place the feature at detector pixel <strong>({controls.detector_pixel.join(", ")})</strong> in both images. Each image’s coordinate solution maps that same pixel to a different sky position.</p>
          <dl className="reference-measurements">
            <div><dt>Same pixel, mapped sky separation</dt><dd>{controls.mapped_sky_shift_arcsec} arcsec</dd></div>
            <div><dt>Prediction from field-star detector shifts</dt><dd>{controls.predicted_sky_shift_arcsec} arcsec</dd></div>
          </dl>
          <p>The prediction uses {controls.field_star_count} usable field stars and the first image’s coordinate solution. Those stars agree on the sky within {controls.max_field_star_sky_shift_arcsec} arcsec. This is a check of the detector mapping, not a precision measurement of a celestial source’s motion.</p>
          <a href={controls.source_review_url} target="_blank" rel="noreferrer">Read the detector and field-star checks</a>
        </div>
      </details>}

      <details className="reference-details">
        <summary>Full reference and scientific limits<span aria-hidden="true" className="reference-disclosure-icon">+</span></summary>
        <div className="reference-detail-body">
          {guide.supported?.length ? <div>
            <h4>Supported by these images</h4>
            <ul className="plain-list">{guide.supported.map((text, i) => <li key={i}>{text}</li>)}</ul>
          </div> : null}
          {guide.not_supported?.length ? <div>
            <h4>What these images cannot establish</h4>
            <ul className="plain-list">{guide.not_supported.map((text, i) => <li key={i}>{text}</li>)}</ul>
          </div> : null}
          {guide.example_claim && <div><h4>Example claim</h4><p>{guide.example_claim}</p></div>}
        </div>
      </details>
      <a className="reference-next" href={`/${card.data_origin === "fixture" ? "?fixtures=1" : ""}#investigations`}>Try another investigation</a>
    </section>
  );
}
