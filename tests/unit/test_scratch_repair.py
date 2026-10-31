"""Unit test suite for Archival Scratch Repair and Inpainting Engine (Phase 5.3).

Tests:
1. Directional morphological scratch detection (vertical, horizontal, diagonal 45, diagonal 135).
2. Polarity detection (dark scratches on light regions, bright scratches on dark regions).
3. False-positive rejection (checkerboards, step edges, solid circles/blobs, gradients, uniform fields).
4. Mask generation and validation (binary values, dimensions, dtypes, safety coverage threshold).
5. Inpainting reconstruction quality (MAE reduction against clean reference, finite values).
6. Inpainting algorithm options (Telea vs Navier-Stokes, radius parameterization).
7. Empty mask zero-overhead bypass (clean images pass through untouched).
8. Grayscale (1-channel) and Color (3-channel) image preservation.
9. Pipeline integration via `enhance_image` and backward compatibility defaults.
"""

import cv2
import numpy as np
import pytest

from backend.src.processing.restoration import (
    ScratchRepairMetadata,
    detect_scratch_mask,
    enhance_image,
    repair_scratches,
)
from backend.src.processing.restoration.scratch_repair import (
    DEFAULT_INPAINT_METHOD,
    DEFAULT_INPAINT_RADIUS,
    MAX_REPAIR_COVERAGE,
)


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def clean_uniform_image():
    """150x150 uniform mid-gray color image."""
    return np.full((150, 150, 3), 128, dtype=np.uint8)


@pytest.fixture
def clean_grayscale_image():
    """150x150 uniform mid-gray 1-channel image."""
    return np.full((150, 150), 128, dtype=np.uint8)


@pytest.fixture
def clean_synthetic_scene():
    """200x200 smooth continuous color scene with non-trivial gradients."""
    h, w = 200, 200
    scene = np.zeros((h, w, 3), dtype=np.uint8)
    for r in range(h):
        for c in range(w):
            scene[r, c] = [
                int(110 + 45 * np.sin(r / 25.0)),
                int(125 + 35 * np.cos(c / 30.0)),
                int(140 + 30 * np.sin((r + c) / 35.0)),
            ]
    return scene


# =====================================================================
# 1. Scratch Detection Tests
# =====================================================================


class TestScratchDetection:
    """Test directional and polarity scratch detection capabilities."""

    def test_vertical_dark_scratch_detection(self, clean_uniform_image):
        """Test vertical dark scratch detection against lighter background."""
        img = clean_uniform_image.copy()
        img[30:120, 75] = (25, 25, 25)

        mask, meta = detect_scratch_mask(img)

        assert isinstance(meta, ScratchRepairMetadata)
        assert meta.applied is True
        assert meta.detected_components >= 1
        assert meta.repaired_pixels > 0
        assert meta.skipped is False
        assert mask.shape == (150, 150)
        # Scratch center should be marked
        assert mask[75, 75] == 255

    def test_horizontal_bright_scratch_detection(self, clean_uniform_image):
        """Test horizontal bright scratch detection against darker background."""
        img = clean_uniform_image.copy()
        img[75, 30:120] = (245, 245, 245)

        mask, meta = detect_scratch_mask(img)

        assert meta.applied is True
        assert meta.detected_components >= 1
        assert meta.repaired_pixels > 0
        assert meta.skipped is False
        assert mask[75, 75] == 255

    def test_diagonal_45_dark_scratch_detection(self, clean_uniform_image):
        """Test ~45 degree diagonal dark scratch detection."""
        img = clean_uniform_image.copy()
        for d in range(30, 110):
            img[d, 140 - d] = (20, 20, 20)

        mask, meta = detect_scratch_mask(img)

        assert meta.applied is True
        assert meta.detected_components >= 1
        assert meta.repaired_pixels > 0
        assert mask[70, 70] == 255

    def test_diagonal_135_bright_scratch_detection(self, clean_uniform_image):
        """Test ~135 degree diagonal bright scratch detection."""
        img = clean_uniform_image.copy()
        for d in range(30, 110):
            img[d, d] = (245, 245, 245)

        mask, meta = detect_scratch_mask(img)

        assert meta.applied is True
        assert meta.detected_components >= 1
        assert meta.repaired_pixels > 0
        assert mask[70, 70] == 255

    def test_multiple_scratches_detected(self, clean_uniform_image):
        """Test detection of multiple distinct scratches in the same photograph."""
        img = clean_uniform_image.copy()
        # Vertical scratch
        img[20:80, 40] = (20, 20, 20)
        # Horizontal scratch
        img[110, 80:140] = (240, 240, 240)

        mask, meta = detect_scratch_mask(img)

        assert meta.applied is True
        assert meta.detected_components >= 2
        assert mask[50, 40] == 255
        assert mask[110, 110] == 255

    def test_clean_image_produces_zero_detections(self, clean_uniform_image):
        """Pristine uniform image must produce exactly 0 detected components and 0 pixels."""
        mask, meta = detect_scratch_mask(clean_uniform_image)

        assert meta.applied is False
        assert meta.detected_components == 0
        assert meta.repaired_pixels == 0
        assert meta.coverage_percentage == 0.0
        assert meta.skipped is False
        assert np.count_nonzero(mask) == 0

    def test_smooth_gradient_produces_zero_detections(self):
        """Smooth lighting gradient must not trigger false positive scratch detections."""
        grad = np.tile(np.linspace(20, 230, 160, dtype=np.uint8), (160, 1))
        grad_bgr = cv2.cvtColor(grad, cv2.COLOR_GRAY2BGR)

        mask, meta = detect_scratch_mask(grad_bgr)

        assert meta.detected_components == 0
        assert meta.repaired_pixels == 0
        assert np.count_nonzero(mask) == 0

    def test_grayscale_input_supported(self, clean_grayscale_image):
        """Single-channel grayscale input must be processed without error."""
        img = clean_grayscale_image.copy()
        img[30:100, 75] = 20

        mask, meta = detect_scratch_mask(img)

        assert meta.applied is True
        assert mask.shape == (150, 150)
        assert mask[65, 75] == 255


# =====================================================================
# 2. Detail Preservation & False-Positive Control Tests
# =====================================================================


class TestFalsePositiveControl:
    """Ensure natural photographic features are not mistakenly classified as scratches."""

    def test_checkerboard_pattern_not_detected_as_scratch(self):
        """Checkerboard textures must not be marked as scratches."""
        checker = (np.indices((140, 140)).sum(axis=0) % 16 < 8).astype(np.uint8) * 180 + 40
        bgr = cv2.cvtColor(checker, cv2.COLOR_GRAY2BGR)

        mask, meta = detect_scratch_mask(bgr)

        assert meta.detected_components == 0
        assert meta.repaired_pixels == 0

    def test_step_edge_not_detected_as_scratch(self):
        """High-contrast step edges (e.g. wall or horizon) must be rejected via ridge filtering."""
        step_edge = np.full((120, 120), 40, dtype=np.uint8)
        step_edge[:, 60:] = 210
        bgr = cv2.cvtColor(step_edge, cv2.COLOR_GRAY2BGR)

        mask, meta = detect_scratch_mask(bgr)

        assert meta.detected_components == 0
        assert meta.repaired_pixels == 0

    def test_solid_circular_blobs_not_detected(self):
        """Solid circular shapes (e.g. eyes, buttons, dots) must be rejected by aspect-ratio & ridge checks."""
        img = np.full((140, 140, 3), 130, dtype=np.uint8)
        cv2.circle(img, (50, 50), 16, (30, 30, 30), -1)
        cv2.circle(img, (90, 90), 20, (220, 220, 220), -1)

        mask, meta = detect_scratch_mask(img)

        assert meta.detected_components == 0
        assert meta.repaired_pixels == 0


# =====================================================================
# 3. Mask Validation & Safety Guards
# =====================================================================


class TestMaskValidation:
    """Test mask shape, dtypes, safety coverage threshold, and error handling."""

    def test_mask_binary_values_and_dtype(self, clean_uniform_image):
        """Mask must be uint8 containing only 0 and 255 values."""
        img = clean_uniform_image.copy()
        img[30:90, 60] = (20, 20, 20)

        mask, _ = detect_scratch_mask(img)

        assert mask.dtype == np.uint8
        unique_vals = set(np.unique(mask))
        assert unique_vals.issubset({0, 255})

    def test_excessive_coverage_triggers_safety_guard(self, clean_uniform_image):
        """If defect mask exceeds MAX_REPAIR_COVERAGE (5%), repair must be safely skipped."""
        img = clean_uniform_image.copy()
        # Create multiple distinct scratches exceeding 5% coverage
        for col in [25, 60, 95, 130]:
            img[10:140, col] = (15, 15, 15)

        mask, meta = detect_scratch_mask(img, max_coverage=0.05)

        assert meta.skipped is True
        assert meta.applied is False
        assert "exceeds safety threshold" in (meta.skip_reason or "")
        # Safe no-op mask returned
        assert np.count_nonzero(mask) == 0

    def test_invalid_input_types_raise_errors(self):
        """Invalid inputs must raise appropriate TypeError or ValueError."""
        with pytest.raises(TypeError):
            detect_scratch_mask("not-an-array")  # type: ignore

        with pytest.raises(ValueError):
            detect_scratch_mask(np.zeros((50, 50), dtype=np.float32))

        with pytest.raises(ValueError):
            detect_scratch_mask(np.zeros((1, 1), dtype=np.uint8))

        with pytest.raises(ValueError):
            detect_scratch_mask(np.zeros((50, 50, 5), dtype=np.uint8))


# =====================================================================
# 4. Inpainting Reconstruction Tests
# =====================================================================


class TestInpaintingReconstruction:
    """Test OpenCV inpainting quality, parameterization, and edge cases."""

    def test_inpainting_reduces_mae_on_synthetic_scene(self, clean_synthetic_scene):
        """Inpainting must significantly reduce Mean Absolute Error on scratched image."""
        ref = clean_synthetic_scene
        damaged = ref.copy()

        # Inject realistic vertical dark scratch and diagonal bright scratch
        damaged[35:165, 90] = [15, 15, 15]
        for d in range(40, 160):
            damaged[d, d] = [240, 240, 240]

        repaired, meta = repair_scratches(damaged, inpaint_radius=3, method="telea")

        mae_damaged = float(np.mean(np.abs(damaged.astype(float) - ref.astype(float))))
        mae_repaired = float(np.mean(np.abs(repaired.astype(float) - ref.astype(float))))

        assert meta.applied is True
        assert meta.detected_components >= 2
        # Repair should achieve at least 80% error reduction
        assert mae_repaired < mae_damaged * 0.2
        assert repaired.shape == ref.shape
        assert repaired.dtype == np.uint8
        assert np.all(np.isfinite(repaired))

    def test_empty_mask_returns_original_copy(self, clean_synthetic_scene):
        """Empty mask must return an untouched copy of the original image without running inpainting."""
        empty_mask = np.zeros(clean_synthetic_scene.shape[:2], dtype=np.uint8)
        repaired, meta = repair_scratches(clean_synthetic_scene, mask=empty_mask)

        assert meta.applied is False
        assert np.array_equal(repaired, clean_synthetic_scene)

    def test_clean_image_automatic_bypass(self, clean_synthetic_scene):
        """Clean image with no scratches detected must automatically bypass inpainting."""
        repaired, meta = repair_scratches(clean_synthetic_scene)

        assert meta.applied is False
        assert meta.repaired_pixels == 0
        assert np.array_equal(repaired, clean_synthetic_scene)

    def test_navier_stokes_inpainting_method(self, clean_synthetic_scene):
        """Navier-Stokes (NS) inpainting algorithm must execute successfully."""
        damaged = clean_synthetic_scene.copy()
        damaged[40:150, 80] = [20, 20, 20]

        repaired, meta = repair_scratches(damaged, method="ns", inpaint_radius=3)

        assert meta.applied is True
        assert meta.method == "ns"
        assert repaired.shape == clean_synthetic_scene.shape

    def test_grayscale_inpainting(self, clean_grayscale_image):
        """Single-channel grayscale images must remain single-channel after inpainting."""
        damaged = clean_grayscale_image.copy()
        damaged[30:120, 60] = 15

        repaired, meta = repair_scratches(damaged)

        assert meta.applied is True
        assert repaired.shape == (150, 150)
        assert repaired.dtype == np.uint8
        assert repaired[75, 60] > 100  # Restored close to background 128

    def test_invalid_parameters_raise_error(self, clean_uniform_image):
        """Invalid inpainting method or radius must raise ValueError."""
        with pytest.raises(ValueError):
            repair_scratches(clean_uniform_image, method="invalid_algorithm")

        with pytest.raises(ValueError):
            repair_scratches(clean_uniform_image, inpaint_radius=0)


# =====================================================================
# 5. Pipeline Integration & Backward Compatibility Tests
# =====================================================================


class TestPipelineIntegration:
    """Verify integration into `enhance_image` and backward compatibility."""

    def test_enhance_image_repair_disabled_by_default(self, clean_synthetic_scene):
        """repair=False must be the default and must bypass scratch repair entirely."""
        damaged = clean_synthetic_scene.copy()
        damaged[40:140, 80] = [20, 20, 20]

        # Call with default arguments (repair defaults to False)
        out_default = enhance_image(damaged, denoise=False, contrast=False, sharpen=False)

        # Output should be identical to input because all stages are disabled
        assert np.array_equal(out_default, damaged)

    def test_enhance_image_repair_enabled(self, clean_synthetic_scene):
        """When repair=True, scratches must be reconstructed within enhance_image."""
        damaged = clean_synthetic_scene.copy()
        damaged[40:140, 80] = [20, 20, 20]

        out_repaired = enhance_image(
            damaged,
            denoise=False,
            contrast=False,
            sharpen=False,
            repair=True,
        )

        # Scratched pixel should be repaired
        assert not np.array_equal(out_repaired, damaged)
        assert np.all(out_repaired[90, 80] > 80)

    def test_combined_full_pipeline_with_repair(self, clean_synthetic_scene):
        """All stages (repair + adaptive denoise + contrast + sharpen) must execute in harmony."""
        damaged = clean_synthetic_scene.copy()
        damaged[40:140, 80] = [20, 20, 20]

        restored = enhance_image(
            damaged,
            denoise=True,
            contrast=True,
            sharpen=True,
            adaptive_denoise=True,
            repair=True,
        )

        assert restored.shape == damaged.shape
        assert restored.dtype == np.uint8
        assert np.all(np.isfinite(restored))
