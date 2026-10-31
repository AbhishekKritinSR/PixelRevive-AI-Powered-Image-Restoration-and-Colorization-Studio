"""Module: restorer.py

Purpose:
Coordinates the classical digital image restoration pipeline in strict sequential order:
1. Denoising (denoiser.py)
2. Contrast enhancement (contrast.py)
3. Sharpening (sharpener.py)

Responsibilities:
- Coordinate the individual restoration processors based on user-selected options.
- Maintain the authoritative sequence: denoise -> contrast -> sharpen.
- Allow independent toggling of any stage.
- Pass through the original image unchanged if all restoration stages are disabled.

Inputs:
- image: 3-channel BGR uint8 NumPy array with shape (H, W, 3).
- denoise: Boolean flag to enable/disable Non-Local Means denoising.
- contrast: Boolean flag to enable/disable CLAHE contrast enhancement.
- sharpen: Boolean flag to enable/disable Laplacian edge sharpening.

Outputs:
- Restored 3-channel BGR uint8 NumPy array.

Dependencies:
- .denoiser.denoise_image
- .contrast.enhance_contrast
- .sharpener.sharpen_image

This module does not:
- Execute AI colorization (handled by the colorization subsystem).
- Perform image file I/O or HTTP handling.
- Modify pipeline order dynamically.
"""

import numpy as np

from .contrast import enhance_contrast
from .denoiser import adaptive_denoise_image, denoise_image
from .face_restorer import FaceRestorer
from .scratch_repair import repair_scratches
from .sharpener import sharpen_image
from .super_resolution import upscale_image


def enhance_image(
    image: np.ndarray,
    denoise: bool = True,
    contrast: bool = True,
    sharpen: bool = True,
    adaptive_denoise: bool = True,
    repair: bool = False,
    upscale: bool = False,
    scale: int = 2,
    inpaint_method: str = "telea",
    face_restore: bool = False,
    sr_model: str = "fsrcnn",
    preserve_texture: bool = True,
) -> np.ndarray:
    """Run the classical restoration pipeline on a BGR uint8 image.

    The stages execute in sequence:
        1. Repair (detects and inpaints archival scratches/defects via Telea, NS, or LaMa)
        2. Denoise (smooths noise while preserving texture micro-contrast)
        3. Contrast (enhances local dynamic range on cleaned signal via CLAHE)
        4. Face Restoration (optional localized identity-preserving facial enhancement)
        5. Sharpen (restores micro-edge definition smoothed by denoising)
        6. Super-Resolution (AI 2x or 4x upscaling via FSRCNN or Real-ESRGAN if enabled)

    Each stage can be independently enabled or disabled. Disabled stages
    are bypassed completely with zero computational overhead.

    Args:
        image:
            Input BGR image as a uint8 NumPy array of shape (height, width, 3).
        denoise:
            Whether to apply Non-Local Means denoising.
        contrast:
            Whether to apply CLAHE contrast enhancement on the L channel.
        sharpen:
            Whether to apply unity-gain Laplacian sharpening.
        adaptive_denoise:
            Whether to adaptively select denoising strength based on image noise.
            Default is True. If False, uses fixed Non-Local Means parameters.
        repair:
            Whether to detect archival scratches and reconstruct them.
            Default is False (disabled by default for full backward compatibility).
        upscale:
            Whether to upscale the output using AI super-resolution (FSRCNN or Real-ESRGAN).
            Default is False.
        scale:
            Super-resolution scale factor (2 or 4). Default is 2.
        inpaint_method:
            Inpainting algorithm ('telea', 'ns', or 'lama'). Default is 'telea'.
        face_restore:
            Whether to perform localized identity-preserving facial enhancement. Default is False.
        sr_model:
            Super-resolution model identifier ('fsrcnn' or 'realesrgan'). Default is 'fsrcnn'.
        preserve_texture:
            Whether to blend back high-frequency photographic texture. Default is True.

    Returns:
        Restored BGR image as a uint8 NumPy array.
    """
    result = image

    if repair:
        result, _ = repair_scratches(result, method=inpaint_method)

    if denoise:
        if adaptive_denoise:
            result, _ = adaptive_denoise_image(result, preserve_texture=preserve_texture)
        else:
            result = denoise_image(result, preserve_texture=preserve_texture)

    if contrast:
        result = enhance_contrast(result)

    if face_restore:
        result, _ = FaceRestorer.restore_faces(result)

    if sharpen:
        result = sharpen_image(result)

    if upscale:
        result, _ = upscale_image(result, scale=scale, model=sr_model)

    return result

