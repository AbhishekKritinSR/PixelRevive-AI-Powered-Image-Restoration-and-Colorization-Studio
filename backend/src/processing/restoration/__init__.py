"""Classical digital image restoration subpackage.

Provides independent modules for:
- Archival scratch detection and inpainting (scratch_repair.py)
- Non-Local Means image denoising (denoiser.py)
- CLAHE contrast enhancement in LAB space (contrast.py)
- Unity-gain Laplacian image sharpening (sharpener.py)
- Restoration pipeline orchestration (restorer.py)
"""

from .contrast import enhance_contrast
from .denoiser import (
    DenoiseParameters,
    adaptive_denoise_image,
    denoise_image,
    select_denoising_parameters,
)
from .restorer import enhance_image
from .scratch_repair import (
    ScratchRepairMetadata,
    detect_scratch_mask,
    repair_scratches,
)
from .sharpener import sharpen_image

__all__ = [
    "DenoiseParameters",
    "select_denoising_parameters",
    "adaptive_denoise_image",
    "denoise_image",
    "enhance_contrast",
    "sharpen_image",
    "enhance_image",
    "ScratchRepairMetadata",
    "detect_scratch_mask",
    "repair_scratches",
]

