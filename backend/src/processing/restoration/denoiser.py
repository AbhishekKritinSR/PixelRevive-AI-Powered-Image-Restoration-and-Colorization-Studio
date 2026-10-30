"""Module: denoiser.py

Purpose:
Provides edge-preserving image denoising using OpenCV's Non-Local Means algorithm.

Responsibilities:
- Validate input image format and dimensions.
- Apply Non-Local Means color denoising (cv2.fastNlMeansDenoisingColored).
- Return the denoised image preserving array shape, dtype (uint8), and color space (BGR).

Inputs:
- image: 3-channel BGR uint8 NumPy array with shape (H, W, 3).
- h: Filter strength for luminance component (default: DENOISE_H = 8).
- h_color: Filter strength for chrominance components (default: DENOISE_H_COLOR = 8).
- template_window_size: Size of local patch used for similarity comparison (default: 7).
- search_window_size: Size of window searched for similar patches (default: 21).

Outputs:
- Denoised 3-channel BGR uint8 NumPy array with identical dimensions.

Dependencies:
- cv2 (OpenCV)
- numpy
- src.config (DENOISE_H, DENOISE_H_COLOR, DENOISE_TEMPLATE_WINDOW, DENOISE_SEARCH_WINDOW)

This module does not:
- Handle file I/O or web requests.
- Convert color spaces (it operates directly on BGR).
- Modify contrast or sharpen edges.
"""

import cv2
import numpy as np

from src.config import (
    DENOISE_H,
    DENOISE_H_COLOR,
    DENOISE_SEARCH_WINDOW,
    DENOISE_TEMPLATE_WINDOW,
)


def denoise_image(
    image: np.ndarray,
    h: int = DENOISE_H,
    h_color: int = DENOISE_H_COLOR,
    template_window_size: int = DENOISE_TEMPLATE_WINDOW,
    search_window_size: int = DENOISE_SEARCH_WINDOW,
) -> np.ndarray:
    """Remove sensor and scan noise while preserving edges via Non-Local Means denoising.

    Non-Local Means (Buades et al., 2005) computes pixel estimates as a weighted
    average of surrounding patches with similar texture and structure, rather than
    blurring local neighborhoods like a Gaussian or bilateral filter.

    Args:
        image:
            Input BGR image as a uint8 NumPy array of shape (height, width, 3).
        h:
            Filter strength controlling luminance noise removal. Larger values
            remove more noise but risk softening subtle image textures.
        h_color:
            Filter strength controlling chrominance noise removal.
        template_window_size:
            Odd integer specifying the template patch size (e.g. 7 for a 7x7 patch).
        search_window_size:
            Odd integer specifying the search area window (e.g. 21 for a 21x21 window).

    Returns:
        Denoised BGR image as a uint8 NumPy array with the same shape as the input.

    Raises:
        ValueError:
            If input image is None, not a NumPy array, or does not have 3 channels.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"Expected a 3-channel color image (H, W, 3), but got shape {image.shape}."
        )

    # cv2.fastNlMeansDenoisingColored processes luminance and chrominance
    # components with separate smoothing parameters to preserve edge sharpness.
    return cv2.fastNlMeansDenoisingColored(
        image,
        None,
        h,
        h_color,
        template_window_size,
        search_window_size,
    )

