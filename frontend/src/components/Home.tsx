import { useState } from "react";
import type { PerigeeApi } from "../api/client";
import type { PresetDescriptor } from "../api/types";
import {
  browserStorage,
  loadStore,
  persistStore,
  removeCard,
  type EvidenceCard,
} from "../evidence/card";
import { formatDateShort } from "../lib/format";
import { ErrorBlock, useAsync } from "./common";
import { downloadEvidence } from "./EvidencePanel";

export function Home(props: {
  api: PerigeeApi;
  onOpenPreset: (id: string) => void;
  onOpenQuery: () => void;
  onUseFixture?: () => void;
}) {
  const { state, retry } = useAsync((signal) => props.api.presets(signal), [props.api]);
  return (
    <div className="home">
      <header className="home-head">
        <h1>Compare real SPHEREx observations</h1>
        <p>Step through images of the same patch of sky taken on different dates, check whether they can be fairly compared, and write down what the evidence supports.</p>
      </header>

      <section aria-labelledby="presets-h">
        <h2 id="presets-h">Start with a target</h2>
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

      <section aria-labelledby="query-h">
        <h2 id="query-h">Or search any sky position</h2>
        <p>Enter coordinates to find SPHEREx images covering that spot.</p>
        <button type="button" onClick={props.onOpenQuery}>
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
        {preset.object_type && <span className="muted block">{preset.object_type}</span>}
        {preset.one_line && <span className="block">{preset.one_line}</span>}
        <span className="muted block">
          {preset.case_ids.length ? "Guided investigation" : "Free exploration"}
          {preset.retained_frames?.total != null ? ` · ${preset.retained_frames.total} frames` : ""}
        </span>
      </button>
    </li>
  );
}

function SavedEvidence() {
  const [cards, setCards] = useState<EvidenceCard[]>(() => loadStore(browserStorage()).cards);
  const [failed, setFailed] = useState(false);
  if (cards.length === 0) return null;
  const remove = (id: string) => {
    if (!window.confirm("Delete this evidence card from this browser? This cannot be undone; export it first to keep a copy.")) {
      return;
    }
    const storage = browserStorage();
    const next = removeCard(loadStore(storage), id);
    setFailed(!persistStore(storage, next));
    setCards(next.cards);
  };
  return (
    <section aria-labelledby="saved-h">
      <h2 id="saved-h">Evidence saved in this browser</h2>
      <p className="muted">Stored only on this device. Export a card to keep or share it.</p>
      <ul className="saved-list">
        {cards.map((c) => (
          <li key={c.id}>
            <span>
              <strong>{c.case_id ?? c.preset_id ?? "Coordinate search"}</strong>
              {c.data_origin === "fixture" && <span className="fixture-tag"> · fixture</span>}
              <span className="muted block">
                Updated {formatDateShort(c.updated_at_utc)} · {c.frames.length} frame{c.frames.length === 1 ? "" : "s"}
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
      {failed && <p role="alert">This browser would not update its saved evidence.</p>}
    </section>
  );
}
