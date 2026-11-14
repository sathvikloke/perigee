import { useMemo, useState, type MouseEvent } from "react";
import type { PerigeeApi } from "../api/client";
import type { PresetDescriptor } from "../api/types";
import {
  browserStorage,
  forgetDraft,
  listCards,
  loadStore,
  persistStore,
  removeCard,
  sessionDrafts,
  type EvidenceStore,
} from "../evidence/card";
import { reopenTarget, savedContextKey, type ReopenTarget } from "../evidence/reopen";
import { evidenceTitle, type TitleSources } from "../evidence/title";
import { formatDateShort } from "../lib/format";
import { routeToSearch, type Route } from "../lib/route";
import { ErrorBlock, useAsync } from "./common";
import { downloadEvidence } from "./Notebook";
import { PageHeading } from "./PageHeading";

export function Home(props: {
  api: PerigeeApi;
  onOpenPreset: (id: string) => void;
  onOpenQuery: () => void;
  /** Opens a saved card's investigation; `fixtures` is the card's data origin. */
  onOpenRoute: (route: Route, fixtures: boolean) => void;
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

      <SavedEvidence
        api={props.api}
        presets={state.status === "ready" ? state.data : null}
        onOpenRoute={props.onOpenRoute}
      />
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

function SavedEvidence(props: {
  api: PerigeeApi;
  presets: PresetDescriptor[] | null;
  onOpenRoute: (route: Route, fixtures: boolean) => void;
}) {
  const [store, setStore] = useState<EvidenceStore>(() => loadStore(browserStorage()));
  const cards = useMemo(() => listCards(store), [store]);
  const [failed, setFailed] = useState(false);
  const caseIds = useMemo(
    () => [...new Set(cards.map(({ card }) => card.case_id).filter((id): id is string => Boolean(id)))].sort(),
    [cards],
  );
  // Case titles for the card headings. A failed lookup only costs the
  // case title; the target name or coordinates still identify the card.
  const { state: caseState } = useAsync(
    async (signal) =>
      Object.fromEntries(
        (
          await Promise.all(
            caseIds.map((id) =>
              props.api.caseContent(id, signal).then(
                (c) => [[id, { title: c.title, target_id: c.target_id }]] as const,
                () => [],
              ),
            ),
          )
        ).flat(),
      ),
    [props.api, caseIds.join("|")],
  );
  const sources: TitleSources = {
    presets: props.presets,
    cases: caseState.status === "ready" ? caseState.data : null,
  };
  const remove = (id: string) => {
    if (!window.confirm("Delete this evidence card from this browser? This cannot be undone; export it first to keep a copy.")) {
      return;
    }
    const storage = browserStorage();
    forgetDraft(id);
    const next = removeCard(loadStore(storage), id);
    setFailed(!persistStore(storage, next));
    setStore(next);
  };
  return (
    <section className="card" id="my-evidence" aria-labelledby="saved-h">
      <div className="section-head">
        <h2 id="saved-h">My evidence</h2>
        <p>Cards are saved only in this browser. Reopen one to keep working, or export it to keep or share it.</p>
      </div>
      {cards.length === 0 ? (
        <p className="status">No evidence cards yet. Open a target and write in its notebook.</p>
      ) : (
        <ul className="saved-list">
          {cards.map(({ card: c, unsaved }) => {
            const title = evidenceTitle(c, sources);
            const target = reopenTarget(c, savedContextKey(c.id, store, sessionDrafts));
            return (
              <li key={c.id}>
                <span className="saved-summary">
                  <strong className="saved-title">{title}</strong>
                  {c.data_origin === "fixture" && <span className="fixture-tag"> · development fixture</span>}
                  {unsaved && <span className="fixture-tag"> · not saved on this device; export to keep it</span>}
                  <span className="muted block">
                    Updated {formatDateShort(c.updated_at_utc)} · {c.frames.length} observation
                    {c.frames.length === 1 ? "" : "s"}
                    {c.claim ? ` · “${c.claim.slice(0, 80)}${c.claim.length > 80 ? "…" : ""}”` : " · no claim yet"}
                  </span>
                </span>
                <span className="actions">
                  {target && <ReopenLink target={target} title={title} onOpen={props.onOpenRoute} />}
                  <button type="button" onClick={() => downloadEvidence(c)}>
                    Export JSON
                  </button>
                  <button type="button" className="link" onClick={() => remove(c.id)}>
                    Delete from this browser
                  </button>
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {failed && <p role="alert">This browser would not update its saved evidence.</p>}
    </section>
  );
}

/**
 * A real link (it can be opened in a new tab and its URL shared): the URL
 * carries only the target or coordinates, never the notes, which stay in
 * this browser and come back through the notebook's own context key.
 */
function ReopenLink(props: {
  target: ReopenTarget;
  title: string;
  onOpen: (route: Route, fixtures: boolean) => void;
}) {
  const { route, fixtures } = props.target;
  const href = `${window.location.pathname}${routeToSearch(route, fixtures)}`;
  const onClick = (e: MouseEvent<HTMLAnchorElement>) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    props.onOpen(route, fixtures);
  };
  return (
    // The accessible name starts with the visible word, then names the card.
    <a className="reopen" href={href} onClick={onClick} aria-label={`Reopen ${props.title}`}>
      Reopen
    </a>
  );
}
