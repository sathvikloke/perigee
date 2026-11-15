import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { resolveAssetSrc } from "../api/client";
import type { FrameRecord } from "../api/types";
import { markerXY } from "../lib/compare";
import { QUALITY_LABEL, daysBetween, formatDateShort, formatDuration, formatMicrons } from "../lib/format";
import { nextPlayableIndex, playAnnouncement, playCadenceMs, playableCount, playbackCaveats } from "../lib/playback";
import {
  ALL_WAVELENGTHS,
  applyWaveFilter,
  filterOptionLabel,
  filterScope,
  filterSummary,
  shortMicrons,
  sliderPosition,
  slotStatusTag,
  stepWithin,
  type WaveFilter,
} from "../lib/wavelengthFilter";
import { Elapsed, friendlyError } from "./common";
import { FrameDetails } from "./FrameDetails";
import { Plate } from "./Plate";

const PHONE = "(max-width: 560px)";
const REDUCED = "(prefers-reduced-motion: reduce)";
const media = (q: string): MediaQueryList | null =>
  typeof window !== "undefined" && typeof window.matchMedia === "function" ? window.matchMedia(q) : null;

export type SlotStatus = "pending" | "loading" | "ready" | "error";

export interface FrameSlot {
  key: string;
  ref: string | null;
  status: SlotStatus;
  frame: FrameRecord | null;
  observed_at_utc: string | null;
  mjd: number | null;
  error: { code: string; message: string; retryable: boolean } | null;
  /** When this frame's request started (epoch ms), while it is loading. */
  startedAt?: number | null;
  retryAttempt?: number;
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
  /** Active guided-comparison frames are included by the comparison, not a removable extra. */
  requiredKeys?: Set<string>;
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
  // Let the learner see the image first. The quality badge, hatched-pixel
  // explanation and warning remain visible while the overlay is off.
  const [showFlags, setShowFlags] = useState(false);

  const [pair, setPair] = useState<[string, string] | null>(() =>
    slots.length >= 2 ? [slots[0].key, slots[slots.length - 1].key] : null,
  );
  useEffect(() => {
    if (pair || slots.length < 2) return;
    setPair([slots[0].key, slots[slots.length - 1].key]);
  }, [slots, pair]);
  // One motion at a time: the two-frame blink or playing the whole series.
  // Neither starts on its own; both stop on a hidden tab, printing, crossing
  // the phone breakpoint, a pair change or any manual step.
  const [motion, setMotion] = useState<"blink" | "play" | null>(null);
  const blinking = motion === "blink";
  const playing = motion === "play";
  // Wavelength filter: narrows Earlier/Later, the slider and Play to frames
  // near one wavelength (or one detector). Time order never changes.
  const [waveFilter, setWaveFilter] = useState<WaveFilter>(ALL_WAVELENGTHS);
  // A different series (new search or preset) starts on all wavelengths again.
  const seriesKey = slots.map((s) => s.key).join("|");
  const [filterSeries, setFilterSeries] = useState(seriesKey);
  if (filterSeries !== seriesKey) {
    setFilterSeries(seriesKey);
    setWaveFilter(ALL_WAVELENGTHS);
  }
  const filtered = useMemo(() => applyWaveFilter(slots, waveFilter), [slots, waveFilter]);
  const allowed = waveFilter.mode === "all" ? undefined : filtered.indices;
  const idxRef = useRef(index);
  idxRef.current = index;
  const slotsRef = useRef(slots);
  slotsRef.current = slots;
  const allowedRef = useRef(allowed);
  allowedRef.current = allowed;
  useEffect(() => {
    if (!blinking || !pair) return;
    const a = slots.findIndex((s) => s.key === pair[0]);
    const b = slots.findIndex((s) => s.key === pair[1]);
    if (a < 0 || b < 0) return;
    const ms = media(REDUCED)?.matches ? 1500 : 1000;
    const id = window.setInterval(() => onIndexChange(idxRef.current === a ? b : a), ms);
    return () => window.clearInterval(id);
  }, [blinking, pair, slots, onIndexChange]);

  // Series playback reads slots through a ref, so frames that finish loading
  // join the loop without restarting the timer.
  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      const next = nextPlayableIndex(slotsRef.current, idxRef.current, allowedRef.current);
      if (next < 0) setMotion(null);
      else onIndexChange(next);
    }, playCadenceMs(Boolean(media(REDUCED)?.matches)));
    return () => window.clearInterval(id);
  }, [playing, onIndexChange]);

  // Warm only the one image that plays next; the series is never prefetched.
  useEffect(() => {
    if (!playing) return;
    const next = slots[nextPlayableIndex(slots, index, allowed)]?.frame?.image;
    if (next && typeof Image !== "undefined") new Image().src = resolveAssetSrc(next.src);
  }, [playing, index, slots, allowed]);

  useEffect(() => {
    if (!motion) return;
    const stop = () => setMotion(null);
    const onVis = () => document.hidden && stop();
    const phone = media(PHONE);
    window.addEventListener("beforeprint", stop);
    document.addEventListener("visibilitychange", onVis);
    phone?.addEventListener("change", stop);
    return () => {
      window.removeEventListener("beforeprint", stop);
      document.removeEventListener("visibilitychange", onVis);
      phone?.removeEventListener("change", stop);
    };
  }, [motion]);

  const readyCount = playableCount(slots, allowed);
  const inFilter = !allowed || allowed.includes(index);
  const togglePlay = () => {
    if (playing) return setMotion(null);
    if (readyCount < 2) return;
    // Start from a ready frame inside the filter so the first tick never
    // lands on a placeholder or on another wavelength.
    if (!(slot?.status === "ready" && slot.frame && inFilter)) {
      const first = nextPlayableIndex(slots, index, allowed);
      if (first >= 0) onIndexChange(first);
    }
    setMotion("play");
  };

  const goTo = (i: number) => {
    setMotion(null);
    if (!slots.length) return;
    onIndexChange(Math.min(slots.length - 1, Math.max(0, i)));
  };

  // Earlier/Later, arrow keys and Home/End stay inside the filter. From a
  // frame outside it (reached by a case-frame jump) they move to the nearest
  // kept frame in that direction.
  const prevIdx = allowed ? stepWithin(allowed, index, -1) : index > 0 ? index - 1 : -1;
  const nextIdx = allowed ? stepWithin(allowed, index, 1) : index < slots.length - 1 ? index + 1 : -1;
  const firstIdx = allowed ? allowed[0] ?? -1 : 0;
  const lastIdx = allowed ? allowed[allowed.length - 1] ?? -1 : slots.length - 1;

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    const t = e.target as HTMLElement;
    if (t.closest("input, textarea, select, summary")) return;
    const map: Record<string, number> = { ArrowLeft: prevIdx, ArrowRight: nextIdx, Home: firstIdx, End: lastIdx };
    if (e.key in map) {
      e.preventDefault();
      if (map[e.key] >= 0) goTo(map[e.key]);
    }
  };

  const chooseFilter = (mode: string) => {
    setMotion(null);
    if (mode === "near" && frame?.wavelength_um != null && frame.bandwidth_um != null) {
      setWaveFilter({ mode: "near", center_um: frame.wavelength_um });
    } else if (mode === "detector" && frame?.wavelength_um != null && frame.detector != null) {
      setWaveFilter({ mode: "detector", detector: frame.detector });
    } else {
      setWaveFilter(ALL_WAVELENGTHS);
    }
  };

  const guideY = useMemo(() => {
    if (!props.guideLine || !showGuide) return null;
    const a = slots.find((s) => s.ref === "A")?.frame;
    return a ? markerXY(a.marker)?.y ?? null : null;
  }, [props.guideLine, showGuide, slots]);

  if (!slots.length) return null;

  // "#4 · 1 Jun 2026 · failed to load": frames without an image say so in the
  // slider's spoken value and the blink picker, and stay selectable.
  const slotName = (s: FrameSlot, i: number) => {
    const tag = slotStatusTag(s);
    const wl = s.frame?.wavelength_um;
    const tail = tag ?? (s.frame ? (wl != null ? shortMicrons(wl) : "no wavelength at target") : null);
    return `#${i + 1} · ${s.ref ? `${s.ref} · ` : ""}${formatDateShort(s.observed_at_utc)}${tail ? ` · ${tail}` : ""}`;
  };
  const currentTag = slot ? slotStatusTag(slot) : null;
  const filterLines = filterSummary(waveFilter, filtered);
  // The near/detector options describe the current frame until one is chosen.
  const nearOption: WaveFilter | null =
    waveFilter.mode === "near"
      ? waveFilter
      : frame?.wavelength_um != null && frame.bandwidth_um != null
      ? { mode: "near", center_um: frame.wavelength_um }
      : null;
  const detectorOption: WaveFilter | null =
    waveFilter.mode === "detector"
      ? waveFilter
      : frame?.wavelength_um != null && frame.detector != null
      ? { mode: "detector", detector: frame.detector }
      : null;
  // While blinking or playing, announce once instead of narrating every frame.
  const announcement = blinking
    ? "Playing two images for comparison. Use Pause comparison to stop."
    : playing
    ? playAnnouncement(readyCount, waveFilter)
    : slot
    ? `${
        allowed && inFilter
          ? `Frame ${sliderPosition(allowed, index) + 1} of ${allowed.length}${filterScope(waveFilter)} (${index + 1} of ${slots.length} in all)`
          : `Frame ${index + 1} of ${slots.length}${allowed ? ", outside the wavelength filter" : ""}`
      }. ${formatDateShort(slot.observed_at_utc)}. ${
        frame
          ? `${frame.wavelength_um == null ? "Wavelength not available" : formatMicrons(frame.wavelength_um)}. ${QUALITY_LABEL[frame.quality.status]}.`
          : statusText(slot)
      }`
    : "";
  const caveats = playing ? playbackCaveats(slots, allowed, waveFilter) : [];
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
        <button
          type="button"
          className="play-toggle"
          aria-pressed={playing}
          aria-disabled={readyCount < 2}
          onClick={togglePlay}
          title={
            readyCount < 2
              ? allowed
                ? "Needs at least two processed frames inside the wavelength filter"
                : "Needs at least two processed frames"
              : undefined
          }
        >
          {playing ? "Ⅱ Pause" : "▷ Play"}
        </button>
        {/* aria-disabled keeps focus on the button at either end; a disabled
            button would drop keyboard focus to <body> after Home/End. */}
        <button
          type="button"
          onClick={() => prevIdx >= 0 && goTo(prevIdx)}
          aria-disabled={prevIdx < 0}
          aria-label="Earlier frame"
        >
          ← Earlier
        </button>
        <label className="slider">
          <span className="visually-hidden">Frame position</span>
          <input
            type="range"
            min={0}
            max={allowed ? Math.max(0, allowed.length - 1) : slots.length - 1}
            value={allowed ? sliderPosition(allowed, index) : index}
            onChange={(e) => {
              const v = Number(e.target.value);
              const target = allowed ? allowed[v] : v;
              if (target != null) goTo(target);
            }}
            disabled={allowed ? allowed.length === 0 : false}
            aria-valuetext={slot ? `${slotName(slot, index)}${inFilter ? "" : " · outside the wavelength filter"}` : undefined}
          />
        </label>
        <button
          type="button"
          onClick={() => nextIdx >= 0 && goTo(nextIdx)}
          aria-disabled={nextIdx < 0}
          aria-label="Later frame"
        >
          Later →
        </button>
        <span className="counter" aria-hidden="true">
          {allowed && inFilter ? `${sliderPosition(allowed, index) + 1} / ${allowed.length}` : `${index + 1} / ${slots.length}`}
          {currentTag && <span className="counter-tag"> · {currentTag}</span>}
        </span>
      </div>
      <div className="wave-filter">
        <label>
          <span>Wavelengths to step and play</span>
          <select value={waveFilter.mode} onChange={(e) => chooseFilter(e.target.value)}>
            <option value="all">{filterOptionLabel(ALL_WAVELENGTHS)}</option>
            <option value="near" disabled={!nearOption}>
              {nearOption ? filterOptionLabel(nearOption) : "Near this frame's wavelength (not available)"}
            </option>
            <option value="detector" disabled={!detectorOption}>
              {detectorOption ? filterOptionLabel(detectorOption) : "This frame's detector only (not available)"}
            </option>
          </select>
        </label>
        {filterLines.length > 0 && (
          <div className="wave-filter-summary" aria-live="polite">
            {filterLines.map((l) => (
              <p key={l}>{l}</p>
            ))}
            {!inFilter && (
              <p>Frame #{index + 1} is outside this filter; Earlier and Later move to the nearest frame inside it.</p>
            )}
          </div>
        )}
      </div>
      <p className="visually-hidden" aria-live="polite">
        {announcement}
      </p>
      {playing && caveats.length > 0 && (
        <div className="notice play-note">
          {caveats.map((c) => (
            <p key={c}>{c}</p>
          ))}
        </div>
      )}

      <div className="sequence-body">
        <div className="sequence-stage">
          {slot && (
            <Plate
              letter={slot.ref ?? String(index + 1)}
              heading={slot.ref ? `Investigation image ${slot.ref}` : `Image ${index + 1} of ${slots.length}`}
              headingId="sequence-plate-h"
              frame={frame}
              pendingDate={slot.observed_at_utc}
              pendingWavelength={slot.status === "error" ? "Wavelength unknown (not loaded)" : undefined}
              showMarker={showMarker}
              showFlags={showFlags}
              guideY={guideY}
              placeholder={
                <>
                  <p>
                    {slot.status === "loading" && slot.retryAttempt ? `This image request was interrupted. Retrying (${slot.retryAttempt} of 2)…` : statusText(slot)}
                    {slot.status === "loading" && slot.startedAt ? (
                      <>
                        {" "}
                        <Elapsed since={slot.startedAt} />
                      </>
                    ) : null}
                  </p>
                  {slot.status === "error" && slot.error && (
                    <p>{friendlyError(slot.error.code)}</p>
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
          {!showFlags && frame && frame.quality.status !== "clear" && <p className="sequence-quality-note">This image needs a quality check. {frame.flag_image
            ? "Turn on flagged pixels to inspect affected areas; a hidden overlay does not make those pixels reliable."
            : "No pixel overlay is provided. Read the quality details before interpreting this image."}</p>}
          {slots.some((s) => s.ref) && (
            <div className="ref-jump" role="group" aria-label="Jump to case frame">
              {slots.map((s, i) =>
                s.ref ? (
                  <button key={s.key} type="button" aria-pressed={i === index} onClick={() => goTo(i)}>
                    Image {s.ref}
                  </button>
                ) : null,
              )}
            </div>
          )}
          {props.blinkTool && slots.length >= 2 && pair && (
            <fieldset className="pair-picker">
              <legend>Compare two images</legend>
              {[0, 1].map((side) => (
                <label key={side}>
                  <span>{side === 0 ? "First" : "Second"}</span>
                  <select
                    value={pair[side]}
                    onChange={(e) => {
                      const next: [string, string] = [...pair] as [string, string];
                      next[side] = e.target.value;
                      setMotion(null);
                      setPair(next);
                    }}
                  >
                    {slots.map((s, i) => (
                      <option key={s.key} value={s.key}>
                        {slotName(s, i)}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              <button
                type="button"
                aria-pressed={blinking}
                onClick={() => setMotion((m) => (m === "blink" ? null : "blink"))}
                disabled={!pf[0] || !pf[1] || pair[0] === pair[1]}
              >
                {blinking ? "Pause comparison" : "Play comparison"}
              </button>
              {(!pf[0] || !pf[1]) && (
                <p className="pair-summary">
                  {pairIdx
                    .filter((i, k) => i >= 0 && !pf[k])
                    .map((i) => slots[i].status === "loading" || slots[i].status === "pending"
                      ? `Image ${i + 1} is still loading.`
                      : `Image ${i + 1} is unavailable.`)
                    .join(" ")}{" "}
                  {pairIdx.some((i) => i >= 0 && (slots[i].status === "loading" || slots[i].status === "pending"))
                    ? "You can use the ready images while it loads."
                    : props.onRetry ? "Retry that image, or choose another image to compare." : "Choose another image to compare."}
                </p>
              )}
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
              {props.requiredKeys?.has(frame.frame_key) ? <p className="comparison-attached">Included with your comparison. Choose a different pair above to change it.</p> : <button
                type="button"
                aria-pressed={inEvidence}
                onClick={() => props.onToggleEvidence(frame, slot?.ref ?? null)}
              >
                {inEvidence ? "Attached to notebook · remove" : "Attach this frame to notebook"}
              </button>}
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
      return slot.error?.code === "SUPERSEDED"
        ? "This frame was not processed because a newer search started."
        : "This frame could not be processed. The other frames are unaffected.";
    default:
      return "";
  }
}
