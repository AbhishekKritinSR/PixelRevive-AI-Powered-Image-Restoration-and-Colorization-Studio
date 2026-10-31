"""Module: analysis_service.py

Purpose:
Coordinates image quality diagnostic analysis, degradation measurement, and rule-based
restoration recommendation generation for photographic images.

Responsibilities:
- Validate uploaded file extensions and file size limits against configuration.
- Safely decode image bytes into normalized RGB NumPy arrays.
- Enforce the 1600px maximum dimension cap via aspect-preserving downscaling.
- Compute robust blind noise estimation via Laplacian residual operator.
- Compute high-frequency edge sharpness via 2D discrete Laplacian variance.
- Compute contrast dispersion and dynamic range percentiles.
- Detect monochrome vs. color images via chromatic channel variation.
- Generate explainable, rule-based restoration recommendations for each pipeline stage.
- Return structured Pydantic ImageAnalysisResponse without modifying the image or executing restoration.

Dependencies:
- io, time, pathlib.Path
- PIL.Image, cv2, numpy
- backend.src.core.config.settings
- backend.src.core.exceptions (CorruptedImageError, FileTooLargeError, UnsupportedFormatError)
- backend.src.processing.utils.geometry.resize_if_too_large
- backend.src.schemas.analysis.*

This service does NOT:
- Execute image restoration or filtering.
- Load or invoke the Caffe colorization model.
- Write files to permanent storage.
"""

import io
from pathlib import Path
import time
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image

from backend.src.core.config import settings
from backend.src.core.exceptions import (
    CorruptedImageError,
    FileTooLargeError,
    UnsupportedFormatError,
)
from backend.src.processing.evaluation.heuristics import (
    NOISE_HIGH_THRESHOLD,
    NOISE_KERNEL,
    NOISE_LOW_THRESHOLD,
    estimate_noise_sigma,
)
from backend.src.processing.utils.geometry import resize_if_too_large
from backend.src.schemas.analysis import (
    AnalysisMetrics,
    ContrastAnalysis,
    ImageAnalysisResponse,
    ImageDimensions,
    MonochromeAnalysis,
    NoiseAnalysis,
    RecommendationItem,
    RestorationRecommendations,
    SharpnessAnalysis,
)


class AnalysisService:
    """Service orchestrating image degradation diagnosis and restoration recommendations."""

    # Documented classification thresholds
    NOISE_LOW_THRESHOLD: float = 4.0
    NOISE_HIGH_THRESHOLD: float = 10.0

    SHARPNESS_BLURRY_THRESHOLD: float = 100.0
    SHARPNESS_SHARP_THRESHOLD: float = 500.0

    CONTRAST_LOW_STD: float = 30.0
    CONTRAST_LOW_RANGE: float = 100.0
    CONTRAST_HIGH_STD: float = 65.0

    MONOCHROME_DIFF_THRESHOLD: float = 3.5

    # 3x3 Immerkær Laplacian noise estimation mask
    _NOISE_KERNEL: np.ndarray = np.array(
        [[1.0, -2.0, 1.0], [-2.0, 4.0, -2.0], [1.0, -2.0, 1.0]],
        dtype=np.float32,
    )

    def validate_file_metadata(self, filename: str, file_size: int) -> None:
        """Validate filename extension and byte size.

        Args:
            filename: Original filename provided by client.
            file_size: Byte length of uploaded content.

        Raises:
            UnsupportedFormatError: If file extension is not in settings.ALLOWED_IMAGE_EXTENSIONS.
            FileTooLargeError: If file_size exceeds settings.MAX_UPLOAD_SIZE_BYTES.
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
            file_bytes: Raw uploaded binary data.

        Returns:
            RGB uint8 NumPy array of shape (height, width, 3).

        Raises:
            CorruptedImageError: If bytes cannot be identified or opened as a valid image.
        """
        if not file_bytes:
            raise CorruptedImageError("Uploaded file is empty (0 bytes).")

        try:
            pil_image = Image.open(io.BytesIO(file_bytes))
            pil_image.verify()

            # Re-open after verify
            pil_image = Image.open(io.BytesIO(file_bytes))
            rgb_image = pil_image.convert("RGB")
            return np.array(rgb_image, dtype=np.uint8)
        except Exception as e:
            raise CorruptedImageError(f"Could not read image content: {str(e)}")

    def estimate_noise(self, image: np.ndarray) -> NoiseAnalysis:
        """Estimate blind noise standard deviation (sigma) using an Immerkær Laplacian operator.

        The operator convolves the grayscale luminance image with a normalized 3x3 difference
        mask and computes robust mean absolute deviation excluding outer boundary pixels.

        Args:
            image: RGB uint8 array (H, W, 3) or grayscale (H, W).

        Returns:
            NoiseAnalysis schema containing estimated sigma and qualitative level.
        """
        sigma, level = estimate_noise_sigma(image)
        return NoiseAnalysis(
            noise_score=sigma,
            noise_level=level,
        )

    def estimate_sharpness(self, image: np.ndarray) -> SharpnessAnalysis:
        """Calculate high-frequency edge sharpness using discrete 2D Laplacian variance.

        Args:
            image: RGB uint8 array (H, W, 3) or grayscale (H, W).

        Returns:
            SharpnessAnalysis schema containing variance score and qualitative level.
        """
        if not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a valid NumPy array.")

        gray = (
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            if image.ndim == 3 and image.shape[2] == 3
            else image
        )

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        score = float(laplacian.var())

        if np.isnan(score) or np.isinf(score):
            score = 0.0

        if score < self.SHARPNESS_BLURRY_THRESHOLD:
            level = "blurry"
        elif score < self.SHARPNESS_SHARP_THRESHOLD:
            level = "moderate"
        else:
            level = "sharp"

        return SharpnessAnalysis(
            sharpness_score=round(score, 2),
            sharpness_level=level,
        )

    def estimate_contrast(self, image: np.ndarray) -> ContrastAnalysis:
        """Calculate luminance dispersion and occupied dynamic range.

        Args:
            image: RGB uint8 array (H, W, 3) or grayscale (H, W).

        Returns:
            ContrastAnalysis schema containing standard deviation, dynamic range, and level.
        """
        if not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a valid NumPy array.")

        gray = (
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            if image.ndim == 3 and image.shape[2] == 3
            else image
        )

        score = float(gray.std())
        if np.isnan(score) or np.isinf(score):
            score = 0.0

        if gray.size > 0:
            p99 = float(np.percentile(gray, 99))
            p1 = float(np.percentile(gray, 1))
            dynamic_range = max(0.0, p99 - p1)
        else:
            dynamic_range = 0.0

        if score < self.CONTRAST_LOW_STD or dynamic_range < self.CONTRAST_LOW_RANGE:
            level = "low"
        elif score >= self.CONTRAST_HIGH_STD:
            level = "high"
        else:
            level = "moderate"

        return ContrastAnalysis(
            contrast_score=round(score, 2),
            dynamic_range=round(dynamic_range, 2),
            contrast_level=level,
        )

    def estimate_monochrome(self, image: np.ndarray) -> MonochromeAnalysis:
        """Detect whether an image is monochrome or color by measuring inter-channel variation.

        Args:
            image: RGB uint8 array (H, W, 3).

        Returns:
            MonochromeAnalysis schema indicating monochrome flag, color variation score, and confidence.
        """
        if not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a valid NumPy array.")

        if image.ndim != 3 or image.shape[2] != 3:
            return MonochromeAnalysis(
                is_monochrome=True,
                color_variation_score=0.0,
                confidence=1.0,
            )

        rgb_f = image.astype(np.float32)
        diff_rg = np.abs(rgb_f[:, :, 0] - rgb_f[:, :, 1])
        diff_gb = np.abs(rgb_f[:, :, 1] - rgb_f[:, :, 2])
        diff_br = np.abs(rgb_f[:, :, 2] - rgb_f[:, :, 0])

        color_var = float(np.mean((diff_rg + diff_gb + diff_br) / 3.0))
        if np.isnan(color_var) or np.isinf(color_var):
            color_var = 0.0

        is_mono = bool(color_var < self.MONOCHROME_DIFF_THRESHOLD)

        # Heuristic confidence based on margin from threshold
        if is_mono:
            conf = float(np.clip(1.0 - (color_var / self.MONOCHROME_DIFF_THRESHOLD) * 0.4, 0.6, 1.0))
        else:
            conf = float(
                np.clip(
                    0.6 + ((color_var - self.MONOCHROME_DIFF_THRESHOLD) / 20.0) * 0.4,
                    0.6,
                    1.0,
                )
            )

        return MonochromeAnalysis(
            is_monochrome=is_mono,
            color_variation_score=round(color_var, 2),
            confidence=round(conf, 2),
        )

    def generate_recommendations(
        self,
        noise: NoiseAnalysis,
        sharpness: SharpnessAnalysis,
        contrast: ContrastAnalysis,
        monochrome: MonochromeAnalysis,
    ) -> Tuple[RestorationRecommendations, List[str]]:
        """Generate explainable, rule-based restoration toggles and detected issue tags.

        Args:
            noise: Computed NoiseAnalysis.
            sharpness: Computed SharpnessAnalysis.
            contrast: Computed ContrastAnalysis.
            monochrome: Computed MonochromeAnalysis.

        Returns:
            Tuple of (RestorationRecommendations, List[str] of detected issues).
        """
        detected_issues: List[str] = []

        # 1. Denoise recommendation
        if noise.noise_level == "high":
            detected_issues.append("High Photographic Grain / Sensor Noise")
            denoise_item = RecommendationItem(
                recommended=True,
                reason=(
                    f"High noise level detected (estimated sigma={noise.noise_score:.1f}). "
                    "Non-Local Means denoising is strongly recommended to remove sensor/scan grain."
                ),
                evidence="noise_level_high",
            )
        elif noise.noise_level == "medium":
            detected_issues.append("Moderate Noise / Film Grain")
            denoise_item = RecommendationItem(
                recommended=True,
                reason=(
                    f"Moderate noise detected (estimated sigma={noise.noise_score:.1f}). "
                    "Denoising is recommended to smooth background grain while preserving major edges."
                ),
                evidence="noise_level_medium",
            )
        else:
            denoise_item = RecommendationItem(
                recommended=False,
                reason=(
                    f"Low noise detected (estimated sigma={noise.noise_score:.1f}). "
                    "Denoising is not needed and may soften subtle natural textures."
                ),
                evidence="noise_level_low",
            )

        # 2. Contrast recommendation
        if contrast.contrast_level == "low":
            detected_issues.append("Low Dynamic Range / Faded Contrast")
            contrast_item = RecommendationItem(
                recommended=True,
                reason=(
                    f"Low contrast detected (std dev={contrast.contrast_score:.1f}, "
                    f"dynamic range={contrast.dynamic_range:.1f}). "
                    "CLAHE contrast enhancement on the L channel will recover faded shadow/highlight details."
                ),
                evidence="contrast_level_low",
            )
        else:
            contrast_item = RecommendationItem(
                recommended=False,
                reason=(
                    f"Contrast is adequate (std dev={contrast.contrast_score:.1f}, "
                    f"dynamic range={contrast.dynamic_range:.1f}). "
                    "Additional contrast expansion is optional."
                ),
                evidence="contrast_level_adequate",
            )

        # 3. Sharpening recommendation
        if sharpness.sharpness_level == "blurry":
            detected_issues.append("Soft / Low Edge Definition")
            sharpen_item = RecommendationItem(
                recommended=True,
                reason=(
                    f"Image exhibits low edge sharpness (Laplacian variance={sharpness.sharpness_score:.1f}). "
                    "Laplacian sharpening can recover edge definition, though it cannot recreate unrecorded optical details."
                ),
                evidence="sharpness_level_blurry",
            )
        elif sharpness.sharpness_level == "moderate" and noise.noise_level == "high":
            sharpen_item = RecommendationItem(
                recommended=False,
                reason=(
                    "Sharpening is not recommended on high-noise images as it can amplify photographic grain artifacts."
                ),
                evidence="noise_precludes_sharpening",
            )
        elif sharpness.sharpness_level == "moderate":
            sharpen_item = RecommendationItem(
                recommended=False,
                reason=(
                    f"Edge definition is moderate (Laplacian variance={sharpness.sharpness_score:.1f}). "
                    "Sharpening is optional but not strictly required."
                ),
                evidence="sharpness_level_moderate",
            )
        else:
            sharpen_item = RecommendationItem(
                recommended=False,
                reason=(
                    f"Image already exhibits crisp edge sharpness (Laplacian variance={sharpness.sharpness_score:.1f}). "
                    "Additional sharpening may cause haloing."
                ),
                evidence="sharpness_level_sharp",
            )

        # 4. Colorization recommendation
        if monochrome.is_monochrome:
            detected_issues.append("Monochrome / Black & White")
            colorize_item = RecommendationItem(
                recommended=True,
                reason=(
                    "Image is classified as monochrome. AI colorization can synthesize plausible colors "
                    "using learned visual priors from the Zhang et al. (ECCV 2016) deep neural network."
                ),
                evidence="image_is_monochrome",
            )
        else:
            colorize_item = RecommendationItem(
                recommended=False,
                reason=(
                    f"Image contains active color channels (color variation score={monochrome.color_variation_score:.1f}). "
                    "Re-colorization is unnecessary."
                ),
                evidence="image_has_color",
            )

        recommendations = RestorationRecommendations(
            denoise=denoise_item,
            contrast=contrast_item,
            sharpen=sharpen_item,
            colorize=colorize_item,
        )

        return recommendations, detected_issues

    def analyze_array(
        self,
        image_rgb: np.ndarray,
        filename: str = "image.png",
        was_resized: bool = False,
    ) -> ImageAnalysisResponse:
        """Run complete diagnostic analysis on an in-memory RGB NumPy array.

        Args:
            image_rgb: RGB uint8 array of shape (height, width, 3).
            filename: Identifier filename.
            was_resized: Whether image was previously downscaled by the caller.

        Returns:
            ImageAnalysisResponse containing all measurements and recommendations.
        """
        start_time = time.perf_counter()
        h, w = image_rgb.shape[:2]
        channels = image_rgb.shape[2] if image_rgb.ndim == 3 else 1

        noise = self.estimate_noise(image_rgb)
        sharpness = self.estimate_sharpness(image_rgb)
        contrast = self.estimate_contrast(image_rgb)
        monochrome = self.estimate_monochrome(image_rgb)

        recommendations, issues = self.generate_recommendations(
            noise, sharpness, contrast, monochrome
        )

        elapsed = time.perf_counter() - start_time

        return ImageAnalysisResponse(
            status="success",
            filename=filename,
            image=ImageDimensions(
                width=w,
                height=h,
                channels=channels,
                was_resized=was_resized,
            ),
            analysis=AnalysisMetrics(
                noise=noise,
                sharpness=sharpness,
                contrast=contrast,
                monochrome=monochrome,
            ),
            detected_issues=issues,
            recommended_options=recommendations,
            elapsed_seconds=round(elapsed, 4),
        )

    def analyze_image(self, file_bytes: bytes, filename: str) -> ImageAnalysisResponse:
        """Validate, decode, downscale (if >1600px), and analyze an uploaded image file.

        Args:
            file_bytes: Raw binary bytes of uploaded image.
            filename: Original client filename.

        Returns:
            ImageAnalysisResponse schema.
        """
        self.validate_file_metadata(filename, len(file_bytes))
        image_rgb = self.decode_image_bytes(file_bytes)

        # Enforce the 1600px cap to keep analysis memory-bounded and fast
        processed_rgb, was_resized = resize_if_too_large(
            image_rgb, max_dimension=settings.MAX_IMAGE_DIMENSION
        )

        return self.analyze_array(
            image_rgb=processed_rgb,
            filename=filename,
            was_resized=was_resized,
        )

