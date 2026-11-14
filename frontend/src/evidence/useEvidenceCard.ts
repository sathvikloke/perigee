import { useCallback, useEffect, useRef, useState } from "react";
import type { FrameRecord } from "../api/types";
import type { SaveState } from "../components/EvidencePanel";
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

  const [card, setCard] = useState<EvidenceCard>(() => initial(contextKey, makeCard));
  const [saveState, setSaveState] = useState<SaveState>({ kind: "idle" });
  const timer = useRef<number | null>(null);
  const pending = useRef<EvidenceCard | null>(null);

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
    setCard(initial(contextKey, makeRef.current));
    setSaveState({ kind: "idle" });
    return () => flush();
  }, [contextKey, flush]);

  const update = useCallback(
    (next: EvidenceCard) => {
      setCard(next);
      pending.current = next;
      if (timer.current !== null) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(flush, SAVE_DEBOUNCE_MS);
    },
    [flush],
  );

  const toggleFrame = useCallback(
    (frame: FrameRecord, ref: string | null) => update(toggleEvidenceFrame(card, frame, ref)),
    [card, update],
  );

  const removeFrame = useCallback(
    (frameKey: string) =>
      update({
        ...card,
        frames: card.frames.filter((f) => f.frame_key !== frameKey),
        updated_at_utc: new Date().toISOString(),
      }),
    [card, update],
  );

  return { card, update, toggleFrame, removeFrame, saveState };
}

function initial(contextKey: string, makeCard: () => EvidenceCard): EvidenceCard {
  const store = loadStore(browserStorage());
  const id = store.contexts[contextKey];
  return (id && store.cards.find((c) => c.id === id)) || makeCard();
}
