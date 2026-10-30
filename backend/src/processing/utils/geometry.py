"""Module: geometry.py

Purpose:
Provides geometric transformation and resizing utilities for images.

Responsibilities:
- Downscale images exceeding maximum dimension limits while strictly preserving aspect ratio.
- Use area-based decimation (cv2.INTER_AREA) for optimal anti-aliased image reduction.
- Report whether downscaling occurred so callers can inform the user.

Inputs:
- image: NumPy array of shape (H, W) or (H, W, C).
- max_dimension: Maximum allowable length (in pixels) for the longest dimension.

Outputs:
- Tuple[np.ndarray, bool]: (processed_image, was_resized).

Dependencies:
- cv2 (OpenCV)
- src.config (MAX_IMAGE_DIMENSION)

This module does not:
- Perform color conversions or filtering.
- Modify aspect ratios.
"""

from typing import Tuple

import cv2
import numpy as np

from src.config import MAX_IMAGE_DIMENSION


def resize_if_too_large(
    image: np.ndarray,
    max_dimension: int = MAX_IMAGE_DIMENSION,
) -> Tuple[np.ndarray, bool]:
    """Downscale an image if its longest dimension exceeds max_dimension.

    Preserves original aspect ratio and only touches images that genuinely
    exceed the threshold. Returns (image, was_resized) so callers can notify
    users when downscaling occurred.

    Args:
        image:
            Input NumPy array with shape (height, width) or (height, width, channels).
        max_dimension:
            Maximum allowed length in pixels for the longer edge (default: 1600).

    Returns:
        Tuple of (resulting_image, was_resized_boolean).
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")

    height, width = image.shape[:2]
    longest_side = max(height, width)

    if longest_side <= max_dimension:
        return image, False

    scale = max_dimension / float(longest_side)
    new_size = (round(width * scale), round(height * scale))

    # cv2.INTER_AREA provides superior pixel-area resampling when shrinking images
    resized = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    return resized, True

