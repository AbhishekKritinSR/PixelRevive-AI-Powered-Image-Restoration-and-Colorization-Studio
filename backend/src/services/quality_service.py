"""Module: quality_service.py

Purpose:
Application service orchestrating no-reference quality (BRISQUE), reference-based
structural similarity (SSIM), and chromatic variance (Colorfulness) assessments.

Responsibilities:
- Validate uploaded file formats and size limits for both target and reference images.
- Safely decode image bytes into normalized RGB/BGR NumPy arrays using Pillow.
- Coordinate independent computation of BRISQUE, SSIM, and Colorfulness metrics.
- Maintain separate, uncombined metric categorizations without fabricating composite scores.
- Return structured ImageQualityAssessmentResponse schemas.

Dependencies:
- io, time, pathlib.Path
- PIL.Image, cv2, numpy
- backend.src.core.config.settings
- backend.src.core.exceptions (CorruptedImageError, FileTooLargeError, UnsupportedFormatError, ImageValidationError)
- backend.src.processing.evaluation (compute_brisque, compute_ssim, compute_colorfulness,
                                     estimate_sharpness, estimate_contrast, estimate_noise_sigma)
- backend.src.schemas.quality.*
"""

import io
from pathlib import Path
import time
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from backend.src.core.config import settings
from backend.src.core.exceptions import (
    CorruptedImageError,
    DimensionMismatchError,
    FileTooLargeError,
    ImageValidationError,
    UnsupportedFormatError,
)
from backend.src.processing.evaluation.brisque import compute_brisque
from backend.src.processing.evaluation.colorfulness import compute_colorfulness
from backend.src.processing.evaluation.heuristics import (
    estimate_contrast,
    estimate_noise_sigma,
    estimate_sharpness,
)
from backend.src.processing.evaluation.ssim import compute_ssim
from backend.src.schemas.quality import (
    ImageQualityAssessmentResponse,
    MetricDetail,
    QualityImageDimensions,
)


class QualityService:
    """Service orchestrating image quality, similarity, and colorfulness evaluations."""

    def validate_file_metadata(self, filename: str, file_size: int, label: str = "Target image") -> None:
        """Validate filename extension and byte size limit.

        Args:
            filename: Original filename provided by client.
            file_size: Byte length of uploaded content.
            label: Descriptive label for error messages ('Target image' or 'Reference image').

        Raises:
            UnsupportedFormatError: If file extension is not in settings.ALLOWED_IMAGE_EXTENSIONS.
            FileTooLargeError: If file_size exceeds settings.MAX_UPLOAD_SIZE_BYTES.
        """
        extension = Path(filename).suffix.lower()
        if extension not in settings.ALLOWED_IMAGE_EXTENSIONS:
            raise UnsupportedFormatError(
                f"{label} has unsupported file format '{extension}'. "
                f"Supported formats: {sorted(list(settings.ALLOWED_IMAGE_EXTENSIONS))}"
            )

        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise FileTooLargeError(
                f"{label} size ({actual_mb:.1f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB."
            )

    def decode_image_bytes(self, file_bytes: bytes, label: str = "image") -> np.ndarray:
        """Decode raw file bytes into an RGB uint8 NumPy array using Pillow.

        Args:
            file_bytes: Raw uploaded binary data.
            label: Error label context.

        Returns:
            RGB uint8 NumPy array of shape (height, width, 3).

        Raises:
            CorruptedImageError: If bytes cannot be opened as a valid image.
        """
        if not file_bytes:
            raise CorruptedImageError(f"Uploaded {label} is empty (0 bytes).")

        try:
            pil_image = Image.open(io.BytesIO(file_bytes))
            pil_image.verify()

            pil_image = Image.open(io.BytesIO(file_bytes))
            rgb_image = pil_image.convert("RGB")
            return np.array(rgb_image, dtype=np.uint8)
        except Exception as e:
            raise CorruptedImageError(f"Could not read {label} content: {str(e)}")

    def assess_quality(
        self,
        file_bytes: bytes,
        filename: str,
        reference_bytes: Optional[bytes] = None,
        reference_filename: Optional[str] = None,
    ) -> ImageQualityAssessmentResponse:
        """Evaluate target image quality, similarity to optional reference, and colorfulness.

        Args:
            file_bytes: Binary data of target image.
            filename: Filename of target image.
            reference_bytes: Optional binary data of reference image.
            reference_filename: Optional filename of reference image.

        Returns:
            Structured ImageQualityAssessmentResponse.
        """
        start_time = time.perf_counter()

        # 1. Validate and decode target image
        self.validate_file_metadata(filename, len(file_bytes), label="Target image")
        target_rgb = self.decode_image_bytes(file_bytes, label="target image")
        target_bgr = cv2.cvtColor(target_rgb, cv2.COLOR_RGB2BGR)

        h, w, c = target_rgb.shape

        metrics_dict = {}

        # 2. BRISQUE no-reference quality assessment
        brisque_avail, brisque_score, brisque_interp = compute_brisque(target_bgr)
        metrics_dict["brisque"] = MetricDetail(
            metric_id="brisque",
            display_name="BRISQUE (No-Reference Quality)",
            available=brisque_avail,
            score=brisque_score,
            interpretation=brisque_interp,
        )

        # 3. SSIM structural similarity assessment
        if reference_bytes:
            ref_name = reference_filename or "reference.png"
            self.validate_file_metadata(ref_name, len(reference_bytes), label="Reference image")
            ref_rgb = self.decode_image_bytes(reference_bytes, label="reference image")
            ref_bgr = cv2.cvtColor(ref_rgb, cv2.COLOR_RGB2BGR)

            if target_bgr.shape != ref_bgr.shape:
                raise DimensionMismatchError(
                    f"Dimension mismatch for SSIM comparison: target image is {w}x{h} ({c} channels), "
                    f"but reference image is {ref_rgb.shape[1]}x{ref_rgb.shape[0]} ({ref_rgb.shape[2]} channels). "
                    "SSIM requires identical spatial dimensions and channel counts."
                )

            ssim_score, channel_scores, mode, ssim_interp = compute_ssim(target_bgr, ref_bgr)
            metrics_dict["ssim"] = MetricDetail(
                metric_id="ssim",
                display_name="SSIM (Structural Similarity Index)",
                available=True,
                score=ssim_score,
                interpretation=ssim_interp,
                details={"comparison_mode": mode, "channel_scores": channel_scores},
            )
        else:
            metrics_dict["ssim"] = MetricDetail(
                metric_id="ssim",
                display_name="SSIM (Structural Similarity Index)",
                available=False,
                score=None,
                interpretation="SSIM requires a reference image for comparison. No reference image was supplied.",
            )

        # 4. Colorfulness metric
        colorfulness_score, color_components, color_interp = compute_colorfulness(target_bgr)
        metrics_dict["colorfulness"] = MetricDetail(
            metric_id="colorfulness",
            display_name="Hasler-Süsstrunk Colorfulness",
            available=True,
            score=colorfulness_score,
            interpretation=color_interp,
            details=color_components,
        )

        # 5. Baseline heuristics (separately identified)
        sharpness_val = round(estimate_sharpness(target_rgb), 2)
        contrast_val = round(estimate_contrast(target_rgb), 2)
        noise_sigma, noise_level = estimate_noise_sigma(target_rgb)

        metrics_dict["sharpness"] = MetricDetail(
            metric_id="sharpness",
            display_name="Laplacian Sharpness Variance",
            available=True,
            score=sharpness_val,
            interpretation=f"Variance of 2D discrete Laplacian edge response: {sharpness_val:.2f}.",
        )

        metrics_dict["contrast"] = MetricDetail(
            metric_id="contrast",
            display_name="Luminance Contrast Standard Deviation",
            available=True,
            score=contrast_val,
            interpretation=f"Standard deviation of grayscale luminance intensity: {contrast_val:.2f}.",
        )

        metrics_dict["noise"] = MetricDetail(
            metric_id="noise",
            display_name="Immerkær Noise Standard Deviation",
            available=True,
            score=noise_sigma,
            interpretation=f"Estimated additive noise sigma: {noise_sigma:.2f} ({noise_level} noise).",
            details={"noise_level": noise_level},
        )

        elapsed = round(time.perf_counter() - start_time, 4)

        return ImageQualityAssessmentResponse(
            status="success",
            filename=filename,
            reference_filename=reference_filename if reference_bytes else None,
            image=QualityImageDimensions(width=w, height=h, channels=c),
            elapsed_seconds=elapsed,
            metrics=metrics_dict,
        )
