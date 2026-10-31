"""Module: colorfulness.py

Purpose:
Computes the Hasler and Süsstrunk (2003) metric to objectively quantify image colorfulness
based on opponent-color channel standard deviations and means.

Responsibilities:
- Validate that the input image is a valid uint8 NumPy array.
- Explicitly identify and handle single-channel and monochrome images (returning 0.0).
- Extract opponent color distributions (rg = R - G, yb = (R + G)/2 - B).
- Compute combined chromatic dispersion and central tendency.
- Return structured colorfulness metric results with factual interpretation.

Scientific Background:
Hasler and Süsstrunk, "Measuring Colorfulness in Natural Images",
Human Vision and Electronic Imaging VIII, SPIE Proceedings Vol. 5007, 2003.
The metric models experimental psychophysical perceptions of colorfulness via:
    rg = R - G
    yb = 0.5 * (R + G) - B
    sigma_rgyb = sqrt(sigma_rg^2 + sigma_yb^2)
    mu_rgyb = sqrt(mu_rg^2 + mu_yb^2)
    Colorfulness = sigma_rgyb + 0.3 * mu_rgyb

Dependencies:
- numpy
"""

from typing import Dict, Tuple

import numpy as np


def compute_colorfulness(image_bgr: np.ndarray) -> Tuple[float, Dict[str, float], str]:
    """Compute the Hasler and Süsstrunk (2003) colorfulness metric on an image.

    Args:
        image_bgr:
            NumPy array of shape (H, W, 3) or (H, W) with uint8 dtype.

    Returns:
        Tuple of:
            - score (float): Numerical colorfulness metric (0.0 for grayscale, >= 0.0 for color).
            - components (Dict[str, float]): Component standard deviations and means.
            - interpretation (str): Factual explanation of the metric.

    Raises:
        ValueError:
            If input is not a valid non-empty uint8 NumPy array.
    """
    if not isinstance(image_bgr, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")
    if image_bgr.size == 0:
        raise ValueError("Input image array is empty (0 pixels).")
    if image_bgr.dtype != np.uint8:
        raise ValueError(f"Input image must have uint8 dtype, got {image_bgr.dtype}.")

    # Grayscale image (2D or 3D with 1 channel)
    if image_bgr.ndim == 2 or (image_bgr.ndim == 3 and image_bgr.shape[2] == 1):
        return (
            0.0,
            {"std_rgyb": 0.0, "mean_rgyb": 0.0, "std_rg": 0.0, "std_yb": 0.0},
            "Colorfulness metric: 0.00 (monochrome / grayscale image has zero chromatic dispersion).",
        )

    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError(f"Expected 3-channel image (H, W, 3), got shape {image_bgr.shape}.")

    # Extract RGB channels from BGR image (preventing mutation)
    b = image_bgr[:, :, 0].astype(np.float64)
    g = image_bgr[:, :, 1].astype(np.float64)
    r = image_bgr[:, :, 2].astype(np.float64)

    # Opponent color channels
    rg = r - g
    yb = 0.5 * (r + g) - b

    # Component dispersion and means
    std_rg = float(np.std(rg))
    mean_rg = float(np.mean(rg))
    std_yb = float(np.std(yb))
    mean_yb = float(np.mean(yb))

    std_rgyb = float(np.sqrt(std_rg**2 + std_yb**2))
    mean_rgyb = float(np.sqrt(mean_rg**2 + mean_yb**2))

    colorfulness = std_rgyb + 0.3 * mean_rgyb
    score_rounded = round(float(colorfulness), 2)

    components = {
        "std_rgyb": round(std_rgyb, 2),
        "mean_rgyb": round(mean_rgyb, 2),
        "std_rg": round(std_rg, 2),
        "std_yb": round(std_yb, 2),
    }

    interpretation = (
        f"Hasler & Süsstrunk colorfulness score: {score_rounded:.2f}. "
        "Measures chromatic variation and opponent channel dispersion across the image. "
        "A higher score reflects greater saturation and color variance, not color accuracy or realism."
    )

    return score_rounded, components, interpretation
