import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { CaseContent, FrameRecord } from "../api/types";
import { QUALITY_CHIP, analyzePair, markerXY, releaseLabel } from "../lib/compare";
import {
  qualityExplanation,
  formatMicrons,
  formatFlagNames,
  formatPixelCount,
  formatUtc,
  qualityNotes,
} from "../lib/format";
import { Plate } from "./Plate";

const PHONE = "(max-width: 560px)";
const REDUCED = "(prefers-reduced-motion: reduce)";

function media(q: string): MediaQueryList | null {
  return typeof window !== "undefined" && window.matchMedia ? window.matchMedia(q) : null;
}

/**
 * The comparison shell from design A: pair switch + blink above two equal,
 * registered plates; marker toggle, explanation, quality and sources below.
 * Switching the pair changes image, date, wavelength, source and explanation
 * together.
 */
export function CaseBench(props: {
  caseContent: CaseContent;
  /** Case-set frames by ref (shared stretch per the case display requirements). */
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
  const [flagChoice, setShowFlags] = useState<boolean | null>(null);
  const [visible, setVisible] = useState<"first" | "second">("first");
  const [blinking, setBlinking] = useState(false);
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
    const phone = media(PHONE);
    const onPhone = () => {
      stopBlink();
      setVisible("first");
    };
    document.addEventListener("visibilitychange", onVis);
    window.addEventListener("beforeprint", stopBlink);
    phone?.addEventListener("change", onPhone);
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      window.removeEventListener("beforeprint", stopBlink);
      phone?.removeEventListener("change", onPhone);
    };
  }, [stopBlink]);

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
  // On by default when either frame failed the flag screen (see Plate legend).
  const showFlags = flagChoice ?? pairFrames.some((f) => f.quality.status !== "clear");
  const statuses = new Set(pairFrames.map((f) => f.quality.status));
  const qualitySummary =
    statuses.size === 1 ? `What does “${QUALITY_CHIP[pairFrames[0].quality.status].toLowerCase()}” mean?` : "What do these quality labels mean?";
  const limitations = [...new Set(pairFrames.flatMap((f) => f.limitations))];

  const missing = refs.length < 2;

  return (
    <>
      <div className="comparison-shell">
        <div className="comparison-toolbar">
          <div className="segmented pair-control" role="group" aria-label="Choose comparison">
            {others.map((r) => {
              const other = framesByRef.get(r);
              const sub = a && other ? analyzePair(a, other).subtitle : "";
              return (
                <button
                  key={r}
                  type="button"
                  className="segment"
                  aria-pressed={r === otherRef}
                  onClick={() => choosePair(r)}
                >
                  {firstRef} + {r} <span>{sub}</span>
                </button>
              );
            })}
          </div>
          {/* Phones show one plate: the explicit A/B choice and blink share one row
              so the sky reaches the first screen. Desktop shows only blink here. */}
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
                Observation {firstRef}
              </button>
              <button
                type="button"
                aria-pressed={visible === "second"}
                onClick={() => {
                  stopBlink();
                  setVisible("second");
                }}
              >
                Observation {otherRef}
              </button>
            </div>
            <button
              type="button"
              className="quiet blink-toggle"
              aria-pressed={blinking}
              onClick={() => setBlinking((v) => !v)}
              disabled={!a || !b}
            >
              {blinking ? "Ⅱ Pause blink" : "▷ Blink pair"}
            </button>
          </div>
        </div>

        {missing ? (
          <p className="status">This case needs two processed frames; they are not published yet.</p>
        ) : (
          <div className={`plates${blinking ? " blinking" : ""}`} aria-live={blinking ? "off" : undefined}>
            <Plate
              letter={firstRef}
              heading={headings[0]}
              headingId="plate-first-h"
              frame={a}
              showMarker={showMarker}
              showFlags={showFlags}
              guideY={guideY}
              className={visible === "first" ? "" : "mobile-hidden is-hidden"}
              placeholder={<p>Frame {firstRef} is not available.</p>}
            />
            <Plate
              letter={otherRef}
              heading={headings[1]}
              headingId="plate-second-h"
              frame={b}
              showMarker={showMarker}
              showFlags={showFlags}
              guideY={guideY}
              className={visible === "second" ? "" : "mobile-hidden is-hidden"}
              placeholder={<p>Frame {otherRef} is not available.</p>}
            />
          </div>
        )}

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
              <label>
                <input type="checkbox" checked={showFlags} onChange={(e) => setShowFlags(e.target.checked)} /> Show
                flagged pixels
              </label>
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
              <p>{analysis.body}</p>
              {analysis.caveats.length > 0 && (
                <ul>
                  {analysis.caveats.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>

      {props.afterShell}

      {pairFrames.length > 0 && (
        <details className="panel">
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
                Hatched areas are outside the image, not empty sky.
              </p>
            </div>
          </div>
        </details>
      )}

      {pairFrames.length > 0 && (
        <details className="panel" id="sources">
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
            <div className="table-scroll">
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
            {a && <ProcessingNote frame={a} pair />}
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

/** `pair`: the note sits under the case comparison plates, not a timeline frame. */
export function ProcessingNote({ frame, pair = false }: { frame: FrameRecord; pair?: boolean }) {
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
  if (d) {
    parts.push(
      `${d.mode === "shared" ? "One shared" : "A per-frame"}${typeof d.method === "string" ? ` ${d.method}` : ""} display stretch.`,
    );
    // The same frame appears in the timeline below with its own stretch (F4).
    if (pair && d.mode === "shared") {
      parts.push("The pair shares one stretch so the plates can be compared by eye; the timeline below gives each frame its own.");
    }
  }
  if (frame.provenance?.processing_version) parts.push(`Processing ${frame.provenance.processing_version}.`);
  parts.push("For visual inspection only.");
  return <p>{parts.join(" ")}</p>;
}
