import type { CaseContent } from "../api/types";

/** Renders Sathvik's authored case copy as-is: short layer first, depth in disclosures. */
export function CasePanel({ content }: { content: CaseContent }) {
  return (
    <section className="case" aria-labelledby="case-title">
      <p className="kicker">Investigation</p>
      <h2 id="case-title">{content.title}</h2>
      <p className="question">{content.opening_question}</p>
      {content.background?.short && <p>{content.background.short}</p>}
      {content.background?.details?.length ? (
        <details className="disclosure">
          <summary>More background</summary>
          <ul className="plain-list">
            {content.background.details.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </details>
      ) : null}

      <h3 className="sub">Steps</h3>
      <ol className="steps">
        {content.steps.map((s) => (
          <li key={s.id}>
            <p>{s.prompt}</p>
            {s.hint && (
              <details className="disclosure">
                <summary>Hint</summary>
                <p>{s.hint}</p>
              </details>
            )}
          </li>
        ))}
      </ol>

      {(content.limitations?.length || content.sources?.length) && (
        <details className="disclosure">
          <summary>Limitations and sources</summary>
          {content.limitations?.length ? (
            <ul className="plain-list">
              {content.limitations.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          ) : null}
          {content.sources?.length ? (
            <ul className="plain-list">
              {content.sources.map((s) => (
                <li key={s.url}>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.label}
                  </a>
                </li>
              ))}
            </ul>
          ) : null}
        </details>
      )}
    </section>
  );
}
