// DEVELOPMENT FIXTURE — NOT NASA DATA.
//
// Lets the UI run before the API exists. Frame metadata (dates, wavelengths,
// expected quality, source URLs) is copied from Sathvik's authored case
// content on origin/codex/sathvik-science (backend/content/cases/*.json), but
// these are NOT processor outputs and carry NO sky imagery: every image is a
// labeled placeholder. Every record is tagged `_fixture: true` and the UI shows
// a persistent banner whenever this layer is active. It is only used when the
// person explicitly switches to it; it never replaces a failed real request.

import { ApiError, compareChronological, type PerigeeApi } from "../api/client";
import type {
  CaseContent,
  FrameRecord,
  ObservationDescriptor,
  PresetDescriptor,
  QualityStatus,
  SearchResponse,
} from "../api/types";

const PLACEHOLDER_SIZE = 256;

function placeholderImage(label: string): FrameRecord["image"] {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${PLACEHOLDER_SIZE}" height="${PLACEHOLDER_SIZE}" viewBox="0 0 256 256"><rect width="256" height="256" fill="#d9d9d9"/><path d="M0 0L256 256M256 0L0 256" stroke="#b0b0b0" stroke-width="2"/><rect x="16" y="96" width="224" height="64" fill="#ffffff"/><text x="128" y="120" font-family="sans-serif" font-size="13" text-anchor="middle" fill="#000">DEVELOPMENT FIXTURE</text><text x="128" y="138" font-family="sans-serif" font-size="11" text-anchor="middle" fill="#000">No sky image — not NASA data</text><text x="128" y="153" font-family="monospace" font-size="9" text-anchor="middle" fill="#333">${label}</text></svg>`;
  return {
    src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`,
    width: PLACEHOLDER_SIZE,
    height: PLACEHOLDER_SIZE,
    media_type: "image/svg+xml",
  };
}

interface Seed {
  preset: string;
  observation_id: string;
  detector: number;
  collection_id: string;
  observed_at_utc: string;
  mjd: number;
  wavelength_um: number;
  bandwidth_um: number;
  status: QualityStatus;
  flags: string[];
  source_url: string;
  target: string;
}

const SEEDS: Seed[] = [
  { preset: "epsilon_indi_b", target: "Epsilon Indi B", observation_id: "2026W18_1A_0516_1", detector: 3, collection_id: "spherex_dr1", observed_at_utc: "2026-04-29T12:05:47.874", mjd: 61159.504026317, wavelength_um: 2.3232, bandwidth_um: 0.0577, status: "clear", flags: [], source_url: "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2026W18_1A/l2b-v27-2026-244/3/level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits" },
  { preset: "epsilon_indi_b", target: "Epsilon Indi B", observation_id: "2026W39_2A_0597_4", detector: 3, collection_id: "spherex_qr3", observed_at_utc: "2026-09-27T07:44:24.312", mjd: 61310.322503608, wavelength_um: 2.322, bandwidth_um: 0.0573, status: "clear", flags: [], source_url: "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/2026W39_2A/l2b-v27-2026-271/3/level2_2026W39_2A_0597_4D3_spx_l2b-v27-2026-271.fits" },
  { preset: "epsilon_indi_b", target: "Epsilon Indi B", observation_id: "2026W18_1A_0516_1", detector: 6, collection_id: "spherex_dr1", observed_at_utc: "2026-04-29T12:05:47.874", mjd: 61159.504026317, wavelength_um: 4.9399, bandwidth_um: 0.0376, status: "clear", flags: [], source_url: "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2026W18_1A/l2b-v27-2026-244/6/level2_2026W18_1A_0516_1D6_spx_l2b-v27-2026-244.fits" },
  { preset: "barnards_star", target: "Barnard's Star", observation_id: "2025W35_1A_0008_1", detector: 3, collection_id: "spherex_dr1", observed_at_utc: "2025-08-25T00:50:31.845", mjd: 60912.035090796, wavelength_um: 2.0062, bandwidth_um: 0.0497, status: "flagged", flags: ["OVERFLOW", "BLOOM"], source_url: "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W35_1A/l2b-v27-2026-230/3/level2_2025W35_1A_0008_1D3_spx_l2b-v27-2026-230.fits" },
  { preset: "barnards_star", target: "Barnard's Star", observation_id: "2026W12_1A_0610_2", detector: 3, collection_id: "spherex_dr1", observed_at_utc: "2026-03-19T09:06:02.748", mjd: 61118.379198469, wavelength_um: 2.0123, bandwidth_um: 0.0493, status: "flagged", flags: ["OVERFLOW", "BLOOM"], source_url: "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2026W12_1A/l2b-v27-2026-235/3/level2_2026W12_1A_0610_2D3_spx_l2b-v27-2026-235.fits" },
  { preset: "barnards_star", target: "Barnard's Star", observation_id: "2026W34_1A_0431_1", detector: 3, collection_id: "spherex_qr3", observed_at_utc: "2026-08-19T04:57:42.053", mjd: 61271.206736722, wavelength_um: 2.0284, bandwidth_um: 0.0502, status: "flagged", flags: ["OVERFLOW", "BLOOM"], source_url: "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/2026W34_1A/l2b-v27-2026-243/3/level2_2026W34_1A_0431_1D3_spx_l2b-v27-2026-243.fits" },
];

function seedToRecord(s: Seed, markerY = 128): FrameRecord {
  const key = `${s.observation_id}_D${s.detector}`;
  return {
    _fixture: true,
    frame_id: `fixture:${key}`,
    frame_key: key,
    observation_id: s.observation_id,
    detector: s.detector,
    collection_id: s.collection_id,
    observed_at_utc: s.observed_at_utc,
    mjd: s.mjd,
    source_url: s.source_url,
    wavelength_um: s.wavelength_um,
    bandwidth_um: s.bandwidth_um,
    wavelength_location: `Catalog-predicted position of ${s.target} at this observation time`,
    image: placeholderImage(key),
    flag_image: null,
    registration: { method: "fixture placeholder — no registration performed" },
    quality: {
      status: s.status,
      covered: true,
      valid_aperture_pixels: null,
      adverse_aperture_pixels: null,
      flag_names: s.flags,
      notes: ["Development fixture: status copied from case content, not computed."],
    },
    display_scale: { mode: "shared", method: "fixture placeholder" },
    marker: {
      kind: "catalog_prediction",
      x: 128,
      y: markerY,
      epoch: s.observed_at_utc,
      explanation: "Fixture marker drawn at the image center. Not a computed prediction.",
    },
    provenance: {
      retrieved_at_utc: null,
      original_url: s.source_url,
      file_sha256: null,
      processing_version: "development-fixture",
      acknowledgments: ["Metadata copied from authored case content. Not NASA data."],
    },
    limitations: ["Development fixture — not NASA data. No image was processed."],
  };
}

const PRESETS: PresetDescriptor[] = [
  { id: "barnards_star", display_name: "Barnard's Star", object_type: "Red dwarf star (M4V)", one_line: "The nearby star with the largest known proper motion.", query_center: { ra_deg: 269.4462585584787, dec_deg: 4.768324486236583 }, default_fov_arcmin: 6, case_ids: ["moving_neighbor"] },
  { id: "epsilon_indi_b", display_name: "Epsilon Indi B", object_type: "Pair of brown dwarfs (T1 + T6)", one_line: "Two brown dwarfs about 12 light-years away, seen as one source.", query_center: { ra_deg: 331.0966687831005, dec_deg: -56.80064917516836 }, default_fov_arcmin: 6, case_ids: ["fair_comparison"] },
  { id: "wise_0855", display_name: "WISE 0855", object_type: "Very cold brown dwarf (Y2)", one_line: "One of the coldest known brown dwarfs.", query_center: { ra_deg: 133.75976526566546, dec_deg: -7.242182182223836 }, default_fov_arcmin: 6, case_ids: [] },
  { id: "rw_aurigae", display_name: "RW Aurigae", object_type: "Young variable star system", one_line: "A young star system known for irregular dimming episodes.", query_center: { ra_deg: 76.95658657511666, dec_deg: 30.40129134698889 }, default_fov_arcmin: 6, case_ids: [] },
  { id: "r_draconis", display_name: "R Draconis", object_type: "Mira-type pulsating variable star", one_line: "A red giant that brightens and fades over about 245 days.", query_center: { ra_deg: 248.16723307041877, dec_deg: 66.75502382641281 }, default_fov_arcmin: 6, case_ids: [] },
];

function caseFrom(id: "fair_comparison" | "moving_neighbor"): CaseContent {
  const isFair = id === "fair_comparison";
  const seeds = SEEDS.filter((s) => s.preset === (isFair ? "epsilon_indi_b" : "barnards_star"));
  return {
    case_id: id,
    title: isFair ? "Is this a fair comparison? (fixture)" : "Follow a nearby moving star (fixture)",
    target_id: isFair ? "epsilon_indi_b" : "barnards_star",
    opening_question: isFair
      ? "Fixture copy: did Epsilon Indi B change between April and September 2026? Check whether the pictures can be fairly compared."
      : "Fixture copy: can you see Barnard's Star move in images taken a year apart?",
    background: {
      short: "Development fixture. The real case text is served by GET /api/v1/cases/{id}.",
      details: ["This placeholder exists only so the layout can be exercised without the API."],
    },
    frames: seeds.map((s, i) => ({
      ref: "ABC"[i],
      frame_key: `${s.observation_id}_D${s.detector}`,
      observation_id: s.observation_id,
      detector: s.detector,
    })),
    display_requirements: isFair ? {} : { reference_line: "Fixture: guide line through frame A's marker." },
    steps: [
      { id: "dates", prompt: "Fixture step: compare dates and wavelengths.", check: ["observed_at_utc", "wavelength_um"], hint: "Fixture hint." },
      { id: "quality", prompt: "Fixture step: open the quality details.", check: ["quality.status"], hint: "Fixture hint." },
    ],
    claim_prompt: "Fixture prompt: what can you conclude, and what can't you?",
    evidence_requirements: {
      min_selected_frames: 2,
      must_include_refs_any_of: [isFair ? ["A", "B"] : ["A", "C"]],
    },
    limitations: ["Development fixture — not NASA data."],
    sources: [{ label: "SPHEREx data at NASA/IPAC IRSA", url: "https://irsa.ipac.caltech.edu/Missions/spherex.html" }],
  };
}

const delay = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(t);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });

const FAILING_TOKEN = "fixture:failing-frame";

export function createFixtureApi(): PerigeeApi {
  return {
    mode: "fixture",
    async health() {
      return { status: "fixture", version: "development-fixture" };
    },
    async presets(signal) {
      await delay(150, signal);
      return PRESETS;
    },
    async caseContent(caseId, signal) {
      await delay(150, signal);
      if (caseId !== "fair_comparison" && caseId !== "moving_neighbor") {
        throw new ApiError({ code: "NOT_FOUND", message: `No case "${caseId}".`, httpStatus: 404 });
      }
      return caseFrom(caseId);
    },
    async presetFrames(presetId, signal) {
      await delay(200, signal);
      if (!PRESETS.some((p) => p.id === presetId)) {
        throw new ApiError({ code: "NOT_FOUND", message: `No preset "${presetId}".`, httpStatus: 404 });
      }
      return SEEDS.filter((s) => s.preset === presetId)
        .map((s, i) => seedToRecord(s, presetId === "barnards_star" ? 128 - i : 128))
        .sort(compareChronological);
    },
    async search(req, signal) {
      await delay(500, signal);
      const observations: ObservationDescriptor[] = SEEDS.filter((s) => s.preset === "epsilon_indi_b").map((s) => ({
        observation_id: s.observation_id,
        frame_key: `${s.observation_id}_D${s.detector}`,
        detector: s.detector,
        collection_id: s.collection_id,
        observed_at_utc: s.observed_at_utc,
        mjd: s.mjd,
        source_url: s.source_url,
        frame_token: `fixture:${s.observation_id}_D${s.detector}`,
      }));
      observations.push({
        observation_id: "FIXTURE_FAILING_OBSERVATION",
        frame_key: "FIXTURE_FAILING_OBSERVATION_D1",
        detector: 1,
        collection_id: "spherex_qr3",
        observed_at_utc: "2026-06-01T00:00:00.000",
        mjd: 61192,
        source_url: null,
        frame_token: FAILING_TOKEN,
      });
      observations.sort(compareChronological);
      const res: SearchResponse = {
        schema_version: 1,
        request_id: `fixture-${Date.now()}`,
        query: { ra_deg: req.ra_deg, dec_deg: req.dec_deg, fov_arcmin: req.fov_arcmin, limit: req.limit },
        status: "partial",
        observations: observations.slice(0, req.limit),
        returned_count: Math.min(observations.length, req.limit),
        total_matches: null,
        truncated: false,
        warnings: [
          "Development fixture: the same Epsilon Indi B frames are returned for every coordinate. No archive was queried.",
        ],
        collections_queried: ["spherex_dr1", "spherex_qr3"],
        queried_at_utc: new Date().toISOString(),
      };
      return res;
    },
    async frame(frameToken, signal) {
      await delay(400 + Math.random() * 600, signal);
      if (frameToken === FAILING_TOKEN) {
        throw new ApiError({
          code: "UPSTREAM_UNAVAILABLE",
          message: "Fixture: simulated archive failure for this frame.",
          httpStatus: 502,
          retryable: true,
        });
      }
      const key = frameToken.replace(/^fixture:/, "");
      const seed = SEEDS.find((s) => `${s.observation_id}_D${s.detector}` === key);
      if (!seed) {
        throw new ApiError({ code: "INVALID_FRAME_TOKEN", message: "Unknown fixture token.", httpStatus: 400 });
      }
      return seedToRecord(seed);
    },
  };
}
