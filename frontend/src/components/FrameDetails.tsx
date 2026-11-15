import type { ReactNode } from "react";
import type { FrameRecord } from "../api/types";
import { QUALITY_CHIP, releaseLabel } from "../lib/compare";
import { qualityExplanation, formatFlagNames, formatPixelCount, formatUtc, formatWavelength, qualityNotes } from "../lib/format";
import { ProcessingNote } from "./CaseBench";

function Disclosure(props: { icon: string; title: string; children: ReactNode }) {
  return (
    <details className="panel">
      <summary>
        <span>
          <span className="section-icon" aria-hidden="true">
            {props.icon}
          </span>
          {props.title}
        </span>
        <span className="expand" aria-hidden="true">
          +
        </span>
      </summary>
      <div className="details-body">{props.children}</div>
    </details>
  );
}

/** Metadata beside the sequence plate: renders documented FrameRecord fields only. */
export function FrameDetails({ frame }: { frame: FrameRecord }) {
  const q = frame.quality;
  const prov = frame.provenance;
  const ack = prov?.acknowledgments ? (Array.isArray(prov.acknowledgments) ? prov.acknowledgments : [prov.acknowledgments]) : [];
  return (
    <>
      <dl className="facts">
        <div>
          <dt>Observed (UTC)</dt>
          <dd>
            {formatUtc(frame.observed_at_utc)}, MJD {frame.mjd.toFixed(4)}
          </dd>
        </div>
        <div>
          <dt>Wavelength</dt>
          <dd>{formatWavelength(frame)}</dd>
        </div>
        {frame.wavelength_location && (
          <div>
            <dt>Measured at</dt>
            <dd>{frame.wavelength_location}</dd>
          </div>
        )}
        <div>
          <dt>Release and detector</dt>
          <dd>
            {releaseLabel(frame.collection_id)}, Detector {frame.detector ?? "n/a"}
          </dd>
        </div>
        <div>
          <dt>Frame</dt>
          <dd className="mono">{frame.frame_key}</dd>
        </div>
      </dl>
      <p>
        <span className="quality" data-status={q.status}>
          {QUALITY_CHIP[q.status]}
        </span>{" "}
        {qualityExplanation(frame)}
      </p>
      {frame.display_scale?.mode === "per_frame" && (
        <p className="notice">Brightness is not directly comparable: this frame has its own contrast stretch.</p>
      )}
      <Disclosure icon="✓" title="Quality details">
        <dl className="facts">
          <div>
            <dt>Position covered</dt>
            <dd>{q.covered == null ? "not available" : q.covered ? "yes" : "no"}</dd>
          </div>
          <div>
            <dt>Usable pixels near target</dt>
            <dd>{formatPixelCount(q.valid_aperture_pixels)}</dd>
          </div>
          <div>
            <dt>Problem pixels near target</dt>
            <dd>{formatPixelCount(q.adverse_aperture_pixels)}</dd>
          </div>
          <div>
            <dt>Problem flags</dt>
            <dd>{formatFlagNames(q)}</dd>
          </div>
        </dl>
        {qualityNotes(q.notes).length > 0 && (
          <ul className="plain-list">
            {qualityNotes(q.notes).map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}
      </Disclosure>
      <Disclosure icon="≡" title="Source & processing">
        <dl className="facts">
          <div>
            <dt>Original file</dt>
            <dd>
              {frame.source_url ? (
                <a href={frame.source_url} target="_blank" rel="noreferrer" className="break">
                  {releaseLabel(frame.collection_id)} / D{frame.detector ?? "?"} FITS ↗
                </a>
              ) : (
                "not available"
              )}
            </dd>
          </div>
          <div>
            <dt>Observation ID</dt>
            <dd className="mono">{frame.observation_id}</dd>
          </div>
          <div>
            <dt>Retrieved</dt>
            <dd>{prov?.retrieved_at_utc ? formatUtc(prov.retrieved_at_utc) : "not available"}</dd>
          </div>
          <div>
            <dt>Source SHA-256</dt>
            <dd className="mono break">{prov?.file_sha256 ?? "not available"}</dd>
          </div>
        </dl>
        <ProcessingNote frame={frame} />
        {frame.limitations.length > 0 && (
          <ul className="plain-list">
            {frame.limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        )}
        {ack.length > 0 && <p>{ack.join(" ")}</p>}
      </Disclosure>
    </>
  );
}
