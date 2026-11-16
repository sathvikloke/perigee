import { afterEach, describe, expect, it, vi } from "vitest";
import { createHttpApi, type FetchLike } from "../src/api/client";
import emptyResult from "./contract-examples/search_response.empty.fixture.json";

afterEach(() => vi.useRealTimers());

function pendingFetch() {
  let signal: AbortSignal;
  let respond: (value: Response) => void;
  const fetchImpl: FetchLike = (_url, init) => new Promise((resolve, reject) => {
    signal = init!.signal!;
    respond = resolve;
    signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
  });
  return { fetchImpl, aborted: () => signal.aborted,
    respond: () => respond(new Response(JSON.stringify(emptyResult), { headers: { "content-type": "application/json" } })) };
}

const query = { ra_deg: 330.84, dec_deg: -56.786, fov_arcmin: 6, limit: 12 };

describe("live search timeout", () => {
  it("accepts a response after the backend search budget instead of aborting at the old 45-second limit", async () => {
    vi.useFakeTimers();
    const transport = pendingFetch();
    const outcome = createHttpApi({ fetchImpl: transport.fetchImpl }).search(query)
      .then(value => ({ value, error: null }), error => ({ value: null, error }));
    await vi.advanceTimersByTimeAsync(51_000);
    expect(transport.aborted()).toBe(false);
    transport.respond();
    expect((await outcome).value?.status).toBe("empty");
    expect(vi.getTimerCount()).toBe(0);
  });

  it("still aborts a stalled request at 60 seconds with a retryable timeout", async () => {
    vi.useFakeTimers();
    const transport = pendingFetch();
    const outcome = createHttpApi({ fetchImpl: transport.fetchImpl }).search(query).catch(error => error);
    await vi.advanceTimersByTimeAsync(59_999);
    expect(transport.aborted()).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    expect(transport.aborted()).toBe(true);
    expect(await outcome).toMatchObject({ code: "CLIENT_TIMEOUT", retryable: true });
    expect(vi.getTimerCount()).toBe(0);
  });
});
