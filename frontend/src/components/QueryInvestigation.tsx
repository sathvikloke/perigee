import { useCallback, useEffect, useId, useMemo, useRef, useState, type FormEvent } from "react";
import {
  FRAME_CONCURRENCY,
  createRequestGate,
  isAbortError,
  runWithConcurrency,
  type PerigeeApi,
} from "../api/client";
import type { FrameRecord, SearchResponse } from "../api/types";
import { createEvidenceCard } from "../evidence/card";
import { useEvidenceCard } from "../evidence/useEvidenceCard";
import {
  FOV_DEFAULT,
  FOV_MAX,
  FOV_MIN,
  LIMIT_DEFAULT,
  LIMIT_MAX,
  LIMIT_MIN,
  validateQuery,
  type QueryErrors,
  type QueryInput,
  type ValidQuery,
} from "../lib/coords";
import { ErrorBlock, errorInfo } from "./common";
import { FrameViewer, type FrameSlot } from "./FrameViewer";
import { Notebook } from "./Notebook";
import { PageHeading } from "./PageHeading";

type Phase =
  | { kind: "idle" }
  | { kind: "searching"; query: ValidQuery }
  | { kind: "searched"; query: ValidQuery }
  | { kind: "failed"; query: ValidQuery; error: unknown };

/** The results currently on screen. They change only when a new search succeeds. */
interface Shown {
  query: ValidQuery;
  response: SearchResponse;
}

const describe = (q: ValidQuery) => `RA ${q.ra_deg}°, Dec ${q.dec_deg}°, ${q.fov_arcmin}′ field`;

export function QueryInvestigation(props: {
  api: PerigeeApi;
  initial: { ra?: string; dec?: string; fov?: string; caseId?: string };
  frameCache: Map<string, FrameRecord>;
  onQueryChange: (q: ValidQuery) => void;
  onUseFixture?: () => void;
}) {
  const { api, frameCache } = props;
  const id = useId();
  const [input, setInput] = useState<QueryInput>({
    ra: props.initial.ra ?? "",
    dec: props.initial.dec ?? "",
    fov: props.initial.fov ?? String(FOV_DEFAULT),
    limit: String(LIMIT_DEFAULT),
  });
  const [errors, setErrors] = useState<QueryErrors>({});
  const [notices, setNotices] = useState<string[]>([]);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [shown, setShown] = useState<Shown | null>(null);
  const [slots, setSlots] = useState<FrameSlot[]>([]);
  const [index, setIndex] = useState(0);
  const gate = useRef(createRequestGate());
  const fieldRefs = useRef<Partial<Record<keyof QueryInput, HTMLInputElement | null>>>({});

  useEffect(() => () => gate.current.cancel(), []);

  const patchSlot = (i: number, patch: Partial<FrameSlot>) =>
    setSlots((prev) => prev.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const cacheKey = (key: string) => `${api.mode}:${key}`;

  const loadFrame = useCallback(
    async (ticketId: number, signal: AbortSignal, i: number, token: string, key: string) => {
      const cached = frameCache.get(cacheKey(key));
      if (cached) {
        if (gate.current.isCurrent(ticketId)) patchSlot(i, { status: "ready", frame: cached, error: null });
        return;
      }
      if (gate.current.isCurrent(ticketId)) patchSlot(i, { status: "loading", error: null });
      try {
        const frame = await api.frame(token, signal);
        frameCache.set(cacheKey(key), frame);
        if (gate.current.isCurrent(ticketId)) patchSlot(i, { status: "ready", frame, error: null });
      } catch (err) {
        if (isAbortError(err) || !gate.current.isCurrent(ticketId)) return;
        patchSlot(i, { status: "error", error: errorInfo(err) });
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [api, frameCache],
  );

  const runSearch = useCallback(
    async (query: ValidQuery) => {
      const ticket = gate.current.begin();
      setPhase({ kind: "searching", query });
      // Frames of the previous search that never finished stay unfinished;
      // their requests were aborted with the old ticket.
      setSlots((prev) =>
        prev.map((s) =>
          s.status === "pending" || s.status === "loading"
            ? { ...s, status: "error", error: { code: "SUPERSEDED", message: "Stopped by a newer search.", retryable: false } }
            : s,
        ),
      );
      try {
        const response = await api.search(query, ticket.signal);
        if (!gate.current.isCurrent(ticket.id)) return;
        setPhase({ kind: "searched", query });
        setShown({ query, response });
        setIndex(0);
        setSlots(
          response.observations.map((o) => {
            const key = o.frame_key ?? o.observation_id;
            const cached = frameCache.get(cacheKey(key));
            return {
              key,
              ref: null,
              status: cached ? ("ready" as const) : ("pending" as const),
              frame: cached ?? null,
              observed_at_utc: o.observed_at_utc,
              mjd: o.mjd,
              error: null,
            };
          }),
        );
        await runWithConcurrency(
          response.observations,
          FRAME_CONCURRENCY,
          (o, i) => loadFrame(ticket.id, ticket.signal, i, o.frame_token, o.frame_key ?? o.observation_id),
          ticket.signal,
        );
      } catch (err) {
        if (isAbortError(err) || !gate.current.isCurrent(ticket.id)) return;
        setPhase({ kind: "failed", query, error: err });
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [api, frameCache, loadFrame],
  );

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    const v = validateQuery(input);
    if (!v.ok) {
      setErrors(v.errors);
      setNotices([]);
      const first = (["ra", "dec", "fov", "limit"] as const).find((k) => v.errors[k]);
      if (first) fieldRefs.current[first]?.focus();
      return;
    }
    setErrors({});
    setNotices(v.notices);
    if (v.value.ra_deg !== Number(input.ra)) setInput((p) => ({ ...p, ra: String(v.value.ra_deg) }));
    if (phase.kind === "searching" && sameQuery(phase.query, v.value)) return;
    props.onQueryChange(v.value);
    void runSearch(v.value);
  };

  const autoRan = useRef(false);
  useEffect(() => {
    if (autoRan.current) return;
    autoRan.current = true;
    if (props.initial.ra && props.initial.dec) submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const retryFrame = (i: number) => {
    const o = shown?.response.observations[i];
    const ticket = gate.current.active();
    if (!o || !ticket || phase.kind !== "searched") return;
    void loadFrame(ticket.id, ticket.signal, i, o.frame_token, o.frame_key ?? o.observation_id);
  };

  // Notes belong to the results on screen, so a failed new search never hides them.
  const q = shown?.query ?? null;
  const contextKey = q ? `${api.mode}:query:${q.ra_deg},${q.dec_deg},${q.fov_arcmin}` : `${api.mode}:query:none`;
  const makeCard = useCallback(
    () =>
      createEvidenceCard({
        case_id: props.initial.caseId ?? null,
        query: q ? { ra_deg: q.ra_deg, dec_deg: q.dec_deg, fov_arcmin: q.fov_arcmin } : null,
        sources: [{ label: "SPHEREx data at NASA/IPAC IRSA", url: "https://irsa.ipac.caltech.edu/Missions/spherex.html" }],
        app_version: __APP_VERSION__,
        data_origin: api.mode,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [contextKey],
  );
  const ev = useEvidenceCard(contextKey, makeCard);
  const selected = useMemo(() => new Set(ev.card.frames.map((f) => f.frame_key)), [ev.card.frames]);

  const counts = slots.reduce(
    (acc, s) => ({ ...acc, [s.status]: acc[s.status] + 1 }),
    { pending: 0, loading: 0, ready: 0, error: 0 } as Record<FrameSlot["status"], number>,
  );
  const expired = slots.some((s) => s.error?.code === "TOKEN_EXPIRED");
  const showingOld = shown && phase.kind !== "idle" && phase.kind !== "searched" && !sameQuery(phase.query, shown.query);

  const field = (key: keyof QueryInput, label: string, help: string, numeric = false) => (
    <div className="field">
      <label htmlFor={`${id}-${key}`}>{label}</label>
      <span className="field-hint" id={`${id}-${key}-help`}>
        {help}
      </span>
      <input
        id={`${id}-${key}`}
        ref={(el) => {
          fieldRefs.current[key] = el;
        }}
        type="text"
        inputMode={numeric ? "numeric" : "decimal"}
        autoComplete="off"
        spellCheck={false}
        value={input[key]}
        aria-invalid={errors[key] ? true : undefined}
        aria-describedby={`${id}-${key}-help${errors[key] ? ` ${id}-${key}-err` : ""}`}
        onChange={(e) => setInput((p) => ({ ...p, [key]: e.target.value }))}
      />
      {errors[key] && (
        <p className="field-error" id={`${id}-${key}-err`}>
          {errors[key]}
        </p>
      )}
    </div>
  );

  return (
    <>
      <PageHeading
        eyebrow="SPHEREx investigation"
        eyebrowDetail="Any sky position"
        title="Which SPHEREx images cover this spot?"
        intro="Enter a position. Perigee asks the archive, then processes each image one at a time so you can compare dates, wavelengths and quality."
        mode={api.mode}
      />
      <div className={`workspace${shown ? "" : " single"}`}>
        <section className="bench" aria-label="Coordinate search">
          <form className="comparison-shell query-form" onSubmit={submit} noValidate aria-label="Sky position">
            <div className="query-fields">
              {field("ra", "Right ascension", "Degrees, 0 to under 360 (ICRS).")}
              {field("dec", "Declination", "Degrees, −90 to 90 (ICRS).")}
              {field("fov", "Field of view", `Arcminutes, ${FOV_MIN}–${FOV_MAX}; default ${FOV_DEFAULT}.`)}
              {field("limit", "Maximum results", `${LIMIT_MIN}–${LIMIT_MAX}; default ${LIMIT_DEFAULT}.`, true)}
            </div>
            <div className="actions">
              <button type="submit" className="primary">
                Search the archive
              </button>
              {phase.kind === "searching" && (
                <button
                  type="button"
                  onClick={() => {
                    gate.current.cancel();
                    setPhase({ kind: "idle" });
                  }}
                >
                  Cancel
                </button>
              )}
            </div>
            <p className="field-hint">
              Need a starting point?{" "}
              <button
                type="button"
                className="link"
                onClick={() => setInput((p) => ({ ...p, ra: "330.84", dec: "-56.786" }))}
              >
                Use Epsilon Indi A, J2000 catalog position (330.84, −56.786)
              </button>
              . The star has moved about 2′ from there by 2026; a 6′ field still includes it.
            </p>
            {notices.map((n) => (
              <p key={n} className="notice" role="note">
                {n}
              </p>
            ))}
          </form>

          <p className="visually-hidden" role="status">
            {phase.kind === "searching"
              ? "Searching the archive."
              : phase.kind === "searched" && shown
                ? shown.response.status === "empty"
                  ? "Search finished with no matching images."
                  : `Search finished: ${shown.response.returned_count} observations. Frames are processing.`
                : phase.kind === "failed"
                  ? "The search failed."
                  : ""}
          </p>

          {phase.kind === "searching" && <p className="status">Searching the archive for {describe(phase.query)}…</p>}
          {phase.kind === "failed" && (
            <ErrorBlock
              title="The archive search failed. This is not a result about the sky."
              error={phase.error}
              onRetry={() => void runSearch(phase.query)}
              onUseFixture={api.mode === "api" ? props.onUseFixture : undefined}
            />
          )}
          {showingOld && shown && (
            <p className="notice" role="note">
              Still showing the previous images and notes, from {describe(shown.query)}.
            </p>
          )}
          {shown && !showingOld && <SearchSummary response={shown.response} counts={counts} />}
          {expired && phase.kind === "searched" && shown && (
            <div className="notice" role="alert">
              <p>This search has expired. Run it again to continue; your notes are kept.</p>
              <button type="button" onClick={() => void runSearch(shown.query)}>
                Run the search again
              </button>
            </div>
          )}

          {slots.length > 0 && (
            <FrameViewer
              title={`Results in time order`}
              description={shown ? describe(shown.query) : undefined}
              slots={slots}
              index={Math.min(index, slots.length - 1)}
              onIndexChange={setIndex}
              selectedKeys={selected}
              onToggleEvidence={ev.toggleFrame}
              onRetry={retryFrame}
              blinkTool
            />
          )}
        </section>

        {shown && (
          <Notebook
            card={ev.card}
            onChange={ev.update}
            onRemoveFrame={ev.removeFrame}
            saveState={ev.saveState}
          />
        )}
      </div>
    </>
  );
}

function sameQuery(a: ValidQuery, b: ValidQuery) {
  return a.ra_deg === b.ra_deg && a.dec_deg === b.dec_deg && a.fov_arcmin === b.fov_arcmin && a.limit === b.limit;
}

function SearchSummary({
  response,
  counts,
}: {
  response: SearchResponse;
  counts: Record<FrameSlot["status"], number>;
}) {
  const scope = response.collections_queried.length
    ? response.collections_queried.join(", ")
    : "the supported collections";
  if (response.status === "empty") {
    return (
      <div className="status">
        <p>
          <strong>No matching images in {scope}.</strong> The archive answered, and none of its records in these
          collections cover this position and field. That is not proof the sky there is empty, or that other missions
          lack data.
        </p>
      </div>
    );
  }
  return (
    <div className="status">
      <p>
        <strong>
          {response.returned_count} observation{response.returned_count === 1 ? "" : "s"} found
        </strong>{" "}
        in {scope}
        {response.total_matches != null ? ` (of ${response.total_matches} matches)` : ""}
        {response.truncated ? ", shortened by the result limit" : ""}. {counts.ready} ready · {counts.loading}{" "}
        processing · {counts.pending} waiting · {counts.error} failed.
      </p>
      {response.status === "partial" && (
        <p className="notice">Partial results: part of the archive could not be searched. Some images may be missing.</p>
      )}
      {response.warnings.length > 0 && (
        <ul className="plain-list">
          {response.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
