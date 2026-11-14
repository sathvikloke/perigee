// Worker 12: series playback (judging finding 2) and evidence export /
// storage-failure hardening. Browser evidence lives in qa/play-export.
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { normalizeFrameRecord } from "../src/api/client";
import type { FrameRecord } from "../src/api/types";
import { FrameViewer, type FrameSlot } from "../src/components/FrameViewer";
import {
  STORAGE_KEY,
  attachPair,
  browserStorage,
  createEvidenceCard,
  forgetDraft,
  listCards,
  loadStore,
  persistStore,
  resolveDraft,
  serializeEvidenceCard,
  toggleEvidenceFrame,
  updateEvidenceText,
  upsertCard,
  validateEvidenceCard,
  type DraftMemory,
} from "../src/evidence/card";
import {
  PLAY_MS,
  PLAY_MS_REDUCED,
  nextPlayableIndex,
  playAnnouncement,
  playCadenceMs,
  playableCount,
  playbackCaveats,
} from "../src/lib/playback";
import { parseRoute, routeToSearch } from "../src/lib/route";

const NOW = new Date("2026-11-14T18:00:00.000Z");
const LATER = new Date("2026-11-14T18:05:00.000Z");

function frame(n: number, opts: { mode?: "shared" | "per_frame"; wl?: number | null } = {}): FrameRecord {
  const obs = `2025W${String(10 + n).padStart(2, "0")}_1B_0001_${n}`;
  return normalizeFrameRecord({
    frame_id: `${obs}_D2`,
    frame_key: `${obs}_D2`,
    observation_id: obs,
    detector: 2,
    collection_id: "spherex_qr2",
    observed_at_utc: `2025-0${(n % 9) + 1}-0${(n % 9) + 1}T01:02:03.456`,
    mjd: 60700 + n * 10,
    source_url: `https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/${obs}/level2_${obs}_D2_spx_l2b-v20-2025-1.fits`,
    wavelength_um: opts.wl === undefined ? 1.1 + n * 0.01 : opts.wl,
    bandwidth_um: 0.03,
    wavelength_location: "Catalog-predicted position",
    image: { src: `/assets/frames/${obs}.png`, width: 128, height: 128, media_type: "image/png" },
    flag_image: null,
    registration: { method: "wcs_reproject_to_shared_grid", grid_id: "g1", orientation: "north_up_east_left" },
    quality: { status: n % 3 === 0 ? "flagged" : "clear", covered: true, valid_aperture_pixels: 9, adverse_aperture_pixels: n % 3 === 0 ? 2 : 0, flag_names: n % 3 === 0 ? ["SOURCE"] : [], notes: null },
    display_scale: { mode: opts.mode ?? "per_frame", method: "asinh_percentile_0.5_99.7" },
    marker: { kind: "catalog_prediction", x: 64, y: 60 },
    // The processor writes `sha256`; the client normalizes it to file_sha256.
    provenance: { sha256: `sha-${n}`, processing_version: "perigee-processor 0.3.0", pipeline_version: "l2b-v20-2025-1" },
    limitations: [],
  });
}

function slot(f: FrameRecord | null, status: FrameSlot["status"] = "ready", key?: string): FrameSlot {
  return {
    key: f?.frame_key ?? key ?? "missing",
    ref: null,
    status,
    frame: f,
    observed_at_utc: f?.observed_at_utc ?? null,
    mjd: f?.mjd ?? null,
    error: null,
  };
}

describe("series playback", () => {
  it("advances over ready frames in order, skipping pending/failed frames and wrapping", () => {
    const slots = [slot(frame(1)), slot(null, "loading", "x"), slot(frame(2)), slot(null, "error", "y"), slot(frame(3))];
    expect(playableCount(slots)).toBe(3);
    expect(nextPlayableIndex(slots, 0)).toBe(2);
    expect(nextPlayableIndex(slots, 2)).toBe(4);
    expect(nextPlayableIndex(slots, 4)).toBe(0);
    // Starting on a placeholder moves to the next ready frame.
    expect(nextPlayableIndex(slots, 1)).toBe(2);
  });

  it("has nothing to play with fewer than two ready frames", () => {
    expect(nextPlayableIndex([slot(frame(1))], 0)).toBe(-1);
    expect(nextPlayableIndex([slot(frame(1)), slot(null, "pending", "p")], 0)).toBe(-1);
    expect(nextPlayableIndex([], 0)).toBe(-1);
  });

  it("plays at about 2 fps, slower under reduced motion", () => {
    expect(playCadenceMs(false)).toBe(PLAY_MS);
    expect(PLAY_MS).toBe(500);
    expect(playCadenceMs(true)).toBe(PLAY_MS_REDUCED);
    expect(PLAY_MS_REDUCED).toBeGreaterThan(PLAY_MS);
  });

  it("carries the per-frame stretch caveat, and the wavelength caveat only when wavelengths differ", () => {
    const perFrame = playbackCaveats([slot(frame(1)), slot(frame(2))]);
    expect(perFrame).toContain("Each frame has its own contrast stretch, so brightness is not directly comparable.");
    expect(perFrame.some((c) => c.includes("wavelength also changes"))).toBe(true);
    const shared = playbackCaveats([slot(frame(1, { mode: "shared", wl: 2 })), slot(frame(2, { mode: "shared", wl: 2 }))]);
    expect(shared).toEqual([]);
  });

  it("announces once with the frame count", () => {
    expect(playAnnouncement(44)).toBe("Playing 44 frames in time order. Use Pause to stop.");
  });

  function render(slots: FrameSlot[]) {
    return renderToStaticMarkup(
      createElement(FrameViewer, {
        slots,
        index: 0,
        onIndexChange: () => {},
        selectedKeys: new Set<string>(),
        onToggleEvidence: () => {},
        title: "All frames in time order",
      }),
    );
  }

  it("offers Play in the stepper, paused on load, with no playing caveat or announcement", () => {
    const html = render([slot(frame(1)), slot(frame(2)), slot(frame(3))]);
    const stepper = html.slice(html.indexOf('class="stepper"'), html.indexOf("Earlier frame"));
    expect(stepper).toMatch(/<button[^>]*class="play-toggle"[^>]*aria-pressed="false"[^>]*aria-disabled="false"[^>]*>▷ Play<\/button>/);
    expect(html).not.toContain("Pause");
    expect(html).not.toContain("play-note");
    expect(html).not.toContain("Playing ");
    expect(html).toContain("Frame 1 of 3");
  });

  it("keeps Play focusable but unavailable until two frames are ready", () => {
    const html = render([slot(frame(1)), slot(null, "loading", "x")]);
    expect(html).toMatch(/class="play-toggle"[^>]*aria-disabled="true"/);
    expect(html).not.toMatch(/class="play-toggle"[^>]*disabled=""/);
  });
});

describe("evidence export shape", () => {
  it("exports IDs, detector, release, UTC, wavelength, flags, sources, processing, notes, case and query", () => {
    const a = frame(1);
    const c = frame(3);
    let card = createEvidenceCard({
      id: "abcdef12-0000-4000-8000-000000000000",
      case_id: "moving_neighbor",
      preset_id: "barnards_star",
      query: { ra_deg: 269.452, dec_deg: 4.6934, fov_arcmin: 6 },
      sources: [{ label: "IRSA SPHEREx", url: "https://irsa.ipac.caltech.edu/Missions/spherex.html" }],
      app_version: "0.1.0",
      data_origin: "api",
      now: NOW,
    });
    card = attachPair(card, [{ frame: c, ref: "C" }, { frame: a, ref: "A" }], ["A", "B", "C"], NOW);
    card = updateEvidenceText(card, "claim", "The star sits north of the guide line in C.", NOW);
    card = updateEvidenceText(card, "observations", "Field stars stay on the grid; the star shifts.", NOW);
    card = updateEvidenceText(card, "uncertainty", "Different wavelengths; no measured motion.", NOW);

    const out = JSON.parse(serializeEvidenceCard(card));
    expect(validateEvidenceCard(out).ok).toBe(true);
    expect(out).toMatchObject({
      case_id: "moving_neighbor",
      preset_id: "barnards_star",
      query: { ra_deg: 269.452, dec_deg: 4.6934, fov_arcmin: 6 },
      claim: "The star sits north of the guide line in C.",
      observations: "Field stars stay on the grid; the star shifts.",
      uncertainty: "Different wavelengths; no measured motion.",
      data_origin: "api",
    });
    expect(out.frames.map((f: { ref: string }) => f.ref)).toEqual(["A", "C"]);
    expect(out.frames[1]).toEqual({
      ref: "C",
      frame_key: c.frame_key,
      frame_id: c.frame_id,
      observation_id: c.observation_id,
      detector: 2,
      collection_id: "spherex_qr2",
      observed_at_utc: c.observed_at_utc,
      mjd: c.mjd,
      wavelength_um: c.wavelength_um,
      bandwidth_um: 0.03,
      wavelength_location: "Catalog-predicted position",
      quality_status: "flagged",
      quality_flag_names: ["SOURCE"],
      display_scale_mode: "per_frame",
      source_url: c.source_url,
      processing: {
        processing_version: "perigee-processor 0.3.0",
        pipeline_version: "l2b-v20-2025-1",
        file_sha256: "sha-3",
        registration_method: "wcs_reproject_to_shared_grid",
        display_scale_method: "asinh_percentile_0.5_99.7",
        marker_kind: "catalog_prediction",
      },
    });
    // No image bytes, data URLs or asset paths in the export.
    expect(JSON.stringify(out)).not.toMatch(/data:image|\/assets\/frames/);
  });

  it("never puts private notes in a coordinate or preset URL", () => {
    const secret = "my private claim";
    const search = routeToSearch({ view: "query", ra: "269.452", dec: "4.6934", fov: "6", caseId: "moving_neighbor" }, false);
    expect(search).toBe("?view=query&ra=269.452&dec=4.6934&fov=6&case=moving_neighbor");
    expect(search).not.toContain(secret);
    expect(routeToSearch({ view: "preset", presetId: "barnards_star" }, false)).toBe("?preset=barnards_star");
    // Extra parameters in a pasted link are ignored, not turned into notes.
    expect(parseRoute(`?view=query&ra=1&dec=2&claim=${encodeURIComponent(secret)}`)).toEqual({
      view: "query",
      ra: "1",
      dec: "2",
      fov: undefined,
      caseId: undefined,
    });
  });
});

describe("storage failure keeps notes", () => {
  const g = globalThis as { window?: unknown };
  const hadWindow = "window" in g;
  let memory: DraftMemory;

  beforeEach(() => {
    memory = new Map();
  });
  afterEach(() => {
    if (!hadWindow) delete g.window;
  });

  function draft(now: Date, claim: string) {
    const base = createEvidenceCard({
      id: "11111111-aaaa-4bbb-8ccc-000000000000",
      preset_id: "barnards_star",
      case_id: "moving_neighbor",
      app_version: "0.1.0",
      data_origin: "api",
      now: NOW,
    });
    return updateEvidenceText(toggleEvidenceFrame(base, frame(1), "A", now), "claim", claim, now);
  }

  it("keeps the in-memory draft when localStorage.setItem throws (quota)", () => {
    const writes: string[] = [];
    g.window = {
      localStorage: {
        getItem: () => null,
        setItem: (k: string) => {
          writes.push(k);
          throw new DOMException("The quota has been exceeded.", "QuotaExceededError");
        },
      },
    };
    const storage = browserStorage();
    const ctx = "api:preset:barnards_star";
    const card = draft(LATER, "Unsaved claim survives");
    memory.set(ctx, card); // what useEvidenceCard.update does first
    expect(persistStore(storage, upsertCard(loadStore(storage), ctx, card))).toBe(false);
    expect(writes).toEqual([STORAGE_KEY]);
    // Coming back to the target in the same tab restores the draft from memory.
    const found = resolveDraft(ctx, loadStore(storage), memory);
    expect(found?.source).toBe("memory");
    expect(found?.card.claim).toBe("Unsaved claim survives");
    expect(found?.card.frames).toHaveLength(1);
  });

  it("treats a throwing localStorage getter as unavailable storage", () => {
    g.window = Object.defineProperty({}, "localStorage", {
      get() {
        throw new DOMException("denied", "SecurityError");
      },
    });
    expect(browserStorage()).toBeNull();
    expect(persistStore(browserStorage(), loadStore(null))).toBe(false);
  });

  it("prefers a newer session draft, otherwise the stored card", () => {
    const ctx = "api:preset:barnards_star";
    const stored = draft(NOW, "stored");
    const store = upsertCard(loadStore(null), ctx, stored);
    expect(resolveDraft(ctx, store, memory)).toEqual({ card: stored, source: "storage" });
    memory.set(ctx, draft(LATER, "newer in memory"));
    expect(resolveDraft(ctx, store, memory)?.card.claim).toBe("newer in memory");
    memory.set(ctx, stored);
    expect(resolveDraft(ctx, store, memory)).toEqual({ card: stored, source: "storage" });
    const newerStore = upsertCard(store, ctx, draft(new Date("2026-11-15T00:00:00Z"), "newer on disk"));
    memory.set(ctx, draft(LATER, "older in memory"));
    expect(resolveDraft(ctx, newerStore, memory)?.card.claim).toBe("newer on disk");
  });

  it("lists unsaved session drafts in My evidence, marked as unsaved", () => {
    const ctx = "api:preset:barnards_star";
    const stored = draft(NOW, "stored");
    const store = upsertCard(loadStore(null), ctx, stored);
    expect(listCards(store, memory)).toEqual([{ card: stored, unsaved: false }]);
    const newer = draft(LATER, "edited but not saved");
    memory.set(ctx, newer);
    // An untouched draft (no frames, no notes) is not listed.
    memory.set("api:preset:wise_0855", createEvidenceCard({ preset_id: "wise_0855", app_version: "0.1.0", data_origin: "api", now: LATER }));
    expect(listCards(store, memory)).toEqual([{ card: newer, unsaved: true }]);
    expect(listCards(loadStore(null), memory)).toEqual([{ card: newer, unsaved: true }]);
  });

  it("forgets a deleted card's session copy", () => {
    const card = draft(LATER, "delete me");
    memory.set("a", card);
    memory.set("b", { ...card, id: "other" });
    forgetDraft(card.id, memory);
    expect([...memory.keys()]).toEqual(["b"]);
  });
});
