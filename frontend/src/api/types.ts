// Shapes documented in docs/INTEGRATION_CONTRACT.md and observed from the
// real API (backend/tests/api/examples). Only documented fields are rendered.

export type QualityStatus = 'clear' | 'flagged' | 'not_covered' | 'unknown';

export interface ImageRef {
  src: string;
  width: number;
  height: number;
  media_type: string;
  asset_id?: string;
  /** Overlay colours, RGBA 0-255, as supplied by the processor. */
  legend?: Record<string, number[]> | null;
}

export interface FrameRecord {
  frame_id: string;
  frame_key?: string;
  observation_id: string;
  detector?: number | null;
  collection_id: string;
  observed_at_utc: string | null;
  mjd: number | null;
  time_basis?: string;
  source_url: string;
  wavelength_um: number | null;
  bandwidth_um: number | null;
  wavelength_location?: string | null;
  image: ImageRef;
  flag_image?: ImageRef | null;
  registration?: {
    center_ra_deg?: number;
    center_dec_deg?: number;
    fov_arcmin?: number;
    scale_arcsec_per_px?: number;
    native_scale_arcsec_per_px?: number;
    orientation?: string;
    method?: string;
    method_detail?: string;
    grid_id?: string;
    width?: number;
    height?: number;
  } | null;
  quality?: {
    status?: QualityStatus | string | null;
    covered?: boolean | null;
    valid_aperture_pixels?: number | null;
    adverse_aperture_pixels?: number | null;
    flag_names?: string[] | null;
    notes?: string[] | null;
    screen_radius_native_px?: number | null;
  } | null;
  display_scale?: {
    mode?: 'shared' | 'per_frame' | string;
    method?: string;
    basis?: string;
    low?: number;
    high?: number;
    unit?: string;
  } | null;
  marker?: {
    kind: string;
    label?: string;
    x: number;
    y: number;
    on_grid?: boolean;
    epoch_utc?: string;
    source?: string;
  } | null;
  provenance?: {
    retrieved_at?: string;
    original_url?: string;
    cutout_url?: string;
    sha256?: string | null;
    processing_version?: string;
    pipeline_version?: string;
    acknowledgments?: string[];
  } | null;
  limitations?: string[];
}

export interface PresetDescriptor {
  id: string;
  display_name: string;
  object_type?: string;
  one_line?: string;
  case_ids: string[];
  frames_available?: boolean;
  frame_count?: number;
  quality_summary?: string;
  query_center?: { ra_deg: number; dec_deg: number; note?: string };
  default_fov_arcmin?: number;
}

export interface PresetsResponse {
  presets: PresetDescriptor[];
}

export interface CaseFrameRef {
  ref: string;
  frame_key: string;
  observation_id: string;
  role?: string;
}

export interface CaseStep {
  id: string;
  prompt: string;
  hint?: string;
}

export interface CaseContent {
  case_id: string;
  title: string;
  target_id: string;
  opening_question: string;
  summary?: string;
  background?: { short?: string; details?: string[] };
  frames: CaseFrameRef[];
  steps: CaseStep[];
  claim_prompt?: string;
  display_requirements?: Record<string, string>;
  conclusion_guide?: { supported?: string[]; not_supported?: string[] };
  limitations?: string[];
  sources?: { label: string; url: string }[];
}

export interface PresetFramesResponse {
  preset_id: string;
  case_id?: string | null;
  status: string;
  frames: FrameRecord[];
  reason?: string | null;
  warnings?: string[];
}

export interface SearchRequest {
  schema_version: 1;
  ra_deg: number;
  dec_deg: number;
  fov_arcmin: number;
  limit: number;
}

export interface ObservationDescriptor {
  observation_id: string;
  frame_key?: string;
  detector?: number | null;
  collection_id: string;
  observed_at_utc: string | null;
  mjd: number | null;
  source_url: string;
  frame_token: string;
}

export interface SearchResponse {
  request_id: string;
  query: { ra_deg: number; dec_deg: number; fov_arcmin: number; limit: number; collection_ids?: string[] };
  status: 'ready' | 'partial' | 'empty';
  observations: ObservationDescriptor[];
  returned_count: number;
  total_matches?: number | null;
  truncated: boolean;
  warnings: string[];
  collections_queried: string[];
  collections_failed?: string[];
  queried_at_utc: string;
}

export interface FrameResponse {
  request_id: string;
  frame: FrameRecord;
}

export interface ErrorEnvelope {
  schema_version?: number;
  request_id?: string;
  error: { code: string; message: string; retryable: boolean; details?: Record<string, unknown> };
}
