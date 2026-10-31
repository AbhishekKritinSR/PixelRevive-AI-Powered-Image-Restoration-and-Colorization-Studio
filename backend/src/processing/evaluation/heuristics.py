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


NOISE_LOW_THRESHOLD: float = 4.0
NOISE_HIGH_THRESHOLD: float = 10.0

NOISE_KERNEL: np.ndarray = np.array(
    [[1.0, -2.0, 1.0], [-2.0, 4.0, -2.0], [1.0, -2.0, 1.0]],
    dtype=np.float32,
)


def estimate_noise_sigma(image: np.ndarray) -> tuple[float, str]:
    """Estimate blind noise standard deviation (sigma) using an Immerkær Laplacian operator.

    The operator convolves the grayscale luminance image with a normalized 3x3 difference
    mask and computes robust mean absolute deviation excluding outer boundary pixels.

    Args:
        image: RGB/BGR uint8 array (H, W, 3) or grayscale (H, W).

    Returns:
        Tuple of (sigma: float, qualitative_level: str) where level is 'low', 'medium', or 'high'.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")

    gray = _to_gray(image)
    h, w = gray.shape[:2]

    if h < 3 or w < 3:
        return 0.0, "low"

    gray_f = gray.astype(np.float32)
    conv = cv2.filter2D(gray_f, -1, NOISE_KERNEL, borderType=cv2.BORDER_CONSTANT)

    inner = conv[1:-1, 1:-1]
    sum_abs = float(np.sum(np.abs(inner)))

    inner_count = (w - 2) * (h - 2)
    if inner_count <= 0:
        return 0.0, "low"

    norm_factor = np.sqrt(np.pi / 2.0) / (6.0 * inner_count)
    sigma = float(sum_abs * norm_factor)

    if np.isnan(sigma) or np.isinf(sigma):
        sigma = 0.0

    if sigma < NOISE_LOW_THRESHOLD:
        level = "low"
    elif sigma < NOISE_HIGH_THRESHOLD:
        level = "medium"
    else:
        level = "high"

    return round(sigma, 2), level

