// What "My evidence" lists: the stored cards plus this tab's drafts that the
// browser refused to store (marked unsaved).
//
// Read it twice on the home view. The first read happens while Home renders.
// That can be before the investigation being left has saved its last edit,
// because useEvidenceCard writes a pending (debounced) edit in its unmount
// cleanup, which React runs after the new view renders. A read at that point
// sees the newer session draft and an older stored copy, and would wrongly say
// "not saved on this device". Home reads again in a mount effect, which React
// runs after unmount cleanups in the same commit. A write that really failed
// still shows as unsaved, because the stored copy stays older than the draft.

import { listCards, loadStore, sessionDrafts, type DraftMemory, type EvidenceStore } from "./card";

type StorageLike = Pick<Storage, "getItem" | "setItem">;

export function readSavedList(
  storage: StorageLike | null,
  memory: DraftMemory = sessionDrafts,
): { store: EvidenceStore; cards: ReturnType<typeof listCards> } {
  const store = loadStore(storage);
  return { store, cards: listCards(store, memory) };
}
