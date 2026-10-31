"""Module: denoiser.py

Purpose:
Provides edge-preserving image denoising using OpenCV's Non-Local Means algorithm,
supporting both fixed-parameter execution and intelligent, noise-adaptive parameter selection.

Responsibilities:
- Validate input image format, channel structure, and data types.
- Provide a deterministic parameter selector mapping noise metrics to Non-Local Means parameters.
- Provide adaptive denoising that scales smoothing strength according to measured noise level.
- Support both 3-channel color (BGR) and single-channel (grayscale) images safely.
- Preserve fine details and skip/minimize filtering on clean images to prevent texture loss.
- Preserve backward compatibility for legacy fixed-strength Non-Local Means calls.

Dependencies:
- cv2 (OpenCV)
- numpy
- dataclasses.dataclass
- backend.src.services.analysis_service.AnalysisService
- src.config (DENOISE_H, DENOISE_H_COLOR, DENOISE_TEMPLATE_WINDOW, DENOISE_SEARCH_WINDOW)
"""

from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

from backend.src.processing.evaluation.heuristics import (
    NOISE_HIGH_THRESHOLD,
    NOISE_LOW_THRESHOLD,
    estimate_noise_sigma,
)
from src.config import (
    DENOISE_H,
    DENOISE_H_COLOR,
    DENOISE_SEARCH_WINDOW,
    DENOISE_TEMPLATE_WINDOW,
)


@dataclass(frozen=True)
class DenoiseParameters:
    """Configuration parameters for Non-Local Means denoising."""

    h: float
    h_color: float
    template_window_size: int = DENOISE_TEMPLATE_WINDOW
    search_window_size: int = DENOISE_SEARCH_WINDOW
    noise_score: float = 0.0
    noise_level: str = "medium"
    skip: bool = False


def select_denoising_parameters(
    noise_score: Optional[float] = None,
    noise_level: Optional[str] = None,
) -> DenoiseParameters:
    """Select optimal Non-Local Means denoising parameters based on noise metrics.

    Thresholds conform to the Phase 5.1 Analysis Engine:
    - Low noise: sigma < 4.0
    - Medium noise: 4.0 <= sigma < 10.0
    - High noise: sigma >= 10.0

    Adaptive Parameter Mapping Strategy:
    1. Low Noise (sigma < 4.0):
       - If sigma < 1.5: Pristine image. Skip filtering completely (skip=True, h=0.0)
         to preserve 100% of fine micro-textures (hair, skin pores, fabric, leaves).
       - If 1.5 <= sigma < 4.0: Minimal gentle filtering (h=3.0, h_color=3.0) to clean
         subtle electronic noise without blurring edges.
    2. Medium Noise (4.0 <= sigma < 10.0):
       - Standard moderate filtering (h=7.0, h_color=7.0) to smooth film grain while
         preserving structural boundaries.
    3. High Noise (sigma >= 10.0):
       - Strong filtering (h=12.0 to 16.0, h_color=h) to suppress heavy grain or sensor noise.

    Args:
        noise_score: Estimated noise standard deviation (sigma >= 0.0).
        noise_level: Qualitative classification ('low', 'medium', 'high').

    Returns:
        DenoiseParameters instance containing h, h_color, window sizes, and skip flag.
    """
    # 1. Parameter selection based on numeric noise score
    if noise_score is not None:
        try:
            score = max(0.0, float(noise_score))
        except (ValueError, TypeError):
            score = 0.0

        if score < NOISE_LOW_THRESHOLD:  # < 4.0
            if score < 1.5:
                # Pristine clean image: bypass filtering completely to preserve fine detail
                return DenoiseParameters(
                    h=0.0,
                    h_color=0.0,
                    noise_score=round(score, 2),
                    noise_level="low",
                    skip=True,
                )
            else:
                # Very mild noise: gentle smoothing
                return DenoiseParameters(
                    h=3.0,
                    h_color=3.0,
                    noise_score=round(score, 2),
                    noise_level="low",
                    skip=False,
                )
        elif score < NOISE_HIGH_THRESHOLD:  # 4.0 <= score < 10.0
            # Moderate noise: balanced smoothing
            return DenoiseParameters(
                h=7.0,
                h_color=7.0,
                noise_score=round(score, 2),
                noise_level="medium",
                skip=False,
            )
        else:  # score >= 10.0
            # High noise: strong smoothing scaled to noise intensity
            h_val = float(min(16.0, max(12.0, round(score * 0.9, 1))))
            return DenoiseParameters(
                h=h_val,
                h_color=h_val,
                noise_score=round(score, 2),
                noise_level="high",
                skip=False,
            )

    # 2. Parameter selection based on qualitative classification string
    if noise_level is not None:
        level_str = str(noise_level).strip().lower()
        if level_str == "low":
            return DenoiseParameters(
                h=3.0,
                h_color=3.0,
                noise_score=2.0,
                noise_level="low",
                skip=False,
            )
        elif level_str == "medium":
            return DenoiseParameters(
                h=7.0,
                h_color=7.0,
                noise_score=6.0,
                noise_level="medium",
                skip=False,
            )
        elif level_str == "high":
            return DenoiseParameters(
                h=12.0,
                h_color=12.0,
                noise_score=12.0,
                noise_level="high",
                skip=False,
            )

    # 3. Fallback default (safe medium Non-Local Means configuration)
    return DenoiseParameters(
        h=float(DENOISE_H),
        h_color=float(DENOISE_H_COLOR),
        noise_score=0.0,
        noise_level="medium",
        skip=False,
    )


def _apply_texture_guided_residual(
    image: np.ndarray,
    denoised: np.ndarray,
    is_color: bool,
    texture_weight: float = 0.35,
) -> np.ndarray:
    """Blend high-frequency detail back into textured areas while keeping flat regions clean.

    Flat areas (skies, walls) have near-zero gradient magnitude, ensuring noise is not
    re-introduced into smooth surfaces. High-gradient areas (fabrics, hair, pores)
    receive proportional residual injection to prevent the plastic/waxy appearance
    common in naive Non-Local Means filtering.

    VIT BCSE403L Mapping:
        Module 2: Spatial Filtering (Sobel gradient operators, spatial domain blending)
        Module 4: Image Restoration (adaptive spatial noise filtering, detail preservation)
    """
    if texture_weight <= 0.0:
        return denoised

    if is_color:
        gray_denoised = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
    else:
        gray_denoised = denoised.squeeze() if denoised.ndim == 3 else denoised

    sobel_x = cv2.Sobel(gray_denoised, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray_denoised, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = cv2.magnitude(sobel_x, sobel_y)
    grad_mag = cv2.GaussianBlur(grad_mag, (5, 5), 1.5)
    text_mask = np.clip((grad_mag - 4.0) / 14.0, 0.0, 1.0)

    if is_color:
        text_mask = text_mask[:, :, np.newaxis]
    elif denoised.ndim == 3:
        text_mask = text_mask[:, :, np.newaxis]

    detail = image.astype(np.float32) - denoised.astype(np.float32)
    clamped_detail = np.clip(detail, -7.0, 7.0)
    blended = np.clip(
        denoised.astype(np.float32) + texture_weight * text_mask * clamped_detail, 0, 255
    ).astype(np.uint8)
    return blended


def adaptive_denoise_image(
    image: np.ndarray,
    noise_score: Optional[float] = None,
    params: Optional[DenoiseParameters] = None,
    preserve_texture: bool = True,
    texture_weight: float = 0.35,
) -> Tuple[np.ndarray, DenoiseParameters]:
    """Denoise an image adaptively based on its measured noise characteristics.

    Preserves fine micro-textures by minimizing or skipping filtering on low-noise images,
    while applying robust Non-Local Means filtering on high-noise images with high-frequency
    photographic texture residual blending.

    Args:
        image:
            Input BGR or grayscale uint8 NumPy array of shape (H, W, 3) or (H, W).
        noise_score:
            Optional precomputed noise estimate. If omitted, noise is estimated via AnalysisService.
        params:
            Optional preselected DenoiseParameters instance.
        preserve_texture:
            Whether to blend back high-frequency micro-texture to prevent plastic/waxy appearance.
        texture_weight:
            Blending coefficient for clamped texture residual (default 0.35).

    Returns:
        Tuple of (denoised_image_array, applied_DenoiseParameters).

    Raises:
        ValueError: If input is not a valid NumPy array or has unsupported dimensions.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")

    if image.dtype != np.uint8:
        raise ValueError(f"Input image must have dtype uint8, but got {image.dtype}.")

    # Validate channel dimensions
    is_color = False
    if image.ndim == 3 and image.shape[2] == 3:
        is_color = True
    elif image.ndim == 2 or (image.ndim == 3 and image.shape[2] == 1):
        is_color = False
    else:
        raise ValueError(
            f"Expected a 3-channel color image (H, W, 3) or single-channel grayscale (H, W), "
            f"but got shape {image.shape}."
        )

    # 1. Determine parameters
    if params is None:
        if noise_score is None:
            # Reuse blind noise estimation
            sigma, level = estimate_noise_sigma(image)
            selected_params = select_denoising_parameters(
                noise_score=sigma,
                noise_level=level,
            )
        else:
            selected_params = select_denoising_parameters(noise_score=noise_score)
    else:
        selected_params = params

    # 2. Check if denoising should be skipped (e.g. pristine low-noise images)
    if selected_params.skip or selected_params.h <= 0.0:
        return image.copy(), selected_params

    # 3. Apply Non-Local Means filtering
    if is_color:
        denoised = cv2.fastNlMeansDenoisingColored(
            image,
            None,
            selected_params.h,
            selected_params.h_color,
            selected_params.template_window_size,
            selected_params.search_window_size,
        )
    else:
        # Grayscale single-channel image
        gray_input = image[:, :, 0] if image.ndim == 3 else image
        denoised = cv2.fastNlMeansDenoising(
            gray_input,
            None,
            selected_params.h,
            selected_params.template_window_size,
            selected_params.search_window_size,
        )
        if image.ndim == 3 and image.shape[2] == 1:
            denoised = denoised[:, :, np.newaxis]

    # 4. Detail-Preserving High-Frequency Residual Blending (Anti-Smoothing)
    if preserve_texture and texture_weight > 0.0:
        denoised = _apply_texture_guided_residual(
            image, denoised, is_color=is_color, texture_weight=texture_weight
        )

    return denoised, selected_params


def denoise_image(
    image: np.ndarray,
    h: Optional[int] = None,
    h_color: Optional[int] = None,
    template_window_size: int = DENOISE_TEMPLATE_WINDOW,
    search_window_size: int = DENOISE_SEARCH_WINDOW,
    adaptive: bool = False,
    preserve_texture: bool = True,
    texture_weight: float = 0.35,
) -> np.ndarray:
    """Remove sensor and scan noise while preserving edges via Non-Local Means denoising.

    Supports both fixed-parameter execution (default for direct calls) and adaptive
    noise-aware execution.

    Args:
        image:
            Input BGR image as a uint8 NumPy array of shape (height, width, 3),
            or grayscale image of shape (height, width).
        h:
            Filter strength controlling luminance noise removal (default: DENOISE_H = 8).
        h_color:
            Filter strength controlling chrominance noise removal (default: DENOISE_H_COLOR = 8).
        template_window_size:
            Odd integer specifying the template patch size (default: 7).
        search_window_size:
            Odd integer specifying the search area window (default: 21).
        adaptive:
            If True, automatically estimates image noise and selects optimal parameters.
        preserve_texture:
            Whether to blend back high-frequency photographic texture.
        texture_weight:
            Blending coefficient for clamped texture residual.

    Returns:
        Denoised BGR or grayscale image as a uint8 NumPy array.
    """
    if adaptive:
        result, _ = adaptive_denoise_image(
            image,
            preserve_texture=preserve_texture,
            texture_weight=texture_weight,
        )
        return result

    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")

    # Validate channel dimensions
    is_color = False
    if image.ndim == 3 and image.shape[2] == 3:
        is_color = True
    elif image.ndim == 2 or (image.ndim == 3 and image.shape[2] == 1):
        is_color = False
    else:
        raise ValueError(
            f"Expected a 3-channel color image (H, W, 3) or single-channel grayscale (H, W), "
            f"but got shape {image.shape}."
        )

    h_val = float(h if h is not None else DENOISE_H)
    h_col_val = float(h_color if h_color is not None else DENOISE_H_COLOR)

    if is_color:
        denoised = cv2.fastNlMeansDenoisingColored(
            image,
            None,
            h_val,
            h_col_val,
            template_window_size,
            search_window_size,
        )
    else:
        gray_input = image[:, :, 0] if image.ndim == 3 else image
        denoised = cv2.fastNlMeansDenoising(
            gray_input,
            None,
            h_val,
            template_window_size,
            search_window_size,
        )
        if image.ndim == 3 and image.shape[2] == 1:
            denoised = denoised[:, :, np.newaxis]

    if preserve_texture and texture_weight > 0.0:
        denoised = _apply_texture_guided_residual(
            image, denoised, is_color=is_color, texture_weight=texture_weight
        )

    return denoised
