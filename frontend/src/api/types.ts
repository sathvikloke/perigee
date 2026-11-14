// Types for the Perigee public API, version 1 (docs/INTEGRATION_CONTRACT.md),
// plus the additive fields from science/INTEGRATION_BOARD.md decision 1
// (`detector`, `frame_key = <observation_id>_D<detector>`).
//
// Fields the contract marks nullable stay nullable here. The UI must render
// "not available" for null and never invent a value.

export const SCHEMA_VERSION = 1 as const;

export type QualityStatus = "clear" | "flagged" | "not_covered" | "unknown";

export interface ErrorBody {
  code: string;
  message: string;
  retryable: boolean;
  details?: unknown;
}

export interface ErrorEnvelope {
  schema_version: number;
  request_id: string | null;
  error: ErrorBody;
}

export interface HealthResponse {
  schema_version?: number;
  version?: string;
  status?: string;
  capabilities?: unknown;
  [key: string]: unknown;
}

export interface SkyPosition {
  ra_deg: number;
  dec_deg: number;
  epoch_jyear?: number;
  kind?: string;
  note?: string;
}

export interface PresetDescriptor {
  id: string;
  /** Server-added (catalog): whether curated frame products exist, and how many. */
  frames_available?: boolean;
  frame_count?: number;
  display_name: string;
  object_type?: string;
  one_line?: string;
  query_center?: SkyPosition | null;
  default_fov_arcmin?: number;
  case_ids: string[];
  quality_summary?: string;
  retained_frames?: { total?: number; clear?: number; flagged?: number; not_covered?: number };
}

export interface CaseFrameRef {
  ref: string;
  frame_key: string;
  observation_id: string;
  detector?: number;
  collection_id?: string;
  observed_at_utc?: string;
  mjd?: number;
  wavelength_um?: number | null;
  bandwidth_um?: number | null;
  wavelength_location?: string;
  expected_quality_status?: QualityStatus;
  role?: string;
  source_url?: string;
}

export interface CaseStep {
  id: string;
  prompt: string;
  check?: string[];
  hint?: string;
}

export interface SourceLink {
  label: string;
  url: string;
}

export interface CaseContent {
  schema_version?: number;
  case_id: string;
  content_version?: string;
  title: string;
  target_id: string;
  opening_question: string;
  summary?: string;
  background?: { short?: string; details?: string[] };
  frames: CaseFrameRef[];
  display_requirements?: {
    grid?: string;
    stretch?: string;
    marker?: string;
    reference_line?: string;
  };
  steps: CaseStep[];
  claim_prompt?: string;
  evidence_requirements?: {
    min_selected_frames?: number;
    must_include_refs_any_of?: string[][];
    fields?: string[];
    card_must_show_per_frame?: string[];
  };
  conclusion_guide?: {
    supported?: string[];
    not_supported?: string[];
    example_claim?: string;
  };
  limitations?: string[];
  sources?: SourceLink[];
}

export interface ImageRef {
  src: string;
  width: number;
  height: number;
  media_type: string;
}

export interface Registration {
  center_ra_deg?: number;
  center_dec_deg?: number;
  fov_arcmin?: number;
  arcsec_per_pixel?: number;
  /** Processor/API name for the display grid scale. */
  scale_arcsec_per_px?: number;
  /** Identical for frames registered to the same sky grid. */
  grid_id?: string;
  width?: number;
  height?: number;
  orientation?: string;
  method?: string;
  [key: string]: unknown;
}

export interface Quality {
  status: QualityStatus;
  covered: boolean | null;
  valid_aperture_pixels: number | null;
  adverse_aperture_pixels: number | null;
  flag_names: string[];
  notes: string[] | string | null;
}

export interface DisplayScale {
  mode: "shared" | "per_frame";
  method?: string;
  [key: string]: unknown;
}

export interface Marker {
  kind: "catalog_prediction";
  x?: number;
  y?: number;
  x_px?: number;
  y_px?: number;
  epoch?: string | number;
  explanation?: string;
  source?: string;
  [key: string]: unknown;
}

export interface Provenance {
  retrieved_at_utc?: string | null;
  original_url?: string | null;
  file_sha256?: string | null;
  processing_version?: string | null;
  acknowledgments?: string[] | string | null;
  [key: string]: unknown;
}

export interface FrameRecord {
  frame_id: string;
  frame_key: string;
  observation_id: string;
  detector: number | null;
  collection_id: string;
  observed_at_utc: string;
  mjd: number;
  source_url: string;
  wavelength_um: number | null;
  bandwidth_um: number | null;
  wavelength_location: string | null;
  image: ImageRef | null;
  flag_image: ImageRef | null;
  registration: Registration | null;
  quality: Quality;
  display_scale: DisplayScale | null;
  marker: Marker | null;
  provenance: Provenance | null;
  limitations: string[];
  /** Set only by the development fixture layer. Never by the real API. */
  _fixture?: true;
}

export interface SearchRequest {
  schema_version: typeof SCHEMA_VERSION;
  ra_deg: number;
  dec_deg: number;
  fov_arcmin: number;
  limit: number;
  collection_ids?: string[];
}

export interface ObservationDescriptor {
  observation_id: string;
  frame_key?: string;
  detector?: number | null;
  collection_id: string;
  observed_at_utc: string | null;
  mjd: number | null;
  source_url: string | null;
  frame_token: string;
}

export interface SearchResponse {
  schema_version: number;
  request_id: string;
  query: { ra_deg: number; dec_deg: number; fov_arcmin: number; limit?: number };
  status: "ready" | "partial" | "empty";
  observations: ObservationDescriptor[];
  returned_count: number;
  total_matches?: number | null;
  truncated: boolean;
  warnings: string[];
  collections_queried: string[];
  queried_at_utc: string;
}

export interface FrameRequest {
  schema_version: typeof SCHEMA_VERSION;
  frame_token: string;
}

/** GET /presets/{id}/frames. `missing` means no generated products yet; frames are never synthesized. */
export interface PresetFramesResult {
  status: "ready" | "partial" | "missing";
  frames: FrameRecord[];
  reason: string | null;
  warnings: string[];
}
