"""Module: sharpener.py

Purpose:
Provides high-frequency edge sharpening using a discrete unity-gain Laplacian
convolution kernel.

Responsibilities:
- Validate input image format.
- Apply 2D spatial convolution with the unity-gain Laplacian kernel.
- Ensure output maintains original baseline regional brightness.
- Preserve image shape and uint8 data type.

Inputs:
- image: 3-channel BGR uint8 NumPy array with shape (H, W, 3).
- kernel: 2D NumPy array representing the convolution kernel (default: SHARPEN_KERNEL).

Outputs:
- Sharpened 3-channel BGR uint8 NumPy array.

Dependencies:
- cv2 (OpenCV)
- numpy
- src.config (SHARPEN_KERNEL)

This module does not:
- Apply unsharp masking with blurred subtractive masks.
- Alter overall luminance (the kernel coefficients sum to 1.0).
- Alter color balance.
"""

import cv2
import numpy as np

from src.config import SHARPEN_KERNEL


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

