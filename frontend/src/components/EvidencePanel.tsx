import { useId } from "react";
import type { CaseContent } from "../api/types";
import {
  CLAIM_MAX,
  TEXT_MAX,
  checkCaseRequirements,
  exportFilename,
  serializeEvidenceCard,
  updateEvidenceText,
  type EvidenceCard,
} from "../evidence/card";
import { QUALITY_LABEL, formatDateShort, formatMicrons } from "../lib/format";

export type SaveState = { kind: "idle" } | { kind: "saved"; at: string } | { kind: "failed" };

export function downloadEvidence(card: EvidenceCard): void {
  const blob = new Blob([serializeEvidenceCard(card)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = exportFilename(card);
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function EvidencePanel(props: {
  card: EvidenceCard;
  onChange: (card: EvidenceCard) => void;
  onRemoveFrame: (frameKey: string) => void;
  saveState: SaveState;
  caseContent?: CaseContent | null;
}) {
  const { card, caseContent } = props;
  const id = useId();
  const issues = checkCaseRequirements(card, caseContent?.evidence_requirements);
  const set = (field: "claim" | "observations" | "uncertainty") => (v: string) =>
    props.onChange(updateEvidenceText(card, field, v));

  return (
    <section className="evidence" aria-labelledby={`${id}-h`}>
      <h2 id={`${id}-h`}>Evidence card</h2>
      {card.data_origin === "fixture" && (
        <p className="fixture-tag">This card uses development fixture data — not NASA data.</p>
      )}

      <h3 className="sub">Selected frames ({card.frames.length})</h3>
      {card.frames.length === 0 ? (
        <p className="muted">Use “Add this frame to evidence” in the viewer to choose the frames that support your claim.</p>
      ) : (
        <ul className="evidence-frames">
          {card.frames.map((f) => (
            <li key={f.frame_key}>
              <span>
                {f.ref ? <strong>{f.ref} · </strong> : null}
                {formatDateShort(f.observed_at_utc)} · {formatMicrons(f.wavelength_um)} ·{" "}
                <span className="quality" data-status={f.quality_status}>
                  {QUALITY_LABEL[f.quality_status]}
                </span>
                <span className="mono muted block">{f.frame_key}</span>
              </span>
              <button type="button" className="link" onClick={() => props.onRemoveFrame(f.frame_key)}>
                Remove<span className="visually-hidden"> {f.frame_key}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="field">
        <label htmlFor={`${id}-claim`}>Claim</label>
        {caseContent?.claim_prompt && (
          <p className="hint" id={`${id}-claim-hint`}>
            {caseContent.claim_prompt}
          </p>
        )}
        <textarea
          id={`${id}-claim`}
          rows={3}
          maxLength={CLAIM_MAX}
          value={card.claim}
          aria-describedby={`${caseContent?.claim_prompt ? `${id}-claim-hint ` : ""}${id}-claim-count`}
          onChange={(e) => set("claim")(e.target.value)}
        />
        <p className="count" id={`${id}-claim-count`}>
          {card.claim.length} / {CLAIM_MAX} characters
        </p>
      </div>
      <div className="field">
        <label htmlFor={`${id}-obs`}>What I saw</label>
        <textarea
          id={`${id}-obs`}
          rows={3}
          maxLength={TEXT_MAX}
          value={card.observations}
          onChange={(e) => set("observations")(e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor={`${id}-unc`}>What I can’t tell</label>
        <textarea
          id={`${id}-unc`}
          rows={2}
          maxLength={TEXT_MAX}
          value={card.uncertainty}
          onChange={(e) => set("uncertainty")(e.target.value)}
        />
      </div>

      {issues.length > 0 && (
        <div className="checklist" aria-label="Before you export">
          <p>Before you export:</p>
          <ul>
            {issues.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="actions">
        <button type="button" className="primary" onClick={() => downloadEvidence(card)}>
          Export JSON
        </button>
        <p className="save-state" role="status">
          {props.saveState.kind === "saved" && `Saved in this browser at ${new Date(props.saveState.at).toLocaleTimeString()}.`}
          {props.saveState.kind === "failed" &&
            "This browser would not save the card (storage unavailable or full). Export it to keep your work."}
        </p>
      </div>

      {caseContent?.conclusion_guide && (
        <details className="disclosure">
          <summary>Check your claim against the case guide</summary>
          {caseContent.conclusion_guide.supported?.length ? (
            <>
              <h4>Supported by these images</h4>
              <ul className="plain-list">
                {caseContent.conclusion_guide.supported.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </>
          ) : null}
          {caseContent.conclusion_guide.not_supported?.length ? (
            <>
              <h4>Not supported</h4>
              <ul className="plain-list">
                {caseContent.conclusion_guide.not_supported.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </>
          ) : null}
          {caseContent.conclusion_guide.example_claim && (
            <>
              <h4>Example claim</h4>
              <p>{caseContent.conclusion_guide.example_claim}</p>
            </>
          )}
        </details>
      )}
    </section>
  );
}
