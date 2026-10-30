"""Classical digital image restoration subpackage.

Provides independent modules for:
- Non-Local Means image denoising (denoiser.py)
- CLAHE contrast enhancement in LAB space (contrast.py)
- Unity-gain Laplacian image sharpening (sharpener.py)
- Restoration pipeline orchestration (restorer.py)
"""

from .contrast import enhance_contrast
from .denoiser import denoise_image
from .restorer import enhance_image
from .sharpener import sharpen_image

__all__ = [
    "denoise_image",
    "enhance_contrast",
    "sharpen_image",
    "enhance_image",
]

