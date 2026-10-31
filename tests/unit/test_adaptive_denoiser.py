"""Module: test_adaptive_denoiser.py

Purpose:
Comprehensive unit and integration test suite for the Adaptive Denoising Engine.

Verifies:
- Parameter selection mapping, boundary handling (3.99, 4.0, 9.99, 10.0), and deterministic behavior.
- Adaptive Non-Local Means filtering on synthetic images with varied noise levels.
- Detail preservation on fine textures, checkerboards, thin lines, and sharp edges.
- Grayscale (1-channel) and color (3-channel) image support.
- Restoration pipeline integration and backward compatibility.
"""

import cv2
import numpy as np
import pytest

from backend.src.processing.restoration.denoiser import (
    DenoiseParameters,
    adaptive_denoise_image,
    denoise_image,
    select_denoising_parameters,
)
from backend.src.processing.restoration.restorer import enhance_image


class TestParameterSelection:
    """Tests for select_denoising_parameters."""

    def test_low_noise_score_selects_low_or_skip(self):
        # Pristine image (sigma < 1.5) skips filtering entirely
        params_pristine = select_denoising_parameters(noise_score=0.8)
        assert params_pristine.noise_level == "low"
        assert params_pristine.skip is True
        assert params_pristine.h == 0.0

        # Mild noise (1.5 <= sigma < 4.0) selects gentle filtering
        params_mild = select_denoising_parameters(noise_score=2.5)
        assert params_mild.noise_level == "low"
        assert params_mild.skip is False
        assert params_mild.h == 3.0
        assert params_mild.h_color == 3.0

    def test_medium_noise_score_selects_medium_strength(self):
        params = select_denoising_parameters(noise_score=6.5)
        assert params.noise_level == "medium"
        assert params.skip is False
        assert params.h == 7.0
        assert params.h_color == 7.0

    def test_high_noise_score_selects_high_strength(self):
        params = select_denoising_parameters(noise_score=15.0)
        assert params.noise_level == "high"
        assert params.skip is False
        assert params.h >= 12.0
        assert params.h <= 16.0
        assert params.h_color == params.h

    @pytest.mark.parametrize(
        "score,expected_level,expected_h",
        [
            (3.99, "low", 3.0),
            (4.00, "medium", 7.0),
            (9.99, "medium", 7.0),
            (10.0, "high", 12.0),
        ],
    )
    def test_boundary_values(self, score, expected_level, expected_h):
        params = select_denoising_parameters(noise_score=score)
        assert params.noise_level == expected_level
        assert params.h == expected_h

    def test_qualitative_noise_level_string_mapping(self):
        low = select_denoising_parameters(noise_level="low")
        assert low.noise_level == "low"
        assert low.h == 3.0

        med = select_denoising_parameters(noise_level="medium")
        assert med.noise_level == "medium"
        assert med.h == 7.0

        high = select_denoising_parameters(noise_level="high")
        assert high.noise_level == "high"
        assert high.h == 12.0

    def test_invalid_and_fallback_inputs(self):
        # Unknown string falls back to standard safe medium setting
        fallback = select_denoising_parameters(noise_level="unknown_noise_type")
        assert fallback.noise_level == "medium"
        assert fallback.h == 8.0

        # None input
        default_fallback = select_denoising_parameters()
        assert default_fallback.h == 8.0

        # Negative noise score clamped to 0.0 -> pristine low noise
        neg = select_denoising_parameters(noise_score=-5.0)
        assert neg.noise_score == 0.0
        assert neg.skip is True

    def test_opencv_parameter_constraints(self):
        for score in [0.0, 2.0, 5.0, 12.0, 25.0]:
            p = select_denoising_parameters(noise_score=score)
            assert p.h >= 0.0
            assert p.h_color >= 0.0
            # Window sizes must be positive odd integers
            assert p.template_window_size % 2 == 1
            assert p.search_window_size % 2 == 1
            assert p.search_window_size > p.template_window_size


class TestAdaptiveDenoisingExecution:
    """Tests for adaptive_denoise_image and denoise_image execution."""

    def test_pristine_clean_image_skips_processing_identically(self):
        clean_img = np.full((60, 60, 3), 128, dtype=np.uint8)
        denoised, params = adaptive_denoise_image(clean_img)

        assert params.skip is True
        assert np.array_equal(denoised, clean_img)

    def test_noisy_image_variance_is_reduced(self):
        rng = np.random.default_rng(42)
        base = np.full((80, 80, 3), 128, dtype=np.int16)
        noise = rng.normal(0, 15, size=base.shape).astype(np.int16)
        noisy = np.clip(base + noise, 0, 255).astype(np.uint8)

        denoised, params = adaptive_denoise_image(noisy)

        assert params.noise_level in ("medium", "high")
        assert params.h >= 7.0
        # Measurable variance reduction
        assert denoised.std() < noisy.std()
        assert denoised.shape == noisy.shape
        assert denoised.dtype == np.uint8

    def test_grayscale_single_channel_image(self):
        gray = np.full((80, 80), 100, dtype=np.uint8)
        # Add salt and pepper / gaussian noise
        noise = np.random.normal(0, 10, (80, 80)).astype(np.int16)
        noisy_gray = np.clip(gray + noise, 0, 255).astype(np.uint8)

        denoised, params = adaptive_denoise_image(noisy_gray)

        assert denoised.shape == (80, 80)
        assert denoised.dtype == np.uint8
        assert denoised.std() < noisy_gray.std()

    def test_denoise_image_adaptive_flag(self):
        clean_img = np.full((50, 50, 3), 100, dtype=np.uint8)
        # Adaptive=True should detect clean image and leave it identical
        result = denoise_image(clean_img, adaptive=True)
        assert np.array_equal(result, clean_img)

    def test_denoise_image_legacy_fixed_behavior(self):
        clean_img = np.full((50, 50, 3), 100, dtype=np.uint8)
        # Adaptive=False runs standard fixed NLM
        result = denoise_image(clean_img, adaptive=False)
        assert result.shape == clean_img.shape
        assert result.dtype == np.uint8

    def test_invalid_input_types_raise_value_error(self):
        with pytest.raises(ValueError, match="Input image must be a valid NumPy array"):
            adaptive_denoise_image("not an array")  # type: ignore

        with pytest.raises(ValueError, match="Input image must have dtype uint8"):
            adaptive_denoise_image(np.zeros((50, 50, 3), dtype=np.float32))

        with pytest.raises(ValueError, match="Expected a 3-channel color image"):
            adaptive_denoise_image(np.zeros((50, 50, 4), dtype=np.uint8))


class TestDetailPreservation:
    """Tests confirming fine edges, lines, and textures are preserved."""

    def test_checkerboard_pattern_retains_edges(self):
        # 8x8 checkerboard pattern with sharp high-contrast transitions
        board = np.zeros((64, 64, 3), dtype=np.uint8)
        for i in range(8):
            for j in range(8):
                if (i + j) % 2 == 0:
                    board[i * 8 : (i + 1) * 8, j * 8 : (j + 1) * 8] = 255

        # Denoise with adaptive
        denoised, params = adaptive_denoise_image(board)

        # On high-frequency periodic patterns, moderate parameters are chosen and edges are preserved
        assert params.h <= 8.0
        # Edges should remain crisp (gradient variance stays high)
        orig_grad = cv2.Laplacian(cv2.cvtColor(board, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        denoised_grad = cv2.Laplacian(
            cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY), cv2.CV_64F
        ).var()
        # Edge definition is strongly preserved by Non-Local Means patch matching (>= 90%)
        assert denoised_grad >= 0.90 * orig_grad

    def test_thin_lines_preserved(self):
        # 1-pixel thin white lines on dark background
        img = np.zeros((80, 80, 3), dtype=np.uint8)
        img[40, :] = 255  # Horizontal thin line
        img[:, 40] = 255  # Vertical thin line

        denoised, params = adaptive_denoise_image(img)
        # Line pixels must still have high intensity (> 240)
        assert denoised[40, 10, 0] >= 240
        assert denoised[10, 40, 0] >= 240


class TestRestorationIntegration:
    """Tests for enhance_image integration with adaptive denoising."""

    def test_enhance_image_with_adaptive_denoise_default(self):
        sample = np.full((60, 60, 3), 120, dtype=np.uint8)
        result = enhance_image(sample, denoise=True, contrast=False, sharpen=False)
        assert result.shape == sample.shape
        assert result.dtype == sample.dtype

    def test_enhance_image_with_denoise_disabled(self):
        sample = np.full((60, 60, 3), 120, dtype=np.uint8)
        result = enhance_image(sample, denoise=False, contrast=False, sharpen=False)
        assert np.array_equal(result, sample)

    def test_enhance_image_explicit_fixed_denoise(self):
        sample = np.full((60, 60, 3), 120, dtype=np.uint8)
        result = enhance_image(
            sample, denoise=True, contrast=False, sharpen=False, adaptive_denoise=False
        )
        assert result.shape == sample.shape
        assert result.dtype == sample.dtype
