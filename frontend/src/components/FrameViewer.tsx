import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { resolveAssetSrc } from "../api/client";
import type { FrameRecord, Marker } from "../api/types";
import { QUALITY_LABEL, daysBetween, formatDateShort, formatDuration, formatMicrons } from "../lib/format";
import { FrameDetails } from "./FrameDetails";

export type SlotStatus = "pending" | "loading" | "ready" | "error";

export interface FrameSlot {
  key: string;
  ref: string | null;
  status: SlotStatus;
  frame: FrameRecord | null;
  observed_at_utc: string | null;
  mjd: number | null;
  error: { code: string; message: string; retryable: boolean } | null;
}

function markerXY(m: Marker | null): { x: number; y: number } | null {
  if (!m) return null;
  const x = m.x ?? m.x_px ?? (m.pixel as { x?: number } | undefined)?.x;
  const y = m.y ?? m.y_px ?? (m.pixel as { y?: number } | undefined)?.y;
  return typeof x === "number" && typeof y === "number" ? { x, y } : null;
}

const BLINK_MS = 700;

export function FrameViewer(props: {
  slots: FrameSlot[];
  index: number;
  onIndexChange: (i: number) => void;
  selectedKeys: Set<string>;
  onToggleEvidence: (frame: FrameRecord, ref: string | null) => void;
  onRetry?: (index: number) => void;
  /** Case asks for a fixed guide line through frame A's marker. */
  guideLine?: boolean;
  /** Default blink pair, as case refs. */
  defaultPair?: [string, string];
  label: string;
}) {
  const { slots, index, onIndexChange } = props;
  const slot = slots[index] as FrameSlot | undefined;
  const frame = slot?.frame ?? null;

  const [showMarker, setShowMarker] = useState(true);
  const [showGuide, setShowGuide] = useState(true);
  const [showFlags, setShowFlags] = useState(false);
  const [imageFailed, setImageFailed] = useState<string | null>(null);

  // Blink pair, stored as frame keys so it survives slot updates.
  const refIndex = (ref: string) => slots.findIndex((s) => s.ref === ref);
  const [pair, setPair] = useState<[string, string] | null>(null);
  useEffect(() => {
    if (pair || slots.length < 2) return;
    if (props.defaultPair) {
      const a = refIndex(props.defaultPair[0]);
      const b = refIndex(props.defaultPair[1]);
      if (a >= 0 && b >= 0) {
        setPair([slots[a].key, slots[b].key]);
        return;
      }
    }
    setPair([slots[0].key, slots[slots.length - 1].key]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slots, props.defaultPair, pair]);

  const [blinking, setBlinking] = useState(false);
  const blinkRef = useRef(index);
  blinkRef.current = index;
  useEffect(() => {
    if (!blinking || !pair) return;
    const a = slots.findIndex((s) => s.key === pair[0]);
    const b = slots.findIndex((s) => s.key === pair[1]);
    if (a < 0 || b < 0) return;
    const id = window.setInterval(() => {
      onIndexChange(blinkRef.current === a ? b : a);
    }, BLINK_MS);
    return () => window.clearInterval(id);
  }, [blinking, pair, slots, onIndexChange]);

  const step = (delta: number) => {
    setBlinking(false);
    if (!slots.length) return;
    onIndexChange(Math.min(slots.length - 1, Math.max(0, index + delta)));
  };
  const goTo = (i: number) => {
    setBlinking(false);
    onIndexChange(i);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    const t = e.target as HTMLElement;
    if (t.closest("input, textarea, select, summary")) return;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      step(-1);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      step(1);
    } else if (e.key === "Home") {
      e.preventDefault();
      goTo(0);
    } else if (e.key === "End") {
      e.preventDefault();
      goTo(slots.length - 1);
    }
  };

  // Guide line: fixed at frame A's marker row (case display requirement).
  const guideY = useMemo(() => {
    if (!props.guideLine) return null;
    const a = slots.find((s) => s.ref === "A")?.frame;
    return a ? markerXY(a.marker)?.y ?? null : null;
  }, [props.guideLine, slots]);

  useEffect(() => setImageFailed(null), [frame?.image?.src]);

  const pairIdx = pair ? pair.map((k) => slots.findIndex((s) => s.key === k)) : [];
  const pairFrames =
    pairIdx.length === 2 ? pairIdx.map((i) => (i >= 0 ? slots[i].frame : null)) : [null, null];
  const pairComparison =
    pairFrames[0] && pairFrames[1]
      ? {
          dt: formatDuration(daysBetween(pairFrames[0].mjd, pairFrames[1].mjd)),
          dl:
            pairFrames[0].wavelength_um != null && pairFrames[1].wavelength_um != null
              ? Math.abs(pairFrames[0].wavelength_um - pairFrames[1].wavelength_um)
              : null,
          scales: [pairFrames[0].display_scale?.mode, pairFrames[1].display_scale?.mode],
        }
      : null;

  const slotName = (s: FrameSlot, i: number) =>
    `${s.ref ? `${s.ref} · ` : ""}${formatDateShort(s.observed_at_utc)}${s.ref ? "" : ` (#${i + 1})`}`;

  const announcement = slot
    ? `Frame ${index + 1} of ${slots.length}. ${formatDateShort(slot.observed_at_utc)}. ${
        frame ? `${formatMicrons(frame.wavelength_um)}. ${QUALITY_LABEL[frame.quality.status]}.` : statusText(slot)
      }`
    : "";

  if (!slots.length) return null;

  const xy = frame ? markerXY(frame.marker) : null;
  const img = frame?.image ?? null;
  const inEvidence = frame ? props.selectedKeys.has(frame.frame_key) : false;

  return (
    <section className="viewer" aria-label={props.label} onKeyDown={onKeyDown}>
      <div className="viewer-stage">
        <figure className="plate" aria-busy={slot?.status === "loading"}>
          {frame && img && !imageFailed ? (
            <div className="plate-frame" style={{ aspectRatio: `${img.width} / ${img.height}` }}>
              <img
                src={resolveAssetSrc(img.src)}
                width={img.width}
                height={img.height}
                alt={`${frame._fixture ? "Development fixture placeholder (no sky image) for" : "SPHEREx image"} ${frame.frame_key}, observed ${formatDateShort(frame.observed_at_utc)}, ${formatMicrons(frame.wavelength_um)}`}
                onError={() => setImageFailed(img.src)}
                draggable={false}
              />
              {showFlags && frame.flag_image && (
                <img className="plate-overlay" src={resolveAssetSrc(frame.flag_image.src)} alt="Flag map overlay" />
              )}
              <svg className="plate-overlay" viewBox={`0 0 ${img.width} ${img.height}`} aria-hidden="true">
                {guideY != null && showGuide && (
                  <line className="guide-line" x1={0} x2={img.width} y1={guideY} y2={guideY} />
                )}
                {xy && showMarker && <circle className="marker" cx={xy.x} cy={xy.y} r={Math.max(4, img.width / 32)} />}
              </svg>
            </div>
          ) : (
            <div className="plate-frame plate-empty" style={{ aspectRatio: "1 / 1" }}>
              <p>
                {imageFailed
                  ? "The image for this frame could not be loaded."
                  : slot
                    ? statusText(slot)
                    : ""}
              </p>
              {slot?.status === "error" && slot.error && (
                <p className="muted">
                  <span className="mono">{slot.error.code}</span>: {slot.error.message}
                </p>
              )}
              {slot?.status === "error" && slot.error?.retryable && props.onRetry && (
                <button type="button" onClick={() => props.onRetry?.(index)}>
                  Retry this frame
                </button>
              )}
            </div>
          )}
          <figcaption>
            {frame ? (
              <>
                <strong>{slot?.ref ? `Frame ${slot.ref}` : `Frame ${index + 1}`}</strong> ·{" "}
                {formatDateShort(frame.observed_at_utc)} · {formatMicrons(frame.wavelength_um)} ·{" "}
                <span className="quality" data-status={frame.quality.status}>
                  {QUALITY_LABEL[frame.quality.status]}
                </span>
                {frame._fixture && <span className="fixture-tag"> · Development fixture — not NASA data</span>}
              </>
            ) : (
              <span>{slot ? slotName(slot, index) : ""}</span>
            )}
          </figcaption>
          {frame && xy && showMarker && (
            <p className="legend">
              <span className="legend-marker" aria-hidden="true" /> Catalog prediction for this date — not a detection.
            </p>
          )}
        </figure>

        <div className="controls" role="group" aria-label="Step through frames">
          <button type="button" onClick={() => step(-1)} disabled={index === 0} aria-label="Previous frame">
            ← Earlier
          </button>
          <label className="slider">
            <span className="visually-hidden">Frame position</span>
            <input
              type="range"
              min={0}
              max={slots.length - 1}
              value={index}
              onChange={(e) => goTo(Number(e.target.value))}
              aria-valuetext={slot ? slotName(slot, index) : undefined}
            />
          </label>
          <button
            type="button"
            onClick={() => step(1)}
            disabled={index === slots.length - 1}
            aria-label="Next frame"
          >
            Later →
          </button>
          <span className="counter" aria-hidden="true">
            {index + 1} / {slots.length}
          </span>
        </div>
        <p className="visually-hidden" aria-live="polite">
          {announcement}
        </p>

        <div className="toggles">
          <label>
            <input type="checkbox" checked={showMarker} onChange={(e) => setShowMarker(e.target.checked)} /> Marker
          </label>
          {props.guideLine && (
            <label>
              <input type="checkbox" checked={showGuide} onChange={(e) => setShowGuide(e.target.checked)} /> Guide line
            </label>
          )}
          {frame?.flag_image && (
            <label>
              <input type="checkbox" checked={showFlags} onChange={(e) => setShowFlags(e.target.checked)} /> Flag map
            </label>
          )}
        </div>

        {slots.length >= 2 && pair && (
          <fieldset className="blink">
            <legend>Blink two frames</legend>
            {[0, 1].map((side) => (
              <label key={side}>
                <span>{side === 0 ? "First" : "Second"}</span>
                <select
                  value={pair[side]}
                  onChange={(e) => {
                    const next: [string, string] = [...pair] as [string, string];
                    next[side] = e.target.value;
                    setPair(next);
                  }}
                >
                  {slots.map((s, i) => (
                    <option key={s.key} value={s.key} disabled={s.status !== "ready"}>
                      {slotName(s, i)}
                    </option>
                  ))}
                </select>
              </label>
            ))}
            <button
              type="button"
              aria-pressed={blinking}
              onClick={() => setBlinking((b) => !b)}
              disabled={!pairFrames[0] || !pairFrames[1] || pair[0] === pair[1]}
            >
              {blinking ? "Stop blinking" : "Blink"}
            </button>
            <button
              type="button"
              onClick={() => {
                setBlinking(false);
                const a = pairIdx[0];
                const b = pairIdx[1];
                if (a >= 0 && b >= 0) onIndexChange(index === a ? b : a);
              }}
              disabled={!pairFrames[0] || !pairFrames[1]}
            >
              Swap
            </button>
            {pairComparison && (
              <p className="pair-summary">
                {pairComparison.dt}
                {pairComparison.dl != null
                  ? ` · wavelengths differ by ${pairComparison.dl.toFixed(4)} µm`
                  : " · wavelength not available for one frame"}
                {pairComparison.scales.includes("per_frame") && " · brightness not directly comparable"}
              </p>
            )}
          </fieldset>
        )}

        {slots.some((s) => s.ref) && (
          <div className="ref-jump" role="group" aria-label="Jump to case frame">
            {slots.map((s, i) =>
              s.ref ? (
                <button key={s.key} type="button" aria-current={i === index ? "true" : undefined} onClick={() => goTo(i)}>
                  Frame {s.ref}
                </button>
              ) : null,
            )}
          </div>
        )}
      </div>

      <div className="viewer-side">
        {frame ? (
          <>
            <button
              type="button"
              className="primary"
              aria-pressed={inEvidence}
              onClick={() => props.onToggleEvidence(frame, slot?.ref ?? null)}
            >
              {inEvidence ? "Remove from evidence card" : "Add this frame to evidence"}
            </button>
            <FrameDetails frame={frame} refLabel={slot?.ref} />
          </>
        ) : (
          <p className="muted">Details appear when this frame is ready.</p>
        )}
      </div>
    </section>
  );
}

function statusText(slot: FrameSlot): string {
  switch (slot.status) {
    case "pending":
      return "Waiting to process this frame…";
    case "loading":
      return "Processing this frame…";
    case "error":
      return "This frame could not be processed. The other frames are unaffected.";
    default:
      return "";
  }
}
