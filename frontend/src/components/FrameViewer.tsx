import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import type { FrameRecord } from "../api/types";
import { markerXY } from "../lib/compare";
import { QUALITY_LABEL, daysBetween, formatDateShort, formatDuration, formatMicrons } from "../lib/format";
import { FrameDetails } from "./FrameDetails";
import { Plate } from "./Plate";

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

/**
 * Chronological stepper over every frame of a preset or search, in the
 * design's plate language. Failed frames stay in place; nothing reorders.
 */
export function FrameViewer(props: {
  slots: FrameSlot[];
  index: number;
  onIndexChange: (i: number) => void;
  selectedKeys: Set<string>;
  onToggleEvidence: (frame: FrameRecord, ref: string | null) => void;
  onRetry?: (index: number) => void;
  guideLine?: boolean;
  title: string;
  description?: string;
  /** Offer the two-frame blink tool (used where there is no case pair). */
  blinkTool?: boolean;
}) {
  const { slots, index, onIndexChange } = props;
  const slot = slots[index] as FrameSlot | undefined;
  const frame = slot?.frame ?? null;
  const [showMarker, setShowMarker] = useState(true);
  const [showGuide, setShowGuide] = useState(true);
  // Flag overlay defaults on for frames that failed the screen (saturated cores
  // are transparent and must not read as dimming); the learner's choice wins.
  const [flagChoice, setShowFlags] = useState<boolean | null>(null);
  const showFlags = flagChoice ?? (frame != null && frame.quality.status !== "clear");

  const [pair, setPair] = useState<[string, string] | null>(null);
  useEffect(() => {
    if (pair || slots.length < 2) return;
    setPair([slots[0].key, slots[slots.length - 1].key]);
  }, [slots, pair]);
  const [blinking, setBlinking] = useState(false);
  const idxRef = useRef(index);
  idxRef.current = index;
  useEffect(() => {
    if (!blinking || !pair) return;
    const a = slots.findIndex((s) => s.key === pair[0]);
    const b = slots.findIndex((s) => s.key === pair[1]);
    if (a < 0 || b < 0) return;
    const ms = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? 1500 : 1000;
    const id = window.setInterval(() => onIndexChange(idxRef.current === a ? b : a), ms);
    const stop = () => setBlinking(false);
    window.addEventListener("beforeprint", stop);
    const onVis = () => document.hidden && stop();
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("beforeprint", stop);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [blinking, pair, slots, onIndexChange]);

  const goTo = (i: number) => {
    setBlinking(false);
    if (!slots.length) return;
    onIndexChange(Math.min(slots.length - 1, Math.max(0, i)));
  };

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    const t = e.target as HTMLElement;
    if (t.closest("input, textarea, select, summary")) return;
    const map: Record<string, number> = { ArrowLeft: index - 1, ArrowRight: index + 1, Home: 0, End: slots.length - 1 };
    if (e.key in map) {
      e.preventDefault();
      goTo(map[e.key]);
    }
  };

  const guideY = useMemo(() => {
    if (!props.guideLine || !showGuide) return null;
    const a = slots.find((s) => s.ref === "A")?.frame;
    return a ? markerXY(a.marker)?.y ?? null : null;
  }, [props.guideLine, showGuide, slots]);

  if (!slots.length) return null;

  const slotName = (s: FrameSlot, i: number) =>
    `${s.ref ? `${s.ref} · ` : ""}${formatDateShort(s.observed_at_utc)} (#${i + 1})`;
  // While blinking, announce once instead of narrating every alternation.
  const announcement = blinking
    ? "Blinking two frames. Use Pause blink to stop."
    : slot
    ? `Frame ${index + 1} of ${slots.length}. ${formatDateShort(slot.observed_at_utc)}. ${
        frame ? `${formatMicrons(frame.wavelength_um)}. ${QUALITY_LABEL[frame.quality.status]}.` : statusText(slot)
      }`
    : "";
  const inEvidence = frame ? props.selectedKeys.has(frame.frame_key) : false;
  const pairIdx = pair ? pair.map((k) => slots.findIndex((s) => s.key === k)) : [-1, -1];
  const pf = pairIdx.map((i) => (i >= 0 ? slots[i].frame : null));

  return (
    <section className="comparison-shell sequence" aria-labelledby="sequence-h" onKeyDown={onKeyDown}>
      <div className="sequence-head">
        <h2 id="sequence-h">{props.title}</h2>
        {props.description && <p className="counter">{props.description}</p>}
      </div>

      <div className="stepper" role="group" aria-label="Step through frames in time order">
        {/* aria-disabled keeps focus on the button at either end; a disabled
            button would drop keyboard focus to <body> after Home/End. */}
        <button
          type="button"
          onClick={() => index > 0 && goTo(index - 1)}
          aria-disabled={index === 0}
          aria-label="Earlier frame"
        >
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
          onClick={() => index < slots.length - 1 && goTo(index + 1)}
          aria-disabled={index === slots.length - 1}
          aria-label="Later frame"
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

      <div className="sequence-body">
        <div className="sequence-stage">
          {slot && (
            <Plate
              letter={slot.ref ?? String(index + 1)}
              heading={slot.ref ? `Case frame ${slot.ref}` : `Frame ${index + 1} of ${slots.length}`}
              headingId="sequence-plate-h"
              frame={frame}
              pendingDate={slot.observed_at_utc}
              showMarker={showMarker}
              showFlags={showFlags}
              guideY={guideY}
              placeholder={
                <>
                  <p>{statusText(slot)}</p>
                  {slot.status === "error" && slot.error && (
                    <p className="mono">
                      {slot.error.code}: {slot.error.message}
                    </p>
                  )}
                  {slot.status === "error" && slot.error?.retryable && props.onRetry && (
                    <button type="button" onClick={() => props.onRetry?.(index)}>
                      Retry this frame
                    </button>
                  )}
                </>
              }
            />
          )}
          <div className="view-controls">
            <div className="checks">
              <label>
                <input type="checkbox" checked={showMarker} onChange={(e) => setShowMarker(e.target.checked)} /> Show
                predicted position
              </label>
              {props.guideLine && (
                <label>
                  <input type="checkbox" checked={showGuide} onChange={(e) => setShowGuide(e.target.checked)} /> Guide
                  line through A
                </label>
              )}
              {frame?.flag_image && (
                <label>
                  <input type="checkbox" checked={showFlags} onChange={(e) => setShowFlags(e.target.checked)} /> Show
                  flagged pixels
                </label>
              )}
            </div>
          </div>
          {slots.some((s) => s.ref) && (
            <div className="ref-jump" role="group" aria-label="Jump to case frame">
              {slots.map((s, i) =>
                s.ref ? (
                  <button key={s.key} type="button" aria-pressed={i === index} onClick={() => goTo(i)}>
                    Frame {s.ref}
                  </button>
                ) : null,
              )}
            </div>
          )}
          {props.blinkTool && slots.length >= 2 && pair && (
            <fieldset className="pair-picker">
              <legend>Blink two frames</legend>
              {[0, 1].map((side) => (
                <label key={side}>
                  <span>{side === 0 ? "First" : "Second"}</span>
                  <select
                    value={pair[side]}
                    onChange={(e) => {
                      const next: [string, string] = [...pair] as [string, string];
                      next[side] = e.target.value;
                      setBlinking(false);
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
                disabled={!pf[0] || !pf[1] || pair[0] === pair[1]}
              >
                {blinking ? "Ⅱ Pause blink" : "▷ Blink"}
              </button>
              {pf[0] && pf[1] && (
                <p className="pair-summary">
                  {formatDuration(daysBetween(pf[0].mjd, pf[1].mjd))}
                  {pf[0].wavelength_um != null && pf[1].wavelength_um != null
                    ? ` · wavelengths differ by ${Math.abs(pf[0].wavelength_um - pf[1].wavelength_um).toFixed(4)} µm`
                    : " · wavelength not available for one frame"}
                  {(pf[0].display_scale?.mode === "per_frame" || pf[1].display_scale?.mode === "per_frame") &&
                    " · brightness not directly comparable"}
                </p>
              )}
            </fieldset>
          )}
        </div>

        <div className="sequence-side">
          {frame ? (
            <>
              <button
                type="button"
                aria-pressed={inEvidence}
                onClick={() => props.onToggleEvidence(frame, slot?.ref ?? null)}
              >
                {inEvidence ? "✓ Attached to notebook · remove" : "+ Attach this frame to notebook"}
              </button>
              <FrameDetails frame={frame} />
            </>
          ) : (
            <p className="status">Details appear when this frame is ready.</p>
          )}
        </div>
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
