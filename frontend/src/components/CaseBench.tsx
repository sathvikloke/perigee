import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { CaseContent, FrameRecord } from "../api/types";
import { QUALITY_CHIP, analyzePair, markerXY, pairStretchExplanation, releaseLabel } from "../lib/compare";
import {
  qualityExplanation,
  formatMicrons,
  formatFlagNames,
  formatPixelCount,
  formatUtc,
  qualityNotes,
  HATCH_EXPLANATION,
} from "../lib/format";
import { FlagLegend, Plate } from "./Plate";
import "../styles/investigation-flow.css";
import { useContentCue } from "../lib/contentMotion";

const PHONE = "(max-width: 560px)";
const REDUCED = "(prefers-reduced-motion: reduce)";

function media(q: string): MediaQueryList | null {
  return typeof window !== "undefined" && window.matchMedia ? window.matchMedia(q) : null;
}

/** A comparison gesture must be clearly horizontal; scrolling never changes images. */
export function comparisonSwipe(start: { x: number; y: number }, end: { x: number; y: number }): "first" | "second" | null {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  return Math.abs(dx) >= 50 && Math.abs(dy) <= 24 && Math.abs(dx) > Math.abs(dy) * 2 ? dx < 0 ? "second" : "first" : null;
}

/**
 * A guided comparison with a fixed image plane, optional overlays and sources.
 * Switching the pair changes image, date, wavelength, source and explanation
 * together.
 */
export function CaseBench(props: {
  caseContent: CaseContent;
  /** Case-set frames by ref; each selected pair must establish stretch compatibility. */
  framesByRef: Map<string, FrameRecord>;
  otherRef: string;
  onOtherRefChange: (ref: string) => void;
  /** Rendered between the comparison shell and its disclosures (case steps). */
  afterShell?: ReactNode;
}) {
  const { caseContent, framesByRef, otherRef } = props;
  const refs = useMemo(() => [...framesByRef.keys()].sort(), [framesByRef]);
  const firstRef = refs[0];
  const others = refs.slice(1);
  const a = framesByRef.get(firstRef) ?? null;
  const b = framesByRef.get(otherRef) ?? null;

  const [showMarker, setShowMarker] = useState(true);
  const [showGuide, setShowGuide] = useState(true);
  // Begin with the images. Quality labels stay visible before the learner
  // chooses to highlight flagged pixels.
  const [showFlags, setShowFlags] = useState(false);
  const [visible, setVisible] = useState<"first" | "second">("first");
  const [blinking, setBlinking] = useState(false);
  const [phone, setPhone] = useState(() => media(PHONE)?.matches ?? false);
  const swipeStart = useRef<{ x: number; y: number; id: number } | null>(null);
  const visibleRef = useRef(visible);
  visibleRef.current = visible;

  const stopBlink = useCallback(() => setBlinking(false), []);

  useEffect(() => {
    if (!blinking) return;
    setVisible("first");
    const ms = media(REDUCED)?.matches ? 1500 : 1000;
    const id = window.setInterval(() => setVisible(visibleRef.current === "first" ? "second" : "first"), ms);
    return () => window.clearInterval(id);
  }, [blinking]);

  // Leaving blink: hidden tab, printing, or crossing the phone breakpoint stops the timer.
  useEffect(() => {
    const onVis = () => document.hidden && stopBlink();
    const phoneQuery = media(PHONE);
    const onPhone = () => {
      stopBlink();
      setVisible("first");
      setPhone(phoneQuery?.matches ?? false);
      swipeStart.current = null;
    };
    setPhone(phoneQuery?.matches ?? false);
    document.addEventListener("visibilitychange", onVis);
    window.addEventListener("beforeprint", stopBlink);
    phoneQuery?.addEventListener("change", onPhone);
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      window.removeEventListener("beforeprint", stopBlink);
      phoneQuery?.removeEventListener("change", onPhone);
    };
  }, [stopBlink]);

  // Pair changes can also come from the notebook's required-pair action.
  useEffect(() => {
    stopBlink();
    setVisible("first");
    swipeStart.current = null;
  }, [firstRef, otherRef, stopBlink]);

  const choosePair = (ref: string) => {
    stopBlink();
    setVisible("first");
    props.onOtherRefChange(ref);
  };

  const analysis = a && b ? analyzePair(a, b) : null;
  const headings = (() => {
    if (!a || !b || !analysis) return ["Observation", "Observation"];
    if (analysis.kind === "wavelength") {
      const aShorter = (a.wavelength_um ?? 0) <= (b.wavelength_um ?? 0);
      return aShorter ? ["Shorter wavelength", "Longer wavelength"] : ["Longer wavelength", "Shorter wavelength"];
    }
    return a.mjd <= b.mjd ? ["Earlier observation", "Later observation"] : ["Later observation", "Earlier observation"];
  })();

  const guideY = caseContent.display_requirements?.reference_line && showGuide && a ? markerXY(a.marker)?.y ?? null : null;
  const sameGrid =
    a && b
      ? a.registration?.grid_id && b.registration?.grid_id
        ? a.registration.grid_id === b.registration.grid_id
        : a.registration?.center_ra_deg === b.registration?.center_ra_deg &&
          a.registration?.center_dec_deg === b.registration?.center_dec_deg &&
          a.registration?.center_ra_deg != null
      : false;
  const northUp = typeof a?.registration?.orientation === "string" && a.registration.orientation.startsWith("north_up");

  const pairFrames = [a, b].filter((f): f is FrameRecord => Boolean(f));
  const statuses = new Set(pairFrames.map((f) => f.quality.status));
  const qualitySummary =
    statuses.size === 1 ? `What does “${QUALITY_CHIP[pairFrames[0].quality.status].toLowerCase()}” mean?` : "What do these quality labels mean?";
  const limitations = [...new Set(pairFrames.flatMap((f) => f.limitations))];
  const flagFrames = pairFrames.filter((f) => f.flag_image);
  const sameLegend = flagFrames.length === 2 && JSON.stringify(flagFrames[0].flag_image?.legend) === JSON.stringify(flagFrames[1].flag_image?.legend);
  const instruction = caseContent.case_id === "moving_neighbor"
    ? "Play the comparison. Watch the bright star near the ring against the smaller stars."
    : caseContent.case_id === "wise_0855_quality_trap"
      ? otherRef === "B"
        ? "Play the comparison. Watch the bright dot above-left of centre, then turn on flagged pixels."
        : "Look at the dates and wavelengths. This pair also uses different brightness scales."
      : caseContent.case_id === "fair_comparison"
        ? "Look for a visible difference, then check the dates and wavelengths before explaining it."
        : "Play the comparison and notice what changes and what stays in place.";

  const missing = refs.length < 2;
  const activeSide = (phone || blinking) ? visible : "first";
  const whatYouCanLearn = caseContent.case_id === "moving_neighbor"
    ? "You can compare the glow’s position with nearby stars. Its saturated center limits exact position and brightness measurements."
    : caseContent.case_id === "wise_0855_quality_trap"
      ? "You can check whether a changing dot overlaps flagged pixels. The flags cannot establish what physically caused it."
      : "You can compare the field’s appearance. A new dot still needs a pixel-quality check.";
  const takeaway = analysis?.kind === "wavelength"
    ? "This pair shows different infrared colors at the same time. It cannot show a change over time."
    : analysis?.kind === "both"
      ? "Both the date and infrared color change, so this pair cannot isolate a change over time."
      : analysis?.kind === "unknown" ? analysis.body : whatYouCanLearn;
  // Quality and display-mapping limits change what can be claimed now.
  // Exact numerical separations and release context remain in the details.
  const essentialCaveats = analysis?.caveats.filter((caveat) => !caveat.startsWith("The frames come from different data releases")) ?? [];
  const instructionCue = useContentCue<HTMLParagraphElement>("instruction", `${caseContent.case_id}:${otherRef}`);

  return (
    <>
      <div className="comparison-shell guided-comparison">
        <div className="comparison-toolbar">
          <div className="segmented pair-control" role="group" aria-label="Choose comparison">
            {others.map((r) => {
              const other = framesByRef.get(r);
              const pairAnalysis = a && other ? analyzePair(a, other) : null;
              const days = a && other ? Math.abs(a.mjd - other.mjd) : 0;
              const duration = days >= 330 ? `${(days / 365.25).toFixed(1).replace(/\.0$/, "")} year${days >= 548 ? "s" : ""} apart` : days >= 45 ? `${Math.round(days / 30.44)} months apart` : `${Math.round(days)} days apart`;
              const purpose = pairAnalysis?.kind === "wavelength" ? "Compare wavelengths" : pairAnalysis?.kind === "time" ? duration : "Dates + wavelengths";
              return (
                <button
                  key={r}
                  type="button"
                  className="segment"
                  aria-pressed={r === otherRef}
                  onClick={() => choosePair(r)}
                >
                  {purpose}<span>Images {firstRef} + {r}</span>
                </button>
              );
            })}
          </div>
          {/* Phones offer manual image selection alongside playback. */}
          <div className="view-switch">
            <div className="mobile-frame-control" role="group" aria-label="Visible observation">
              <button
                type="button"
                aria-pressed={visible === "first"}
                onClick={() => {
                  stopBlink();
                  setVisible("first");
                }}
              >
                Image {firstRef}
              </button>
              <button
                type="button"
                aria-pressed={visible === "second"}
                onClick={() => {
                  stopBlink();
                  setVisible("second");
                }}
              >
                Image {otherRef}
              </button>
            </div>
            <button
              type="button"
              className="quiet blink-toggle"
              aria-pressed={blinking}
              onClick={() => setBlinking((v) => !v)}
              disabled={!a || !b}
            >
              {blinking ? "Pause comparison" : "Play comparison"}
            </button>
          </div>
        </div>

        <p className="comparison-task" ref={instructionCue}><strong>Notice</strong> {instruction}</p>

        {missing ? (
          <p className="status">This case needs two processed frames; they are not published yet.</p>
        ) : (
          <div className={`plates comparison-plates${blinking ? " blinking" : ""}`} aria-live={blinking ? "off" : undefined}
            onTouchStart={(event) => {
              const touch = event.touches[0];
              swipeStart.current = phone && event.touches.length === 1 && touch
                ? { x: touch.clientX, y: touch.clientY, id: touch.identifier } : null;
            }}
            onTouchMove={(event) => {
              const start = swipeStart.current;
              const touch = Array.from(event.touches).find((item) => item.identifier === start?.id);
              if (!start || !touch || event.touches.length !== 1 || Math.abs(touch.clientY - start.y) > 24) {
                swipeStart.current = null;
              }
            }}
            onTouchCancel={() => { swipeStart.current = null; }}
            onTouchEnd={(event) => {
              const start = swipeStart.current;
              swipeStart.current = null;
              const end = Array.from(event.changedTouches).find((item) => item.identifier === start?.id);
              if (start && end && event.touches.length === 0) {
                const next = comparisonSwipe(start, { x: end.clientX, y: end.clientY });
                if (next) {
                  stopBlink(); setVisible(next);
                }
              }
            }}>
            {/* Both layers contribute their height. Playback never changes the
                image well or shifts the controls below a longer quality note. */}
            <div className="comparison-stack">
              <div className={`comparison-layer comparison-base${activeSide === "first" ? "" : " is-inactive"}`} aria-hidden={activeSide !== "first"}>
            <Plate
              letter={firstRef}
              heading={headings[0]}
              headingId="plate-first-h"
              frame={a}
              showMarker={showMarker}
              showFlags={showFlags}
              guideY={guideY}
              placeholder={<p>Frame {firstRef} is not available.</p>}
            />
              </div>
              <div className={`comparison-layer comparison-alternate${activeSide === "second" ? "" : " is-inactive"}`} aria-hidden={activeSide !== "second"}>
                <Plate letter={otherRef} heading={headings[1]} headingId="plate-playing-h" frame={b}
                  showMarker={showMarker} showFlags={showFlags} guideY={guideY}
                  placeholder={<p>Frame {otherRef} is not available.</p>} />
              </div>
            </div>
            <div className="comparison-reference">
            <Plate
              letter={otherRef}
              heading={headings[1]}
              headingId="plate-second-h"
              frame={b}
              showMarker={showMarker}
              showFlags={showFlags}
              guideY={guideY}
              placeholder={<p>Frame {otherRef} is not available.</p>}
            />
            </div>
          </div>
        )}

        <p className="comparison-playback-note" aria-live="polite">
          {blinking ? phone ? `Playing images ${firstRef} and ${otherRef} in the same position.` : `The left image alternates between ${firstRef} and ${otherRef}; the right stays on ${otherRef}.` : ""}
        </p>
        <p className="mobile-swipe-hint">Swipe left or right, or use the image buttons.</p>
        <div className="view-controls">
          <div className="checks">
            <label>
              <input type="checkbox" checked={showMarker} onChange={(e) => setShowMarker(e.target.checked)} /> Show
              predicted position
            </label>
            {caseContent.display_requirements?.reference_line && (
              <label>
                <input type="checkbox" checked={showGuide} onChange={(e) => setShowGuide(e.target.checked)} /> Guide
                line through {firstRef}
              </label>
            )}
            {pairFrames.some((f) => f.flag_image) && (
              <div className="flag-tools">
                <label>
                  <input type="checkbox" checked={showFlags} onChange={(e) => setShowFlags(e.target.checked)} /> Show
                  flagged pixels
                </label>
                {showFlags && <div className="control-legend">
                  {(sameLegend ? flagFrames.slice(0, 1) : flagFrames).map((f) => (
                    <div key={f.frame_key}>
                      {!sameLegend && flagFrames.length > 1 && <span>{f === a ? firstRef : otherRef}: </span>}
                      <FlagLegend legend={f.flag_image?.legend} />
                    </div>
                  ))}
                </div>}
              </div>
            )}
          </div>
          <span>
            {sameGrid ? "Same sky grid" : "Sky grids differ"}
            {northUp ? " · north up, east left" : ""}
          </span>
        </div>

        {analysis && (
          <div className={`comparison-insight${analysis.kind === "time" ? "" : " different"}`} aria-live="polite">
            <span className="insight-icon" aria-hidden="true">
              ↔
            </span>
            <div>
              <strong>{analysis.title}</strong>
              <p>{takeaway}</p>
              {essentialCaveats.length > 0 && (
                <ul>
                  {essentialCaveats.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
        <details className="comparison-help">
          <summary>Comparison details and terms</summary>
          {analysis && <>
            <p>{analysis.body}</p>
            {analysis.caveats.length > 0 && <ul>{analysis.caveats.map((caveat) => <li key={caveat}>{caveat}</li>)}</ul>}
          </>}
          <dl>
            <div><dt>Play comparison</dt><dd>Alternates the selected images so you can compare positions. Use Pause to stop.</dd></div>
            <div><dt>Wavelength (µm)</dt><dd>The infrared color recorded in each observation. A different wavelength can change an object's appearance.</dd></div>
            <div><dt>Predicted position</dt><dd>The ring shows where a catalog expects the object to be. It does not confirm a detection.</dd></div>
            <div><dt>Flagged pixels</dt><dd>Colored overlays mark pixels that need caution. A passed check does not prove that an object was detected.</dd></div>
          </dl>
        </details>
      </div>

      <a className="notebook-jump" href="#notebook">Record your evidence</a>
      {props.afterShell}

      {pairFrames.length > 0 && (
        <details className="panel content-disclosure">
          <summary>
            <span>
              <span className="section-icon" aria-hidden="true">
                ✓
              </span>
              {qualitySummary}
            </span>
            <span className="expand" aria-hidden="true">
              +
            </span>
          </summary>
          <div className="details-body">
            <div className="quality-grid">
              {[
                [firstRef, a],
                [otherRef, b],
              ].map(([ref, f]) =>
                f && typeof f !== "string" ? (
                  <div key={ref as string}>
                    <p>
                      <strong>
                        {ref as string} · {QUALITY_CHIP[f.quality.status]}
                      </strong>
                    </p>
                    <p>{qualityExplanation(f)}</p>
                    <dl className="facts">
                      <div>
                        <dt>Usable pixels near target</dt>
                        <dd>{formatPixelCount(f.quality.valid_aperture_pixels)}</dd>
                      </div>
                      <div>
                        <dt>Problem pixels near target</dt>
                        <dd>{formatPixelCount(f.quality.adverse_aperture_pixels)}</dd>
                      </div>
                      <div>
                        <dt>Problem flags</dt>
                        <dd>{formatFlagNames(f.quality)}</dd>
                      </div>
                    </dl>
                    {qualityNotes(f.quality.notes).length > 0 && (
                      <ul className="plain-list">
                        {qualityNotes(f.quality.notes).map((n) => (
                          <li key={n}>{n}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ) : null,
              )}
            </div>
            <div className="quality-grid">
              <p>
                <strong className="block">Known limits</strong>A passed screen is not a detection and not a brightness
                measurement. A brightness claim needs calibrated photometry.
              </p>
              <p>
                <strong className="block">Reading the image</strong>The ring marks a catalog prediction for that date.
                {" "}{HATCH_EXPLANATION}
              </p>
            </div>
          </div>
        </details>
      )}

      {pairFrames.length > 0 && (
        <details className="panel content-disclosure" id="sources">
          <summary>
            <span>
              <span className="section-icon" aria-hidden="true">
                ≡
              </span>
              Observation sources &amp; processing
            </span>
            <span className="expand" aria-hidden="true">
              +
            </span>
          </summary>
          <div className="details-body">
            <p>Each image can be traced back to its original SPHEREx observation.</p>
            <div className="table-scroll provenance-table">
              <table>
                <caption className="visually-hidden">Selected observation provenance</caption>
                <thead>
                  <tr>
                    <th scope="col">Frame</th>
                    <th scope="col">Date (UTC)</th>
                    <th scope="col">Wavelength</th>
                    <th scope="col">Original data</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    [firstRef, a],
                    [otherRef, b],
                  ].map(([ref, f]) =>
                    f && typeof f !== "string" ? (
                      <tr key={ref as string}>
                        <td>
                          {ref as string} · <span className="mono">{f.frame_key}</span>
                        </td>
                        <td>{formatUtc(f.observed_at_utc)}</td>
                        <td>{formatMicrons(f.wavelength_um)}</td>
                        <td>
                          {f.source_url ? (
                            <a href={f.source_url} target="_blank" rel="noreferrer">
                              {releaseLabel(f.collection_id)} / D{f.detector ?? "?"} FITS ↗
                            </a>
                          ) : (
                            "not available"
                          )}
                        </td>
                      </tr>
                    ) : null,
                  )}
                </tbody>
              </table>
            </div>
            <div className="provenance-mobile">
              {pairFrames.map((f) => (
                <section key={f.frame_key} aria-label={`Observation ${f === a ? firstRef : otherRef} provenance`}>
                  <h3>Observation {f === a ? firstRef : otherRef}</h3>
                  <dl className="facts">
                    <div><dt>Frame</dt><dd className="mono">{f.frame_key}</dd></div>
                    <div><dt>Date (UTC)</dt><dd>{formatUtc(f.observed_at_utc)}</dd></div>
                    <div><dt>Wavelength</dt><dd>{formatMicrons(f.wavelength_um)}</dd></div>
                    <div><dt>Original data</dt><dd>{f.source_url ? (
                      <a href={f.source_url} target="_blank" rel="noreferrer">{releaseLabel(f.collection_id)} / D{f.detector ?? "?"} FITS ↗</a>
                    ) : "not available"}</dd></div>
                  </dl>
                </section>
              ))}
            </div>
            {a && <ProcessingNote frame={a} comparedWith={b} />}
            {limitations.length > 0 && (
              <ul className="plain-list">
                {limitations.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            )}
          </div>
        </details>
      )}
    </>
  );
}

/** Pair wording is based on both selected records, not the first frame's group. */
export function ProcessingNote({ frame, comparedWith }: { frame: FrameRecord; comparedWith?: FrameRecord | null }) {
  const r = frame.registration;
  const d = frame.display_scale;
  const parts: string[] = [];
  if (r) {
    const w = typeof r.width === "number" ? r.width : frame.image?.width;
    const h = typeof r.height === "number" ? r.height : frame.image?.height;
    const scale = typeof r.scale_arcsec_per_px === "number" ? r.scale_arcsec_per_px : r.arcsec_per_pixel;
    parts.push(
      `Fixed ${w ?? "?"} × ${h ?? "?"} grid${typeof scale === "number" ? ` at ${scale.toFixed(3)} arcsec/pixel` : ""}${
        typeof r.method === "string" ? `, ${r.method.replace(/_/g, " ")} resampling` : ""
      }.`,
    );
  }
  if (comparedWith) {
    parts.push(pairStretchExplanation(frame, comparedWith));
  } else if (d) {
    parts.push(
      `${d.mode === "shared" ? "This frame belongs to a shared" : "A per-frame"}${typeof d.method === "string" ? ` ${d.method}` : ""} display stretch.`,
    );
  }
  if (frame.provenance?.processing_version) parts.push(`Processing ${frame.provenance.processing_version}.`);
  parts.push("For visual inspection only.");
  return <p>{parts.join(" ")}</p>;
}
