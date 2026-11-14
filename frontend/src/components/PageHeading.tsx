/** Investigation heading row (design: `.heading-row`). */
export function PageHeading(props: {
  eyebrow: string;
  eyebrowDetail?: string | null;
  title: string;
  intro?: string | null;
  mode: "api" | "fixture";
}) {
  return (
    <div className="heading-row">
      <div>
        <p className="eyebrow">
          {props.eyebrow}
          {props.eyebrowDetail && <span>{props.eyebrowDetail}</span>}
        </p>
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
