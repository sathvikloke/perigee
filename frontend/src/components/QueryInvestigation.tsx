import { useCallback, useEffect, useId, useMemo, useRef, useState, type FormEvent } from "react";
import {
  FRAME_CONCURRENCY,
  SEARCH_TIMEOUT_MS,
  createLimiter,
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
import {
  SLOW_SEARCH_MS,
  isDuplicateSubmit,
  retryActionLabel,
  retryableFailedIndices,
  sameQuery,
  searchFailureTitle,
  searchScope,
  stoppedCount,
} from "../lib/requestState";
import { Elapsed, ErrorBlock, errorInfo, useNow } from "./common";
import { FrameViewer, type FrameSlot } from "./FrameViewer";
import { Notebook } from "./Notebook";
import { PageHeading } from "./PageHeading";

type Phase =
  | { kind: "idle" }
  | { kind: "searching"; query: ValidQuery; startedAt: number }
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
  // The notebook's position: the results on screen, or, before any search has
  // succeeded, the position in the opened link. A failed or unfinished search
  // never switches it, so saved notes stay visible while the archive is down.
  const [notesQuery, setNotesQuery] = useState<ValidQuery | null>(null);
  // Search requests and frame requests have separate generations, so frames
  // of the results on screen can still be retried after a search fails or is
  // cancelled. One limiter caps every frame request at FRAME_CONCURRENCY.
  const searchGate = useRef(createRequestGate());
  const frameGate = useRef(createRequestGate());
  const limiter = useRef(createLimiter(FRAME_CONCURRENCY));
  const inFlight = useRef<ValidQuery | null>(null);
  const onQueryChange = useRef(props.onQueryChange);
  onQueryChange.current = props.onQueryChange;
  const fieldRefs = useRef<Partial<Record<keyof QueryInput, HTMLInputElement | null>>>({});

  const patchSlot = (i: number, patch: Partial<FrameSlot>) =>
    setSlots((prev) => prev.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const cacheKey = (key: string) => `${api.mode}:${key}`;

  const loadFrame = useCallback(
    async (ticketId: number, signal: AbortSignal, i: number, token: string, key: string) => {
      const live = () => frameGate.current.isCurrent(ticketId);
      const cached = frameCache.get(cacheKey(key));
      if (cached) {
        if (live()) patchSlot(i, { status: "ready", frame: cached, error: null, startedAt: null });
        return;
      }
      if (live()) patchSlot(i, { status: "pending", error: null, startedAt: null });
      try {
        const frame = await limiter.current.run(() => {
          if (live()) patchSlot(i, { status: "loading", startedAt: Date.now() });
          return api.frame(token, signal);
        }, signal);
        frameCache.set(cacheKey(key), frame);
        if (live()) patchSlot(i, { status: "ready", frame, error: null, startedAt: null });
      } catch (err) {
        if (isAbortError(err) || !live()) return;
        patchSlot(i, { status: "error", error: errorInfo(err), startedAt: null });
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [api, frameCache],
  );

  const runSearch = useCallback(
    async (query: ValidQuery) => {
      const ticket = searchGate.current.begin();
      inFlight.current = query;
      setPhase({ kind: "searching", query, startedAt: Date.now() });
      // Frames of the previous search that never finished are stopped; they
      // stay retryable in case this search fails and those results remain.
      frameGate.current.cancel();
      setSlots((prev) =>
        prev.map((s) =>
          s.status === "pending" || s.status === "loading"
            ? {
                ...s,
                status: "error",
                startedAt: null,
                error: { code: "SUPERSEDED", message: "Stopped when a newer search started.", retryable: true },
              }
            : s,
        ),
      );
      try {
        const response = await api.search(query, ticket.signal);
        if (!searchGate.current.isCurrent(ticket.id)) return;
        inFlight.current = null;
        const frames = frameGate.current.begin();
        setPhase({ kind: "searched", query });
        setShown({ query, response });
        setNotesQuery(query);
        // The link follows the results on screen, so a reload during an
        // archive outage reopens the position whose notes were being written.
        onQueryChange.current(query);
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
          (o, i) => loadFrame(frames.id, frames.signal, i, o.frame_token, o.frame_key ?? o.observation_id),
          frames.signal,
        );
      } catch (err) {
        if (isAbortError(err) || !searchGate.current.isCurrent(ticket.id)) return;
        inFlight.current = null;
        setPhase({ kind: "failed", query, error: err });
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [api, frameCache, loadFrame],
  );

  /** Every search start goes through here: a repeat of the one in flight is ignored. */
  const startSearch = (query: ValidQuery) => {
    if (isDuplicateSubmit(inFlight.current, query)) return;
    void runSearch(query);
  };

  const submit = (e?: FormEvent): ValidQuery | null => {
    e?.preventDefault();
    const v = validateQuery(input);
    if (!v.ok) {
      setErrors(v.errors);
      setNotices([]);
      const first = (["ra", "dec", "fov", "limit"] as const).find((k) => v.errors[k]);
      if (first) fieldRefs.current[first]?.focus();
      return null;
    }
    setErrors({});
    setNotices(v.notices);
    if (v.value.ra_deg !== Number(input.ra)) setInput((p) => ({ ...p, ra: String(v.value.ra_deg) }));
    startSearch(v.value);
    return v.value;
  };

  const cancelSearch = () => {
    searchGate.current.cancel();
    inFlight.current = null;
    setPhase({ kind: "idle" });
  };

  // Run once when opened from a shared coordinate link. The cleanup cancels
  // in-flight work on unmount; under StrictMode's mount/unmount/mount the
  // second mount simply starts the search again.
  useEffect(() => {
    if (props.initial.ra && props.initial.dec) {
      const q = submit();
      if (q) setNotesQuery((prev) => prev ?? q);
    }
    const s = searchGate.current;
    const f = frameGate.current;
    return () => {
      s.cancel();
      f.cancel();
      inFlight.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Retries frames of the results on screen, in order, within the shared limit. */
  const retryFrames = (indices: number[]) => {
    const obs = shown?.response.observations;
    if (!obs || !indices.length) return;
    const ticket = frameGate.current.active() ?? frameGate.current.begin();
    void runWithConcurrency(
      indices,
      FRAME_CONCURRENCY,
      (i) => {
        const o = obs[i];
        return o ? loadFrame(ticket.id, ticket.signal, i, o.frame_token, o.frame_key ?? o.observation_id) : Promise.resolve();
      },
      ticket.signal,
    );
  };
  const retryFrame = (i: number) => retryFrames([i]);

  // Notes belong to the notebook's position, so a failed new search never hides them.
  const q = notesQuery;
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
  const failedIdx = retryableFailedIndices(slots);
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
        // iOS decimal/numeric keypads have no minus sign; declination is often negative.
        inputMode={numeric ? "numeric" : key === "dec" ? undefined : "decimal"}
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
      <div className={`workspace${notesQuery ? "" : " single"}`}>
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
                <button type="button" onClick={cancelSearch}>
                  Cancel search
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
                  : shown.response.status === "partial" && shown.response.observations.length === 0
                    ? "Search incomplete: part of the archive could not be searched."
                    : `Search finished${shown.response.status === "partial" ? " with partial results" : ""}: ${
                        shown.response.returned_count
                      } observations. Frames are processing.`
                : phase.kind === "failed"
                  ? "The search failed."
                  : ""}
          </p>

          {phase.kind === "searching" && <SearchProgress query={phase.query} startedAt={phase.startedAt} />}
          {phase.kind === "failed" && (
            <ErrorBlock
              title={searchFailureTitle(errorInfo(phase.error).code)}
              error={phase.error}
              onRetry={() => startSearch(phase.query)}
              onUseFixture={api.mode === "api" ? props.onUseFixture : undefined}
            />
          )}
          {showingOld && shown && (
            <p className="notice" role="note">
              Still showing the previous images and notes, from {describe(shown.query)}.
            </p>
          )}
          {!shown && notesQuery && phase.kind === "failed" && (
            <p className="notice" role="note">
              Your notes for {describe(notesQuery)} are kept. Images appear once the search succeeds.
            </p>
          )}
          {shown && !showingOld && (
            <SearchSummary
              response={shown.response}
              counts={counts}
              failedIdx={failedIdx}
              stopped={stoppedCount(slots)}
              retryLabel={retryActionLabel(slots, failedIdx)}
              onRetryFailed={() => retryFrames(failedIdx)}
              onJump={setIndex}
              onSearchAgain={() => startSearch(shown.query)}
            />
          )}
          {expired && phase.kind === "searched" && shown && (
            <div className="notice" role="alert">
              <p>This search has expired. Run it again to continue; your notes are kept.</p>
              <button type="button" onClick={() => startSearch(shown.query)}>
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

        {notesQuery && (
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

/** Search progress with elapsed time; after a few seconds it says why it may be slow. */
function SearchProgress({ query, startedAt }: { query: ValidQuery; startedAt: number }) {
  const now = useNow(true);
  return (
    <div className="status">
      <p>
        Searching the archive for {describe(query)}… <Elapsed since={startedAt} />
      </p>
      {now - startedAt >= SLOW_SEARCH_MS && (
        <p>
          The NASA/IPAC archive is slow to answer right now. Perigee stops waiting after{" "}
          {Math.round(SEARCH_TIMEOUT_MS / 1000)} seconds; you can cancel sooner.
        </p>
      )}
    </div>
  );
}

function SearchSummary({
  response,
  counts,
  failedIdx,
  stopped,
  retryLabel,
  onRetryFailed,
  onJump,
  onSearchAgain,
}: {
  response: SearchResponse;
  counts: Record<FrameSlot["status"], number>;
  failedIdx: number[];
  /** Frames stopped by a newer search that was then cancelled or failed. */
  stopped: number;
  retryLabel: string;
  onRetryFailed: () => void;
  onJump: (i: number) => void;
  onSearchAgain: () => void;
}) {
  const { answered, failed } = searchScope(response);
  const scope = answered.length ? answered.join(", ") : "the supported collections";
  // The partial notice below names the failed collections; skip the API's copy of that sentence.
  const warnings = failed.length
    ? response.warnings.filter((w) => !w.startsWith("Some collections could not be searched"))
    : response.warnings;
  if (response.status === "partial" && response.observations.length === 0) {
    return (
      <div className="notice" role="note">
        <p>
          <strong>No images from {scope}, and {failed.length ? failed.join(", ") : "part of the archive"} could not be
          searched.</strong>{" "}
          This is an incomplete answer, not a result about the sky.
        </p>
        <button type="button" onClick={onSearchAgain}>
          Search again
        </button>
      </div>
    );
  }
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
        processing · {counts.pending} waiting · {counts.error - stopped} failed
        {stopped ? ` · ${stopped} stopped by a newer search` : ""}.
      </p>
      {failedIdx.length > 0 && (
        <div className="actions">
          <button type="button" onClick={onRetryFailed}>
            {retryLabel}
          </button>
          <span className="counter">
            Not loaded:{" "}
            {failedIdx.map((i, n) => (
              <span key={i}>
                {n > 0 && ", "}
                <button type="button" className="link" onClick={() => onJump(i)} aria-label={`Show frame ${i + 1}`}>
                  #{i + 1}
                </button>
              </span>
            ))}
          </span>
        </div>
      )}
      {response.status === "partial" && (
        <div className="notice">
          <p>
            Partial results: {failed.length ? failed.join(", ") : "part of the archive"} could not be searched, so some
            images may be missing.
          </p>
          <button type="button" onClick={onSearchAgain}>
            Search again
          </button>
        </div>
      )}
      {warnings.length > 0 && (
        <ul className="plain-list">
          {warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
