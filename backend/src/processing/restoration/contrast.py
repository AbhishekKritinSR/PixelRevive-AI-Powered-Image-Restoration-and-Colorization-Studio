"""Module: contrast.py

Purpose:
Provides adaptive local contrast enhancement using CLAHE (Contrast Limited
Adaptive Histogram Equalization) applied strictly to the Lightness channel
in CIE LAB color space, with intelligent image-quality-based clean-image protection.

Responsibilities:
- Validate input image format.
- Transform BGR image to CIE LAB color space.
- Apply CLAHE exclusively to the L (Lightness) channel to boost local dynamic range.
- Preserve the chromatic A and B channels without alteration to avoid color shift.
- Recombine channels and transform back to BGR.
- Provide adaptive contrast evaluation to bypass CLAHE on images that already possess
  adequate natural dynamic range, preventing over-enhancement and false contouring.
"""

from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np

from src.config import CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE

CONTRAST_LOW_STD_THRESHOLD: float = 22.0
CONTRAST_LOW_RANGE_THRESHOLD: float = 65.0


@dataclass(frozen=True)
class ContrastParameters:
    """Diagnostic parameters and decision metadata for CLAHE contrast enhancement."""

    applied: bool
    skip: bool
    reason: str
    contrast_score: float
    dynamic_range: float
    clip_limit: float = CLAHE_CLIP_LIMIT
    tile_grid_size: Tuple[int, int] = CLAHE_TILE_GRID_SIZE


def evaluate_contrast_protection(
    image: np.ndarray,
    clip_limit: float = CLAHE_CLIP_LIMIT,
    tile_grid_size: Tuple[int, int] = CLAHE_TILE_GRID_SIZE,
    force: bool = False,
) -> ContrastParameters:
    """Evaluate image dynamic range to determine whether CLAHE enhancement is needed.

    Distinguishes genuinely faded or low-contrast images from images that already
    exhibit adequate natural contrast distribution.

    Args:
        image: Input BGR uint8 array of shape (H, W, 3) or grayscale (H, W).
        clip_limit: Threshold for contrast limiting.
        tile_grid_size: Tuple (grid_x, grid_y) for local equalization.
        force: If True, overrides adaptive protection and forces CLAHE execution.

    Returns:
        ContrastParameters containing decision flags, measured indicators, and explanation.
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
        return ContrastParameters(
            applied=False,
            skip=True,
            reason="Bypassed: flat image with zero luminance variance.",
            contrast_score=0.0,
            dynamic_range=0.0,
            clip_limit=clip_limit,
            tile_grid_size=tile_grid_size,
        )

    std = float(gray.std())
    p1, p5, p95, p99 = [float(x) for x in np.percentile(gray, [1, 5, 95, 99])]
    span90 = p95 - p5
    span98 = p99 - p1
    dynamic_range = span98

    if force:
        return ContrastParameters(
            applied=True,
            skip=False,
            reason=(
                f"Applied: Contrast Limited Adaptive Histogram Equalization (CLAHE) on luminance "
                f"channel (explicit user request: std={std:.1f}, dynamic range={dynamic_range:.1f})."
            ),
            contrast_score=round(std, 2),
            dynamic_range=round(dynamic_range, 2),
            clip_limit=clip_limit,
            tile_grid_size=tile_grid_size,
        )

    # Faded / low-contrast detection:
    # A photograph requires contrast expansion if its luminance std is below threshold
    # OR if its 90th percentile span is compressed (<62) with dynamic range < 65.
    is_low_contrast = std < CONTRAST_LOW_STD_THRESHOLD or (
        span90 < 62.0 and span98 < CONTRAST_LOW_RANGE_THRESHOLD
    )

    if is_low_contrast:
        reason = (
            f"Applied: Contrast Limited Adaptive Histogram Equalization (CLAHE) on luminance channel "
            f"(low dynamic range: std={std:.1f} < {CONTRAST_LOW_STD_THRESHOLD:.1f}, "
            f"dynamic range={dynamic_range:.1f} < {CONTRAST_LOW_RANGE_THRESHOLD:.1f})."
        )
        return ContrastParameters(
            applied=True,
            skip=False,
            reason=reason,
            contrast_score=round(std, 2),
            dynamic_range=round(dynamic_range, 2),
            clip_limit=clip_limit,
            tile_grid_size=tile_grid_size,
        )
    else:
        reason = (
            f"Bypassed: image exhibits adequate natural contrast (std={std:.1f} >= "
            f"{CONTRAST_LOW_STD_THRESHOLD:.1f}, dynamic range={dynamic_range:.1f} >= "
            f"{CONTRAST_LOW_RANGE_THRESHOLD:.1f}). CLAHE skipped to prevent over-enhancement."
        )
        return ContrastParameters(
            applied=False,
            skip=True,
            reason=reason,
            contrast_score=round(std, 2),
            dynamic_range=round(dynamic_range, 2),
            clip_limit=clip_limit,
            tile_grid_size=tile_grid_size,
        )


def adaptive_enhance_contrast(
    image: np.ndarray,
    clip_limit: float = CLAHE_CLIP_LIMIT,
    tile_grid_size: Tuple[int, int] = CLAHE_TILE_GRID_SIZE,
    force: bool = False,
) -> Tuple[np.ndarray, ContrastParameters]:
    """Adaptively enhance contrast on the Lightness channel with clean-image protection.

    Args:
        image: Input BGR uint8 NumPy array of shape (H, W, 3).
        clip_limit: Threshold for contrast limiting.
        tile_grid_size: Contextual grid tile dimensions.
        force: If True, forces CLAHE execution without adaptive bypass.

    Returns:
        Tuple of (enhanced or bypassed BGR image, ContrastParameters).
    """
    params = evaluate_contrast_protection(
        image, clip_limit=clip_limit, tile_grid_size=tile_grid_size, force=force
    )
    if params.skip:
        return image.copy(), params

    enhanced = enhance_contrast(image, clip_limit=clip_limit, tile_grid_size=tile_grid_size)
    return enhanced, params


def enhance_contrast(
    image: np.ndarray,
    clip_limit: float = CLAHE_CLIP_LIMIT,
    tile_grid_size: tuple[int, int] = CLAHE_TILE_GRID_SIZE,
) -> np.ndarray:
    """Boost local contrast using CLAHE on the Lightness channel in CIE LAB space.

    Standard histogram equalization flattens intensity across the whole image,
    frequently creating washed-out regions and unnatural artifacts. CLAHE divides
    the image into contextual tiles (e.g. 8x8), clips the local histogram at
    `clip_limit` to prevent noise amplification, redistributes clipped counts,
    and applies bilinear interpolation between tile borders.

    Applying CLAHE to the L (lightness) channel ensures only perceptual brightness
    and local contrast are enhanced, leaving the A (green-red) and B (blue-yellow)
    chrominance channels completely unchanged.

    Args:
        image:
            Input BGR image as a uint8 NumPy array of shape (height, width, 3).
        clip_limit:
            Threshold for contrast limiting. Higher values yield stronger local
            contrast but increase the risk of highlighting residual noise.
        tile_grid_size:
            Tuple (grid_x, grid_y) determining the grid resolution for local equalization.

    Returns:
        Contrast-enhanced BGR image as a uint8 NumPy array.

    Raises:
        ValueError:
            If input is not a 3-channel NumPy array.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"Expected a 3-channel color image (H, W, 3), but got shape {image.shape}."
        )

    # Convert BGR -> CIE LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # Initialize CLAHE operator and process luminance only
    clahe = cv2.createCLAHE(
        clipLimit=clip_limit,
        tileGridSize=tile_grid_size,
    )
    enhanced_l = clahe.apply(l_channel)

    # Merge untouched chromatic channels with enhanced luminance
    enhanced_lab = cv2.merge((enhanced_l, a_channel, b_channel))

    # Convert back to standard BGR color space
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

