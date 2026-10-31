"""Classical (non-learned) image restoration: denoise, contrast, sharpen.

This module is a backward-compatibility wrapper that exposes the authoritative
modular implementations from `backend.src.processing.restoration`.
"""

from backend.src.processing.restoration import (
    ContrastParameters,
    DenoiseParameters,
    ScratchRepairMetadata,
    SharpenParameters,
    SuperResolutionMetadata,
    adaptive_denoise_image,
    adaptive_enhance_contrast,
    adaptive_sharpen_image,
    denoise_image,
    detect_scratch_mask,
    enhance_contrast,
    enhance_image,
    evaluate_contrast_protection,
    evaluate_sharpen_protection,
    repair_scratches,
    select_denoising_parameters,
    sharpen_image,
    upscale_image,
)

__all__ = [
    "DenoiseParameters",
    "select_denoising_parameters",
    "adaptive_denoise_image",
    "denoise_image",
    "ContrastParameters",
    "adaptive_enhance_contrast",
    "evaluate_contrast_protection",
    "enhance_contrast",
    "SharpenParameters",
    "adaptive_sharpen_image",
    "evaluate_sharpen_protection",
    "sharpen_image",
    "enhance_image",
    "ScratchRepairMetadata",
    "detect_scratch_mask",
    "repair_scratches",
    "SuperResolutionMetadata",
    "upscale_image",
]
