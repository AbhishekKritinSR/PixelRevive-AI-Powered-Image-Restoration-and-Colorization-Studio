/**
 * Centralized API service layer for communicating with the FastAPI backend.
 * Provides typed methods, error normalization, and download helpers.
 */

import {
  HealthResponse,
  ModelStatusResponse,
  ModelRegistryListResponse,
  RestorationOptions,
  SingleRestorationResponse,
  BatchRestorationResponse,
  ImageAnalysisResponse,
  ImageQualityAssessmentResponse,
  DamageMaskResponse,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

/**
 * Extract an informative error message from an API response or network exception.
 */
async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const errorJson = await response.json();
    if (typeof errorJson.detail === "string") {
      return errorJson.detail;
    }
    if (Array.isArray(errorJson.detail)) {
      return errorJson.detail.map((d: { msg: string }) => d.msg).join(", ");
    }
    return `Server returned HTTP ${response.status}: ${response.statusText}`;
  } catch {
    return `Server error (${response.status} ${response.statusText})`;
  }
}

/**
 * Verify backend operational status and active device.
 */
export async function fetchHealth(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error(await parseErrorResponse(response));
    }
    return (await response.json()) as HealthResponse;
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "TypeError") {
      throw new Error(
        "Cannot reach backend server. Please verify FastAPI is running at " +
          API_BASE_URL
      );
    }
    throw err;
  }
}

/**
 * Inspect model files availability and loaded status.
 */
export async function fetchModelStatus(): Promise<ModelStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/models/status`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }
  return (await response.json()) as ModelStatusResponse;
}

/**
 * Retrieve registered colorization and restoration models from the model registry.
 */
export async function fetchModelRegistry(): Promise<ModelRegistryListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/models`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }
  return (await response.json()) as ModelRegistryListResponse;
}

/**
 * Analyze an uploaded photograph for noise, sharpness, contrast, and monochrome characteristics.
 * Returns empirical diagnostics and rule-based restoration recommendations.
 */
export async function analyzeImage(file: File): Promise<ImageAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file, file.name);

  const response = await fetch(`${API_BASE_URL}/api/v1/restoration/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return (await response.json()) as ImageAnalysisResponse;
}

/**
 * Preview detected scratch damage mask and visual overlay without inpainting.
 */
export async function previewDamageMask(
  file: File,
  threshold: number = 25,
  minLength: number = 10
): Promise<DamageMaskResponse> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("threshold", String(threshold));
  formData.append("min_length", String(minLength));

  const response = await fetch(`${API_BASE_URL}/api/v1/restoration/mask`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return (await response.json()) as DamageMaskResponse;
}

/**
 * Assess photographic image quality via BRISQUE, SSIM, and Colorfulness.
 */
export async function assessQuality(
  targetFile: File | Blob,
  targetFilename: string = "target.png",
  referenceFile?: File | Blob | null,
  referenceFilename: string = "reference.png"
): Promise<ImageQualityAssessmentResponse> {
  const formData = new FormData();
  formData.append("file", targetFile, targetFilename);

  if (referenceFile) {
    formData.append("reference_file", referenceFile, referenceFilename);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/restoration/quality`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return (await response.json()) as ImageQualityAssessmentResponse;
}

/**
 * Restore and colorize an individual photograph with extended Phase 5 parameters.
 */
export async function restoreSingleImage(
  file: File,
  options: RestorationOptions
): Promise<SingleRestorationResponse> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("denoise", String(options.denoise));
  formData.append("contrast", String(options.contrast));
  formData.append("sharpen", String(options.sharpen));
  formData.append("colorize", String(options.colorize));
  formData.append("adaptive_denoise", String(options.adaptive_denoise ?? true));
  formData.append("adaptive_contrast", String(options.adaptive_contrast ?? true));
  formData.append("adaptive_sharpen", String(options.adaptive_sharpen ?? true));
  formData.append("repair", String(options.repair ?? false));
  formData.append("upscale", String(options.upscale ?? false));
  formData.append("scale", String(options.scale ?? 2));
  formData.append("colorization_model", options.colorization_model || "zhang_caffe");
  formData.append("render_factor", String(options.render_factor ?? 14));
  formData.append("inpaint_method", options.inpaint_method || "lama");
  formData.append("face_restore", String(options.face_restore ?? false));
  formData.append("sr_model", options.sr_model || "fsrcnn");
  formData.append("color_saturation", String(options.color_saturation ?? 0.85));
  formData.append("color_temperature", String(options.color_temperature ?? 0.0));

  const response = await fetch(`${API_BASE_URL}/api/v1/restoration/process`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return (await response.json()) as SingleRestorationResponse;
}

/**
 * Process a batch of up to 10 images with per-item fault tolerance and extended options.
 */
export async function restoreBatchImages(
  files: File[],
  options: RestorationOptions
): Promise<BatchRestorationResponse> {
  if (files.length === 0) {
    throw new Error("Please select at least one photograph for batch processing.");
  }
  if (files.length > 10) {
    throw new Error("Batch processing allows a maximum of 10 photographs per request.");
  }

  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file, file.name);
  }
  formData.append("denoise", String(options.denoise));
  formData.append("contrast", String(options.contrast));
  formData.append("sharpen", String(options.sharpen));
  formData.append("colorize", String(options.colorize));
  formData.append("adaptive_denoise", String(options.adaptive_denoise ?? true));
  formData.append("adaptive_contrast", String(options.adaptive_contrast ?? true));
  formData.append("adaptive_sharpen", String(options.adaptive_sharpen ?? true));
  formData.append("repair", String(options.repair ?? false));
  formData.append("upscale", String(options.upscale ?? false));
  formData.append("scale", String(options.scale ?? 2));
  formData.append("colorization_model", options.colorization_model || "zhang_caffe");
  formData.append("render_factor", String(options.render_factor ?? 14));
  formData.append("inpaint_method", options.inpaint_method || "lama");
  formData.append("face_restore", String(options.face_restore ?? false));
  formData.append("sr_model", options.sr_model || "fsrcnn");
  formData.append("color_saturation", String(options.color_saturation ?? 0.85));
  formData.append("color_temperature", String(options.color_temperature ?? 0.0));

  const response = await fetch(`${API_BASE_URL}/api/v1/restoration/batch`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return (await response.json()) as BatchRestorationResponse;
}

/**
 * Convert a Base64 data URI (e.g. "data:image/png;base64,...") to a Blob.
 */
export function dataUriToBlob(dataUri: string): Blob {
  const parts = dataUri.split(",");
  const byteString = atob(parts[1]);
  const mimeMatch = parts[0].match(/:(.*?);/);
  const mimeString = mimeMatch ? mimeMatch[1] : "image/png";

  const arrayBuffer = new ArrayBuffer(byteString.length);
  const uint8Array = new Uint8Array(arrayBuffer);
  for (let i = 0; i < byteString.length; i++) {
    uint8Array[i] = byteString.charCodeAt(i);
  }

  return new Blob([uint8Array], { type: mimeString });
}

/**
 * Client-side helper to trigger file download from a Base64 Data URI.
 */
export function downloadDataUri(dataUri: string, filename: string): void {
  const anchor = document.createElement("a");
  anchor.href = dataUri;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}
