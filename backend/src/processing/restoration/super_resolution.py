"""Module: super_resolution.py

Purpose:
Provides optional AI super-resolution 2x and 4x upscaling using OpenCV DNN Super Resolution
and authoritative FSRCNN (Fast Super-Resolution Convolutional Neural Network) model assets.

Key Responsibilities:
- Model registry managing FSRCNN x2 and x4 model paths, scales, and licenses.
- Lazy, thread-safe model loading and memory caching.
- Strict resource safety checks enforcing maximum output dimensions and pixel budgets.
- Grayscale (1-channel) and BGR (3-channel) image upscaling.
- Execution timing and metadata tracking.

Dependencies:
- threading, time, pathlib.Path, dataclasses, typing
- cv2 (opencv-contrib-python-headless), numpy
- backend.src.core.config.settings
- backend.src.core.exceptions (ModelUnavailableError, UnsupportedScaleError, SuperResolutionResourceError)
"""

from dataclasses import dataclass
from pathlib import Path
import threading
import time
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from backend.src.core.config import settings
from backend.src.core.exceptions import (
    ModelUnavailableError,
    SuperResolutionResourceError,
    UnsupportedScaleError,
)

# Supported scaling factors
SUPPORTED_SCALES: Tuple[int, ...] = (2, 4)

# Registered Model Specifications
MODEL_REGISTRY: Dict[int, Dict[str, Any]] = {
    2: {
        "model_name": "fsrcnn_x2",
        "algorithm": "fsrcnn",
        "scale": 2,
        "filename": "FSRCNN_x2.pb",
        "path": settings.FSRCNN_X2_PATH,
        "architecture": "Fast Super-Resolution Convolutional Neural Network (Dong et al., 2016)",
        "source": "https://github.com/Saafke/FSRCNN_Tensorflow",
        "license": "Apache-2.0",
        "expected_sha256": "366b33f0084c7b3f2bf6724f0a2c77bca94fcec9d7b6d72389d330073b380d5c",
    },
    4: {
        "model_name": "fsrcnn_x4",
        "algorithm": "fsrcnn",
        "scale": 4,
        "filename": "FSRCNN_x4.pb",
        "path": settings.FSRCNN_X4_PATH,
        "architecture": "Fast Super-Resolution Convolutional Neural Network (Dong et al., 2016)",
        "source": "https://github.com/Saafke/FSRCNN_Tensorflow",
        "license": "Apache-2.0",
        "expected_sha256": "5c68d18db561aed8ead4ffedf1b897ea615baaf60ebf6c35f8e641f8fa4a21bf",
    },
}

# Cache for loaded DnnSuperResImpl instances (keyed by integer scale factor)
_model_cache: Dict[int, Any] = {}
_cache_lock: threading.Lock = threading.Lock()


@dataclass
class SuperResolutionMetadata:
    """Metadata describing the AI super-resolution upscaling operation."""

    applied: bool = False
    scale: int = 2
    model_name: str = "fsrcnn"
    input_dimensions: Tuple[int, int] = (0, 0)   # (width, height)
    output_dimensions: Tuple[int, int] = (0, 0)  # (width, height)
    elapsed_seconds: float = 0.0
    skipped: bool = False
    skip_reason: Optional[str] = None


def get_model_spec(scale: int) -> Dict[str, Any]:
    """Retrieve model registry specification for a scale factor.

    Args:
        scale: Scaling factor (2 or 4).

    Returns:
        Dictionary of model metadata.

    Raises:
        UnsupportedScaleError: If scale is not supported.
    """
    if scale not in MODEL_REGISTRY:
        raise UnsupportedScaleError(
            f"Unsupported scaling factor {scale}. Supported factors: {list(SUPPORTED_SCALES)}."
        )
    return MODEL_REGISTRY[scale]


def is_model_file_present(scale: int) -> bool:
    """Check if the model weights file for the given scale exists on disk."""
    if scale not in MODEL_REGISTRY:
        return False
    path: Path = MODEL_REGISTRY[scale]["path"]
    return path.is_file()


def is_model_loaded(scale: int) -> bool:
    """Check if the super-resolution model for the given scale is loaded into memory."""
    with _cache_lock:
        return scale in _model_cache


def clear_model_cache() -> None:
    """Clear cached model instances from memory."""
    with _cache_lock:
        _model_cache.clear()


def get_super_resolution_model(scale: int) -> Any:
    """Retrieve or lazily initialize the DnnSuperResImpl model for a given scale.

    Thread-safe and caches the loaded network across requests.

    Args:
        scale: Integer scale factor (2 or 4).

    Returns:
        Loaded cv2.dnn_superres.DnnSuperResImpl instance.

    Raises:
        UnsupportedScaleError: If scale is not in (2, 4).
        ModelUnavailableError: If the model file is missing from disk.
    """
    spec = get_model_spec(scale)
    model_path: Path = spec["path"]

    with _cache_lock:
        if scale in _model_cache:
            return _model_cache[scale]

        if not model_path.is_file():
            raise ModelUnavailableError(
                f"Super-resolution model file for scale {scale}x is missing from disk: {model_path.name}. "
                f"Please ensure '{model_path.name}' is placed in the model directory."
            )

        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(str(model_path))
        sr.setModel(spec["algorithm"], scale)

        _model_cache[scale] = sr
        return sr


def validate_super_resolution_resource_limits(
    input_height: int,
    input_width: int,
    scale: int,
) -> Tuple[int, int]:
    """Validate that expected output dimensions and pixel count respect safety resource caps.

    Args:
        input_height: Height of input image in pixels.
        input_width: Width of input image in pixels.
        scale: Super-resolution scale factor.

    Returns:
        Tuple of (expected_output_width, expected_output_height).

    Raises:
        SuperResolutionResourceError: If output dimensions or pixel budget exceed safety limits.
    """
    out_w = input_width * scale
    out_h = input_height * scale
    out_pixels = out_w * out_h

    max_dim = settings.MAX_SUPER_RES_OUTPUT_DIMENSION
    max_pixels = settings.MAX_SUPER_RES_OUTPUT_PIXELS

    if out_w > max_dim or out_h > max_dim:
        raise SuperResolutionResourceError(
            f"Super-resolution output dimensions ({out_w}x{out_h}) exceed the maximum allowable "
            f"dimension limit of {max_dim}px on the longest axis."
        )

    if out_pixels > max_pixels:
        raise SuperResolutionResourceError(
            f"Super-resolution output pixel count ({out_pixels:,} pixels, {out_pixels / 1e6:.1f} MP) "
            f"exceeds the maximum allowable budget of {max_pixels:,} pixels ({max_pixels / 1e6:.1f} MP)."
        )

    return out_w, out_h


def upscale_image(
    image: np.ndarray,
    scale: int = 2,
    model: str = "fsrcnn",
) -> Tuple[np.ndarray, SuperResolutionMetadata]:
    """Upscale a photographic image using AI super-resolution (FSRCNN or Real-ESRGAN).

    Supports both 3-channel BGR and 1-channel Grayscale images.

    Args:
        image:
            Input image as a uint8 NumPy array of shape (H, W) or (H, W, 3).
        scale:
            Upscaling factor (2 or 4). Default is 2.
        model:
            Super-resolution model identifier ('fsrcnn' or 'realesrgan'). Default is 'fsrcnn'.

    Returns:
        Tuple of (upscaled uint8 NumPy array, SuperResolutionMetadata).

    Raises:
        TypeError: If image is not a NumPy array.
        ValueError: If image dtype or dimensions are invalid.
        UnsupportedScaleError: If scale is not 2 or 4.
        SuperResolutionResourceError: If output exceeds memory/dimension safety limits.
        ModelUnavailableError: If required model weights are missing.
    """
    if not isinstance(image, np.ndarray):
        raise TypeError("Input image must be a numpy ndarray")
    if image.dtype != np.uint8:
        raise ValueError("Input image dtype must be uint8")
    if image.ndim not in (2, 3):
        raise ValueError("Input image must be 2D (grayscale) or 3D (color)")
    if image.ndim == 3 and image.shape[2] != 3:
        raise ValueError(f"Color images must have 3 channels, got {image.shape[2]}")
    if image.shape[0] < 2 or image.shape[1] < 2:
        raise ValueError("Image dimensions must be at least 2x2")

    # 1. Validate scale
    if scale not in SUPPORTED_SCALES:
        raise UnsupportedScaleError(
            f"Unsupported scaling factor {scale}. Supported factors: {list(SUPPORTED_SCALES)}."
        )

    in_h, in_w = image.shape[:2]

    # 2. Enforce resource safety limits
    out_w, out_h = validate_super_resolution_resource_limits(in_h, in_w, scale)

    # 3. Handle Real-ESRGAN execution if requested
    if model.lower().strip() == "realesrgan":
        try:
            from .sr_realesrgan import RealESRGANUpscaler
            resrg = RealESRGANUpscaler.get_instance()
            if resrg.is_available:
                t0 = time.perf_counter()
                upscaled, ok = resrg.upscale(image, target_scale=scale)
                if ok:
                    elapsed = time.perf_counter() - t0
                    meta = SuperResolutionMetadata(
                        applied=True,
                        scale=scale,
                        model_name="realesrgan_x4",
                        input_dimensions=(in_w, in_h),
                        output_dimensions=(upscaled.shape[1], upscaled.shape[0]),
                        elapsed_seconds=round(elapsed, 4),
                        skipped=False,
                        skip_reason=None,
                    )
                    return upscaled, meta
        except Exception:
            pass  # Fall back to FSRCNN below

    # 4. Retrieve FSRCNN model instance
    sr = get_super_resolution_model(scale)

    # 5. Execute inference with timing
    t0 = time.perf_counter()
    upscaled = sr.upsample(image)
    elapsed_seconds = time.perf_counter() - t0

    # 5. Output verification
    if upscaled.shape[0] != out_h or upscaled.shape[1] != out_w:
        raise ValueError(
            f"Output shape mismatch: expected ({out_h}, {out_w}), got ({upscaled.shape[0]}, {upscaled.shape[1]})"
        )
    if upscaled.dtype != np.uint8:
        raise ValueError(f"Output dtype must be uint8, got {upscaled.dtype}")
    if not np.all(np.isfinite(upscaled)):
        raise ValueError("Super-resolution output contains non-finite values (NaN or Inf)")

    meta = SuperResolutionMetadata(
        applied=True,
        scale=scale,
        model_name=MODEL_REGISTRY[scale]["model_name"],
        input_dimensions=(in_w, in_h),
        output_dimensions=(out_w, out_h),
        elapsed_seconds=round(elapsed_seconds, 4),
        skipped=False,
        skip_reason=None,
    )

    return upscaled, meta

