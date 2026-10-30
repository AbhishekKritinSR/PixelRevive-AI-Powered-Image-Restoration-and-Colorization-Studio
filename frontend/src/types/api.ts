/**
 * TypeScript interfaces matching the backend Pydantic v2 data models.
 * Source of truth: backend/src/schemas/
 */

export interface HealthResponse {
  status: string;
  application: string;
  version: string;
  device: string;
}

export interface ModelStatusResponse {
  model_name: string;
  files_available: boolean;
  is_loaded: boolean;
  ready_for_inference: boolean;
  detail: string;
}

export interface RestorationOptions {
  denoise: boolean;
  contrast: boolean;
  sharpen: boolean;
  colorize: boolean;
}

export interface QualityMetricsResponse {
  sharpness: number;
  contrast: number;
  brightness: number;
  sharpness_delta: number;
  contrast_delta: number;
  device: string;
  elapsed_seconds: number;
}

export interface SingleRestorationResponse {
  status: string;
  filename: string;
  original_width: number;
  original_height: number;
  processed_width: number;
  processed_height: number;
  was_resized: boolean;
  elapsed_seconds: number;
  options_applied: RestorationOptions;
  metrics: QualityMetricsResponse;
  image_base64: string;
}

export interface BatchItemResult {
  filename: string;
  status: "success" | "failed";
  original_width?: number | null;
  original_height?: number | null;
  processed_width?: number | null;
  processed_height?: number | null;
  elapsed_seconds?: number | null;
  metrics?: QualityMetricsResponse | null;
  image_base64?: string | null;
  error?: string | null;
}

export interface BatchRestorationResponse {
  total_submitted: number;
  total_succeeded: number;
  total_failed: number;
  elapsed_seconds: number;
  items: BatchItemResult[];
  zip_base64?: string | null;
}

export interface ApiErrorDetail {
  detail: string | Array<{ loc: string[]; msg: string; type: string }>;
}

