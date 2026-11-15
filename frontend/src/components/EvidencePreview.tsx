import type { Ref } from "react";
import type { FrameRecord } from "../api/types";
import { resolveAssetSrc } from "../api/client";
import type { EvidenceCard, EvidenceFrame } from "../evidence/card";
import { formatDateShort, formatMicrons, QUALITY_LABEL } from "../lib/format";
import { useContentCue } from "../lib/contentMotion";
import "../styles/evidence-preview.css";

/** Only show a loaded product that represents the observation being exported. */
export function evidencePreviewFrame(frame: EvidenceFrame, records: readonly FrameRecord[]): FrameRecord | undefined {
  return records.find((record) => record.frame_key === frame.frame_key &&
    record.frame_id === frame.frame_id && record.collection_id === frame.collection_id &&
    record.source_url === frame.source_url &&
    (record.display_scale?.mode ?? null) === frame.display_scale_mode &&
    (!frame.processing?.file_sha256 || record.provenance?.file_sha256 === frame.processing.file_sha256) &&
    (!frame.processing?.processing_version || record.provenance?.processing_version === frame.processing.processing_version) &&
    (!frame.processing?.pipeline_version || record.provenance?.pipeline_version === frame.processing.pipeline_version) &&
    (!frame.processing?.registration_method || record.registration?.method === frame.processing.registration_method) &&
    (!frame.processing?.display_scale_method || record.display_scale?.method === frame.processing.display_scale_method));
}

export function EvidencePreview({ card, frames = [], previewRef, onEdit, onPrint, onDownload, status, id }: {
  card: EvidenceCard;
  frames?: readonly FrameRecord[];
  previewRef?: Ref<HTMLElement>;
  onEdit: () => void;
  onPrint: () => void;
  onDownload: () => void;
  status: string;
  id: string;
}) {
  const headingRef = useContentCue<HTMLHeadingElement>("reference", card.id);
  return <section className="evidence-preview" ref={previewRef} tabIndex={-1} aria-labelledby={`${id}-preview-title`}>
    <header className="evidence-preview-heading">
      <div><p>Your record</p><h3 ref={headingRef} id={`${id}-preview-title`}>Your evidence card</h3></div>
      <button type="button" onClick={onEdit}>Edit notes</button>
    </header>
    <p className="evidence-preview-topic">{card.title || (card.query ? "Sky position investigation" : "Observation investigation")}</p>
    {card.data_origin === "fixture" && <p className="fixture-tag">Development fixture. These are not NASA observations.</p>}
    <div className="evidence-preview-notes">
      <div><h4>What you noticed</h4><p>{card.observations}</p></div>
      <div><h4>Your explanation</h4><p className="evidence-preview-claim">{card.claim}</p></div>
      <div><h4>What remains uncertain</h4><p>{card.uncertainty}</p></div>
    </div>
    <div className="evidence-preview-observations">
      <h4>Observations behind your explanation</h4>
      <ol className="evidence-preview-frames">
        {card.frames.map((frame, index) => {
          const record = evidencePreviewFrame(frame, frames);
          const label = frame.ref ? `Image ${frame.ref}` : `Image ${index + 1}`;
          const sourceAvailable = /^https?:\/\//i.test(frame.source_url);
          return <li key={frame.frame_key}>
            {record?.image ? <img src={resolveAssetSrc(record.image.src)} alt={`${label}, ${formatDateShort(frame.observed_at_utc)}, ${formatMicrons(frame.wavelength_um)}. Display preview.`} width={record.image.width} height={record.image.height} /> : <div className="evidence-preview-no-image">Image preview unavailable</div>}
            <strong>{label}</strong>
            <span>{formatDateShort(frame.observed_at_utc)}</span>
            <span>{formatMicrons(frame.wavelength_um)}</span>
            <span className="evidence-preview-quality">{QUALITY_LABEL[frame.quality_status]}</span>
            {sourceAvailable ? <a href={frame.source_url} target="_blank" rel="noreferrer" aria-label={`Open the archive source for ${label}`}>Archive source ↗</a> : <span>Source link unavailable</span>}
          </li>;
        })}
      </ol>
      <p className="evidence-preview-context">The selected observations and source records travel with your notes. This preview does not assess your conclusion.</p>
    </div>
    <details className="evidence-preview-records">
      <summary>Observation IDs and processing details</summary>
      {card.frames.some((frame) => frame.display_scale_mode === "shared") && <p>A shared-scale product uses the contrast chosen for its original processed comparison. It does not establish a common contrast for every image selected here.</p>}
      {card.frames.map((frame) => <div key={frame.frame_key}>
        <p><strong>{frame.ref ? `Image ${frame.ref}` : formatDateShort(frame.observed_at_utc)}</strong></p>
        <p>Observation ID: <span className="mono">{frame.observation_id}</span></p>
        <p>Display contrast: {frame.display_scale_mode === "shared" ? "shared-scale product" : frame.display_scale_mode === "per_frame" ? "set for this image" : "not recorded"}.</p>
        {frame.processing?.processing_version && <p>Processor: {frame.processing.processing_version}</p>}
        {frame.processing?.file_sha256 && <p>Source SHA-256: <span className="mono">{frame.processing.file_sha256}</span></p>}
      </div>)}
    </details>
    <div className="evidence-preview-actions">
      <button type="button" className="primary" onClick={onPrint}>Print / save PDF</button>
      <button type="button" onClick={onDownload}>Download evidence JSON</button>
      <span role="status">{status}</span>
    </div>
  </section>;
}
