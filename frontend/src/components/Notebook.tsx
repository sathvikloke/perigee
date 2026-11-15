import { useId, useRef, useState, type FormEvent } from "react";
import type { CaseContent } from "../api/types";
import {
  CLAIM_MAX,
  TEXT_MAX,
  printedLimitations,
  checkCaseRequirements,
  exportFilename,
  serializeEvidenceCard,
  updateEvidenceText,
  withCaseContext,
  type EvidenceCard,
} from "../evidence/card";
import { releaseLabel } from "../lib/compare";
import { formatDateShort, formatMicrons, formatUtc, QUALITY_LABEL } from "../lib/format";

export type SaveState =
  | { kind: "idle" }
  | { kind: "restored" }
  | { kind: "saved"; at: string }
  | { kind: "failed" };

export function downloadEvidence(card: EvidenceCard): void {
  const blob = new Blob([serializeEvidenceCard(card)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = exportFilename(card);
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

type Field = "claim" | "observations" | "uncertainty";

const FIELDS: { key: Field; label: string; hint: string; placeholder: string; max: number }[] = [
  {
    key: "claim",
    label: "What’s your claim?",
    hint: "",
    placeholder: "I think these observations…",
    max: CLAIM_MAX,
  },
  {
    key: "observations",
    label: "What did you notice?",
    hint: "Point to dates, wavelengths or visible details.",
    placeholder: "The evidence that supports this is…",
    max: TEXT_MAX,
  },
  {
    key: "uncertainty",
    label: "What remains uncertain?",
    hint: "What would you need before saying more?",
    placeholder: "I can’t conclude… because…",
    max: TEXT_MAX,
  },
];

/**
 * The lavender evidence notebook (design: `.notebook`). The primary action
 * exports an evidence card; it never announces a discovery.
 */
export function Notebook(props: {
  card: EvidenceCard;
  /** Applies the learner's edit; the caller may also attach the current pair. */
  onChange: (card: EvidenceCard) => void;
  onRemoveFrame: (frameKey: string) => void;
  /** Card to export/print, e.g. with the current comparison pair attached. */
  exportCard?: EvidenceCard;
  saveState: SaveState;
  caseContent?: CaseContent | null;
  attachedLabel?: string | null;
  onBeforePrint?: () => void;
}) {
  const { card, caseContent } = props;
  const id = useId();
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const refs = useRef<Partial<Record<Field, HTMLTextAreaElement | null>>>({});
  // Export and print carry the case's own limitations, verbatim, with the frames'.
  const out = withCaseContext(props.exportCard ?? card, caseContent);
  const limitations = printedLimitations(out);
  const issues = checkCaseRequirements(out, caseContent?.evidence_requirements).filter(
    (i) => i !== "Write a short claim.",
  );
  const pairRefs = new Set(out.frames.filter((f) => f.ref).map((f) => f.ref));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    for (const f of FIELDS) {
      const el = refs.current[f.key];
      if (el && !el.value.trim()) {
        el.setCustomValidity("Add a note before exporting your evidence.");
        el.reportValidity();
        return;
      }
    }
    if (out.frames.length === 0) {
      setExportStatus("Attach at least one observation before exporting.");
      return;
    }
    downloadEvidence(out);
    setExportStatus("Evidence file downloaded");
  };

  const status =
    exportStatus ??
    (props.saveState.kind === "saved"
      ? "Saved on this device"
      : props.saveState.kind === "restored"
        ? "Restored from this device"
        : props.saveState.kind === "failed"
          ? "Couldn’t save on this device · export to keep these notes"
          : "Notes stay on this device");

  return (
    <aside className="notebook" id="notebook" tabIndex={-1} aria-labelledby={`${id}-title`}>
      <div className="notebook-heading">
        <span className="notebook-icon" aria-hidden="true">
          ▤
        </span>
        <div>
          <p className="eyebrow">Make your reasoning visible</p>
          <h2 id={`${id}-title`}>Evidence notebook</h2>
        </div>
      </div>
      <div className="notebook-body">
        <a className="notebook-jump return-to-images" href="#observations">Back to observations</a>
        <p className="notebook-intro">
          A useful answer includes what you saw <em>and</em> what you still can’t tell.
        </p>
        {card.data_origin === "fixture" && (
          <p className="fixture-tag">This card uses development fixture data — not NASA data.</p>
        )}

        <div className="attached">
          <div className="attached-row">
            <span>Attached observations</span>
            {props.attachedLabel ? (
              <strong>{props.attachedLabel}</strong>
            ) : (
              <span>{out.frames.length || "None yet"}</span>
            )}
          </div>
          {out.frames.some((f) => !f.ref || !pairRefs.has(f.ref) || !props.attachedLabel) && out.frames.length > 0 && (
            <ul>
              {out.frames
                .filter((f) => !props.attachedLabel || !f.ref)
                .map((f) => (
                  <li key={f.frame_key}>
                    <span>
                      {f.ref ? `${f.ref} · ` : ""}
                      {formatDateShort(f.observed_at_utc)} · {formatMicrons(f.wavelength_um)}
                    </span>
                    <button type="button" className="link" onClick={() => props.onRemoveFrame(f.frame_key)}>
                      Remove<span className="visually-hidden"> {f.frame_key}</span>
                    </button>
                  </li>
                ))}
            </ul>
          )}
        </div>

        <form onSubmit={submit} noValidate={false}>
          {FIELDS.map((f) => {
            const hint = f.key === "claim" ? caseContent?.claim_prompt ?? "What do these images show?" : f.hint;
            return (
              <div className="field" key={f.key}>
                <label htmlFor={`${id}-${f.key}`}>{f.label}</label>
                <span className="field-hint" id={`${id}-${f.key}-hint`}>
                  {hint}
                </span>
                <textarea
                  id={`${id}-${f.key}`}
                  ref={(el) => {
                    refs.current[f.key] = el;
                  }}
                  rows={3}
                  maxLength={f.max}
                  required
                  placeholder={f.placeholder}
                  aria-describedby={`${id}-${f.key}-hint${f.key === "claim" ? ` ${id}-claim-count` : ""}`}
                  value={card[f.key]}
                  onChange={(e) => {
                    e.target.setCustomValidity("");
                    setExportStatus(null);
                    props.onChange(updateEvidenceText(card, f.key, e.target.value));
                  }}
                />
                <p className="print-note">{card[f.key]}</p>
                {f.key === "claim" && (
                  <p className="count" id={`${id}-claim-count`}>
                    {card.claim.length} / {CLAIM_MAX}
                  </p>
                )}
              </div>
            );
          })}

          <div className="notebook-tip">
            <span aria-hidden="true">✧</span>
            <p>A different-looking image is a question to investigate, not yet a discovery.</p>
          </div>

          {issues.length > 0 && (
            <div className="checklist">
              <p>For this investigation:</p>
              <ul>
                {issues.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            </div>
          )}

          <button className="primary" type="submit">
            Export evidence card
          </button>
          <div className="notebook-actions">
            <button
              type="button"
              onClick={() => {
                props.onBeforePrint?.();
                window.print();
              }}
            >
              Print / save PDF
            </button>
            <span role="status">{status}</span>
          </div>
        </form>

        {caseContent?.conclusion_guide && (
          <details className="panel guide">
            <summary>
              <span>
                <span className="section-icon" aria-hidden="true">
                  ✓
                </span>{" "}
                Check your claim against the case guide
              </span>
              <span className="expand" aria-hidden="true">
                +
              </span>
            </summary>
            <div className="details-body">
              {caseContent.conclusion_guide.supported?.length ? (
                <div>
                  <strong>Supported by these images</strong>
                  <ul className="plain-list">
                    {caseContent.conclusion_guide.supported.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {caseContent.conclusion_guide.not_supported?.length ? (
                <div>
                  <strong>Not supported</strong>
                  <ul className="plain-list">
                    {caseContent.conclusion_guide.not_supported.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {caseContent.conclusion_guide.example_claim && (
                <div>
                  <strong>Example claim</strong>
                  <p>{caseContent.conclusion_guide.example_claim}</p>
                </div>
              )}
            </div>
          </details>
        )}

        <section className="print-provenance" aria-label="Printed observation provenance">
          <h3>Selected observation provenance</h3>
          {out.frames.map((f) => (
            <div key={f.frame_key}>
              <p>
                <strong>
                  {f.ref ? `Observation ${f.ref} · ` : ""}
                  {f.frame_key}
                </strong>
              </p>
              <p>
                Observation ID: {f.observation_id} | Detector: {f.detector ?? "n/a"} | Release:{" "}
                {releaseLabel(f.collection_id)} ({f.collection_id})
              </p>
              <p>
                UTC: {formatUtc(f.observed_at_utc)} | Wavelength: {formatMicrons(f.wavelength_um)} | Flag screen:{" "}
                {QUALITY_LABEL[f.quality_status]}
              </p>
              <p>Source: {f.source_url}</p>
              {f.processing && (
                <p>
                  Processing: {f.processing.processing_version ?? "n/a"} · grid {f.processing.registration_method ?? "n/a"} ·
                  stretch {f.processing.display_scale_method ?? "n/a"} ({f.display_scale_mode ?? "n/a"}) · source
                  SHA-256 {f.processing.file_sha256 ?? "n/a"}
                </p>
              )}
            </div>
          ))}
          {limitations.length > 0 && (
            <div>
              <p>
                <strong>Stated limitations</strong> (from the {out.case_limitations?.length ? "case" : "observation records"})
              </p>
              <ul>
                {limitations.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </div>
          )}
          <p>
            Perigee {out.app_version} · card {out.id} · {out.data_origin === "fixture" ? "DEVELOPMENT FIXTURE, not NASA data" : "SPHEREx data via NASA/IPAC IRSA"}.
            Display images are for visual comparison only; flag screening is not a detection or a brightness measurement.
          </p>
        </section>
      </div>
    </aside>
  );
}
