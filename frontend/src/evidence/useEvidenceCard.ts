import { useCallback, useEffect, useRef, useState } from "react";
import type { FrameRecord } from "../api/types";
import type { SaveState } from "../components/Notebook";
import {
  browserStorage,
  loadStore,
  persistStore,
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
  const [saveState, setSaveState] = useState<SaveState>(restored ? { kind: "restored" } : { kind: "idle" });
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
    setSaveState(next.restored ? { kind: "restored" } : { kind: "idle" });
    return () => flush();
  }, [contextKey, flush]);

  const update = useCallback(
    (next: EvidenceCard) => {
      if (next === cardRef.current) return;
      setLoaded({ card: next, restored: false });
      pending.current = next;
      if (timer.current !== null) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(flush, SAVE_DEBOUNCE_MS);
    },
    [flush],
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

function initial(contextKey: string, makeCard: () => EvidenceCard): { card: EvidenceCard; restored: boolean } {
  const store = loadStore(browserStorage());
  const id = store.contexts[contextKey];
  const found = id ? store.cards.find((c) => c.id === id) : undefined;
  return found ? { card: found, restored: true } : { card: makeCard(), restored: false };
}
