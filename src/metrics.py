"""Heuristic image-quality metrics and processing device detection.

Backward-compatibility wrapper preserving the original public interface of `src.metrics`,
delegating to the modular implementation in `backend.src.processing.evaluation`.
"""

from backend.src.processing.evaluation import (
    estimate_brightness,
    estimate_contrast,
    estimate_sharpness,
    get_processing_device,
)
from backend.src.processing.evaluation.heuristics import _to_gray

__all__ = [
    "_to_gray",
    "estimate_sharpness",
    "estimate_contrast",
    "estimate_brightness",
    "get_processing_device",
]
