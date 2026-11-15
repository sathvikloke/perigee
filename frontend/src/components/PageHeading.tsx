import type { PresetDescriptor } from "../api/types";
import type { ReactNode } from "react";

/** Investigation heading row (design: `.heading-row`). */
export function PageHeading(props: {
  eyebrow: string;
  eyebrowDetail?: string | null;
  title: string;
  intro?: string | null;
  mode: "api" | "fixture";
  controls?: ReactNode;
}) {
  return (
    <header className="heading-row">
      <div className="heading-topline">
        <p className="eyebrow">
          {props.eyebrow}
          {props.eyebrowDetail && <span>{props.eyebrowDetail}</span>}
        </p>
        {props.controls}
      </div>
      <div className="heading-content">
        <div className="heading-copy">
          <h1>{props.title}</h1>
          {props.intro && <p className="intro">{props.intro}</p>}
        </div>
        {props.mode === "fixture" ? (
          <span className="real-data fixture">Development fixture — not NASA data</span>
        ) : (
          <span className="real-data">
            <span aria-hidden="true">✦</span> Real NASA / IPAC observations
          </span>
        )}
      </div>
    </header>
  );
}

/**
 * One closed disclosure at the top of an investigation for switching target,
 * investigation or coordinates, so the sky reaches the first viewport sooner.
 */
export function InvestigationSwitcher(props: {
  presets: PresetDescriptor[];
  currentId: string;
  onOpenPreset: (id: string) => void;
  onOpenQuery: () => void;
}) {
  return (
    <details className="panel switcher" onKeyDown={(event) => {
      if (event.key === "Escape") {
        event.currentTarget.open = false;
        event.currentTarget.querySelector("summary")?.focus();
      }
    }}>
      <summary aria-label="Change investigation, target or coordinates">
        <span>
          <span className="section-icon" aria-hidden="true">
            ⌖
          </span>
          Change investigation
        </span>
        <span className="expand" aria-hidden="true">
          +
        </span>
      </summary>
      <div className="details-body">
        <ul className="switcher-list">
          {props.presets.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                aria-current={p.id === props.currentId ? "true" : undefined}
                onClick={() => props.onOpenPreset(p.id)}
              >
                {p.display_name}
                <span>{p.case_ids.length ? "Guided investigation" : "Free exploration"}</span>
              </button>
            </li>
          ))}
          <li>
            <button type="button" onClick={props.onOpenQuery}>
              Any sky position
              <span>Search by coordinates</span>
            </button>
          </li>
        </ul>
      </div>
    </details>
  );
}

const WORKFLOW = [
  ["Compare", "Time and wavelength"],
  ["Check", "Quality and context"],
  ["Explain", "What the evidence says"],
] as const;

/** The three-step workflow strip (design: 3 steps, not 4). */
export function WorkflowStrip() {
  return (
    <ol className="steps" aria-label="Investigation workflow">
      {WORKFLOW.map(([title, sub], i) => (
        <li key={title}>
          <span className="step-num" aria-hidden="true">
            {i + 1}
          </span>
          <div>
            <strong>{title}</strong>
            <span>{sub}</span>
          </div>
        </li>
      ))}
    </ol>
  );
}
