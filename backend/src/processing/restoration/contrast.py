"""Module: contrast.py

Purpose:
Provides adaptive local contrast enhancement using CLAHE (Contrast Limited
Adaptive Histogram Equalization) applied strictly to the Lightness channel
in CIE LAB color space.

Responsibilities:
- Validate input image format.
- Transform BGR image to CIE LAB color space.
- Apply CLAHE exclusively to the L (Lightness) channel to boost local dynamic range.
- Preserve the chromatic A and B channels without alteration to avoid color shift.
- Recombine channels and transform back to BGR.

Inputs:
- image: 3-channel BGR uint8 NumPy array with shape (H, W, 3).
- clip_limit: Contrast clipping limit (default: CLAHE_CLIP_LIMIT = 2.5).
- tile_grid_size: Number of contextual grid tiles (default: CLAHE_TILE_GRID_SIZE = (8, 8)).

Outputs:
- Contrast-enhanced 3-channel BGR uint8 NumPy array with identical shape.

Dependencies:
- cv2 (OpenCV)
- numpy
- src.config (CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE)

This module does not:
- Apply global histogram equalization (which blows out highlights and boosts noise).
- Modify A/B color channels.
- Perform denoising or edge sharpening.
"""

import cv2
import numpy as np

from src.config import CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE


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

