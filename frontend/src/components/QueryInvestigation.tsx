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
import type { FrameRecord, SearchResponse, ResolvedObject } from "../api/types";
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
  frameProcessingAnnouncement,
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
import { frameCacheKey, rememberFrame } from "../lib/frameCache";
import { recoverFrame } from "../lib/frameRecovery";
import "../styles/archive-motion.css";
import { useContentCue } from "../lib/contentMotion";
import "../styles/content-motion.css";

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

/** A failed live search can be retried without replacing the current results or notebook. */
export function SearchFailureRecovery(props: { error: unknown; onRetry: () => void; onUseFixture?: () => void }) {
  return <>
    <ErrorBlock title={searchFailureTitle(errorInfo(props.error).code)} error={props.error}
      onRetry={props.onRetry} onUseFixture={props.onUseFixture} />
    <p className="notice">You can also explore the prepared cases: <a href="/#investigations">Open prepared NASA investigations</a>.</p>
  </>;
}

export function QueryInvestigation(props: {
  api: PerigeeApi;
  initial: { ra?: string; dec?: string; fov?: string; limit?: string; caseId?: string };
  frameCache: Map<string, FrameRecord>;
  onQueryChange: (q: ValidQuery) => void;
  onUseFixture?: () => void;
}) {
  const pageArrival = useContentCue<HTMLDivElement>("heading", "search", ".heading-copy");
  const { api, frameCache } = props;
  const id = useId();
  const [input, setInput] = useState<QueryInput>({
    ra: props.initial.ra ?? "",
    dec: props.initial.dec ?? "",
    fov: props.initial.fov ?? String(FOV_DEFAULT),
    limit: props.initial.limit ?? String(LIMIT_DEFAULT),
  });
  const [errors, setErrors] = useState<QueryErrors>({});
  const [searchMode, setSearchMode] = useState<"name" | "coordinates">(api.resolveName && !props.initial.ra ? "name" : "coordinates");
  const [objectName, setObjectName] = useState("");
  const [resolving, setResolving] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [resolved, setResolved] = useState<ResolvedObject | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [openNotebookFor, setOpenNotebookFor] = useState<string | null>(null);
  const lookupGate = useRef(createRequestGate());
  const lookupName = useRef<string | null>(null);
  const [notices, setNotices] = useState<string[]>([]);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [shown, setShown] = useState<Shown | null>(null);
  const [slots, setSlots] = useState<FrameSlot[]>([]);
  const [index, setIndex] = useState(0);
  const selectFirstReady = useRef(true);
  const [motionPaused, setMotionPaused] = useState(false);
  const queryFormRef = useRef<HTMLFormElement>(null);
  useEffect(() => {
    let inView = true;
    const update = () => setMotionPaused(document.hidden || !inView);
    const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(([entry]) => {
      inView = entry.isIntersecting;
      update();
    });
    if (queryFormRef.current) observer?.observe(queryFormRef.current);
    update();
    document.addEventListener("visibilitychange", update);
    return () => { observer?.disconnect(); document.removeEventListener("visibilitychange", update); };
  }, []);
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
  const frameLoads = useRef(new Set<string>());
  const inFlight = useRef<ValidQuery | null>(null);
  const onQueryChange = useRef(props.onQueryChange);
  onQueryChange.current = props.onQueryChange;
  const fieldRefs = useRef<Partial<Record<keyof QueryInput, HTMLInputElement | null>>>({});
  const nameRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const first = (["ra", "dec", "fov", "limit"] as const).find((k) => errors[k]);
    if (first) fieldRefs.current[first]?.focus();
  }, [errors]);

  const patchSlot = (i: number, patch: Partial<FrameSlot>) =>
    setSlots((prev) => prev.map((s, j) => (j === i ? { ...s, ...patch } : s)));

  const loadFrame = useCallback(
    async (ticketId: number, signal: AbortSignal, i: number, token: string, key: string, query: ValidQuery) => {
      const live = () => frameGate.current.isCurrent(ticketId);
      const identity = frameCacheKey(api.mode, key, token, query);
      const cached = frameCache.get(identity);
      if (cached) {
        if (live()) patchSlot(i, { status: "ready", frame: cached, error: null, startedAt: null });
        return;
      }
      const loadKey = `${ticketId}:${i}`;
      if (frameLoads.current.has(loadKey)) return;
      frameLoads.current.add(loadKey);
      if (live()) patchSlot(i, { status: "pending", error: null, startedAt: null, retryAttempt: 0 });
      try {
        const frame = await recoverFrame(() => limiter.current.run(() => {
          if (live()) patchSlot(i, { status: "loading", startedAt: Date.now() });
          return api.frame(token, signal);
        }, signal), signal, (retryAttempt) => {
          if (live()) patchSlot(i, { status: "loading", retryAttempt });
        });
        rememberFrame(frameCache, identity, frame);
        if (live()) patchSlot(i, { status: "ready", frame, error: null, startedAt: null, retryAttempt: 0 });
      } catch (err) {
        if (isAbortError(err) || !live()) return;
        patchSlot(i, { status: "error", error: errorInfo(err), startedAt: null });
      } finally {
        frameLoads.current.delete(loadKey);
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
        selectFirstReady.current = true;
        setSlots(
          response.observations.map((o) => {
            const key = o.frame_key ?? o.observation_id;
            const cached = frameCache.get(frameCacheKey(api.mode, key, o.frame_token, query));
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
          (o, i) => loadFrame(frames.id, frames.signal, i, o.frame_token, o.frame_key ?? o.observation_id, query),
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

  const submitCoordinates = (): ValidQuery | null => {
    const v = validateQuery(input);
    if (!v.ok) {
      if (v.errors.fov || v.errors.limit) setAdvancedOpen(true);
      setErrors(v.errors);
      setNotices([]);
      return null;
    }
    setErrors({});
    setNotices(v.notices);
    setInput((p) => ({ ...p, ra: String(v.value.ra_deg), dec: String(v.value.dec_deg) }));
    startSearch(v.value);
    return v.value;
  };

  const cancelLookup = () => {
    lookupGate.current.cancel();
    lookupName.current = null;
    setResolving(false);
  };

  const searchByName = async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) {
      setLookupError("Enter an object name, or try Barnard’s Star below.");
      nameRef.current?.focus();
      return;
    }
    if (lookupName.current === trimmed) return;
    const options = validateQuery({ ...input, ra: "0", dec: "0" });
    if (!options.ok) {
      setAdvancedOpen(true);
      setErrors(options.errors);
      return;
    }
    if (!api.resolveName) return;
    const ticket = lookupGate.current.begin();
    lookupName.current = trimmed;
    searchGate.current.cancel();
    frameGate.current.cancel();
    inFlight.current = null;
    setSlots((prev) => prev.map((s) => s.status === "pending" || s.status === "loading"
      ? { ...s, status: "error", startedAt: null, error: { code: "SUPERSEDED", message: "Stopped when a newer search started.", retryable: true } }
      : s));
    setPhase({ kind: "idle" });
    setResolving(true);
    setLookupError(null);
    setResolved(null);
    setErrors({});
    setNotices([]);
    try {
      const object = await api.resolveName(trimmed, ticket.signal);
      if (!lookupGate.current.isCurrent(ticket.id)) return;
      setResolved(object);
      const query = { ...options.value, ra_deg: object.search_center.ra_deg, dec_deg: object.search_center.dec_deg };
      setInput((p) => ({ ...p, ra: String(query.ra_deg), dec: String(query.dec_deg) }));
      startSearch(query);
    } catch (error) {
      if (isAbortError(error) || !lookupGate.current.isCurrent(ticket.id)) return;
      setLookupError(errorInfo(error).code === "OBJECT_NOT_FOUND"
        ? "That name wasn’t found. Check its spelling or choose Enter coordinates."
        : "Object lookup isn’t available right now. Try again or choose Enter coordinates.");
    } finally {
      if (lookupGate.current.isCurrent(ticket.id)) {
        lookupName.current = null;
        setResolving(false);
      }
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (searchMode === "name") void searchByName(objectName);
    else {
      cancelLookup();
      setLookupError(null);
      setResolved(null);
      submitCoordinates();
    }
  };

  const cancelSearch = () => {
    cancelLookup();
    searchGate.current.cancel();
    inFlight.current = null;
    setPhase({ kind: "idle" });
  };

  // Run once when opened from a shared coordinate link. The cleanup cancels
  // in-flight work on unmount; under StrictMode's mount/unmount/mount the
  // second mount simply starts the search again.
  useEffect(() => {
    if (props.initial.ra && props.initial.dec) {
      const q = submitCoordinates();
      if (q) setNotesQuery((prev) => prev ?? q);
    }
    const s = searchGate.current;
    const f = frameGate.current;
    const lookup = lookupGate.current;
    return () => {
      lookup.cancel();
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
        return o && shown ? loadFrame(ticket.id, ticket.signal, i, o.frame_token, o.frame_key ?? o.observation_id, shown.query) : Promise.resolve();
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
        // A live coordinate query is not the authored case, even at the same position.
        case_id: null,
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
  const cardMatchesQuery = q && ev.card.query?.ra_deg === q.ra_deg && ev.card.query?.dec_deg === q.dec_deg && ev.card.query?.fov_arcmin === q.fov_arcmin;
  const hasSavedWork = ev.card.frames.length > 0 || Boolean(ev.card.claim.trim() || ev.card.observations.trim() || ev.card.uncertainty.trim());
  const notebookVisible = Boolean(notesQuery && (openNotebookFor === contextKey || (cardMatchesQuery && hasSavedWork)));
  const chooseFrame = (next: number) => { selectFirstReady.current = false; setIndex(next); };

  const counts = slots.reduce(
    (acc, s) => ({ ...acc, [s.status]: acc[s.status] + 1 }),
    { pending: 0, loading: 0, ready: 0, error: 0 } as Record<FrameSlot["status"], number>,
  );
  useEffect(() => {
    if (!selectFirstReady.current) return;
    const readyIndex = slots.findIndex((s) => s.status === "ready" && s.frame);
    if (readyIndex >= 0) { selectFirstReady.current = false; setIndex(readyIndex); }
  }, [slots]);
  const processing = counts.pending + counts.loading > 0;
  const busy = resolving || phase.kind === "searching" || processing;
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
        inputMode={numeric ? "numeric" : key === "fov" ? "decimal" : undefined}
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
      <div className="content-page-arrival" ref={pageArrival}>
      <PageHeading
        eyebrow="SPHEREx investigation"
        eyebrowDetail="Any sky position"
        title="Find images of a patch of sky"
        intro="Start with an object name or a sky position. Then compare the observations you find."
        mode={api.mode}
      />
      </div>
      <div className={`workspace${notebookVisible ? "" : " single"}`}>
        <section className="bench" id="observations" tabIndex={-1} aria-label="Coordinate search">
          <form ref={queryFormRef} className="comparison-shell query-form" data-motion-paused={motionPaused} onSubmit={submit} noValidate aria-label="Sky position">
            {api.resolveName && <div className="search-method" role="group" aria-label="Search by">
              <button type="button" aria-pressed={searchMode === "name"} onClick={() => { cancelLookup(); setLookupError(null); setSearchMode("name"); }}>Object name</button>
              <button type="button" aria-pressed={searchMode === "coordinates"} onClick={() => { cancelLookup(); setLookupError(null); setSearchMode("coordinates"); }}>Enter coordinates</button>
            </div>}
            {searchMode === "name" ? <div className="field object-name-field">
              <label htmlFor={`${id}-object`}>Object name</label>
              <input id={`${id}-object`} ref={nameRef} type="text" value={objectName} maxLength={80} autoComplete="off" spellCheck={false}
                placeholder="For example, Barnard’s Star" aria-describedby={`${id}-name-help${lookupError ? ` ${id}-name-error` : ""}`} aria-invalid={lookupError ? true : undefined}
                onChange={(e) => { cancelLookup(); setLookupError(null); setObjectName(e.target.value); }} />
              <p className="field-hint" id={`${id}-name-help`}>We’ll look up its position in SIMBAD, then search SPHEREx.</p>
              {lookupError && <p className="field-error" id={`${id}-name-error`} role="alert">{lookupError}</p>}
            </div> : <div className="query-fields coordinate-fields">
              {field("ra", "Right ascension (RA)", "Degrees or HH:MM:SS, such as 269.4463 or 17:57:47.1.")}
              {field("dec", "Declination (Dec)", "Degrees or ±DD:MM:SS, such as +4.7683 or +04:46:06.")}
            </div>}
            <details className="search-advanced" open={advancedOpen} onToggle={(e) => setAdvancedOpen(e.currentTarget.open)}>
              <summary>Search options <span>{input.fov || FOV_DEFAULT}′ field, up to {input.limit || LIMIT_DEFAULT} images</span></summary>
              <div className="query-fields coordinate-fields">
                {field("fov", "Image width", `${FOV_MIN}–${FOV_MAX} arcminutes. Changes the cutout size, not which observations cover the center.`)}
                {field("limit", "Maximum images", `${LIMIT_MIN}–${LIMIT_MAX}. Start with ${LIMIT_DEFAULT} to keep loading manageable.`, true)}
              </div>
              <p className="field-hint">Coordinates use the ICRS sky reference system. Images are selected across the available dates.</p>
            </details>
            <div className="actions">
              <button type="submit" className="primary archive-search-button" aria-busy={busy} data-busy={busy}>
                <SearchIcon busy={busy} />
                <span>{resolving || phase.kind === "searching" ? "Searching…" : processing ? "Loading images…" : "Search the archive"}</span>
              </button>
              {api.resolveName && !busy && <button type="button" className="search-example" onClick={() => {
                setSearchMode("name"); setObjectName("Barnard’s Star"); void searchByName("Barnard's Star");
              }}>Try Barnard’s Star <span aria-hidden="true">↗</span></button>}
              {(resolving || phase.kind === "searching") && (
                <button type="button" onClick={cancelSearch}>
                  Cancel search
                </button>
              )}
            </div>
            {resolving && <p className="lookup-status" role="status">Finding the object’s sky position…</p>}
            {resolved && <details className="resolved-position">
              <summary>{resolved.name}, {resolved.search_center.kind === "finder_prediction" ? `${resolved.search_center.epoch_jyear.toFixed(0)} finder position` : `catalog epoch ${resolved.search_center.epoch_jyear.toFixed(0)}`}</summary>
              <p>{resolved.note}</p>
              <p>Search center: RA {resolved.search_center.ra_deg.toFixed(6)}°, Dec {resolved.search_center.dec_deg.toFixed(6)}° (epoch {resolved.search_center.epoch_jyear.toFixed(1)}).</p>
              <p>Catalog: RA {resolved.catalog_position.ra_deg.toFixed(6)}°, Dec {resolved.catalog_position.dec_deg.toFixed(6)}° (epoch {resolved.catalog_position.epoch_jyear.toFixed(1)}). <a href={resolved.source_url} target="_blank" rel="noreferrer">{resolved.source}</a></p>
            </details>}
            {phase.kind === "searching" && <SearchProgress query={phase.query} startedAt={phase.startedAt} />}
            {processing && <div className="archive-progress frame-progress">
              <div className="archive-progress-heading"><SearchIcon busy /><div><strong>Loading observation images</strong><p>{counts.ready} of {slots.length} ready{counts.error ? `, ${counts.error} could not be processed` : ""}</p></div></div>
              <progress aria-label="Images ready" value={counts.ready} max={slots.length} />
            </div>}
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
                      } observation${shown.response.returned_count === 1 ? "" : "s"}. ${frameProcessingAnnouncement(counts)}`
                : phase.kind === "failed"
                  ? "The search failed."
                  : ""}
          </p>

          {phase.kind === "failed" && (
            <SearchFailureRecovery
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
              onJump={chooseFrame}
              firstReadyIndex={slots.findIndex((s) => s.status === "ready" && s.frame?.image)}
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
            <div id="query-results" tabIndex={-1} className="query-image-results">
            <FrameViewer
              title={`Results in time order`}
              description={shown ? describe(shown.query) : undefined}
              slots={slots}
              index={Math.min(index, slots.length - 1)}
              onIndexChange={chooseFrame}
              selectedKeys={selected}
              onToggleEvidence={(frame, ref) => { setOpenNotebookFor(contextKey); ev.toggleFrame(frame, ref); }}
              onRetry={retryFrame}
              blinkTool
            />
            </div>
          )}
          {notesQuery && counts.ready > 0 && !notebookVisible && <div className="query-record-entry">
            <p>Use <strong>Attach this frame to notebook</strong> on an image to keep it with your notes.</p>
            <button type="button" onClick={() => setOpenNotebookFor(contextKey)}>Record findings</button>
          </div>}
        </section>

        {notesQuery && (
          <div hidden={!notebookVisible} className="query-notebook">
          <Notebook
            card={ev.card}
            previewFrames={slots.flatMap((slot) => slot.frame ? [slot.frame] : [])}
            onChange={ev.update}
            onRemoveFrame={ev.removeFrame}
            saveState={ev.saveState}
          />
          </div>
        )}
      </div>
    </>
  );
}

/** Search progress with elapsed time; after a few seconds it says why it may be slow. */
function SearchIcon({ busy = false }: { busy?: boolean }) {
  return <svg className={`archive-search-icon${busy ? " is-searching" : ""}`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <circle className="search-orbit" cx="10.5" cy="10.5" r="6.5" stroke="currentColor" strokeWidth="1.6" />
    <path className="search-handle" d="m15.5 15.5 5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <path className="search-sweep" d="M10.5 4a6.5 6.5 0 0 1 6.5 6.5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
  </svg>;
}

function SearchProgress({ query, startedAt }: { query: ValidQuery; startedAt: number }) {
  const now = useNow(true);
  return (
    <div className="archive-progress">
      <div className="archive-progress-heading">
        <SearchIcon busy />
        <div><strong>Searching the SPHEREx archive</strong><p>{describe(query)}</p></div>
        <Elapsed since={startedAt} />
      </div>
      <div className="archive-scan" aria-hidden="true"><span /></div>
      {now - startedAt >= SLOW_SEARCH_MS && (
        <p>
          Still waiting for the search response. Perigee stops waiting after{" "}
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
  firstReadyIndex,
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
  firstReadyIndex: number;
  onSearchAgain: () => void;
}) {
  const { answered, failed } = searchScope(response);
  const readyCue = useContentCue<HTMLSpanElement>("ready", counts.ready);
  const capped = response.collections_capped ?? [];
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
        <p><strong>No SPHEREx images cover this position in the searched collections.</strong> Try another object or check your coordinates. This does not describe other missions’ coverage.</p>
      </div>
    );
  }
  return (
    <div className="status archive-results">
      <p>
        <strong>
          {response.returned_count} observation{response.returned_count === 1 ? "" : "s"} found
        </strong>.{" "}
        <span className="ready-result-count" ref={readyCue}>{counts.ready} ready</span>{counts.pending + counts.loading ? `, ${counts.pending + counts.loading} loading` : ""}
        {counts.error - stopped > 0 ? `, ${counts.error - stopped} couldn’t load` : ""}
        {stopped ? `, ${stopped} stopped by a newer search` : ""}.
      </p>
      {firstReadyIndex >= 0 && <a className="first-image-link" href="#query-results" onClick={() => onJump(firstReadyIndex)}>View first ready image <span aria-hidden="true">↓</span></a>}
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
      {response.status === "partial" && (failed.length > 0 || capped.length === 0) && (
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
      <details className="search-coverage">
        <summary>Search coverage and details</summary>
        <p>Collections: {scope}.{response.total_matches != null ? ` ${response.total_matches} matching observations.` : ""}
          {response.truncated && response.total_matches != null && response.total_matches > response.returned_count ? " Showing a selection across dates, limited by Maximum images." : ""}</p>
        {warnings.length > 0 && <ul className="plain-list">{warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
      </details>
    </div>
  );
}
