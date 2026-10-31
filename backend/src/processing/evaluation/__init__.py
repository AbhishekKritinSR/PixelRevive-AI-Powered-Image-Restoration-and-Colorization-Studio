"""Image evaluation and device inspection subpackage.

Provides:
- Heuristic image quality metrics (heuristics.py)
- Compute device detection (device.py)
"""

from .brisque import are_brisque_assets_available, compute_brisque
from .colorfulness import compute_colorfulness
from .device import get_processing_device
from .heuristics import (
    estimate_brightness,
    estimate_contrast,
    estimate_noise_sigma,
    estimate_sharpness,
)
from .ssim import compute_ssim

__all__ = [
    "estimate_sharpness",
    "estimate_contrast",
    "estimate_brightness",
    "estimate_noise_sigma",
    "get_processing_device",
    "compute_brisque",
    "are_brisque_assets_available",
    "compute_ssim",
    "compute_colorfulness",
]

