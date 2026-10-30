"""Module: restorer.py

Purpose:
Coordinates the classical digital image restoration pipeline in strict sequential order:
1. Denoising (denoiser.py)
2. Contrast enhancement (contrast.py)
3. Sharpening (sharpener.py)

Responsibilities:
- Coordinate the individual restoration processors based on user-selected options.
- Maintain the authoritative sequence: denoise -> contrast -> sharpen.
- Allow independent toggling of any stage.
- Pass through the original image unchanged if all restoration stages are disabled.

Inputs:
- image: 3-channel BGR uint8 NumPy array with shape (H, W, 3).
- denoise: Boolean flag to enable/disable Non-Local Means denoising.
- contrast: Boolean flag to enable/disable CLAHE contrast enhancement.
- sharpen: Boolean flag to enable/disable Laplacian edge sharpening.

Outputs:
- Restored 3-channel BGR uint8 NumPy array.

Dependencies:
- .denoiser.denoise_image
- .contrast.enhance_contrast
- .sharpener.sharpen_image

This module does not:
- Execute AI colorization (handled by the colorization subsystem).
- Perform image file I/O or HTTP handling.
- Modify pipeline order dynamically.
"""

import numpy as np

from .contrast import enhance_contrast
from .denoiser import denoise_image
from .sharpener import sharpen_image


def enhance_image(
    image: np.ndarray,
    denoise: bool = True,
    contrast: bool = True,
    sharpen: bool = True,
) -> np.ndarray:
    """Run the classical restoration pipeline on a BGR uint8 image.

    The stages execute in strict sequence:
        1. Denoise (smooths noise while preserving major edges)
        2. Contrast (enhances local dynamic range on cleaned signal)
        3. Sharpen (restores micro-edge definition smoothed by denoising)

    Each stage can be independently enabled or disabled. Disabled stages
    are bypassed completely with zero computational overhead.

    Args:
        image:
            Input BGR image as a uint8 NumPy array of shape (height, width, 3).
        denoise:
            Whether to apply Non-Local Means denoising.
        contrast:
            Whether to apply CLAHE contrast enhancement on the L channel.
        sharpen:
            Whether to apply unity-gain Laplacian sharpening.

    Returns:
        Restored BGR image as a uint8 NumPy array.
    """
    result = image

    if denoise:
        result = denoise_image(result)

    if contrast:
        result = enhance_contrast(result)

    if sharpen:
        result = sharpen_image(result)

    return result

