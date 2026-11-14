import { useEffect, useState, type ReactNode } from "react";
import { resolveAssetSrc } from "../api/client";
import type { FrameRecord } from "../api/types";
import { QUALITY_CHIP, markerXY, releaseLabel } from "../lib/compare";
import { formatDateShort, formatMicrons } from "../lib/format";

/**
 * One registered sky plate (design: `.plate`). Date and wavelength are
 * separately labeled; quality text comes from the FrameRecord; the marker is
 * labeled a catalog prediction. When `frame` is null, `placeholder` explains
 * why (processing, failed, not covered) in the same image well.
 */
export function Plate(props: {
  letter: string | null;
  heading: string;
  frame: FrameRecord | null;
  showMarker: boolean;
  guideY?: number | null;
  showFlags?: boolean;
  placeholder?: ReactNode;
  className?: string;
  headingId?: string;
  /** Date/wavelength for a frame still loading (from the search descriptor). */
  pendingDate?: string | null;
}) {
  const { frame } = props;
  const img = frame?.image ?? null;
  const [failed, setFailed] = useState<string | null>(null);
  useEffect(() => setFailed(null), [img?.src]);
  const xy = frame ? markerXY(frame.marker) : null;
  const reg = frame?.registration;
  const northUp = typeof reg?.orientation === "string" && reg.orientation.startsWith("north_up");
  const fov = typeof reg?.fov_arcmin === "number" ? reg.fov_arcmin : null;

  return (
    <article className={`plate ${props.className ?? ""}`} aria-labelledby={props.headingId}>
      <div className="plate-heading">
        <div>
          {props.letter && <span className="frame-letter">{props.letter}</span>}
          <h3 id={props.headingId}>{props.heading}</h3>
        </div>
        {frame && (
          <span className="quality" data-status={frame.quality.status}>
            {frame.quality.status === "clear" && <span aria-hidden="true">✓ </span>}
            {QUALITY_CHIP[frame.quality.status]}
          </span>
        )}
      </div>
      <p className="frame-meta">
        <time dateTime={frame?.observed_at_utc ?? props.pendingDate ?? undefined}>
          {formatDateShort(frame?.observed_at_utc ?? props.pendingDate)}
        </time>
        <span>
          <span className="visually-hidden">Wavelength </span>
          {frame
            ? frame.wavelength_um == null
              ? frame.quality.status === "not_covered"
                ? "Wavelength n/a (off image)"
                : "Wavelength not available"
              : formatMicrons(frame.wavelength_um)
            : "Wavelength pending"}
        </span>
      </p>
      <div className="sky">
        {frame && img && !failed ? (
          <>
            <img
              src={resolveAssetSrc(img.src)}
              width={img.width}
              height={img.height}
              alt={`${frame._fixture ? "Development fixture placeholder, no sky image," : "SPHEREx image of"} frame ${frame.frame_key}, observed ${formatDateShort(frame.observed_at_utc)}${frame.wavelength_um != null ? ` at ${frame.wavelength_um.toFixed(4)} micrometers` : ""}. Hatched areas are outside the image.`}
              onError={() => setFailed(img.src)}
              draggable={false}
            />
            {props.showFlags && frame.flag_image && (
              <img className="flag-overlay" src={resolveAssetSrc(frame.flag_image.src)} alt="" aria-hidden="true" />
            )}
            {props.guideY != null && (
              <span className="guide-line" aria-hidden="true" style={{ top: `${(props.guideY / img.height) * 100}%` }} />
            )}
            {xy && props.showMarker && (
              <span
                className="prediction"
                aria-hidden="true"
                style={{ left: `${(xy.x / img.width) * 100}%`, top: `${(xy.y / img.height) * 100}%` }}
              />
            )}
            {northUp && (
              <span className="compass" aria-hidden="true">
                N ↑<br />E ←
              </span>
            )}
            {fov != null && <span className="sky-scale">{fov} arcmin field</span>}
          </>
        ) : (
          <div className="sky-empty">{failed ? <p>This image could not be loaded.</p> : props.placeholder}</div>
        )}
      </div>
      <div className="plate-foot">
        {frame && xy ? (
          <>
            <span className="prediction-key" aria-hidden="true">
              ⊕
            </span>{" "}
            Catalog prediction, not a detection
          </>
        ) : frame ? (
          <span>No catalog marker for this frame</span>
        ) : null}
        {frame && (
          <span className="release">
            {releaseLabel(frame.collection_id)} · Detector {frame.detector ?? "n/a"}
          </span>
        )}
      </div>
      {frame?._fixture && <p className="plate-note">Development fixture — not NASA data.</p>}
    </article>
  );
}
