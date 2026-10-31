"""Module: ssim.py

Purpose:
Provides Structural Similarity Index Measure (SSIM) reference-based image quality
and structural fidelity assessment.

Responsibilities:
- Validate that target and reference images share identical dimensions and compatible channel counts.
- Compute local luminance, contrast, and structure comparisons using standard Gaussian windowing.
- Support both multi-channel color (BGR) and single-channel grayscale comparisons.
- Return structured similarity metrics with per-channel breakdown and technical interpretation.

Scientific Background:
Wang, Bovik, Sheikh, and Simoncelli, "Image Quality Assessment: From Error Visibility to Structural Similarity",
IEEE Transactions on Image Processing, 2004.
SSIM models structural distortion under the assumption that human visual perception is adapted
to extract structural information from a scene:
    SSIM(x, y) = [l(x, y)]^alpha * [c(x, y)]^beta * [s(x, y)]^gamma
With standard exponents alpha = beta = gamma = 1 and stability constants C1 = (K1 * L)^2, C2 = (K2 * L)^2
where K1 = 0.01, K2 = 0.03, and dynamic range L = 255:
    SSIM(x, y) = ((2 * mu_x * mu_y + C1) * (2 * sigma_xy + C2)) /
                 ((mu_x^2 + mu_y^2 + C1) * (sigma_x^2 + sigma_y^2 + C2))

Dependencies:
- cv2 (OpenCV)
- numpy
"""

from typing import Dict, Optional, Tuple

import cv2
import numpy as np


# Standard SSIM stability constants for 8-bit images (L = 255)
K1: float = 0.01
K2: float = 0.03
L: float = 255.0

C1: float = (K1 * L) ** 2  # 6.5025
C2: float = (K2 * L) ** 2  # 58.5225


def _compute_channel_ssim(
    img1: np.ndarray,
    img2: np.ndarray,
    gaussian_kernel_size: int = 11,
    sigma: float = 1.5,
) -> float:
    """Compute mean SSIM on a single 2D float64 channel using Gaussian spatial weighting.

    Args:
        img1: 2D float64 array of shape (H, W).
        img2: 2D float64 array of shape (H, W).
        gaussian_kernel_size: Size of Gaussian blur kernel (default 11x11).
        sigma: Standard deviation of Gaussian weighting (default 1.5).

    Returns:
        Scalar mean SSIM value in range [-1.0, 1.0].
    """
    # Local means via Gaussian filtering
    mu1 = cv2.GaussianBlur(img1, (gaussian_kernel_size, gaussian_kernel_size), sigma)
    mu2 = cv2.GaussianBlur(img2, (gaussian_kernel_size, gaussian_kernel_size), sigma)

    mu1_sq = mu1 * mu1
    mu2_sq = mu2 * mu2
    mu1_mu2 = mu1 * mu2

    # Local variances and covariance
    sigma1_sq = cv2.GaussianBlur(img1 * img1, (gaussian_kernel_size, gaussian_kernel_size), sigma) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(img2 * img2, (gaussian_kernel_size, gaussian_kernel_size), sigma) - mu2_sq
    sigma12 = cv2.GaussianBlur(img1 * img2, (gaussian_kernel_size, gaussian_kernel_size), sigma) - mu1_mu2

    # Full SSIM formula
    numerator = (2.0 * mu1_mu2 + C1) * (2.0 * sigma12 + C2)
    denominator = (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)

    ssim_map = numerator / (denominator + 1e-12)
    return float(np.mean(ssim_map))


def compute_ssim(
    processed_image: np.ndarray,
    reference_image: np.ndarray,
) -> Tuple[float, Dict[str, float], str, str]:
    """Compute Structural Similarity Index (SSIM) between processed and reference images.

    Args:
        processed_image:
            Target image array of shape (H, W) or (H, W, 3) with uint8 dtype.
        reference_image:
            Ground-truth or pre-processing reference image array with matching shape and uint8 dtype.

    Returns:
        Tuple of:
            - ssim_score (float): Mean SSIM value across active channels [-1.0, 1.0].
            - channel_scores (Dict[str, float]): Per-channel SSIM breakdown.
            - comparison_mode (str): 'color' or 'grayscale'.
            - interpretation (str): Factual explanation of structural similarity.

    Raises:
        ValueError:
            If inputs are not valid NumPy arrays, have mismatched dimensions,
            mismatched channel counts, non-uint8 dtypes, or dimensions < 11x11.
    """
    if not isinstance(processed_image, np.ndarray) or not isinstance(reference_image, np.ndarray):
        raise ValueError("Both processed_image and reference_image must be valid NumPy arrays.")

    if processed_image.size == 0 or reference_image.size == 0:
        raise ValueError("Image arrays must not be empty.")

    if processed_image.dtype != np.uint8 or reference_image.dtype != np.uint8:
        raise ValueError(
            f"Both images must have uint8 dtype. Got processed: {processed_image.dtype}, reference: {reference_image.dtype}."
        )

    if processed_image.shape != reference_image.shape:
        raise ValueError(
            f"Dimension mismatch: processed image shape {processed_image.shape} does not match "
            f"reference image shape {reference_image.shape}. SSIM requires identical spatial dimensions."
        )

    h, w = processed_image.shape[:2]
    if h < 11 or w < 11:
        raise ValueError(
            f"Image dimensions ({w}x{h}) are too small for standard 11x11 Gaussian SSIM windowing (minimum 11x11)."
        )

    # Determine comparison mode and calculate per-channel SSIM
    channel_scores: Dict[str, float] = {}

    if processed_image.ndim == 2 or (processed_image.ndim == 3 and processed_image.shape[2] == 1):
        # Grayscale comparison
        mode = "grayscale"
        img1 = processed_image.squeeze().astype(np.float64)
        img2 = reference_image.squeeze().astype(np.float64)
        score = _compute_channel_ssim(img1, img2)
        channel_scores["luminance"] = round(score, 4)
        overall_ssim = score
    elif processed_image.ndim == 3 and processed_image.shape[2] == 3:
        # 3-channel color comparison (BGR order)
        mode = "color"
        channel_names = ["blue", "green", "red"]
        scores = []
        for c in range(3):
            c_score = _compute_channel_ssim(
                processed_image[:, :, c].astype(np.float64),
                reference_image[:, :, c].astype(np.float64),
            )
            c_score = float(np.clip(c_score, -1.0, 1.0))
            channel_scores[channel_names[c]] = round(c_score, 4)
            scores.append(c_score)

        overall_ssim = float(np.mean(scores))
    else:
        raise ValueError(f"Unsupported image shape {processed_image.shape} for SSIM comparison.")

    overall_rounded = round(float(np.clip(overall_ssim, -1.0, 1.0)), 4)

    interpretation = (
        f"SSIM structural similarity index: {overall_rounded:.4f} (range [-1.0, 1.0]). "
        "Measures luminance, contrast, and structural correlation relative to the reference image. "
        "A higher score indicates greater structural preservation, not necessarily superior aesthetic restoration."
    )

    return overall_rounded, channel_scores, mode, interpretation
