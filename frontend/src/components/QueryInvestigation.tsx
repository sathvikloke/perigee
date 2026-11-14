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
import { EvidencePanel } from "./EvidencePanel";
import { FrameViewer, type FrameSlot } from "./FrameViewer";

type Phase =
  | { kind: "idle" }
  | { kind: "searching"; query: ValidQuery }
  | { kind: "searched"; query: ValidQuery; response: SearchResponse }
  | { kind: "failed"; query: ValidQuery; error: unknown };

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
  const [slots, setSlots] = useState<FrameSlot[]>([]);
  const [index, setIndex] = useState(0);
  const gate = useRef(createRequestGate());
  const fieldRefs = useRef<Partial<Record<keyof QueryInput, HTMLInputElement | null>>>({});

  useEffect(() => () => gate.current.cancel(), []);
  // Changing data source invalidates anything in flight.
  useEffect(() => {
    gate.current.cancel();
    setPhase({ kind: "idle" });
    setSlots([]);
  }, [api]);

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
      setSlots([]);
      setIndex(0);
      try {
        const response = await api.search(query, ticket.signal);
        if (!gate.current.isCurrent(ticket.id)) return;
        setPhase({ kind: "searched", query, response });
        const initialSlots: FrameSlot[] = response.observations.map((o) => {
          const key = o.frame_key ?? o.observation_id;
          const cached = frameCache.get(cacheKey(key));
          return {
            key,
            ref: null,
            status: cached ? "ready" : "pending",
            frame: cached ?? null,
            observed_at_utc: o.observed_at_utc,
            mjd: o.mjd,
            error: null,
          };
        });
        setSlots(initialSlots);
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
    // Ignore a duplicate submit of the query already in flight.
    if (phase.kind === "searching" && sameQuery(phase.query, v.value)) return;
    props.onQueryChange(v.value);
    void runSearch(v.value);
  };

  // Auto-run once when the page was opened from a shared coordinate link.
  const autoRan = useRef(false);
  useEffect(() => {
    if (autoRan.current) return;
    autoRan.current = true;
    if (props.initial.ra && props.initial.dec) submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const retryFrame = (i: number) => {
    if (phase.kind !== "searched") return;
    const o = phase.response.observations[i];
    // Retry inside the current generation without starting a new search.
    const ticket = gate.current.active();
    if (!o || !ticket) return;
    void loadFrame(ticket.id, ticket.signal, i, o.frame_token, o.frame_key ?? o.observation_id);
  };

  const activeQuery = phase.kind === "idle" ? null : phase.query;
  const contextKey = activeQuery
    ? `${api.mode}:query:${activeQuery.ra_deg},${activeQuery.dec_deg},${activeQuery.fov_arcmin}`
    : `${api.mode}:query:none`;
  const makeCard = useCallback(
    () =>
      createEvidenceCard({
        case_id: props.initial.caseId ?? null,
        query: activeQuery
          ? { ra_deg: activeQuery.ra_deg, dec_deg: activeQuery.dec_deg, fov_arcmin: activeQuery.fov_arcmin }
          : null,
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

  const field = (key: keyof QueryInput, label: string, help: string, extra: Record<string, string | number>) => (
    <div className="field">
      <label htmlFor={`${id}-${key}`}>{label}</label>
      <input
        id={`${id}-${key}`}
        ref={(el) => {
          fieldRefs.current[key] = el;
        }}
        inputMode="decimal"
        autoComplete="off"
        spellCheck={false}
        value={input[key]}
        aria-invalid={errors[key] ? true : undefined}
        aria-describedby={`${id}-${key}-help${errors[key] ? ` ${id}-${key}-err` : ""}`}
        onChange={(e) => setInput((p) => ({ ...p, [key]: e.target.value }))}
        {...extra}
      />
      <p className="hint" id={`${id}-${key}-help`}>
        {help}
      </p>
      {errors[key] && (
        <p className="field-error" id={`${id}-${key}-err`}>
          {errors[key]}
        </p>
      )}
    </div>
  );

  return (
    <div className="investigation">
      <header className="investigation-head">
        <h1>Search a sky position</h1>
        <p>Enter a position to find SPHEREx images that cover it. Each image is processed one at a time.</p>
      </header>

      <form className="query-form" onSubmit={submit} noValidate aria-label="Sky position">
        <div className="query-fields">
          {field("ra", "Right ascension (degrees)", "0 to just under 360, decimal degrees (ICRS).", {})}
          {field("dec", "Declination (degrees)", "-90 to 90, decimal degrees (ICRS).", {})}
          {field("fov", "Field of view (arcminutes)", `${FOV_MIN} to ${FOV_MAX}; default ${FOV_DEFAULT}.`, {})}
          {field("limit", "Maximum results", `${LIMIT_MIN} to ${LIMIT_MAX}; default ${LIMIT_DEFAULT}.`, {
            inputMode: "numeric",
          })}
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
        {notices.map((n) => (
          <p key={n} className="notice" role="note">
            {n}
          </p>
        ))}
      </form>

      {/* Announce phase changes only; per-frame counts update too often to narrate. */}
      <p className="visually-hidden" role="status">
        {phase.kind === "searching"
          ? "Searching the archive."
          : phase.kind === "searched"
            ? phase.response.status === "empty"
              ? "Search finished with no matching images."
              : `Search finished: ${phase.response.returned_count} observations. Frames are processing.`
            : ""}
      </p>
      <div className="query-status">
        {phase.kind === "searching" && <p className="status">Searching the archive…</p>}
        {phase.kind === "searched" && <SearchSummary response={phase.response} counts={counts} />}
      </div>
      {phase.kind === "failed" && (
        <ErrorBlock
          title="The archive search failed."
          error={phase.error}
          onRetry={() => void runSearch(phase.query)}
          onUseFixture={api.mode === "api" ? props.onUseFixture : undefined}
        />
      )}
      {expired && phase.kind === "searched" && (
        <div className="notice" role="alert">
          <p>This search has expired. Run it again to continue; your notes are kept.</p>
          <button type="button" onClick={() => void runSearch(phase.query)}>
            Run the search again
          </button>
        </div>
      )}

      {slots.length > 0 && (
        <FrameViewer
          label="Search results in time order"
          slots={slots}
          index={Math.min(index, slots.length - 1)}
          onIndexChange={setIndex}
          selectedKeys={selected}
          onToggleEvidence={ev.toggleFrame}
          onRetry={retryFrame}
        />
      )}

      {activeQuery && (
        <EvidencePanel
          card={ev.card}
          onChange={ev.update}
          onRemoveFrame={ev.removeFrame}
          saveState={ev.saveState}
        />
      )}
    </div>
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
        {response.truncated ? " — list shortened by the result limit" : ""}.{" "}
        {counts.ready} ready · {counts.loading} processing · {counts.pending} waiting · {counts.error} failed.
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
