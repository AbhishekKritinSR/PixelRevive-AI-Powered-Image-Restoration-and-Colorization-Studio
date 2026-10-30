"""Image evaluation and device inspection subpackage.

Provides:
- Heuristic image quality metrics (heuristics.py)
- Compute device detection (device.py)
"""

from .device import get_processing_device
from .heuristics import (
    estimate_brightness,
    estimate_contrast,
    estimate_sharpness,
)

__all__ = [
    "estimate_sharpness",
    "estimate_contrast",
    "estimate_brightness",
    "get_processing_device",
]

