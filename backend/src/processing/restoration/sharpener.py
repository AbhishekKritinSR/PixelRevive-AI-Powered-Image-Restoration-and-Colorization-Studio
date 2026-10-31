"""Module: sharpener.py

Purpose:
Provides high-frequency edge sharpening using a discrete unity-gain Laplacian
convolution kernel, with intelligent image-quality-based clean-image protection.

Responsibilities:
- Validate input image format.
- Apply 2D spatial convolution with the unity-gain Laplacian kernel.
- Ensure output maintains original baseline regional brightness.
- Preserve image shape and uint8 data type.
- Provide adaptive sharpness evaluation to bypass sharpening on images that are already
  sufficiently sharp, images with high noise (to prevent grain amplification), and
  pristine continuous-tone images (to prevent introducing artificial edge steps).
"""

from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np

from backend.src.processing.evaluation.heuristics import estimate_noise_sigma
from src.config import SHARPEN_KERNEL

SHARPEN_MAX_NOISE_THRESHOLD: float = 8.0
SHARPEN_ALREADY_SHARP_THRESHOLD: float = 120.0
SHARPEN_PRISTINE_NOISE_THRESHOLD: float = 1.5
SHARPEN_PRISTINE_GRAD_THRESHOLD: float = 15.0


@dataclass(frozen=True)
class SharpenParameters:
    """Diagnostic parameters and decision metadata for Laplacian sharpening."""

    applied: bool
    skip: bool
    reason: str
    sharpness_score: float
    noise_sigma: float
    edge_strength: float


def evaluate_sharpen_protection(
    image: np.ndarray,
    kernel: np.ndarray = SHARPEN_KERNEL,
    force: bool = False,
) -> SharpenParameters:
    """Evaluate image sharpness, noise, and gradient strength to determine if sharpening is needed.

    Args:
        image: Input BGR uint8 array of shape (H, W, 3) or grayscale (H, W).
        kernel: 2D convolution kernel.
        force: If True, overrides adaptive protection and forces sharpening execution.

    Returns:
        SharpenParameters containing decision flags, measured indicators, and explanation.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")
    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 image, got {image.dtype}.")

    gray = (
        cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if image.ndim == 3 and image.shape[2] == 3
        else image
    )

    if gray.size == 0 or float(gray.std()) == 0.0:
        return SharpenParameters(
            applied=False,
            skip=True,
            reason="Bypassed: flat image with zero high-frequency variance.",
            sharpness_score=0.0,
            noise_sigma=0.0,
            edge_strength=0.0,
        )

    lap = cv2.Laplacian(gray, cv2.CV_64F)
    lap_var = float(lap.var())
    if np.isnan(lap_var) or np.isinf(lap_var):
        lap_var = 0.0

    # Noise sigma estimation
    noise_sigma, _ = estimate_noise_sigma(gray)

    # Sobel gradient magnitude (95th percentile represents primary structural edge strength)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    grad_mag = np.sqrt(sobel_x**2 + sobel_y**2)
    p95_grad = float(np.percentile(grad_mag, 95))

    if force:
        return SharpenParameters(
            applied=True,
            skip=False,
            reason=(
                f"Applied: unity-gain high-pass Laplacian sharpening for edge recovery "
                f"(explicit user request: Laplacian variance={lap_var:.1f}, noise sigma={noise_sigma:.2f})."
            ),
            sharpness_score=round(lap_var, 2),
            noise_sigma=round(noise_sigma, 2),
            edge_strength=round(p95_grad, 2),
        )

    # 1. High noise safeguard: avoid amplifying photographic grain
    if noise_sigma >= SHARPEN_MAX_NOISE_THRESHOLD:
        reason = (
            f"Bypassed: elevated noise level (sigma={noise_sigma:.2f} >= "
            f"{SHARPEN_MAX_NOISE_THRESHOLD:.1f}) precludes sharpening to prevent grain amplification."
        )
        return SharpenParameters(
            applied=False,
            skip=True,
            reason=reason,
            sharpness_score=round(lap_var, 2),
            noise_sigma=round(noise_sigma, 2),
            edge_strength=round(p95_grad, 2),
        )

    # 2. Already sharp safeguard: avoid haloing and ringing artifacts
    if lap_var >= SHARPEN_ALREADY_SHARP_THRESHOLD:
        reason = (
            f"Bypassed: image already exhibits sufficient edge sharpness "
            f"(Laplacian variance={lap_var:.1f} >= {SHARPEN_ALREADY_SHARP_THRESHOLD:.1f}). "
            "Sharpening skipped to prevent haloing."
        )
        return SharpenParameters(
            applied=False,
            skip=True,
            reason=reason,
            sharpness_score=round(lap_var, 2),
            noise_sigma=round(noise_sigma, 2),
            edge_strength=round(p95_grad, 2),
        )

    # 3. Pristine smooth continuous-tone safeguard: avoid artificial gradient steps
    if noise_sigma < SHARPEN_PRISTINE_NOISE_THRESHOLD and p95_grad < SHARPEN_PRISTINE_GRAD_THRESHOLD:
        reason = (
            f"Bypassed: pristine continuous-tone image (noise sigma={noise_sigma:.2f} < "
            f"{SHARPEN_PRISTINE_NOISE_THRESHOLD:.1f}, edge grad={p95_grad:.1f} < "
            f"{SHARPEN_PRISTINE_GRAD_THRESHOLD:.1f}). Sharpening skipped to preserve smooth tones."
        )
        return SharpenParameters(
            applied=False,
            skip=True,
            reason=reason,
            sharpness_score=round(lap_var, 2),
            noise_sigma=round(noise_sigma, 2),
            edge_strength=round(p95_grad, 2),
        )

    # 4. Genuinely soft / blurred image with structural edges
    reason = (
        f"Applied: unity-gain high-pass Laplacian sharpening for edge recovery "
        f"(Laplacian variance={lap_var:.1f} < {SHARPEN_ALREADY_SHARP_THRESHOLD:.1f}, "
        f"noise sigma={noise_sigma:.2f})."
    )
    return SharpenParameters(
        applied=True,
        skip=False,
        reason=reason,
        sharpness_score=round(lap_var, 2),
        noise_sigma=round(noise_sigma, 2),
        edge_strength=round(p95_grad, 2),
    )


def adaptive_sharpen_image(
    image: np.ndarray,
    kernel: np.ndarray = SHARPEN_KERNEL,
    force: bool = False,
) -> Tuple[np.ndarray, SharpenParameters]:
    """Adaptively sharpen image edges with noise-aware clean-image protection.

    Args:
        image: Input BGR uint8 NumPy array of shape (H, W, 3).
        kernel: 2D convolution kernel.
        force: If True, forces sharpening execution without adaptive bypass.

    Returns:
        Tuple of (sharpened or bypassed BGR image, SharpenParameters).
    """
    params = evaluate_sharpen_protection(image, kernel=kernel, force=force)
    if params.skip:
        return image.copy(), params

    sharpened = sharpen_image(image, kernel=kernel)
    return sharpened, params


def sharpen_image(
    image: np.ndarray,
    kernel: np.ndarray = SHARPEN_KERNEL,
) -> np.ndarray:
    """Sharpen image edges using a unity-gain discrete Laplacian kernel.

    The kernel:
        [[ 0, -1,  0],
         [-1,  5, -1],
         [ 0, -1,  0]]
    approximates subtracting the second spatial derivative (discrete Laplacian)
    from the original signal: I_sharp = I - c * nabla^2(I).

    Critical Unity-Gain Property:
    The coefficients sum to exactly 1.0 (0 - 1 + 0 - 1 + 5 - 1 + 0 - 1 + 0 = 1).
    For flat/homogeneous regions where all neighboring pixels have intensity V:
        V * (-1 - 1 - 1 - 1 + 5) = V * 1 = V
    This strictly preserves original regional brightness without inflating exposure.

    Args:
        image:
            Input BGR image as a uint8 NumPy array of shape (height, width, 3).
        kernel:
            A 2D NumPy float or integer kernel of odd dimensions (e.g. 3x3).

    Returns:
        Sharpened BGR image as a uint8 NumPy array.

    Raises:
        ValueError:
            If input image is not a 3-channel NumPy array.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"Expected a 3-channel color image (H, W, 3), but got shape {image.shape}."
        )

    # ddepth=-1 means the output image will have the same depth as the source (uint8)
    return cv2.filter2D(
        image,
        -1,
        kernel,
    )

