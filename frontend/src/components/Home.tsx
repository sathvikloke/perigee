import { useState } from "react";
import type { PerigeeApi } from "../api/client";
import type { PresetDescriptor } from "../api/types";
import { browserStorage, forgetDraft, listCards, loadStore, persistStore, removeCard } from "../evidence/card";
import { formatDateShort } from "../lib/format";
import { ErrorBlock, useAsync } from "./common";
import { downloadEvidence } from "./Notebook";
import { PageHeading } from "./PageHeading";

export function Home(props: {
  api: PerigeeApi;
  onOpenPreset: (id: string) => void;
  onOpenQuery: () => void;
  onUseFixture?: () => void;
}) {
  const { state, retry } = useAsync((signal) => props.api.presets(signal), [props.api]);
  return (
    <div className="home">
      <PageHeading
        eyebrow="SPHEREx investigations"
        title="Compare real infrared observations and decide what they show"
        intro="Step through images of the same patch of sky taken on different dates, check whether they can be fairly compared, and record what the evidence supports."
        mode={props.api.mode}
      />

      <section aria-labelledby="presets-h">
        <div className="section-head">
          <h2 id="presets-h">Start with a target</h2>
          <p>Two targets come with a guided investigation; the others are open for exploration.</p>
        </div>
        {state.status === "loading" && (
          <p className="status" role="status">
            Loading targets…
          </p>
        )}
        {state.status === "error" && (
          <ErrorBlock
            title="The target list could not be loaded."
            error={state.error}
            onRetry={retry}
            onUseFixture={props.api.mode === "api" ? props.onUseFixture : undefined}
          />
        )}
        {state.status === "ready" &&
          (state.data.length === 0 ? (
            <p className="status">No targets are published yet.</p>
          ) : (
            <ul className="preset-list">
              {state.data.map((p) => (
                <PresetItem key={p.id} preset={p} onOpen={() => props.onOpenPreset(p.id)} />
              ))}
            </ul>
          ))}
      </section>

      <section className="card" aria-labelledby="query-h">
        <div className="section-head">
          <h2 id="query-h">Search any sky position</h2>
          <p>Enter coordinates and Perigee asks the SPHEREx archive which images cover that spot.</p>
        </div>
        <button type="button" className="primary" onClick={props.onOpenQuery}>
          Search by coordinates
        </button>
      </section>

      <SavedEvidence />
    </div>
  );
}

function PresetItem({ preset, onOpen }: { preset: PresetDescriptor; onOpen: () => void }) {
  return (
    <li>
      <button type="button" className="preset" onClick={onOpen}>
        <span className="preset-name">{preset.display_name}</span>
        {preset.one_line && <span className="one-line">{preset.one_line}</span>}
        <span className="meta">
          <span className={`chip${preset.case_ids.length ? " guided" : ""}`}>
            {preset.case_ids.length ? "Guided investigation" : "Free exploration"}
          </span>
          {preset.frames_available === false ? (
            <span className="chip">Frames not published yet</span>
          ) : preset.frame_count ? (
            <span className="chip">
              {preset.frame_count} processed frame{preset.frame_count === 1 ? "" : "s"}
            </span>
          ) : null}
        </span>
      </button>
    </li>
  );
}

function SavedEvidence() {
  const [cards, setCards] = useState(() => listCards(loadStore(browserStorage())));
  const [failed, setFailed] = useState(false);
  const remove = (id: string) => {
    if (!window.confirm("Delete this evidence card from this browser? This cannot be undone; export it first to keep a copy.")) {
      return;
    }
    const storage = browserStorage();
    forgetDraft(id);
    const next = removeCard(loadStore(storage), id);
    setFailed(!persistStore(storage, next));
    setCards(listCards(next));
  };
  return (
    <section className="card" id="my-evidence" aria-labelledby="saved-h">
      <div className="section-head">
        <h2 id="saved-h">My evidence</h2>
        <p>Cards are saved only in this browser. Export one to keep or share it.</p>
      </div>
      {cards.length === 0 ? (
        <p className="status">No evidence cards yet. Open a target and write in its notebook.</p>
      ) : (
        <ul className="saved-list">
          {cards.map(({ card: c, unsaved }) => (
            <li key={c.id}>
              <span>
                <strong>{c.case_id ?? c.preset_id ?? "Coordinate search"}</strong>
                {c.data_origin === "fixture" && <span className="fixture-tag"> · development fixture</span>}
                {unsaved && <span className="fixture-tag"> · not saved on this device; export to keep it</span>}
                <span className="muted block">
                  Updated {formatDateShort(c.updated_at_utc)} · {c.frames.length} observation
                  {c.frames.length === 1 ? "" : "s"}
                  {c.claim ? ` · “${c.claim.slice(0, 80)}${c.claim.length > 80 ? "…" : ""}”` : " · no claim yet"}
                </span>
              </span>
              <span className="actions">
                <button type="button" onClick={() => downloadEvidence(c)}>
                  Export JSON
                </button>
                <button type="button" className="link" onClick={() => remove(c.id)}>
                  Delete from this browser
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      {failed && <p role="alert">This browser would not update its saved evidence.</p>}
    </section>
  );
}
