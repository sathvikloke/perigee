import { describe, expect, it } from "vitest";
import {
  createEvidenceCard,
  persistStore,
  updateEvidenceText,
  upsertCard,
  loadStore,
  type DraftMemory,
} from "../src/evidence/card";
import { presetContextKey } from "../src/evidence/reopen";
import { readSavedList } from "../src/evidence/savedList";

/** In-memory localStorage that can be told to refuse writes (quota, private mode). */
function fakeStorage() {
  const data = new Map<string, string>();
  let refuse = false;
  return {
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => {
      if (refuse) throw new Error("QuotaExceededError");
      data.set(k, v);
    },
    refuseWrites: () => (refuse = true),
  };
}

const KEY = presetContextKey("api", "epsilon_indi_b");
const T0 = new Date("2026-11-14T18:00:00.000Z");
const T1 = new Date("2026-11-14T18:00:05.000Z");

/**
 * Leaving an investigation inside the save debounce: the edit is already in
 * this tab's session drafts (useEvidenceCard.update), Home renders, and only
 * then does the investigation's unmount cleanup write the edit (flush).
 */
function editThenLeaveBeforeDebounce(storage: ReturnType<typeof fakeStorage>, memory: DraftMemory) {
  const saved = updateEvidenceText(
    createEvidenceCard({ preset_id: "epsilon_indi_b", case_id: "fair_comparison", app_version: "t", data_origin: "api", now: T0 }),
    "claim",
    "first claim",
    T0,
  );
  persistStore(storage, upsertCard(loadStore(storage), KEY, saved));
  memory.set(KEY, saved);

  const edited = updateEvidenceText(saved, "claim", "edited claim", T1);
  memory.set(KEY, edited); // update(): session copy first, write debounced
  const whileRendering = readSavedList(storage, memory); // Home's first render
  const wrote = persistStore(storage, upsertCard(loadStore(storage), KEY, edited)); // unmount flush
  const afterCleanup = readSavedList(storage, memory); // Home's mount effect
  return { whileRendering, wrote, afterCleanup };
}

describe("My evidence after leaving an investigation before the save debounce", () => {
  it("shows the edit as saved once the cleanup save has run", () => {
    const storage = fakeStorage();
    const { whileRendering, wrote, afterCleanup } = editThenLeaveBeforeDebounce(storage, new Map());
    // The first read cannot see the pending write yet (the reported symptom).
    expect(whileRendering.cards[0]).toMatchObject({ unsaved: true });
    expect(wrote).toBe(true);
    expect(afterCleanup.cards).toHaveLength(1);
    expect(afterCleanup.cards[0].card.claim).toBe("edited claim");
    expect(afterCleanup.cards[0].unsaved).toBe(false);
    // Matches what a reload of Home shows.
    expect(readSavedList(storage, new Map()).cards[0]).toMatchObject({ unsaved: false, card: { claim: "edited claim" } });
  });

  it("still warns when the browser refused the write", () => {
    const storage = fakeStorage();
    const memory: DraftMemory = new Map();
    const first = updateEvidenceText(
      createEvidenceCard({ preset_id: "epsilon_indi_b", case_id: "fair_comparison", app_version: "t", data_origin: "api", now: T0 }),
      "claim",
      "first claim",
      T0,
    );
    persistStore(storage, upsertCard(loadStore(storage), KEY, first));
    const edited = updateEvidenceText(first, "claim", "edited claim", T1);
    memory.set(KEY, edited);
    storage.refuseWrites();
    expect(persistStore(storage, upsertCard(loadStore(storage), KEY, edited))).toBe(false);
    const after = readSavedList(storage, memory);
    expect(after.cards).toHaveLength(1);
    expect(after.cards[0]).toMatchObject({ unsaved: true, card: { claim: "edited claim" } });
  });
});
