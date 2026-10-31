"""Module: brisque.py

Purpose:
Provides Blind/Referenceless Image Spatial Quality Evaluator (BRISQUE) no-reference
image quality assessment using OpenCV's quality module and official trained SVM model assets.

Responsibilities:
- Verify presence of BRISQUE trained SVM model and normalization range data files.
- Thread-safely instantiate and cache the cv2.quality.QualityBRISQUE evaluator instance.
- Compute non-reference perceptual quality scores on grayscale and color images.
- Handle missing assets gracefully without fabricating scores or failing unpredictably.
- Return structured evaluation results with factual technical interpretation.

Scientific Background:
Mittal, Moorthy, and Bovik, "No-Reference Image Quality Assessment in the Spatial Domain",
IEEE Transactions on Image Processing, 2012.
BRISQUE quantifies natural scene statistical distortions (blurring, noise, ringing, compression)
using locally normalized luminance coefficients and asymmetric generalized Gaussian distributions (AGGD).
Scores typically span [0, 100], where lower values denote fewer statistical distortions.

Dependencies:
- cv2 (OpenCV contrib quality module)
- numpy
- pathlib.Path
- threading
- backend.src.core.config.settings
"""

from pathlib import Path
import threading
from typing import Optional, Tuple

import cv2
import numpy as np

from backend.src.core.config import settings


_brisque_instance: Optional[object] = None
_brisque_lock = threading.RLock()


def are_brisque_assets_available() -> bool:
    """Check whether both required BRISQUE YAML data files exist on disk."""
    return settings.BRISQUE_MODEL_PATH.is_file() and settings.BRISQUE_RANGE_PATH.is_file()


def get_brisque_evaluator() -> Optional[object]:
    """Retrieve or lazily initialize the singleton QualityBRISQUE evaluator instance.

    Returns:
        Configured cv2.quality.QualityBRISQUE instance if assets exist, None otherwise.
    """
    global _brisque_instance

    if not are_brisque_assets_available():
        return None

    if _brisque_instance is None:
        with _brisque_lock:
            if _brisque_instance is None:
                if hasattr(cv2, "quality") and hasattr(cv2.quality, "QualityBRISQUE_create"):
                    _brisque_instance = cv2.quality.QualityBRISQUE_create(
                        str(settings.BRISQUE_MODEL_PATH),
                        str(settings.BRISQUE_RANGE_PATH),
                    )

    return _brisque_instance


def clear_brisque_instance() -> None:
    """Clear cached BRISQUE evaluator instance (primarily for testing)."""
    global _brisque_instance
    with _brisque_lock:
        _brisque_instance = None


def compute_brisque(image: np.ndarray) -> Tuple[bool, Optional[float], str]:
    """Compute BRISQUE no-reference quality score on an input image.

    Args:
        image:
            NumPy array of shape (H, W) or (H, W, 3) with uint8 data type.

    Returns:
        Tuple of:
            - available (bool): True if computed, False if model assets are unavailable.
            - score (Optional[float]): Numeric BRISQUE score [0.0, 100.0], or None if unavailable.
            - interpretation (str): Factual interpretation of the result.

    Raises:
        ValueError:
            If image is not a valid non-empty uint8 NumPy array.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")
    if image.size == 0:
        raise ValueError("Input image array is empty (0 pixels).")
    if image.dtype != np.uint8:
        raise ValueError(f"Input image must have uint8 dtype, got {image.dtype}.")
    if image.ndim not in (2, 3) or (image.ndim == 3 and image.shape[2] not in (1, 3)):
        raise ValueError(f"Expected 2D grayscale or 3-channel image, got shape {image.shape}.")

    if not are_brisque_assets_available():
        return (
            False,
            None,
            "BRISQUE model data assets (brisque_model_live.yml, brisque_range_live.yml) are unavailable on disk.",
        )

    evaluator = get_brisque_evaluator()
    if evaluator is None:
        return (
            False,
            None,
            "OpenCV cv2.quality.QualityBRISQUE evaluator could not be initialized.",
        )

    # cv2.quality.QualityBRISQUE accepts either grayscale (H, W) or BGR (H, W, 3)
    raw_score = evaluator.compute(image)
    score_val = float(raw_score[0])

    if np.isnan(score_val) or np.isinf(score_val):
        score_val = 0.0

    score_rounded = round(float(np.clip(score_val, 0.0, 100.0)), 2)

    interpretation = (
        f"BRISQUE no-reference perceptual distortion score: {score_rounded:.2f} (0-100 scale). "
        "Lower values predict fewer statistical natural-scene distortions."
    )

    return True, score_rounded, interpretation
