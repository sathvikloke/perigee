import { describe, expect, it } from "vitest";
import {
  ApiError,
  FRAME_CONCURRENCY,
  createHttpApi,
  createRequestGate,
  errorFromResponse,
  normalizeFrameList,
  normalizeFrameRecord,
  normalizePresetFrames,
  normalizeSearchResponse,
  parseErrorEnvelope,
  resolveApiBase,
  resolveAssetSrc,
  runWithConcurrency,
  type FetchLike,
} from "../src/api/client";

const envelope = {
  schema_version: 1,
  request_id: "req-123",
  error: { code: "TOKEN_EXPIRED", message: "The frame token has expired.", retryable: false, details: { hint: "refresh" } },
};

function jsonResponse(status: number, body: unknown, contentType = "application/json"): Response {
  return new Response(typeof body === "string" ? body : JSON.stringify(body), {
    status,
    headers: { "content-type": contentType },
  });
}

const rawFrame = {
  frame_id: "f1",
  observation_id: "2026W18_1A_0516_1",
  detector: 3,
  collection_id: "spherex_dr1",
  observed_at_utc: "2026-04-29T12:05:47.874",
  mjd: 61159.504026317,
  source_url: "https://irsa.ipac.caltech.edu/x.fits",
  wavelength_um: 2.3232,
  bandwidth_um: 0.0577,
  wavelength_location: "Catalog-predicted position",
  image: { src: "/api/v1/assets/abc", width: 256, height: 256, media_type: "image/png" },
  flag_image: null,
  registration: null,
  quality: { status: "clear", covered: true, valid_aperture_pixels: null, adverse_aperture_pixels: 0, flag_names: [], notes: [] },
  display_scale: { mode: "shared", method: "asinh" },
  marker: null,
  provenance: null,
  limitations: ["Display only."],
};

describe("error envelope parsing", () => {
  it("parses the contract envelope", () => {
    expect(parseErrorEnvelope(envelope)).toEqual({
      schema_version: 1,
      request_id: "req-123",
      error: { code: "TOKEN_EXPIRED", message: "The frame token has expired.", retryable: false, details: { hint: "refresh" } },
    });
  });

  it("rejects bodies without code and message", () => {
    expect(parseErrorEnvelope({ error: { code: 5 } })).toBeNull();
    expect(parseErrorEnvelope("nope")).toBeNull();
    expect(parseErrorEnvelope(null)).toBeNull();
  });

  it("maps a JSON envelope to ApiError with status and retryable flag", () => {
    const err = errorFromResponse(
      503,
      "application/json",
      JSON.stringify({ schema_version: 1, request_id: "r9", error: { code: "UPSTREAM_UNAVAILABLE", message: "IRSA is down", retryable: true } }),
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("UPSTREAM_UNAVAILABLE");
    expect(err.httpStatus).toBe(503);
    expect(err.retryable).toBe(true);
    expect(err.requestId).toBe("r9");
  });

  it("treats an HTML body (SPA fallback or proxy page) as an error, even with 200", () => {
    const err = errorFromResponse(200, "text/html; charset=utf-8", "<!doctype html><html></html>");
    expect(err.code).toBe("NON_JSON_RESPONSE");
    expect(err.retryable).toBe(false);
    const err502 = errorFromResponse(502, "text/html", "<html>Bad gateway</html>");
    expect(err502.code).toBe("NON_JSON_RESPONSE");
    expect(err502.retryable).toBe(true);
  });

  it("maps FastAPI default validation errors", () => {
    const err = errorFromResponse(
      422,
      "application/json",
      JSON.stringify({ detail: [{ loc: ["body", "ra_deg"], msg: "Input should be a finite number" }] }),
    );
    expect(err.code).toBe("INVALID_REQUEST");
    expect(err.message).toContain("body.ra_deg");
  });

  it("surfaces the envelope through the HTTP client", async () => {
    const fetchImpl: FetchLike = async () => jsonResponse(410, envelope);
    const api = createHttpApi({ base: "/api/v1", fetchImpl });
    await expect(api.frame("tok")).rejects.toMatchObject({ code: "TOKEN_EXPIRED", httpStatus: 410, requestId: "req-123" });
  });

  it("reports a network failure as retryable NETWORK_ERROR", async () => {
    const fetchImpl: FetchLike = async () => {
      throw new TypeError("Failed to fetch");
    };
    const api = createHttpApi({ base: "/api/v1", fetchImpl });
    await expect(api.presets()).rejects.toMatchObject({ code: "NETWORK_ERROR", retryable: true });
  });

  it("rejects a 200 HTML response for an API route", async () => {
    const fetchImpl: FetchLike = async () => jsonResponse(200, "<!doctype html>", "text/html");
    const api = createHttpApi({ base: "/api/v1", fetchImpl });
    await expect(api.presets()).rejects.toMatchObject({ code: "NON_JSON_RESPONSE" });
  });
});

describe("request transport", () => {
  it("posts the contract frame body to the same-origin prefix", async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    const fetchImpl: FetchLike = async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { schema_version: 1, request_id: "r", frame: rawFrame });
    };
    const api = createHttpApi({ base: resolveApiBase(undefined), fetchImpl });
    const frame = await api.frame("signed-token");
    expect(calls[0].url).toBe("/api/v1/frame");
    expect(calls[0].init?.method).toBe("POST");
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({ schema_version: 1, frame_token: "signed-token" });
    expect(frame.frame_key).toBe("2026W18_1A_0516_1_D3");
  });

  it("resolves the API base override and rebases asset paths", () => {
    expect(resolveApiBase("")).toBe("/api/v1");
    expect(resolveApiBase("https://api.example.test/")).toBe("https://api.example.test/api/v1");
    expect(resolveApiBase("https://api.example.test/api/v1")).toBe("https://api.example.test/api/v1");
    expect(resolveAssetSrc("/api/v1/assets/x", "/api/v1")).toBe("/api/v1/assets/x");
    expect(resolveAssetSrc("/api/v1/assets/x", "https://api.example.test/api/v1")).toBe(
      "https://api.example.test/api/v1/assets/x",
    );
    expect(resolveAssetSrc("data:image/png;base64,AAA", "https://a.test/api/v1")).toBe("data:image/png;base64,AAA");
  });
});

describe("stale-response guard", () => {
  it("only the latest generation is current, and older ones are aborted", () => {
    const gate = createRequestGate();
    const first = gate.begin();
    const second = gate.begin();
    expect(first.signal.aborted).toBe(true);
    expect(gate.isCurrent(first.id)).toBe(false);
    expect(gate.isCurrent(second.id)).toBe(true);
    expect(gate.active()?.id).toBe(second.id);
    gate.cancel();
    expect(second.signal.aborted).toBe(true);
    expect(gate.isCurrent(second.id)).toBe(false);
    expect(gate.active()).toBeNull();
  });

  it("drops a slow response from an older query", async () => {
    const gate = createRequestGate();
    const shown: string[] = [];
    const respond = (value: string, ms: number) => new Promise<string>((r) => setTimeout(() => r(value), ms));
    const run = async (value: string, ms: number) => {
      const t = gate.begin();
      const v = await respond(value, ms);
      if (gate.isCurrent(t.id)) shown.push(v);
    };
    await Promise.all([run("old query", 30), run("new query", 5)]);
    expect(shown).toEqual(["new query"]);
  });
});

describe("frame concurrency", () => {
  it("never runs more than two frames at once and starts them in order", async () => {
    let inFlight = 0;
    let peak = 0;
    const started: number[] = [];
    await runWithConcurrency([0, 1, 2, 3, 4, 5], FRAME_CONCURRENCY, async (_item, i) => {
      started.push(i);
      inFlight += 1;
      peak = Math.max(peak, inFlight);
      await new Promise((r) => setTimeout(r, 5 + (i % 3) * 3));
      inFlight -= 1;
      if (i === 2) throw new Error("one failed frame");
    });
    expect(FRAME_CONCURRENCY).toBe(2);
    expect(peak).toBe(2);
    expect(started).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it("stops scheduling after abort", async () => {
    const controller = new AbortController();
    const started: number[] = [];
    await runWithConcurrency(
      [0, 1, 2, 3],
      2,
      async (_x, i) => {
        started.push(i);
        if (i === 0) controller.abort();
        await new Promise((r) => setTimeout(r, 1));
      },
      controller.signal,
    );
    expect(started).toEqual([0]);
  });
});

describe("normalizers", () => {
  it("keeps missing pixel counts null and derives frame_key", () => {
    const f = normalizeFrameRecord({ ...rawFrame, frame_key: undefined });
    expect(f.frame_key).toBe("2026W18_1A_0516_1_D3");
    expect(f.quality.valid_aperture_pixels).toBeNull();
    expect(f.quality.adverse_aperture_pixels).toBe(0);
  });

  it("keeps a null wavelength null and falls back to unknown quality", () => {
    const f = normalizeFrameRecord({ ...rawFrame, wavelength_um: null, quality: { status: "weird" } });
    expect(f.wavelength_um).toBeNull();
    expect(f.quality.status).toBe("unknown");
    expect(f.quality.covered).toBeNull();
  });

  it("sorts frames by mjd then frame_key", () => {
    const frames = normalizeFrameList({
      frames: [
        { ...rawFrame, detector: 6, frame_key: "X_D6", mjd: 2 },
        { ...rawFrame, detector: 3, frame_key: "X_D3", mjd: 2 },
        { ...rawFrame, frame_key: "A_D1", mjd: 1 },
      ],
    });
    expect(frames.map((f) => f.frame_key)).toEqual(["A_D1", "X_D3", "X_D6"]);
  });

  it("validates search responses and sorts descriptors", () => {
    const res = normalizeSearchResponse({
      schema_version: 1,
      request_id: "r",
      query: { ra_deg: 1, dec_deg: 2, fov_arcmin: 6 },
      status: "partial",
      observations: [
        { observation_id: "B", detector: 1, collection_id: "c", observed_at_utc: null, mjd: 5, source_url: null, frame_token: "t2" },
        { observation_id: "A", detector: 2, collection_id: "c", observed_at_utc: null, mjd: 4, source_url: null, frame_token: "t1" },
      ],
      truncated: false,
      warnings: ["qr3 failed"],
      collections_queried: ["spherex_dr1"],
      queried_at_utc: "2026-11-14T00:00:00Z",
    });
    expect(res.observations.map((o) => o.frame_key)).toEqual(["A_D2", "B_D1"]);
    expect(res.returned_count).toBe(2);
    expect(res.total_matches).toBeNull();
    expect(() => normalizeSearchResponse({ status: "done", observations: [] })).toThrow(ApiError);
  });
});

describe("catalog and processor payload shapes", () => {
  it("reads a catalog frames response with status, warnings and processor provenance names", () => {
    const res = normalizePresetFrames({
      schema_version: 1,
      preset_id: "epsilon_indi_b",
      case_id: "fair_comparison",
      status: "partial",
      frames_available: true,
      frame_count: 1,
      order: "mjd_then_frame_key",
      frames: [
        {
          ...rawFrame,
          observed_at_utc: "2026-04-29T12:05:47.874Z",
          provenance: { retrieved_at: "2026-11-14T04:27:13Z", sha256: "abc", processing_version: "perigee-processor-a/0.1.0" },
        },
      ],
      reason: null,
      sets: ["case-fair_comparison"],
      warnings: ["one product skipped"],
      source_dir: "x",
    });
    expect(res.status).toBe("partial");
    expect(res.warnings).toEqual(["one product skipped"]);
    expect(res.frames[0].provenance?.retrieved_at_utc).toBe("2026-11-14T04:27:13Z");
    expect(res.frames[0].provenance?.file_sha256).toBe("abc");
  });

  it("reports missing products honestly with no frames", () => {
    const res = normalizePresetFrames({ status: "missing", frames: [], reason: "No generated products yet." });
    expect(res).toEqual({ status: "missing", frames: [], reason: "No generated products yet.", warnings: [] });
  });

  it("requests a case product set with ?case_id=", async () => {
    const urls: string[] = [];
    const api = createHttpApi({
      base: "/api/v1",
      fetchImpl: async (url) => {
        urls.push(url);
        return jsonResponse(200, { status: "ready", frames: [rawFrame] });
      },
    });
    await api.presetFrames("epsilon_indi_b", "fair_comparison");
    expect(urls).toEqual(["/api/v1/presets/epsilon_indi_b/frames?case_id=fair_comparison"]);
  });
});
