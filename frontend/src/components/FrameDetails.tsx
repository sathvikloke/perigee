import type { FrameRecord } from "../api/types";
import {
  QUALITY_EXPLANATION,
  QUALITY_LABEL,
  formatPixelCount,
  formatUtc,
  formatWavelength,
  qualityNotes,
} from "../lib/format";

/** Date, wavelength, quality and provenance for one frame. Renders documented fields only. */
export function FrameDetails({ frame, refLabel }: { frame: FrameRecord; refLabel?: string | null }) {
  const q = frame.quality;
  const notes = qualityNotes(q.notes);
  const prov = frame.provenance;
  const ack = prov?.acknowledgments
    ? Array.isArray(prov.acknowledgments)
      ? prov.acknowledgments
      : [prov.acknowledgments]
    : [];
  return (
    <section className="frame-details" aria-label="Frame details">
      <dl className="facts">
        <div>
          <dt>Observed</dt>
          <dd>
            <time dateTime={frame.observed_at_utc}>{formatUtc(frame.observed_at_utc)}</time>
            <span className="muted"> · MJD {frame.mjd.toFixed(4)}</span>
          </dd>
        </div>
        <div>
          <dt>Wavelength</dt>
          <dd>
            {formatWavelength(frame)}
            {frame.wavelength_location && <span className="muted block">Measured at: {frame.wavelength_location}</span>}
          </dd>
        </div>
        <div>
          <dt>Quality</dt>
          <dd>
            <span className="quality" data-status={q.status}>
              {QUALITY_LABEL[q.status]}
            </span>
            <span className="block">{QUALITY_EXPLANATION[q.status]}</span>
          </dd>
        </div>
        <div>
          <dt>Image</dt>
          <dd>
            {refLabel ? `Frame ${refLabel} · ` : ""}
            <span className="mono">{frame.frame_key}</span>
            <span className="muted block">
              Detector {frame.detector ?? "not available"} · {frame.collection_id}
            </span>
          </dd>
        </div>
      </dl>

      {frame.display_scale?.mode === "per_frame" && (
        <p className="notice" role="note">
          Brightness is not directly comparable: this frame has its own contrast stretch.
        </p>
      )}

      <details className="disclosure">
        <summary>Quality details</summary>
        <dl className="facts compact">
          <div>
            <dt>Status</dt>
            <dd className="mono">{q.status}</dd>
          </div>
          <div>
            <dt>Position covered</dt>
            <dd>{q.covered == null ? "not available" : q.covered ? "yes" : "no"}</dd>
          </div>
          <div>
            <dt>Usable pixels near position</dt>
            <dd>{formatPixelCount(q.valid_aperture_pixels)}</dd>
          </div>
          <div>
            <dt>Problem pixels near position</dt>
            <dd>{formatPixelCount(q.adverse_aperture_pixels)}</dd>
          </div>
          <div>
            <dt>Flags</dt>
            <dd>{q.flag_names.length ? <span className="mono">{q.flag_names.join(", ")}</span> : "none reported"}</dd>
          </div>
        </dl>
        {notes.length > 0 && (
          <ul className="plain-list">
            {notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}
      </details>

      <details className="disclosure">
        <summary>Source and processing</summary>
        <dl className="facts compact">
          <div>
            <dt>Original file</dt>
            <dd>
              {frame.source_url ? (
                <a href={frame.source_url} target="_blank" rel="noreferrer" className="break">
                  {frame.source_url}
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
            <dt>File hash</dt>
            <dd className="mono break">{prov?.file_sha256 ?? "not available"}</dd>
          </div>
          <div>
            <dt>Processing</dt>
            <dd>{prov?.processing_version ?? "not available"}</dd>
          </div>
          <div>
            <dt>Display scale</dt>
            <dd>
              {frame.display_scale
                ? `${frame.display_scale.mode === "shared" ? "Shared across frames" : "Per frame"}${
                    frame.display_scale.method ? ` · ${frame.display_scale.method}` : ""
                  }`
                : "not available"}
            </dd>
          </div>
          {frame.registration?.method && (
            <div>
              <dt>Sky grid</dt>
              <dd>{String(frame.registration.method)}</dd>
            </div>
          )}
        </dl>
        {ack.length > 0 && (
          <ul className="plain-list muted">
            {ack.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        )}
      </details>

      {frame.limitations.length > 0 && (
        <details className="disclosure">
          <summary>Limitations of this frame</summary>
          <ul className="plain-list">
            {frame.limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
