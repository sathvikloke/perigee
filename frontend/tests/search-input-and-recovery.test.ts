import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createHttpApi, createLimiter, createRequestGate, normalizeResolvedObject, FRAME_CONCURRENCY } from "../src/api/client";
import { LIMIT_DEFAULT, parseCoordinate, validateQuery } from "../src/lib/coords";
import { recoverFrame } from "../src/lib/frameRecovery";
import { frameCacheKey, rememberFrame } from "../src/lib/frameCache";
import type { FrameRecord, ResolvedObject } from "../src/api/types";

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

describe("strict decimal and sexagesimal coordinates", () => {
  it("keeps decimal RA in degrees and colon RA in hours", () => {
    expect(parseCoordinate("17.5", "ra")).toBe(17.5);
    expect(parseCoordinate("17:30:00", "ra")).toBe(262.5);
    expect(parseCoordinate("17:57:48.49847", "ra")).toBeCloseTo(269.452076958, 8);
    expect(parseCoordinate("-00:30:00", "dec")).toBe(-0.5);
    expect(parseCoordinate("+90:00:00", "dec")).toBe(90);
    expect(parseCoordinate("-90:00:00", "dec")).toBe(-90);
  });
  it.each(["24:00:00", "-01:00:00", "12:60:00", "12:00:60", "12:0:00", "12:00", "12:00:00abc", "12:00:1e1", "NaN", "Infinity", "12x", "0x10"])("rejects malformed RA %s", (value) => {
    expect(parseCoordinate(value, "ra")).toBeNull();
  });
  it.each(["90:00:00.01", "-90:00:01", "91:00:00", "00:60:00", "-04:00:-01", "04:00:00 north"])("rejects malformed Dec %s", (value) => {
    expect(parseCoordinate(value, "dec")).toBeNull();
  });
  it("converts both coordinates, preserves bounds and defaults to 12 images", () => {
    expect(LIMIT_DEFAULT).toBe(12);
    expect(validateQuery({ ra: "12:00:00", dec: "-04:30:00", fov: "", limit: "" })).toMatchObject({ ok: true, value: { ra_deg: 180, dec_deg: -4.5, fov_arcmin: 6, limit: 12 } });
    expect(validateQuery({ ra: "360", dec: "0", fov: "6", limit: "12" })).toMatchObject({ ok: true, value: { ra_deg: 0 }, notices: [expect.any(String)] });
    for (const ra of ["-1", "360.1", "999999999999999999999999999999999999"]) {
      expect(validateQuery({ ra, dec: "0", fov: "6", limit: "12" }).ok).toBe(false);
    }
  });
});

const unavailable = () => new ApiError({ code: "UPSTREAM_UNAVAILABLE", message: "temporary", httpStatus: 502, retryable: true });

describe("bounded transient frame recovery", () => {
  it("retries two transient failures at bounded delays, then returns the frame", async () => {
    vi.useFakeTimers(); vi.spyOn(Math, "random").mockReturnValue(0);
    const operation = vi.fn().mockRejectedValueOnce(unavailable()).mockRejectedValueOnce(unavailable()).mockResolvedValue("frame");
    const retry = vi.fn();
    const result = recoverFrame(operation, new AbortController().signal, retry);
    await vi.advanceTimersByTimeAsync(899); expect(operation).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1); expect(operation).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(2199); expect(operation).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1); await expect(result).resolves.toBe("frame");
    expect(retry.mock.calls).toEqual([[1], [2]]);
  });
  it("finishes in an error after three total attempts", async () => {
    vi.useFakeTimers();
    const operation = vi.fn().mockRejectedValue(unavailable());
    const result = recoverFrame(operation, new AbortController().signal, () => {}).catch((e) => e);
    await vi.runAllTimersAsync();
    expect(await result).toBeInstanceOf(ApiError);
    expect(operation).toHaveBeenCalledTimes(3);
  });
  it.each(["TOKEN_EXPIRED", "INVALID_FRAME_TOKEN", "PROCESSING_FAILED", "UNSUPPORTED_DATA"])("does not automatically retry %s", async (code) => {
    const operation = vi.fn().mockRejectedValue(new ApiError({ code, message: "needs action", retryable: true }));
    await expect(recoverFrame(operation, new AbortController().signal, () => {})).rejects.toMatchObject({ code });
    expect(operation).toHaveBeenCalledTimes(1);
  });
  it("aborts during backoff without another request or timer left behind", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const operation = vi.fn().mockRejectedValue(unavailable());
    const result = recoverFrame(operation, controller.signal, () => {}).catch((e) => e);
    await vi.advanceTimersByTimeAsync(1);
    controller.abort();
    expect(await result).toMatchObject({ name: "AbortError" });
    await vi.runAllTimersAsync();
    expect(operation).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });
  it("rejects an old successful response after cancellation even if its transport ignored abort", async () => {
    let finish!: (v: string) => void;
    const gate = createRequestGate(), first = gate.begin();
    const result = recoverFrame(() => new Promise<string>((resolve) => { finish = resolve; }), first.signal, () => {}).catch((e) => e);
    gate.begin(); finish("obsolete frame");
    expect(await result).toMatchObject({ name: "AbortError" });
    expect(gate.isCurrent(first.id)).toBe(false);
  });
  it("keeps two requests in flight and releases capacity while an attempt waits to retry", async () => {
    vi.useFakeTimers(); vi.spyOn(Math, "random").mockReturnValue(0);
    const limiter = createLimiter(FRAME_CONCURRENCY);
    let active = 0, highest = 0;
    const operation = vi.fn(async () => {
      active++; highest = Math.max(highest, active);
      await new Promise((resolve) => setTimeout(resolve, 10)); active--;
      if (operation.mock.calls.length <= 2) throw unavailable();
      return "frame";
    });
    const jobs = Array.from({ length: 6 }, () => recoverFrame(() => limiter.run(operation), new AbortController().signal, () => {}));
    await vi.runAllTimersAsync(); await Promise.all(jobs);
    expect(highest).toBe(2); expect(limiter.inFlight()).toBe(0);
  });
});

const resolved: ResolvedObject = {
  name: "Barnard's Star", catalog_position: { ra_deg: 269.45207696, dec_deg: 4.69336497, epoch_jyear: 2000 },
  search_center: { ra_deg: 269.4462585584787, dec_deg: 4.768324486236583, epoch_jyear: 2026, kind: "finder_prediction" },
  source: "SIMBAD via CDS Sesame", source_url: "https://vizier.cfa.harvard.edu/viz-bin/nph-sesame/-oxp/S?Barnard%27s%20Star", position_reference: null, note: "Finder position, not a detection.",
};

describe("live name lookup transport", () => {
  it("posts the name to the same-origin resolver and keeps epoch/source", async () => {
    const fetchImpl = vi.fn(async (_url: string, _init?: RequestInit) => Response.json(resolved));
    const api = createHttpApi({ fetchImpl });
    expect(await api.resolveName!("Barnard's Star")).toEqual(resolved);
    expect(fetchImpl.mock.calls[0]?.[0]).toBe("/api/v1/resolve");
  });
  it("rejects malformed positions and untrusted source links", () => {
    for (const bad of [{ ...resolved, search_center: { ...resolved.search_center, ra_deg: 360 } }, { ...resolved, source_url: "javascript:alert(1)" }, { ...resolved, catalog_position: null }]) {
      expect(() => normalizeResolvedObject(bad)).toThrow(ApiError);
    }
  });
  it("makes interrupted response bodies retryable instead of exposing a raw stream error", async () => {
    const api = createHttpApi({ fetchImpl: async () => new Response(new ReadableStream({ start(c) { c.error(new TypeError("raw stream error")); } }), { headers: { "content-type": "application/json" } }) });
    await expect(api.resolveName!("Barnard's Star")).rejects.toMatchObject({ code: "NETWORK_ERROR", retryable: true });
  });
  it("keeps completed frame cache bounded and query-specific", () => {
    const cache = new Map<string, FrameRecord>();
    const frame = { frame_key: "frame" } as FrameRecord;
    for (let i = 0; i < 130; i++) rememberFrame(cache, String(i), frame);
    expect(cache.size).toBe(128);
    const q = { ra_deg: 1, dec_deg: 2, fov_arcmin: 6, limit: 12 };
    expect(frameCacheKey("api", "frame", "token", q)).not.toBe(frameCacheKey("api", "frame", "token", { ...q, fov_arcmin: 8 }));
  });
});
