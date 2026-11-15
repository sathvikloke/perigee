// Worker 13: wavelength filter for stepping and Play, failed/not-loaded frame
// marking, and honest quality-state text. Browser evidence: qa/quality-controls.
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { normalizeFrameRecord } from "../src/api/client";
import type { FrameRecord, QualityStatus } from "../src/api/types";
import { FrameViewer, type FrameSlot } from "../src/components/FrameViewer";
import { createFixtureApi, unknownQualityFixture } from "../src/fixtures/devFixture";
import { QUALITY_CHIP } from "../src/lib/compare";
import { QUALITY_EXPLANATION, QUALITY_LABEL, formatFlagNames } from "../src/lib/format";
import { nextPlayableIndex, playAnnouncement, playableCount, playbackCaveats } from "../src/lib/playback";
import {
  applyWaveFilter,
  filterSummary,
  nearBand,
  sliderPosition,
  slotStatusTag,
  stepWithin,
  type WaveFilter,
} from "../src/lib/wavelengthFilter";

// Barnard's Star preset, all 34 frames in time order, as served by
// GET /api/v1/presets/barnards_star/frames on 2026-11-14: [frame_key, wavelength_um, bandwidth_um, detector].
const BARNARD: [string, number, number, number][] = [
  ["2025W33_2C_0386_4_D3", 1.669753951918138, 0.03978585292969853, 3],
  ["2025W34_2B_0557_1_D5", 3.854449396891473, 0.0355965098137882, 5],
  ["2025W34_2B_0557_4_D2", 1.209589261746813, 0.029147912654291258, 2],
  ["2025W35_1A_0008_1_D3", 2.006235843264055, 0.049679849744144876, 3],
  ["2025W35_1A_0444_3_D5", 4.060234839769911, 0.0364566306286119, 5],
  ["2025W35_1A_0444_4_D2", 1.3290049818490466, 0.03197121932325586, 2],
  ["2025W35_2A_0233_1_D1", 1.0317788463461535, 0.027492240389690524, 1],
  ["2025W35_2A_0233_1_D4", 3.5082249153683494, 0.09806313279139961, 4],
  ["2025W36_1A_0024_1_D1", 1.0165299971765582, 0.027029007403905087, 1],
  ["2025W36_1A_0024_1_D4", 3.4490324289077625, 0.09828836317545729, 4],
  ["2026W11_1A_0511_1_D1", 0.8041479917056035, 0.01995850296351218, 1],
  ["2026W11_1A_0511_1_D4", 2.6365238192503577, 0.07398747747835507, 4],
  ["2026W11_1A_0556_1_D1", 0.9934683000565393, 0.026270210978649535, 1],
  ["2026W11_1A_0556_1_D4", 3.3603305281329146, 0.09527847904135554, 4],
  ["2026W11_2A_0513_1_D2", 1.1970823455431323, 0.02876656131523651, 2],
  ["2026W11_2A_0513_1_D5", 3.940655691927997, 0.03616493348989827, 5],
  ["2026W12_1A_0311_4_D2", 1.4116183513498795, 0.03406756004594158, 2],
  ["2026W12_1A_0311_4_D5", 4.187262681266733, 0.036744920982987754, 5],
  ["2026W12_1A_0610_2_D3", 2.0122664916325355, 0.0493282871218801, 3],
  ["2026W12_1A_0610_2_D6", 4.720484617098532, 0.03693777567557587, 6],
  ["2026W13_1A_0129_4_D3", 1.7397264099961025, 0.04217888321140712, 3],
  ["2026W13_1A_0129_4_D6", 4.5075001808112605, 0.03626183068133759, 6],
  ["2026W34_1A_0007_3_D6", 4.53030916231226, 0.035752536114403495, 6],
  ["2026W34_1A_0007_4_D3", 1.8086056381082531, 0.044673213233539774, 3],
  ["2026W34_1A_0431_1_D3", 2.0284358707774177, 0.05017590956296267, 3],
  ["2026W34_1A_0431_1_D6", 4.73240114130677, 0.036815421556972525, 6],
  ["2026W34_2A_0178_3_D2", 1.1135167398574817, 0.026452798615278435, 2],
  ["2026W34_2A_0178_3_D5", 3.837515191564584, 0.035225615974433064, 5],
  ["2026W34_2A_0249_3_D2", 1.477796270747014, 0.03588652171660966, 2],
  ["2026W34_2A_0249_3_D5", 4.256666334209871, 0.036726320101438274, 5],
  ["2026W35_1A_0079_1_D1", 0.8523953735425248, 0.021452155345564147, 1],
  ["2026W35_1A_0079_1_D4", 2.8180014735965333, 0.07987736121979906, 4],
  ["2026W35_1A_0375_4_D1", 1.097203769469936, 0.029389062777466075, 1],
  ["2026W35_1A_0375_4_D4", 3.762359460261695, 0.1026620655288408, 4],
];
const CASE_A = 3; // 2025W35_1A_0008_1_D3
const CASE_B = 18; // 2026W12_1A_0610_2_D3
const CASE_C = 24; // 2026W34_1A_0431_1_D3

function rec(
  key: string,
  wl: number | null,
  bw: number | null,
  detector: number,
  status: QualityStatus = "flagged",
  i = 0,
): FrameRecord {
  const obs = key.replace(/_D\d$/, "");
  return normalizeFrameRecord({
    frame_id: key,
    frame_key: key,
    observation_id: obs,
    detector,
    collection_id: "spherex_dr1",
    observed_at_utc: `2026-01-${String((i % 28) + 1).padStart(2, "0")}T00:00:00.000`,
    mjd: 61000 + i,
    source_url: `https://irsa.ipac.caltech.edu/${key}.fits`,
    wavelength_um: wl,
    bandwidth_um: bw,
    wavelength_location: wl == null ? null : "Catalog-predicted position",
    image: { src: `/assets/${key}.png`, width: 256, height: 256, media_type: "image/png" },
    flag_image: null,
    registration: { method: "wcs_reproject_to_shared_grid", orientation: "north_up_east_left" },
    quality: { status, covered: status === "not_covered" ? false : true, valid_aperture_pixels: 9, adverse_aperture_pixels: 0, flag_names: [], notes: null },
    display_scale: { mode: "per_frame", method: "asinh" },
    marker: { kind: "catalog_prediction", x: 128, y: 128 },
    provenance: { processing_version: "test" },
    limitations: [],
  });
}

function slot(f: FrameRecord | null, status: FrameSlot["status"] = "ready", key?: string, code = "UPSTREAM_UNAVAILABLE"): FrameSlot {
  return {
    key: f?.frame_key ?? key ?? "missing",
    ref: null,
    status,
    frame: f,
    observed_at_utc: f?.observed_at_utc ?? "2026-06-01T00:00:00.000",
    mjd: f?.mjd ?? null,
    error: status === "error" ? { code, message: "x", retryable: true } : null,
  };
}

const barnardSlots = () => BARNARD.map(([k, wl, bw, d], i) => slot(rec(k, wl, bw, d, "flagged", i)));

describe("wavelength filter on the real Barnard's Star series", () => {
  it("keeps exactly case frames A, B and C within one band width of A (2.0062 µm)", () => {
    const slots = barnardSlots();
    const near: WaveFilter = { mode: "near", center_um: BARNARD[CASE_A][1] };
    const r = applyWaveFilter(slots, near);
    expect(r.indices).toEqual([CASE_A, CASE_B, CASE_C]);
    expect(r.total).toBe(34);
    expect(r.noWavelength).toBe(0);
    expect(r.notLoaded).toBe(0);
    expect(filterSummary(near, r)[0]).toBe("3 of 34 frames near 2.01 µm, each within its own band width (2.0062–2.0284 µm).");
  });

  it("offers the coarser same-detector option from the detector field, with the real wavelength range", () => {
    const det: WaveFilter = { mode: "detector", detector: 3 };
    const r = applyWaveFilter(barnardSlots(), det);
    expect(r.indices).toEqual([0, 3, 18, 20, 23, 24]);
    expect(filterSummary(det, r)[0]).toBe("6 of 34 frames from detector 3 (1.6698–2.0284 µm).");
  });

  it("plays only the kept frames, in time order, wrapping", () => {
    const slots = barnardSlots();
    const allowed = applyWaveFilter(slots, { mode: "near", center_um: BARNARD[CASE_A][1] }).indices;
    expect(playableCount(slots, allowed)).toBe(3);
    expect(nextPlayableIndex(slots, CASE_A, allowed)).toBe(CASE_B);
    expect(nextPlayableIndex(slots, CASE_B, allowed)).toBe(CASE_C);
    expect(nextPlayableIndex(slots, CASE_C, allowed)).toBe(CASE_A);
    // From a frame outside the filter, Play starts on the next kept frame.
    expect(nextPlayableIndex(slots, 5, allowed)).toBe(CASE_B);
  });

  it("steps Earlier/Later and the slider within the filter", () => {
    const kept = [3, 18, 24];
    expect(stepWithin(kept, 3, 1)).toBe(18);
    expect(stepWithin(kept, 3, -1)).toBe(-1);
    expect(stepWithin(kept, 24, 1)).toBe(-1);
    expect(stepWithin(kept, 10, -1)).toBe(3); // from outside the filter
    expect(stepWithin(kept, 10, 1)).toBe(18);
    expect(sliderPosition(kept, 18)).toBe(1);
    expect(sliderPosition(kept, 10)).toBe(0);
  });

  it("names the filter in the single Play announcement and drops the wavelength-change caveat", () => {
    const slots = barnardSlots();
    const near: WaveFilter = { mode: "near", center_um: 2.006235843264055 };
    const allowed = applyWaveFilter(slots, near).indices;
    expect(playAnnouncement(3, near)).toBe("Playing 3 frames near 2.01 µm in time order. Use Pause to stop.");
    const caveats = playbackCaveats(slots, allowed, near);
    expect(caveats).toEqual(["Each frame has its own contrast stretch, so brightness is not directly comparable."]);
    // Unfiltered, the wavelength caveat stays.
    expect(playbackCaveats(slots).some((c) => c.includes("wavelength also changes"))).toBe(true);
    // Detector filter: wavelengths still differ, and it says so.
    const det: WaveFilter = { mode: "detector", detector: 3 };
    expect(playbackCaveats(slots, applyWaveFilter(slots, det).indices, det)[1]).toBe(
      "These detector 3 frames still differ in wavelength by up to 0.36 µm; each is labeled.",
    );
  });
});

describe("wavelength filter edge cases", () => {
  it("uses each frame's own band width", () => {
    // 0.04 µm away: inside a 0.05 band width, outside a 0.03 one.
    expect(nearBand({ wavelength_um: 2.04, bandwidth_um: 0.05 }, 2.0)).toBe(true);
    expect(nearBand({ wavelength_um: 2.04, bandwidth_um: 0.03 }, 2.0)).toBe(false);
    expect(nearBand({ wavelength_um: 2.0, bandwidth_um: 0.03 }, 2.0)).toBe(true);
  });

  it("leaves out and counts frames with no wavelength, no band width, or not loaded; never treats them as zero", () => {
    const slots = [
      slot(rec("A_D3", 2.32, 0.058, 3, "clear", 0)),
      slot(rec("OFF_D1", null, null, 1, "not_covered", 1)),
      slot(null, "error", "F"),
      slot(null, "pending", "P"),
      slot(rec("NOBW_D3", 2.33, null, 3, "clear", 2)),
      slot(rec("B_D3", 2.322, 0.057, 3, "clear", 3)),
      slot(rec("Z_D4", 0, 0.05, 4, "clear", 4)),
    ];
    const near: WaveFilter = { mode: "near", center_um: 2.32 };
    const r = applyWaveFilter(slots, near);
    expect(r.indices).toEqual([0, 5]);
    expect(r).toMatchObject({ noWavelength: 1, noBandwidth: 1, notLoaded: 2, total: 7 });
    expect(filterSummary(near, r)).toEqual([
      "2 of 7 frames near 2.32 µm, each within its own band width (2.3200–2.3220 µm).",
      "1 frame has no wavelength at the target, so it is left out.",
      "1 frame has no band width, so it is left out.",
      "2 frames are not loaded, so their wavelength is unknown and they are left out.",
    ]);
    // "All wavelengths" keeps every slot and adds no summary.
    const all = applyWaveFilter(slots, { mode: "all" });
    expect(all.indices).toHaveLength(7);
    expect(filterSummary({ mode: "all" }, all)).toEqual([]);
  });
});

describe("failed and not-loaded frames are marked, not hidden", () => {
  it("has a status tag for every non-ready state", () => {
    expect(slotStatusTag({ status: "ready" })).toBeNull();
    expect(slotStatusTag({ status: "pending" })).toBe("not loaded yet");
    expect(slotStatusTag({ status: "loading" })).toBe("loading");
    expect(slotStatusTag({ status: "error", error: { code: "UPSTREAM_UNAVAILABLE" } })).toBe("failed to load");
    expect(slotStatusTag({ status: "error", error: { code: "SUPERSEDED" } })).toBe("not loaded (stopped)");
  });

  function render(slots: FrameSlot[], index = 0) {
    return renderToStaticMarkup(
      createElement(FrameViewer, {
        slots,
        index,
        onIndexChange: () => {},
        selectedKeys: new Set<string>(),
        onToggleEvidence: () => {},
        onRetry: () => {},
        title: "Results in time order",
        blinkTool: true,
      }),
    );
  }

  const live = () => [
    slot(rec("A_D3", 2.32, 0.058, 3, "clear", 0)),
    slot(null, "pending", "P"),
    slot(null, "error", "F"),
    slot(null, "error", "S", "SUPERSEDED"),
    slot(rec("B_D3", 2.322, 0.057, 3, "clear", 3)),
  ];

  it("keeps failed frames selectable in the blink picker, with their status in the option text", () => {
    const html = render(live());
    expect(html).toContain("#2, 1 Jun 2026, not loaded yet</option>");
    expect(html).toContain("#3, 1 Jun 2026, failed to load</option>");
    expect(html).toContain("#4, 1 Jun 2026, not loaded (stopped)</option>");
    expect(html).toContain("#1, 1 Jan 2026, 2.32 µm</option>");
    const picker = html.slice(html.indexOf('class="pair-picker"'));
    expect(picker).not.toMatch(/<option[^>]*disabled/);
  });

  it("shows the status of the current frame next to the slider and in its spoken value", () => {
    const html = render(live(), 2);
    expect(html).toContain('<span class="counter-tag">, failed to load</span>');
    expect(html).toContain('aria-valuetext="#3, 1 Jun 2026, failed to load"');
    expect(html).toContain("Wavelength unknown (not loaded)");
    expect(html).not.toContain("Wavelength pending");
  });

  it("offers the wavelength filter in the stepper, starting on all wavelengths", () => {
    const html = render(live());
    expect(html).toMatch(/<select>?[^]*?<option value="all" selected="">All wavelengths<\/option>/);
    expect(html).toContain("Near 2.32 µm (within one band width)");
    expect(html).toContain("Detector 3 only");
    expect(html).toContain("Wavelengths to step and play");
  });

  it("disables the near option, with a reason, when the current frame has no wavelength", () => {
    const html = render([slot(rec("OFF_D1", null, null, 1, "not_covered", 0)), slot(rec("A_D3", 2.32, 0.058, 3, "clear", 1))]);
    expect(html).toContain('<option value="near" disabled="">Near this frame&#x27;s wavelength (not available)</option>');
  });
});

describe("quality states have distinct, honest text", () => {
  const states: QualityStatus[] = ["clear", "flagged", "not_covered", "unknown"];

  it("uses a different chip, label and explanation for each state", () => {
    for (const table of [QUALITY_CHIP, QUALITY_LABEL, QUALITY_EXPLANATION]) {
      expect(new Set(states.map((s) => table[s])).size).toBe(4);
    }
    expect(QUALITY_EXPLANATION.unknown).toContain("not as clear");
    expect(QUALITY_EXPLANATION.clear).toContain("not a detection");
    expect(QUALITY_EXPLANATION.not_covered).toContain("not evidence the object is absent");
  });

  it("never reports 'none' for flags that were not checked", () => {
    expect(formatFlagNames({ status: "unknown", flag_names: [] })).toBe("not checked");
    expect(formatFlagNames({ status: "not_covered", flag_names: [] })).toBe("not checked (the position is off this image)");
    expect(formatFlagNames({ status: "clear", flag_names: [] })).toBe("none reported");
    expect(formatFlagNames({ status: "flagged", flag_names: ["BLOOM", "OVERFLOW"] })).toBe("BLOOM, OVERFLOW");
  });

  it("has an unknown example only as a labeled development fixture with missing values left missing", async () => {
    const f = unknownQualityFixture();
    expect(f._fixture).toBe(true);
    expect(f.quality.status).toBe("unknown");
    expect(f.quality.covered).toBeNull();
    expect(f.quality.valid_aperture_pixels).toBeNull();
    expect(f.quality.adverse_aperture_pixels).toBeNull();
    expect(f.wavelength_um).toBeNull();
    expect(f.marker).toBeNull();
    // It is reachable through the fixture search, next to the simulated failure.
    const api = createFixtureApi();
    const res = await api.search({ ra_deg: 331.1, dec_deg: -56.8, fov_arcmin: 6, limit: 12 });
    const unknown = res.observations.find((o) => o.frame_key === "FIXTURE_UNKNOWN_QUALITY_D2");
    expect(unknown).toBeTruthy();
    const got = await api.frame(unknown!.frame_token);
    expect(got.quality.status).toBe("unknown");
    expect(got._fixture).toBe(true);
  });
});
