"""Module: restoration_service.py

Purpose:
Coordinates the single-image validation, preparation, classical restoration,
AI colorization, metric calculation, and output encoding workflow.

Responsibilities:
- Validate uploaded file extensions and file size limits.
- Safely decode image bytes using Pillow, catching corrupt or unreadable files.
- Normalize image mode to 3-channel RGB uint8.
- Enforce the 1600px maximum dimension cap via aspect-preserving downscaling.
- Convert RGB to BGR for OpenCV domain processing.
- Coordinate classical enhancement via `enhance_image`.
- Execute AI colorization via `ModelService` and `BaseColorizer`.
- Calculate heuristic quality metrics and before/after deltas.
- Format results into Base64 PNG data URIs and structured Pydantic responses.

Dependencies:
- io, time, pathlib.Path
- PIL.Image, cv2, numpy
- backend.src.core.config.settings
- backend.src.core.exceptions (CorruptedImageError, FileTooLargeError, UnsupportedFormatError)
- backend.src.processing.restoration.restorer.enhance_image
- backend.src.processing.evaluation.heuristics (estimate_sharpness, estimate_contrast, estimate_brightness)
- backend.src.processing.evaluation.device.get_processing_device
- backend.src.processing.utils.geometry.resize_if_too_large
- backend.src.processing.utils.format_converter.image_to_base64_png
- backend.src.schemas.restoration (RestorationOptions, SingleRestorationResponse)
- backend.src.schemas.metrics.QualityMetricsResponse
- backend.src.services.model_service.ModelService
"""

import io
from pathlib import Path
import time
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

from backend.src.core.config import settings
from backend.src.core.exceptions import (
    CorruptedImageError,
    FileTooLargeError,
    UnsupportedFormatError,
)
from backend.src.processing.evaluation.device import get_processing_device
from backend.src.processing.evaluation.heuristics import (
    estimate_brightness,
    estimate_contrast,
    estimate_sharpness,
)
from backend.src.processing.restoration.restorer import enhance_image
from backend.src.processing.utils.format_converter import image_to_base64_png
from backend.src.processing.utils.geometry import resize_if_too_large
from backend.src.schemas.metrics import QualityMetricsResponse
from backend.src.schemas.restoration import (
    RestorationOptions,
    SingleRestorationResponse,
)
from backend.src.services.model_service import ModelService


class RestorationService:
    """Application service for orchestrating single-image restoration operations."""

    def __init__(self, model_service: ModelService):
        self.model_service = model_service

    def validate_file_metadata(self, filename: str, file_size: int) -> None:
        """Validate filename extension and byte size.

        Args:
            filename:
                Original filename provided by client.
            file_size:
                Byte length of uploaded content.

        Raises:
            UnsupportedFormatError:
                If file extension is not in settings.ALLOWED_IMAGE_EXTENSIONS.
            FileTooLargeError:
                If file_size exceeds settings.MAX_UPLOAD_SIZE_BYTES.
        """
        extension = Path(filename).suffix.lower()
        if extension not in settings.ALLOWED_IMAGE_EXTENSIONS:
            raise UnsupportedFormatError(
                f"Unsupported file format '{extension}'. "
                f"Supported formats: {sorted(list(settings.ALLOWED_IMAGE_EXTENSIONS))}"
            )

        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise FileTooLargeError(
                f"File size ({actual_mb:.1f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB."
            )

    def decode_image_bytes(self, file_bytes: bytes) -> np.ndarray:
        """Decode raw file bytes into an RGB uint8 NumPy array using Pillow.

        Args:
            file_bytes:
                Raw uploaded binary data.

        Returns:
            RGB uint8 NumPy array of shape (height, width, 3).

        Raises:
            CorruptedImageError:
                If bytes cannot be identified or opened as a valid image.
        """
        if not file_bytes:
            raise CorruptedImageError("Uploaded file is empty (0 bytes).")

        try:
            pil_image = Image.open(io.BytesIO(file_bytes))
            # Verify image integrity (catches truncated/damaged uploads)
            pil_image.verify()

            # Re-open after verify (Pillow requires re-opening after verify() call)
            pil_image = Image.open(io.BytesIO(file_bytes))
            # Normalize image to RGB color mode
            rgb_image = pil_image.convert("RGB")
            return np.array(rgb_image, dtype=np.uint8)
        except Exception as e:
            raise CorruptedImageError(f"Could not read image content: {str(e)}")

    def process_image(
        self,
        file_bytes: bytes,
        filename: str,
        options: RestorationOptions,
    ) -> Tuple[SingleRestorationResponse, bytes]:
        """Execute complete restoration workflow on uploaded image bytes.

        Args:
            file_bytes:
                Binary contents of the uploaded image.
            filename:
                Client-provided filename.
            options:
                RestorationOptions specifying which stages to run.

        Returns:
            Tuple of (SingleRestorationResponse schema, raw result PNG bytes).
        """
        self.validate_file_metadata(filename, len(file_bytes))

        # 1. Decode to RGB uint8
        image_rgb = self.decode_image_bytes(file_bytes)
        orig_h, orig_w = image_rgb.shape[:2]

        # 2. Downscale if exceeding 1600px cap
        processed_input_rgb, was_resized = resize_if_too_large(
            image_rgb, max_dimension=settings.MAX_IMAGE_DIMENSION
        )

        start_time = time.perf_counter()

        # 3. Convert RGB -> BGR for OpenCV processing
        bgr = cv2.cvtColor(processed_input_rgb, cv2.COLOR_RGB2BGR)

        # 4. Classical restoration stages (denoise, contrast, sharpen)
        enhanced_bgr = enhance_image(
            bgr,
            denoise=options.denoise,
            contrast=options.contrast,
            sharpen=options.sharpen,
        )

        # 5. AI Colorization stage
        if options.colorize:
            colorizer = self.model_service.get_colorizer("zhang_caffe")
            colorized_float = colorizer.colorize(enhanced_bgr)
            # Convert float32 [0.0, 1.0] -> uint8 [0, 255]
            result_bgr = (colorized_float * 255.0).astype(np.uint8)
        else:
            result_bgr = enhanced_bgr

        # 6. Convert BGR -> RGB for display and output encoding
        result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
        elapsed_seconds = time.perf_counter() - start_time

        # 7. Compute heuristic quality metrics
        sharpness_after = estimate_sharpness(result_rgb)
        contrast_after = estimate_contrast(result_rgb)
        brightness_after = estimate_brightness(result_rgb)

        sharpness_before = estimate_sharpness(processed_input_rgb)
        contrast_before = estimate_contrast(processed_input_rgb)

        metrics = QualityMetricsResponse(
            sharpness=round(sharpness_after, 2),
            contrast=round(contrast_after, 2),
            brightness=round(brightness_after, 2),
            sharpness_delta=round(sharpness_after - sharpness_before, 2),
            contrast_delta=round(contrast_after - contrast_before, 2),
            device=get_processing_device(),
            elapsed_seconds=round(elapsed_seconds, 3),
        )

        # 8. Encode result to PNG bytes and Base64 data URI
        pil_result = Image.fromarray(result_rgb)
        png_buf = io.BytesIO()
        pil_result.save(png_buf, format="PNG")
        png_bytes = png_buf.getvalue()

        base64_uri = image_to_base64_png(result_rgb)

        response = SingleRestorationResponse(
            status="success",
            filename=filename,
            original_width=orig_w,
            original_height=orig_h,
            processed_width=result_rgb.shape[1],
            processed_height=result_rgb.shape[0],
            was_resized=was_resized,
            elapsed_seconds=round(elapsed_seconds, 3),
            options_applied=options,
            metrics=metrics,
            image_base64=base64_uri,
        )

        return response, png_bytes

