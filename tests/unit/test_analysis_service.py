"""Module: test_analysis_service.py

Purpose:
Unit test suite for AnalysisService, verifying deterministic behavior for noise estimation,
sharpness evaluation, contrast/dynamic range measurement, monochrome detection, and
rule-based restoration recommendation logic.
"""

import io
import cv2
import numpy as np
import pytest
from PIL import Image

from backend.src.core.exceptions import (
    CorruptedImageError,
    FileTooLargeError,
    UnsupportedFormatError,
)
from backend.src.schemas.analysis import (
    ContrastAnalysis,
    ImageAnalysisResponse,
    MonochromeAnalysis,
    NoiseAnalysis,
    SharpnessAnalysis,
)
from backend.src.services.analysis_service import AnalysisService


@pytest.fixture
def analysis_service() -> AnalysisService:
    """Fixture providing a fresh instance of AnalysisService."""
    return AnalysisService()


class TestNoiseEstimation:
    """Tests for blind Laplacian-residual noise estimation."""

    def test_clean_uniform_image_has_zero_noise(self, analysis_service: AnalysisService):
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        result = analysis_service.estimate_noise(img)
        assert result.noise_score == 0.0
        assert result.noise_level == "low"
        assert result.method == "laplacian_residual"

    def test_increasing_noise_increases_score(self, analysis_service: AnalysisService):
        np.random.seed(42)
        base = np.full((150, 150, 3), 128, dtype=np.float32)

        # Low noise (sigma = 3.0)
        noise_low = np.random.normal(0, 3.0, (150, 150, 3))
        img_low = np.clip(base + noise_low, 0, 255).astype(np.uint8)

        # High noise (sigma = 20.0)
        noise_high = np.random.normal(0, 20.0, (150, 150, 3))
        img_high = np.clip(base + noise_high, 0, 255).astype(np.uint8)

        res_low = analysis_service.estimate_noise(img_low)
        res_high = analysis_service.estimate_noise(img_high)

        assert res_high.noise_score > res_low.noise_score
        assert res_low.noise_score < 6.0
        assert res_high.noise_score > 10.0
        assert res_high.noise_level == "high"

    def test_small_image_does_not_crash(self, analysis_service: AnalysisService):
        # Image smaller than 3x3
        small_img = np.ones((2, 2, 3), dtype=np.uint8) * 100
        res = analysis_service.estimate_noise(small_img)
        assert res.noise_score == 0.0
        assert res.noise_level == "low"

    def test_grayscale_2d_array_supported(self, analysis_service: AnalysisService):
        gray = np.full((80, 80), 50, dtype=np.uint8)
        res = analysis_service.estimate_noise(gray)
        assert res.noise_score == 0.0
        assert res.noise_level == "low"

    def test_invalid_input_raises_value_error(self, analysis_service: AnalysisService):
        with pytest.raises(ValueError, match="Input image must be a valid NumPy array"):
            analysis_service.estimate_noise(None)  # type: ignore


class TestSharpnessEstimation:
    """Tests for discrete Laplacian variance sharpness analysis."""

    def test_uniform_image_has_zero_sharpness(self, analysis_service: AnalysisService):
        img = np.full((100, 100, 3), 200, dtype=np.uint8)
        res = analysis_service.estimate_sharpness(img)
        assert res.sharpness_score == 0.0
        assert res.sharpness_level == "blurry"

    def test_sharp_vs_blurred_edges(self, analysis_service: AnalysisService):
        # Create crisp black-to-white vertical step edge
        sharp_img = np.zeros((100, 100, 3), dtype=np.uint8)
        sharp_img[:, 50:] = 255

        # Blurred version
        blurred_img = cv2.GaussianBlur(sharp_img, (15, 15), 0)

        res_sharp = analysis_service.estimate_sharpness(sharp_img)
        res_blurred = analysis_service.estimate_sharpness(blurred_img)

        assert res_sharp.sharpness_score > res_blurred.sharpness_score
        assert res_sharp.sharpness_level in ("moderate", "sharp")
        assert res_blurred.sharpness_score < res_sharp.sharpness_score


class TestContrastEstimation:
    """Tests for intensity dispersion and dynamic range analysis."""

    def test_uniform_image_has_zero_contrast(self, analysis_service: AnalysisService):
        img = np.full((100, 100, 3), 100, dtype=np.uint8)
        res = analysis_service.estimate_contrast(img)
        assert res.contrast_score == 0.0
        assert res.dynamic_range == 0.0
        assert res.contrast_level == "low"

    def test_low_contrast_image_classified_as_low(self, analysis_service: AnalysisService):
        # Faded/foggy image: pixel values tightly clustered between 120 and 135
        img = np.random.randint(120, 136, (100, 100, 3), dtype=np.uint8)
        res = analysis_service.estimate_contrast(img)
        assert res.contrast_score < 30.0
        assert res.dynamic_range < 100.0
        assert res.contrast_level == "low"

    def test_high_contrast_image_classified_as_high(self, analysis_service: AnalysisService):
        # Half 0, half 255
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, 50:] = 255
        res = analysis_service.estimate_contrast(img)
        assert res.contrast_score >= 65.0
        assert res.dynamic_range > 200.0
        assert res.contrast_level == "high"


class TestMonochromeDetection:
    """Tests for RGB chromatic channel difference evaluation."""

    def test_pure_grayscale_classified_as_monochrome(self, analysis_service: AnalysisService):
        # 3 identical channels
        gray_layer = np.linspace(0, 255, 100, dtype=np.uint8).reshape(10, 10)
        img = np.stack([gray_layer, gray_layer, gray_layer], axis=-1)

        res = analysis_service.estimate_monochrome(img)
        assert res.is_monochrome is True
        assert res.color_variation_score == 0.0
        assert res.confidence == 1.0

    def test_near_grayscale_with_slight_drift_classified_as_monochrome(
        self, analysis_service: AnalysisService
    ):
        # Paper yellowing / scanner drift: R=130, G=129, B=128
        base = np.full((50, 50), 128, dtype=np.uint8)
        img = np.stack([base + 2, base + 1, base], axis=-1)

        res = analysis_service.estimate_monochrome(img)
        assert res.is_monochrome is True
        assert res.color_variation_score < 3.5

    def test_saturated_color_classified_as_color(self, analysis_service: AnalysisService):
        # Vibrant red image
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        img[:, :, 0] = 255  # Red
        res = analysis_service.estimate_monochrome(img)
        assert res.is_monochrome is False
        assert res.color_variation_score > 50.0

    def test_single_channel_grayscale_array(self, analysis_service: AnalysisService):
        img = np.zeros((40, 40), dtype=np.uint8)
        res = analysis_service.estimate_monochrome(img)
        assert res.is_monochrome is True
        assert res.color_variation_score == 0.0


class TestRecommendations:
    """Tests for rule-based recommendation logic."""

    def test_high_noise_triggers_denoise_recommendation(
        self, analysis_service: AnalysisService
    ):
        noise = NoiseAnalysis(noise_score=15.2, noise_level="high")
        sharpness = SharpnessAnalysis(sharpness_score=350.0, sharpness_level="moderate")
        contrast = ContrastAnalysis(contrast_score=50.0, dynamic_range=150.0, contrast_level="moderate")
        mono = MonochromeAnalysis(is_monochrome=False, color_variation_score=20.0, confidence=0.9)

        recs, issues = analysis_service.generate_recommendations(noise, sharpness, contrast, mono)
        assert recs.denoise.recommended is True
        assert "noise_level_high" in recs.denoise.evidence
        assert "High Photographic Grain / Sensor Noise" in issues

    def test_low_contrast_triggers_contrast_recommendation(
        self, analysis_service: AnalysisService
    ):
        noise = NoiseAnalysis(noise_score=2.0, noise_level="low")
        sharpness = SharpnessAnalysis(sharpness_score=350.0, sharpness_level="moderate")
        contrast = ContrastAnalysis(contrast_score=15.0, dynamic_range=60.0, contrast_level="low")
        mono = MonochromeAnalysis(is_monochrome=False, color_variation_score=20.0, confidence=0.9)

        recs, issues = analysis_service.generate_recommendations(noise, sharpness, contrast, mono)
        assert recs.contrast.recommended is True
        assert "contrast_level_low" in recs.contrast.evidence
        assert "Low Dynamic Range / Faded Contrast" in issues

    def test_monochrome_triggers_colorization_recommendation(
        self, analysis_service: AnalysisService
    ):
        noise = NoiseAnalysis(noise_score=2.0, noise_level="low")
        sharpness = SharpnessAnalysis(sharpness_score=350.0, sharpness_level="moderate")
        contrast = ContrastAnalysis(contrast_score=50.0, dynamic_range=150.0, contrast_level="moderate")
        mono = MonochromeAnalysis(is_monochrome=True, color_variation_score=0.5, confidence=0.95)

        recs, issues = analysis_service.generate_recommendations(noise, sharpness, contrast, mono)
        assert recs.colorize.recommended is True
        assert "image_is_monochrome" in recs.colorize.evidence
        assert "Monochrome / Black & White" in issues

    def test_clean_color_image_has_no_aggressive_recommendations(
        self, analysis_service: AnalysisService
    ):
        noise = NoiseAnalysis(noise_score=1.5, noise_level="low")
        sharpness = SharpnessAnalysis(sharpness_score=600.0, sharpness_level="sharp")
        contrast = ContrastAnalysis(contrast_score=68.0, dynamic_range=220.0, contrast_level="high")
        mono = MonochromeAnalysis(is_monochrome=False, color_variation_score=35.0, confidence=0.95)

        recs, issues = analysis_service.generate_recommendations(noise, sharpness, contrast, mono)
        assert recs.denoise.recommended is False
        assert recs.contrast.recommended is False
        assert recs.sharpen.recommended is False
        assert recs.colorize.recommended is False
        assert len(issues) == 0


class TestAnalysisArrayAndImage:
    """Tests for high-level analyze_array and analyze_image methods."""

    def test_analyze_array_returns_valid_schema(self, analysis_service: AnalysisService):
        img = np.full((120, 160, 3), 128, dtype=np.uint8)
        res = analysis_service.analyze_array(img, filename="test.png")
        assert isinstance(res, ImageAnalysisResponse)
        assert res.filename == "test.png"
        assert res.image.width == 160
        assert res.image.height == 120
        assert res.image.channels == 3
        assert res.image.was_resized is False
        assert res.elapsed_seconds >= 0.0

    def test_analyze_image_valid_jpeg_bytes(self, analysis_service: AnalysisService):
        # Generate valid in-memory JPEG
        pil_img = Image.new("RGB", (100, 80), color=(100, 150, 200))
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG")
        jpeg_bytes = buf.getvalue()

        res = analysis_service.analyze_image(jpeg_bytes, "photo.jpg")
        assert res.filename == "photo.jpg"
        assert res.image.width == 100
        assert res.image.height == 80
        assert res.status == "success"

    def test_analyze_image_downscales_oversized(self, analysis_service: AnalysisService):
        # Create oversized image: 1800x600 (longest axis exceeds 1600px cap)
        pil_img = Image.new("RGB", (1800, 600), color=(128, 128, 128))
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        res = analysis_service.analyze_image(png_bytes, "large.png")
        assert res.image.was_resized is True
        assert res.image.width == 1600
        assert res.image.height == 533

    def test_empty_bytes_raises_corrupted_image_error(
        self, analysis_service: AnalysisService
    ):
        with pytest.raises(CorruptedImageError, match="Uploaded file is empty"):
            analysis_service.analyze_image(b"", "empty.jpg")

    def test_corrupt_bytes_raises_corrupted_image_error(
        self, analysis_service: AnalysisService
    ):
        with pytest.raises(CorruptedImageError, match="Could not read image content"):
            analysis_service.analyze_image(b"not an image", "bad.jpg")

    def test_unsupported_format_raises_unsupported_format_error(
        self, analysis_service: AnalysisService
    ):
        with pytest.raises(UnsupportedFormatError, match="Unsupported file format"):
            analysis_service.analyze_image(b"dummy", "doc.pdf")

    def test_file_too_large_raises_file_too_large_error(
        self, analysis_service: AnalysisService
    ):
        huge_bytes = b"0" * (26 * 1024 * 1024)
        with pytest.raises(FileTooLargeError, match="exceeds maximum allowed limit"):
            analysis_service.analyze_image(huge_bytes, "huge.jpg")

