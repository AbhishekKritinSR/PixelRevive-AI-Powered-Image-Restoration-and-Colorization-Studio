/**
 * Centralized API service layer for communicating with the FastAPI backend.
 * Provides typed methods, error normalization, and download helpers.
 */

import {
  HealthResponse,
  ModelStatusResponse,
  RestorationOptions,
  SingleRestorationResponse,
  BatchRestorationResponse,
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
 * Restore and colorize an individual photograph.
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
 * Process a batch of up to 10 images with per-item fault tolerance.
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

