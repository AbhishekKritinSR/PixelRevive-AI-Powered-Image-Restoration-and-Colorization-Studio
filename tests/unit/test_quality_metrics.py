"""Unit tests for Phase 5.6 Quality Metrics: BRISQUE, SSIM, and Colorfulness."""

from pathlib import Path
import cv2
import numpy as np
import pytest

from backend.src.processing.evaluation.brisque import (
    are_brisque_assets_available,
    clear_brisque_instance,
    compute_brisque,
    get_brisque_evaluator,
)
from backend.src.processing.evaluation.colorfulness import compute_colorfulness
from backend.src.processing.evaluation.ssim import compute_ssim


# =====================================================================
# BRISQUE Tests
# =====================================================================

class TestBRISQUEEvaluation:
    """Unit tests for BRISQUE no-reference perceptual quality assessment."""

    def test_brisque_assets_availability(self):
        """Verify that official BRISQUE YAML model assets exist on disk."""
        assert are_brisque_assets_available() is True
        evaluator = get_brisque_evaluator()
        assert evaluator is not None

    def test_brisque_real_inference_color(self):
        """Verify BRISQUE scoring on a realistic 3-channel image."""
        img = np.full((128, 128, 3), 128, dtype=np.uint8)
        avail, score, interp = compute_brisque(img)

        assert avail is True
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0
        assert "BRISQUE" in interp

    def test_brisque_real_inference_grayscale(self):
        """Verify BRISQUE scoring on a 2D single-channel grayscale image."""
        gray = np.full((128, 128), 128, dtype=np.uint8)
        avail, score, interp = compute_brisque(gray)

        assert avail is True
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_brisque_deterministic_and_immutable(self):
        """Verify BRISQUE is deterministic and does not mutate input array."""
        img = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
        img_copy = img.copy()

        _, score1, _ = compute_brisque(img)
        _, score2, _ = compute_brisque(img)

        assert score1 == score2
        np.testing.assert_array_equal(img, img_copy)

    def test_brisque_missing_assets_reporting(self, monkeypatch):
        """Verify graceful reporting when model assets are not found."""
        from backend.src.core.config import settings

        monkeypatch.setattr(settings, "BRISQUE_MODEL_PATH", Path("/tmp/nonexistent_model.yml"))
        clear_brisque_instance()

        img = np.full((64, 64, 3), 128, dtype=np.uint8)
        avail, score, interp = compute_brisque(img)

        assert avail is False
        assert score is None
        assert "unavailable on disk" in interp
        clear_brisque_instance()

    def test_brisque_invalid_inputs_raise_errors(self):
        """Verify that empty, non-array, or wrong-dtype inputs raise ValueError."""
        with pytest.raises(ValueError, match="valid NumPy array"):
            compute_brisque("not_an_image")

        with pytest.raises(ValueError, match="empty"):
            compute_brisque(np.array([], dtype=np.uint8))

        with pytest.raises(ValueError, match="uint8"):
            compute_brisque(np.full((32, 32, 3), 0.5, dtype=np.float32))

        with pytest.raises(ValueError, match="Expected 2D grayscale or 3-channel"):
            compute_brisque(np.zeros((32, 32, 5), dtype=np.uint8))


# =====================================================================
# SSIM Tests
# =====================================================================

class TestSSIMEvaluation:
    """Unit tests for Structural Similarity Index (SSIM) reference-based evaluation."""

    def test_ssim_identical_images_produces_one(self):
        """Identical images must yield an SSIM score of 1.0."""
        img1 = np.full((64, 64, 3), 128, dtype=np.uint8)
        img2 = np.full((64, 64, 3), 128, dtype=np.uint8)

        score, channels, mode, interp = compute_ssim(img1, img2)

        assert score == 1.0
        assert mode == "color"
        assert channels["blue"] == 1.0
        assert channels["green"] == 1.0
        assert channels["red"] == 1.0
        assert "SSIM structural similarity" in interp

    def test_ssim_grayscale_mode(self):
        """Single-channel 2D images must evaluate in grayscale mode."""
        gray1 = np.full((64, 64), 100, dtype=np.uint8)
        gray2 = np.full((64, 64), 100, dtype=np.uint8)

        score, channels, mode, _ = compute_ssim(gray1, gray2)

        assert score == 1.0
        assert mode == "grayscale"
        assert "luminance" in channels
        assert channels["luminance"] == 1.0

    def test_ssim_similar_vs_dissimilar_images(self):
        """Mild perturbations yield high SSIM; extreme changes yield significantly lower SSIM."""
        # Structured gradient pattern
        grad = np.tile(np.linspace(10, 240, 64, dtype=np.uint8), (64, 1))
        ref = np.stack([grad, grad, grad], axis=-1)

        # Mild noise (should have high SSIM > 0.95)
        mild = np.clip(ref.astype(np.int16) + 3, 0, 255).astype(np.uint8)
        score_mild, _, _, _ = compute_ssim(mild, ref)

        # Strong perturbation (inverted image)
        inverted = 255 - ref
        score_inv, _, _, _ = compute_ssim(inverted, ref)

        assert score_mild > 0.95
        assert score_mild > score_inv

    def test_ssim_dimension_mismatch_raises_value_error(self):
        """Dimension mismatch between target and reference must raise ValueError."""
        img1 = np.full((64, 64, 3), 128, dtype=np.uint8)
        img2 = np.full((80, 64, 3), 128, dtype=np.uint8)

        with pytest.raises(ValueError, match="Dimension mismatch"):
            compute_ssim(img1, img2)

    def test_ssim_too_small_dimensions_raises_value_error(self):
        """Dimensions smaller than 11x11 must raise ValueError."""
        tiny1 = np.full((8, 8, 3), 128, dtype=np.uint8)
        tiny2 = np.full((8, 8, 3), 128, dtype=np.uint8)

        with pytest.raises(ValueError, match="too small"):
            compute_ssim(tiny1, tiny2)

    def test_ssim_invalid_types_and_empty_arrays_raise(self):
        """Verify input validation handles invalid arrays."""
        valid = np.full((32, 32, 3), 128, dtype=np.uint8)

        with pytest.raises(ValueError, match="valid NumPy arrays"):
            compute_ssim("not_array", valid)

        with pytest.raises(ValueError, match="must not be empty"):
            compute_ssim(np.array([], dtype=np.uint8), valid)

        with pytest.raises(ValueError, match="uint8 dtype"):
            compute_ssim(valid.astype(np.float32), valid)

    def test_ssim_input_immutability(self):
        """Verify computation does not alter input pixel arrays."""
        img1 = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
        img2 = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
        c1, c2 = img1.copy(), img2.copy()

        compute_ssim(img1, img2)

        np.testing.assert_array_equal(img1, c1)
        np.testing.assert_array_equal(img2, c2)


# =====================================================================
# Colorfulness Tests
# =====================================================================

class TestColorfulnessEvaluation:
    """Unit tests for Hasler and Süsstrunk (2003) colorfulness metric."""

    def test_colorfulness_pure_grayscale_returns_zero(self):
        """Monochrome / grayscale images must yield 0.0 colorfulness."""
        # 3-channel gray (R=G=B)
        gray_3ch = np.full((64, 64, 3), 128, dtype=np.uint8)
        score_3ch, _, interp_3ch = compute_colorfulness(gray_3ch)
        assert score_3ch == 0.0

        # 2-channel or single-channel gray
        gray_1ch = np.full((64, 64), 128, dtype=np.uint8)
        score_1ch, _, interp_1ch = compute_colorfulness(gray_1ch)
        assert score_1ch == 0.0
        assert "0.00" in interp_1ch

    def test_colorfulness_saturated_image_higher_than_pastel(self):
        """Vivid, saturated color images must yield higher colorfulness than pastel ones."""
        # High saturation (pure primaries)
        saturated = np.zeros((64, 64, 3), dtype=np.uint8)
        saturated[:32, :, 2] = 255  # Red
        saturated[32:, :, 0] = 255  # Blue

        # Muted pastel image
        muted = np.full((64, 64, 3), 120, dtype=np.uint8)
        muted[:, :, 2] += 10  # Very faint tint

        score_sat, components_sat, _ = compute_colorfulness(saturated)
        score_muted, components_muted, _ = compute_colorfulness(muted)

        assert score_sat > 50.0
        assert score_sat > score_muted
        assert "std_rgyb" in components_sat
        assert "mean_rgyb" in components_sat

    def test_colorfulness_invalid_inputs_raise_errors(self):
        """Verify validation of bad types, empty arrays, and invalid shapes."""
        with pytest.raises(ValueError, match="valid NumPy array"):
            compute_colorfulness(None)

        with pytest.raises(ValueError, match="empty"):
            compute_colorfulness(np.array([], dtype=np.uint8))

        with pytest.raises(ValueError, match="uint8"):
            compute_colorfulness(np.zeros((32, 32, 3), dtype=np.float32))

        with pytest.raises(ValueError, match="Expected 3-channel image"):
            compute_colorfulness(np.zeros((32, 32, 4), dtype=np.uint8))

    def test_colorfulness_deterministic_and_immutable(self):
        """Verify colorfulness is deterministic and preserves input."""
        img = np.random.randint(0, 255, (40, 40, 3), dtype=np.uint8)
        img_copy = img.copy()

        score1, _, _ = compute_colorfulness(img)
        score2, _, _ = compute_colorfulness(img)

        assert score1 == score2
        np.testing.assert_array_equal(img, img_copy)
