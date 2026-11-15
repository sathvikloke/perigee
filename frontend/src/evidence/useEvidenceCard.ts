import { useCallback, useEffect, useRef, useState } from "react";
import type { FrameRecord } from "../api/types";
import type { SaveState } from "../components/Notebook";
import {
  browserStorage,
  fillCardContext,
  loadStore,
  persistStore,
  resolveDraft,
  sessionDrafts,
  toggleEvidenceFrame,
  upsertCard,
  type EvidenceCard,
} from "./card";

const SAVE_DEBOUNCE_MS = 300;

/**
 * The draft evidence card for one investigation context. Loads the existing
 * draft from localStorage, saves edits (debounced), and keeps the in-memory
 * card intact if storage refuses the write. Network failures never touch it.
 */
export function useEvidenceCard(contextKey: string, makeCard: () => EvidenceCard) {
  const makeRef = useRef(makeCard);
  makeRef.current = makeCard;

  const [{ card, restored }, setLoaded] = useState(() => initial(contextKey, makeCard));
  const [saveState, setSaveState] = useState<SaveState>(initialState(restored));
  const timer = useRef<number | null>(null);
  const pending = useRef<EvidenceCard | null>(null);
  const cardRef = useRef(card);
  cardRef.current = card;

  const flush = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    const c = pending.current;
    if (!c) return;
    pending.current = null;
    const storage = browserStorage();
    const ok = persistStore(storage, upsertCard(loadStore(storage), contextKey, c));
    setSaveState(ok ? { kind: "saved", at: new Date().toISOString() } : { kind: "failed" });
  }, [contextKey]);

  useEffect(() => {
    const next = initial(contextKey, makeRef.current);
    setLoaded(next);
    setSaveState(initialState(next.restored));
    // A stored card from before title/case limitations existed: write the
    // filled-in copy back quietly (same updated_at_utc, learner text
    // untouched) so saved-card lists can show its title. Failure is harmless.
    if (next.filled && next.restored === "storage") {
      const storage = browserStorage();
      persistStore(storage, upsertCard(loadStore(storage), contextKey, next.card));
    }
    // Write a pending edit before the page is hidden or unloaded, so a
    // reload inside the debounce window does not drop the last keystrokes.
    const onHide = () => document.visibilityState === "hidden" && flush();
    window.addEventListener("pagehide", flush);
    document.addEventListener("visibilitychange", onHide);
    return () => {
      window.removeEventListener("pagehide", flush);
      document.removeEventListener("visibilitychange", onHide);
      flush();
    };
  }, [contextKey, flush]);

  const update = useCallback(
    (next: EvidenceCard) => {
      if (next === cardRef.current) return;
      setLoaded({ card: next, restored: false });
      sessionDrafts.set(contextKey, next);
      pending.current = next;
      setSaveState({ kind: "saving" });
      if (timer.current !== null) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(flush, SAVE_DEBOUNCE_MS);
    },
    [flush, contextKey],
  );

  const toggleFrame = useCallback(
    (frame: FrameRecord, ref: string | null) => update(toggleEvidenceFrame(cardRef.current, frame, ref)),
    [update],
  );

  const removeFrame = useCallback(
    (frameKey: string) =>
      update({
        ...cardRef.current,
        frames: cardRef.current.frames.filter((f) => f.frame_key !== frameKey),
        updated_at_utc: new Date().toISOString(),
      }),
    [update],
  );

  return { card, update, toggleFrame, removeFrame, saveState };
}

type Restored = false | "storage" | "memory";

function initial(
  contextKey: string,
  makeCard: () => EvidenceCard,
): { card: EvidenceCard; restored: Restored; filled?: boolean } {
  const found = resolveDraft(contextKey, loadStore(browserStorage()));
  if (!found) return { card: makeCard(), restored: false };
  // Reopened: add a missing title / case limitations the caller now knows.
  const card = fillCardContext(found.card, makeCard());
  return { card, restored: found.source, filled: card !== found.card };
}

/** A draft that only survived in memory was never saved: keep saying so. */
function initialState(restored: Restored): SaveState {
  return restored === "storage" ? { kind: "restored" } : restored === "memory" ? { kind: "failed" } : { kind: "idle" };
}
