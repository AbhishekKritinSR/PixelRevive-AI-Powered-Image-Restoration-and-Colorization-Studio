"""Classical (non-learned) image restoration: denoise, contrast, sharpen.

This module is a backward-compatibility wrapper that exposes the authoritative
modular implementations from `backend.src.processing.restoration`.
"""

from backend.src.processing.restoration import (
    denoise_image,
    enhance_contrast,
    enhance_image,
    sharpen_image,
)

__all__ = [
    "denoise_image",
    "enhance_contrast",
    "sharpen_image",
    "enhance_image",
]
