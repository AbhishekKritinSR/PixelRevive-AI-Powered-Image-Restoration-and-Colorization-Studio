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

from typing import Dict, Tuple, Union

import cv2
import numpy as np

from src.config import CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE
from .contrast import adaptive_enhance_contrast, enhance_contrast
from .denoiser import adaptive_denoise_image, denoise_image
from .face_restorer import FaceRestorer
from .scratch_repair import repair_scratches
from .sharpener import adaptive_sharpen_image, sharpen_image
from .super_resolution import upscale_image


def enhance_image(
    image: np.ndarray,
    denoise: bool = True,
    contrast: bool = True,
    sharpen: bool = True,
    adaptive_denoise: bool = True,
    adaptive_contrast: bool = True,
    adaptive_sharpen: bool = True,
    repair: bool = False,
    upscale: bool = False,
    scale: int = 2,
    inpaint_method: str = "telea",
    face_restore: bool = False,
    sr_model: str = "fsrcnn",
    preserve_texture: bool = True,
    return_summary: bool = False,
) -> Union[np.ndarray, Tuple[np.ndarray, Dict[str, str]]]:
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
        adaptive_contrast:
            Whether to adaptively evaluate dynamic range to bypass CLAHE on images
            with adequate natural contrast. Default is True.
        adaptive_sharpen:
            Whether to adaptively evaluate sharpness and noise to bypass sharpening
            on crisp or high-noise images. Default is True.
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
    summary: Dict[str, str] = {}

    if repair:
        repaired, repair_meta = repair_scratches(result, method=inpaint_method)
        if repair_meta.applied and repair_meta.repaired_pixels > 0:
            result = repaired
            summary["scratch_repair"] = (
                f"Applied: {repair_meta.repaired_pixels} damaged pixels reconstructed "
                f"({repair_meta.coverage_percentage}%) using {repair_meta.method.upper()}."
            )
        else:
            summary["scratch_repair"] = (
                "Bypassed: no significant scratch or surface defects detected."
            )

    if denoise:
        if adaptive_denoise:
            denoised, denoise_params = adaptive_denoise_image(
                result, preserve_texture=preserve_texture
            )
            if denoise_params.skip:
                summary["denoising"] = (
                    f"Bypassed: measured noise variance is pristine "
                    f"(sigma={denoise_params.noise_score:.2f} < 1.5). Filtering skipped to preserve photographic clarity."
                )
            else:
                result = denoised
                summary["denoising"] = (
                    f"Applied: adaptive Non-Local Means (sigma={denoise_params.noise_score:.2f}, "
                    f"level={denoise_params.noise_level}, h={denoise_params.h}) with texture-guided residual blending."
                )
        else:
            result = denoise_image(result, preserve_texture=preserve_texture)
            summary["denoising"] = (
                "Applied: standard Non-Local Means filtering with texture-guided residual blending."
            )

    if contrast:
        gray_before_c = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        before_c_std = float(gray_before_c.std())
        if adaptive_contrast:
            enhanced_contrast, contrast_params = adaptive_enhance_contrast(result)
            if not contrast_params.skip:
                result = enhanced_contrast
                after_c_std = float(cv2.cvtColor(result, cv2.COLOR_BGR2GRAY).std())
                summary["contrast"] = (
                    f"Applied: Contrast Limited Adaptive Histogram Equalization (CLAHE) on luminance channel "
                    f"(clip_limit={contrast_params.clip_limit}, grid={contrast_params.tile_grid_size[0]}x{contrast_params.tile_grid_size[1]}). "
                    f"Requested: true, Executed: true, Bypassed: false. "
                    f"Contrast std: {before_c_std:.1f} -> {after_c_std:.1f}. "
                    f"Reason: {contrast_params.reason}"
                )
            else:
                summary["contrast"] = (
                    f"Bypassed: contrast enhancement skipped by dynamic range safeguard. "
                    f"Requested: true, Executed: false, Bypassed: true. "
                    f"Measured std={contrast_params.contrast_score:.1f}, dynamic range={contrast_params.dynamic_range:.1f}. "
                    f"Reason: {contrast_params.reason}"
                )
        else:
            result = enhance_contrast(result)
            after_c_std = float(cv2.cvtColor(result, cv2.COLOR_BGR2GRAY).std())
            summary["contrast"] = (
                f"Applied: Contrast Limited Adaptive Histogram Equalization (CLAHE) on luminance channel "
                f"(clip_limit={CLAHE_CLIP_LIMIT}, grid={CLAHE_TILE_GRID_SIZE[0]}x{CLAHE_TILE_GRID_SIZE[1]}). "
                f"Requested: true, Executed: true, Bypassed: false. "
                f"Contrast std: {before_c_std:.1f} -> {after_c_std:.1f}. "
                f"Reason: Explicit client request (adaptive safeguard disabled)."
            )
    else:
        summary["contrast"] = (
            "Bypassed: contrast enhancement was not requested by client option. "
            "Requested: false, Executed: false, Bypassed: true."
        )

    if face_restore:
        restored, face_count = FaceRestorer.restore_faces(result, enhancement_strength=0.75)
        if face_count > 0:
            result = restored
            summary["face_enhancement"] = (
                f"Applied: noise-safe localized spatial enhancement on {face_count} detected face(s). "
                f"Requested: true, Executed: true, Bypassed: false."
            )
        else:
            summary["face_enhancement"] = (
                "Bypassed: no frontal faces detected in image canvas. "
                "Requested: true, Executed: false, Bypassed: true."
            )
    else:
        summary["face_enhancement"] = (
            "Bypassed: face enhancement was not requested by client option. "
            "Requested: false, Executed: false, Bypassed: true."
        )

    if sharpen:
        gray_before_s = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        before_lap = float(cv2.Laplacian(gray_before_s, cv2.CV_64F).var())
        if adaptive_sharpen:
            sharpened, sharpen_params = adaptive_sharpen_image(result)
            if not sharpen_params.skip:
                result = sharpened
                after_lap = float(cv2.Laplacian(cv2.cvtColor(result, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
                summary["sharpening"] = (
                    f"Applied: unity-gain high-pass Laplacian sharpening for edge recovery (kernel 3x3). "
                    f"Requested: true, Executed: true, Bypassed: false. "
                    f"Sharpness lap_var: {before_lap:.1f} -> {after_lap:.1f}. "
                    f"Reason: {sharpen_params.reason}"
                )
            else:
                summary["sharpening"] = (
                    f"Bypassed: sharpening skipped by adaptive protection. "
                    f"Requested: true, Executed: false, Bypassed: true. "
                    f"Measured lap_var={sharpen_params.sharpness_score:.1f}, noise_sigma={sharpen_params.noise_sigma:.2f}. "
                    f"Reason: {sharpen_params.reason}"
                )
        else:
            result = sharpen_image(result)
            after_lap = float(cv2.Laplacian(cv2.cvtColor(result, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
            summary["sharpening"] = (
                f"Applied: unity-gain high-pass Laplacian sharpening for edge recovery (kernel 3x3). "
                f"Requested: true, Executed: true, Bypassed: false. "
                f"Sharpness lap_var: {before_lap:.1f} -> {after_lap:.1f}. "
                f"Reason: Explicit client request (adaptive safeguard disabled)."
            )
    else:
        summary["sharpening"] = (
            "Bypassed: sharpening was not requested by client option. "
            "Requested: false, Executed: false, Bypassed: true."
        )

    if upscale:
        result, _ = upscale_image(result, scale=scale, model=sr_model)
        summary["super_resolution"] = (
            f"Applied: {scale}x AI super-resolution using {sr_model.upper()}."
        )

    if return_summary:
        return result, summary
    return result

