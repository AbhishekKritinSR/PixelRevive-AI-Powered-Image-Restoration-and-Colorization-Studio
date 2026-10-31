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
  is_default?: boolean;
  detail?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface ModelRegistryItem {
  model_id: string;
  display_name: string;
  architecture: string;
  authors: string;
  publication: string;
  model_format: string;
  supported_task: string;
  is_default: boolean;
  files_available: boolean;
  is_loaded: boolean;
  ready_for_inference: boolean;
  supported_parameters: Record<string, unknown>;
  runtime_requirements: string;
  description: string;
}

export interface ModelRegistryListResponse {
  default_model: string;
  models: ModelRegistryItem[];
}

export interface RestorationOptions {
  denoise: boolean;
  contrast: boolean;
  sharpen: boolean;
  colorize: boolean;
  adaptive_denoise?: boolean;
  repair?: boolean;
  inpaint_method?: "lama" | "telea" | "ns";
  face_restore?: boolean;
  upscale?: boolean;
  scale?: number;
  sr_model?: "fsrcnn" | "realesrgan";
  colorization_model?: string;
  render_factor?: number;
  color_saturation?: number;
  color_temperature?: number;
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
  operations_summary?: Record<string, string>;
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

// =====================================================================
// Phase 5.1 Image Analysis Schemas
// =====================================================================

export interface ImageDimensions {
  width: number;
  height: number;
  channels: number;
  was_resized: boolean;
}

export interface NoiseAnalysis {
  noise_score: number;
  noise_level: "low" | "medium" | "high";
  method: string;
}

export interface SharpnessAnalysis {
  sharpness_score: number;
  sharpness_level: "blurry" | "moderate" | "sharp";
}

export interface ContrastAnalysis {
  contrast_score: number;
  dynamic_range: number;
  contrast_level: "low" | "moderate" | "high";
}

export interface MonochromeAnalysis {
  is_monochrome: boolean;
  color_variation_score: number;
  confidence: number;
}

export interface RecommendationItem {
  recommended: boolean;
  reason: string;
  evidence: string;
}

export interface RestorationRecommendations {
  denoise: RecommendationItem;
  contrast: RecommendationItem;
  sharpen: RecommendationItem;
  colorize: RecommendationItem;
  repair?: RecommendationItem;
  face_restore?: RecommendationItem;
  upscale?: RecommendationItem;
}

export interface AnalysisMetrics {
  noise: NoiseAnalysis;
  sharpness: SharpnessAnalysis;
  contrast: ContrastAnalysis;
  monochrome: MonochromeAnalysis;
}

export interface ImageAnalysisResponse {
  status: string;
  filename: string;
  image: ImageDimensions;
  analysis: AnalysisMetrics;
  detected_issues: string[];
  recommended_options: RestorationRecommendations;
  degradation_category?: string;
  elapsed_seconds: number;
}

export interface DamageMaskResponse {
  status: string;
  filename: string;
  detected_components: number;
  repaired_pixels: number;
  coverage_percentage: number;
  confidence_score?: number;
  dispatch_reason?: string | null;
  mask_base64: string;
  overlay_base64: string;
  elapsed_seconds: number;
}

// =====================================================================
// Phase 5.6 Quality Assessment Schemas
// =====================================================================

export interface MetricDetail {
  metric_id: string;
  display_name: string;
  available: boolean;
  score: number | null;
  interpretation: string;
  details?: Record<string, unknown> | null;
}

export interface QualityImageDimensions {
  width: number;
  height: number;
  channels: number;
}

export interface ImageQualityAssessmentResponse {
  status: string;
  filename: string;
  reference_filename?: string | null;
  image: QualityImageDimensions;
  elapsed_seconds: number;
  metrics: Record<string, MetricDetail>;
}
