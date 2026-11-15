import type { Ref } from "react";
import type { CaseContent } from "../api/types";
import type { EvidenceCard } from "../evidence/card";
import "../styles/reference-review.css";

interface CaseFinding {
  version: string;
  frames: Record<string, string>;
  title: string;
  evidence: string;
  limit: string;
}

// These summaries belong to the reviewed case revisions, not arbitrary archive
// results. A changed case or selected observation falls back to its own guide.
const FINDINGS: Record<string, CaseFinding> = {
  moving_neighbor: {
    version: "moving_neighbor-2026-11-14b",
    frames: { A: "2025W35_1A_0008_1_D3", C: "2026W34_1A_0431_1_D3" },
    title: "The glow shifts against the surrounding stars",
    evidence: "Images A and C are about a year apart at similar infrared wavelengths. The bright glow shifts north while the nearby stars remain nearly fixed, consistent with Barnard’s Star’s predicted motion.",
    limit: "The saturated center prevents a precise position or speed measurement. The ring shows a catalog prediction.",
  },
  fair_comparison: {
    version: "fair_comparison-2026-11-15a",
    frames: { A: "2026W18_1A_0516_1_D3", B: "2026W39_2A_0597_4_D3" },
    title: "A time comparison and a wavelength comparison",
    evidence: "Epsilon Indi B looks similar in A and B, taken five months apart near 2.323 µm. A and C capture the same moment at different wavelengths and have different appearances. They compare views of the same exposure, not change over time.",
    limit: "A and C also use different detectors and contrast scales. Their gray levels cannot establish a brightness change over time.",
  },
  wise_0855_quality_trap: {
    version: "wise_0855_quality_trap-2026-11-15-staged1",
    frames: { A: "2025W45_2A_0278_1_D2", B: "2025W46_1A_0108_1_D2" },
    title: "The jumping dot is unreliable evidence of motion",
    evidence: "The feature stays at the same detector position in A and B, even though it shifts on the sky display. Both observations flag that pixel as unreliable.",
    limit: "These checks do not establish the pixel’s physical cause. The ring is a catalog prediction, and WISE 0855 is not identified in these images.",
  },
};

/** Return a specific takeaway only for its reviewed observations and revision. */
export function referenceFinding(caseContent: CaseContent, card: EvidenceCard): CaseFinding | null {
  const finding = FINDINGS[caseContent.case_id];
  if (!finding || card.data_origin !== "api" || card.case_id !== caseContent.case_id ||
    caseContent.content_version !== finding.version) return null;
  const matches = Object.entries(finding.frames).every(([ref, key]) =>
    caseContent.frames.some((f) => f.ref === ref && f.frame_key === key) &&
    card.frames.some((f) => f.ref === ref && f.frame_key === key),
  );
  return matches ? finding : null;
}

// Source: science/reviews/overnight-controls/results/results.json, control B,
// F1_PQ_detector_pixel. Restrict the retained measurements to these exact FITS bytes.
const WISE_CONTROL_HASHES: Record<string, string> = {
  "2025W45_2A_0278_1_D2": "fbcca340f53c5652bde70d84c23263219eb22ac0364f02a99a56acd5e26fedd0",
  "2025W46_1A_0108_1_D2": "044658e75337cbd35f04b9ba77fa79e9cef96ea7a6489e33f88896506e5cd90f",
};

export function hasWiseControlEvidence(caseContent: CaseContent, card: EvidenceCard): boolean {
  return caseContent.case_id === "wise_0855_quality_trap" && Boolean(referenceFinding(caseContent, card)) &&
    Object.entries(WISE_CONTROL_HASHES).every(([key, hash]) =>
      card.frames.some((f) => f.frame_key === key && f.processing?.file_sha256 === hash),
    );
}

export function ReferenceReview({ id, card, caseContent, reviewRef }: {
  id: string;
  card: EvidenceCard;
  caseContent: CaseContent;
  reviewRef?: Ref<HTMLElement>;
}) {
  const guide = caseContent.conclusion_guide;
  if (!guide) return null;
  const finding = referenceFinding(caseContent, card);
  const controls = hasWiseControlEvidence(caseContent, card);
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
          <p>The raw files place the feature at detector pixel <strong>(1709, 1364)</strong> in both images. The telescope’s changed pointing maps that pixel to different sky positions.</p>
          <dl className="reference-measurements">
            <div><dt>Measured sky-position shift</dt><dd>5.36 arcsec</dd></div>
            <div><dt>Expected for a detector-fixed feature</dt><dd>5.38 arcsec</dd></div>
          </dl>
          <p>The prediction uses the detector shifts of three usable field stars. Those stars agree on the sky within 0.76 arcsec. This check supports rejecting the dot as evidence of a moving celestial object.</p>
          <a href="https://github.com/sathvikloke/perigee/blob/main/science/reviews/overnight-controls/README.md" target="_blank" rel="noreferrer">Read the detector and field-star checks</a>
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
