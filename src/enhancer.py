"""Classical (non-learned) image restoration: denoise, contrast, sharpen.

This module is a backward-compatibility wrapper that exposes the authoritative
modular implementations from `backend.src.processing.restoration`.
"""

from backend.src.processing.restoration import (
    DenoiseParameters,
    adaptive_denoise_image,
    denoise_image,
    enhance_contrast,
    enhance_image,
    select_denoising_parameters,
    sharpen_image,
)

__all__ = [
    "DenoiseParameters",
    "select_denoising_parameters",
    "adaptive_denoise_image",
    "denoise_image",
    "enhance_contrast",
    "sharpen_image",
    "enhance_image",
]
