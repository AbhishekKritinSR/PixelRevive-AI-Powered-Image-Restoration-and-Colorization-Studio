"""Module: heuristics.py

Purpose:
Provides empirical, non-reference image quality heuristic measurements:
- Sharpness estimation via discrete Laplacian variance.
- Contrast estimation via pixel intensity standard deviation.
- Brightness estimation via arithmetic mean pixel intensity.

Responsibilities:
- Validate input arrays (2D grayscale or 3D RGB/BGR images).
- Safely extract grayscale luminance from 3-channel images.
- Compute mathematical statistics on pixel intensity distributions.
- Return native Python floats for clean serialization.

Important Technical Distinction:
These metrics are empirical heuristic proxies for image statistics, NOT calibrated
ground-truth restoration quality scores (such as PSNR or SSIM), which require an
unimpaired reference image for comparison.

Inputs:
- image: uint8 NumPy array with shape (H, W) or (H, W, 3).

Outputs:
- Float scalar values representing metric scores.

Dependencies:
- cv2 (OpenCV)
- numpy

This module does not:
- Require a ground-truth reference image.
- Probe hardware devices.
- Perform colorization or image enhancement.
"""

import cv2
import numpy as np


def _to_gray(image: np.ndarray) -> np.ndarray:
    """Convert an image to single-channel 8-bit grayscale luminance if it has 3 channels."""
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image


def estimate_sharpness(image: np.ndarray) -> float:
    """Calculate the variance of the 2D discrete Laplacian of the image.

    The discrete Laplacian operator highlights rapid spatial intensity changes
    (edges and textures). Images with sharp, crisp edges produce high Laplacian
    variance, whereas blurred or smoothed images yield low variance.

    Args:
        image:
            NumPy array of shape (H, W) or (H, W, 3).

    Returns:
        Float variance of the Laplacian response.
    """
    gray = _to_gray(image)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def estimate_contrast(image: np.ndarray) -> float:
    """Calculate the standard deviation of pixel intensities across the image.

    Standard deviation measures the dispersion of luminance values around the mean.
    High-contrast images with rich dynamic range have wide histograms (high std. dev.),
    while flat, low-contrast, or foggy images cluster tightly (low std. dev.).

    Args:
        image:
            NumPy array of shape (H, W) or (H, W, 3).

    Returns:
        Float standard deviation of grayscale pixel intensities.
    """
    gray = _to_gray(image)
    return float(gray.std())


def estimate_brightness(image: np.ndarray) -> float:
    """Calculate the arithmetic mean intensity of all pixels in the image.

    Args:
        image:
            NumPy array of shape (H, W) or (H, W, 3).

    Returns:
        Float mean pixel intensity in range [0.0, 255.0].
    """
    gray = _to_gray(image)
    return float(gray.mean())

