// Loading, partial results and recovery (worker 18). Each block pins one gap
// found on the real stack with injected IRSA faults; see
// qa/loading-recovery/README.md for the browser reproduction.

import { describe, expect, it } from "vitest";
import {
  ApiError,
  FRAME_CONCURRENCY,
  createLimiter,
  isAbortError,
  normalizeSearchResponse,
  runWithConcurrency,
} from "../src/api/client";
import {
  formatElapsed,
  isDuplicateSubmit,
  retryActionLabel,
  retryableFailedIndices,
  searchFailureTitle,
  searchScope,
  stoppedCount,
} from "../src/lib/requestState";
import partialFixture from "./contract-examples/search_response.partial.fixture.json";

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms));

describe("shared frame limiter", () => {
  it("keeps the first pass and every retry within FRAME_CONCURRENCY", async () => {
    const limiter = createLimiter(FRAME_CONCURRENCY);
    let inFlight = 0;
    let max = 0;
    const job = (ms: number) => () => {
      inFlight += 1;
      max = Math.max(max, inFlight);
      return tick(ms).then(() => {
        inFlight -= 1;
      });
    };
    // First pass over 12 frames with 2 lanes, plus three single-frame retries
    // and a "retry all" fired while that pass is still running.
    const firstPass = runWithConcurrency(Array.from({ length: 12 }), FRAME_CONCURRENCY, () => limiter.run(job(5)));
    const retries = [limiter.run(job(3)), limiter.run(job(3)), limiter.run(job(3))];
    const retryAll = runWithConcurrency([0, 1, 2, 3], FRAME_CONCURRENCY, () => limiter.run(job(2)));
    await Promise.all([firstPass, retryAll, ...retries]);
    expect(max).toBe(FRAME_CONCURRENCY);
    expect(limiter.inFlight()).toBe(0);
  });

  it("starts queued work in call order", async () => {
    const limiter = createLimiter(1);
    const order: number[] = [];
    await Promise.all([1, 2, 3, 4].map((n) => limiter.run(async () => void order.push(n))));
    expect(order).toEqual([1, 2, 3, 4]);
  });

  it("rejects a queued call on abort without ever running it, and frees no slot it never took", async () => {
    const limiter = createLimiter(1);
    let release!: () => void;
    const holder = limiter.run(() => new Promise<void>((r) => (release = r)));
    const controller = new AbortController();
    let ran = false;
    const queued = limiter.run(async () => {
      ran = true;
    }, controller.signal);
    controller.abort();
    await expect(queued).rejects.toSatisfy(isAbortError);
    release();
    await holder;
    await tick();
    expect(ran).toBe(false);
    expect(limiter.inFlight()).toBe(0);
  });

  it("releases its slot when the work throws", async () => {
    const limiter = createLimiter(1);
    await expect(limiter.run(() => Promise.reject(new Error("502")))).rejects.toThrow("502");
    await expect(limiter.run(async () => "next")).resolves.toBe("next");
  });
});

describe("2 of 12 frames fail, then retry all failed", () => {
  it("fills every slot in result order and never exceeds two requests", async () => {
    type Slot = { key: string; status: string; error: { code: string; retryable: boolean } | null };
    const keys = Array.from({ length: 12 }, (_, i) => `F${i}`);
    const slots: Slot[] = keys.map((key) => ({ key, status: "pending", error: null }));
    const attempts = new Map<string, number>();
    const limiter = createLimiter(FRAME_CONCURRENCY);
    let inFlight = 0;
    let max = 0;
    const frame = async (key: string) => {
      inFlight += 1;
      max = Math.max(max, inFlight);
      attempts.set(key, (attempts.get(key) ?? 0) + 1);
      await tick(key === "F5" ? 8 : 1); // one slow frame
      inFlight -= 1;
      if ((key === "F3" || key === "F8") && attempts.get(key) === 1) {
        throw new ApiError({ code: "UPSTREAM_UNAVAILABLE", message: "502", httpStatus: 502, retryable: true });
      }
      return key;
    };
    const load = async (i: number) => {
      try {
        await limiter.run(() => frame(keys[i]));
        slots[i] = { ...slots[i], status: "ready", error: null };
      } catch (err) {
        const e = err as ApiError;
        slots[i] = { ...slots[i], status: "error", error: { code: e.code, retryable: e.retryable } };
      }
    };
    await runWithConcurrency(keys, FRAME_CONCURRENCY, (_, i) => load(i));
    expect(retryableFailedIndices(slots)).toEqual([3, 8]);
    expect(slots.filter((s) => s.status === "ready")).toHaveLength(10);

    await runWithConcurrency(retryableFailedIndices(slots), FRAME_CONCURRENCY, (i) => load(i));
    expect(slots.map((s) => s.key)).toEqual(keys);
    expect(slots.every((s) => s.status === "ready")).toBe(true);
    expect(attempts.get("F3")).toBe(2);
    expect(attempts.get("F0")).toBe(1);
    expect(max).toBeLessThanOrEqual(FRAME_CONCURRENCY);
  });
});

describe("retryableFailedIndices", () => {
  it("lists retryable failures in order, including frames stopped by a newer search", () => {
    const err = (code: string, retryable = true) => ({ status: "error", error: { code, retryable } });
    const ok = { status: "ready", error: null };
    expect(
      retryableFailedIndices([
        ok,
        err("UPSTREAM_UNAVAILABLE"),
        err("TOKEN_EXPIRED", true),
        err("PROCESSING_FAILED", false),
        { status: "loading", error: null },
        err("SUPERSEDED"),
        err("NETWORK_ERROR"),
      ]),
    ).toEqual([1, 5, 6]);
  });
});

describe("frames stopped by a newer search that was cancelled", () => {
  const err = (code: string) => ({ status: "error", error: { code, retryable: true } });
  const ok = { status: "ready", error: null };

  it("counts stopped frames apart from failures and labels the bulk action honestly", () => {
    const stoppedOnly = [ok, err("SUPERSEDED"), err("SUPERSEDED")];
    expect(stoppedCount(stoppedOnly)).toBe(2);
    expect(retryActionLabel(stoppedOnly, retryableFailedIndices(stoppedOnly))).toBe("Load 2 stopped frames");

    const failedOnly = [ok, err("UPSTREAM_UNAVAILABLE")];
    expect(stoppedCount(failedOnly)).toBe(0);
    expect(retryActionLabel(failedOnly, retryableFailedIndices(failedOnly))).toBe("Retry 1 failed frame");

    const mixed = [err("NETWORK_ERROR"), err("SUPERSEDED"), ok];
    expect(retryActionLabel(mixed, retryableFailedIndices(mixed))).toBe("Retry 2 unfinished frames");
  });
});

describe("partial search results", () => {
  it("keeps collections_failed from the API and defaults it to empty", () => {
    const partial = normalizeSearchResponse(partialFixture);
    expect(partial.status).toBe("partial");
    expect(partial.collections_failed).toEqual(["spherex_qr3"]);
    expect(searchScope(partial)).toEqual({ answered: ["spherex_dr1"], failed: ["spherex_qr3"] });

    const ready = normalizeSearchResponse({ ...partialFixture, status: "ready", collections_failed: undefined });
    expect(ready.collections_failed).toEqual([]);
    expect(searchScope(ready).answered).toEqual(["spherex_dr1", "spherex_qr3"]);
  });
});

describe("search submission and failure wording", () => {
  const q = { ra_deg: 330.84, dec_deg: -56.786, fov_arcmin: 6, limit: 24 };

  it("ignores a repeat of the search in flight but never a different query", () => {
    expect(isDuplicateSubmit(null, q)).toBe(false);
    expect(isDuplicateSubmit(q, { ...q })).toBe(true);
    expect(isDuplicateSubmit(q, { ...q, dec_deg: -56.7 })).toBe(false);
    expect(isDuplicateSubmit(q, { ...q, limit: 12 })).toBe(false);
  });

  it("formats elapsed time in whole seconds", () => {
    expect(formatElapsed(-5)).toBe("0 s");
    expect(formatElapsed(999)).toBe("0 s");
    expect(formatElapsed(18_400)).toBe("18 s");
    expect(formatElapsed(65_000)).toBe("1 min 05 s");
  });

  it("names a connection failure differently from an archive failure, and neither as an empty sky", () => {
    const network = searchFailureTitle("NETWORK_ERROR");
    const timeout = searchFailureTitle("UPSTREAM_TIMEOUT");
    expect(network).toMatch(/did not reach the archive/);
    expect(timeout).toMatch(/archive search failed/);
    for (const t of [network, timeout, searchFailureTitle(null)]) {
      expect(t).toMatch(/not a result about the sky/);
      expect(t).not.toMatch(/no observations|no images/i);
    }
  });
});
