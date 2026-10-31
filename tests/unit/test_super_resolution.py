"""Unit test suite for AI Super-Resolution Engine (Phase 5.4).

Tests:
1. Model Registry and metadata validation (2x, 4x, licenses, architectures).
2. Lazy model loading, thread safety, and cache reuse.
3. Memory and dimension resource protection safeguards.
4. Input validation (types, channels, dtypes, dimensions).
5. Real 2x and 4x FSRCNN inference (output shapes, dtype, finite values).
6. Grayscale (1-channel) and BGR (3-channel) upscaling.
7. Pipeline integration in `enhance_image` and backward compatibility defaults.
"""

from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest

from backend.src.core.exceptions import (
    ModelUnavailableError,
    SuperResolutionResourceError,
    UnsupportedScaleError,
)
from backend.src.processing.restoration import (
    SuperResolutionMetadata,
    enhance_image,
    get_model_spec,
    is_model_file_present,
    is_model_loaded,
    upscale_image,
)
from backend.src.processing.restoration.super_resolution import (
    MODEL_REGISTRY,
    clear_model_cache,
    get_super_resolution_model,
    validate_super_resolution_resource_limits,
)


@pytest.fixture(autouse=True)
def clean_cache():
    """Ensure clean cache before and after each test."""
    clear_model_cache()
    yield
    clear_model_cache()


@pytest.fixture
def sample_bgr_64():
    """64x64 BGR test image."""
    img = np.full((64, 64, 3), 120, dtype=np.uint8)
    img[16:48, 16:48] = (220, 80, 80)
    return img


@pytest.fixture
def sample_gray_64():
    """64x64 Grayscale test image."""
    img = np.full((64, 64), 120, dtype=np.uint8)
    img[16:48, 16:48] = 220
    return img


# =====================================================================
# 1. Model Registry & Metadata Tests
# =====================================================================


class TestModelRegistry:
    """Test model registry entries, metadata, and scale validations."""

    def test_registered_scales(self):
        """Registry must contain configurations for 2x and 4x scaling."""
        assert 2 in MODEL_REGISTRY
        assert 4 in MODEL_REGISTRY

        spec2 = get_model_spec(2)
        assert spec2["scale"] == 2
        assert spec2["algorithm"] == "fsrcnn"
        assert spec2["filename"] == "FSRCNN_x2.pb"
        assert spec2["license"] == "Apache-2.0"

        spec4 = get_model_spec(4)
        assert spec4["scale"] == 4
        assert spec4["algorithm"] == "fsrcnn"
        assert spec4["filename"] == "FSRCNN_x4.pb"
        assert spec4["license"] == "Apache-2.0"

    def test_unsupported_scale_raises_error(self):
        """Unsupported scale factors must raise UnsupportedScaleError."""
        with pytest.raises(UnsupportedScaleError) as exc_info:
            get_model_spec(3)
        assert "Unsupported scaling factor 3" in str(exc_info.value)

        with pytest.raises(UnsupportedScaleError):
            get_model_spec(8)

    def test_model_file_presence_helpers(self):
        """Helper functions must accurately report file presence."""
        assert is_model_file_present(2) is True
        assert is_model_file_present(4) is True
        assert is_model_file_present(3) is False


# =====================================================================
# 2. Model Loading & Caching Tests
# =====================================================================


class TestModelLoadingAndCaching:
    """Test lazy model loading, cache reuse, and error handling."""

    def test_lazy_loading(self):
        """Models must not be loaded into memory until requested."""
        assert is_model_loaded(2) is False
        assert is_model_loaded(4) is False

        model2 = get_super_resolution_model(2)
        assert model2 is not None
        assert is_model_loaded(2) is True
        assert is_model_loaded(4) is False

    def test_cache_reuses_instance(self):
        """Repeated calls for the same scale must return the cached singleton instance."""
        inst1 = get_super_resolution_model(2)
        inst2 = get_super_resolution_model(2)
        assert inst1 is inst2

    def test_separate_cache_for_different_scales(self):
        """Scale 2 and Scale 4 must have distinct cached model instances."""
        inst2 = get_super_resolution_model(2)
        inst4 = get_super_resolution_model(4)
        assert inst2 is not inst4
        assert is_model_loaded(2) is True
        assert is_model_loaded(4) is True

    def test_missing_model_file_raises_model_unavailable(self):
        """Attempting to load a non-existent model file must raise ModelUnavailableError."""
        with patch.object(Path, "is_file", return_value=False):
            with pytest.raises(ModelUnavailableError) as exc_info:
                get_super_resolution_model(2)
            assert "missing from disk" in str(exc_info.value)
            # Ensure failed load does not contaminate the cache
            assert is_model_loaded(2) is False


# =====================================================================
# 3. Resource & Memory Protection Tests
# =====================================================================


class TestResourceProtection:
    """Test dimension and pixel budget limits."""

    def test_within_budget_passes(self):
        """Inputs yielding output within bounds must pass validation."""
        # 800x600 @ 2x -> 1600x1200 = 1.92 MP
        out_w, out_h = validate_super_resolution_resource_limits(600, 800, 2)
        assert out_w == 1600
        assert out_h == 1200

    def test_exceeding_max_dimension_raises_resource_error(self):
        """Outputs exceeding MAX_SUPER_RES_OUTPUT_DIMENSION (4096) must be rejected."""
        # 1200x800 @ 4x -> 4800x3200 (longest axis 4800 > 4096)
        with pytest.raises(SuperResolutionResourceError) as exc_info:
            validate_super_resolution_resource_limits(800, 1200, 4)
        assert "exceed the maximum allowable dimension limit" in str(exc_info.value)

    def test_exceeding_pixel_budget_raises_resource_error(self):
        """Outputs exceeding MAX_SUPER_RES_OUTPUT_PIXELS (12 MP) must be rejected."""
        # 2000x2000 @ 2x -> 4000x4000 = 16 MP (> 12 MP)
        with pytest.raises(SuperResolutionResourceError) as exc_info:
            validate_super_resolution_resource_limits(2000, 2000, 2)
        assert "exceeds the maximum allowable budget" in str(exc_info.value)


# =====================================================================
# 4. Input Validation Tests
# =====================================================================


class TestInputValidation:
    """Test input array shapes, types, and parameter checks."""

    def test_non_array_input_raises_type_error(self):
        with pytest.raises(TypeError):
            upscale_image("not-an-array", scale=2)  # type: ignore

    def test_non_uint8_dtype_raises_value_error(self):
        with pytest.raises(ValueError):
            upscale_image(np.zeros((50, 50), dtype=np.float32), scale=2)

    def test_invalid_dimensions_raises_value_error(self):
        with pytest.raises(ValueError):
            upscale_image(np.zeros((1, 1), dtype=np.uint8), scale=2)

        with pytest.raises(ValueError):
            upscale_image(np.zeros((50, 50, 4), dtype=np.uint8), scale=2)

    def test_unsupported_scale_raises_error(self, sample_bgr_64):
        with pytest.raises(UnsupportedScaleError):
            upscale_image(sample_bgr_64, scale=3)


# =====================================================================
# 5. Real Inference Tests (2x and 4x)
# =====================================================================


class TestRealInference:
    """Test real FSRCNN model inference using official .pb weights."""

    def test_real_inference_scale_2x(self, sample_bgr_64):
        """2x upscaling must double both dimensions and return valid uint8 array."""
        h, w = sample_bgr_64.shape[:2]
        upscaled, meta = upscale_image(sample_bgr_64, scale=2)

        assert isinstance(meta, SuperResolutionMetadata)
        assert meta.applied is True
        assert meta.scale == 2
        assert meta.model_name == "fsrcnn_x2"
        assert meta.input_dimensions == (w, h)
        assert meta.output_dimensions == (w * 2, h * 2)
        assert meta.elapsed_seconds > 0.0

        assert upscaled.shape == (h * 2, w * 2, 3)
        assert upscaled.dtype == np.uint8
        assert np.all(np.isfinite(upscaled))

    def test_real_inference_scale_4x(self, sample_bgr_64):
        """4x upscaling must quadruple both dimensions and return valid uint8 array."""
        h, w = sample_bgr_64.shape[:2]
        upscaled, meta = upscale_image(sample_bgr_64, scale=4)

        assert meta.applied is True
        assert meta.scale == 4
        assert meta.model_name == "fsrcnn_x4"
        assert meta.input_dimensions == (w, h)
        assert meta.output_dimensions == (w * 4, h * 4)

        assert upscaled.shape == (h * 4, w * 4, 3)
        assert upscaled.dtype == np.uint8
        assert np.all(np.isfinite(upscaled))

    def test_grayscale_upscaling(self, sample_gray_64):
        """Single-channel grayscale input must return single-channel upscaled array."""
        h, w = sample_gray_64.shape
        upscaled, meta = upscale_image(sample_gray_64, scale=2)

        assert meta.applied is True
        assert upscaled.shape == (h * 2, w * 2)
        assert upscaled.dtype == np.uint8

    def test_input_immutability(self, sample_bgr_64):
        """Input image array must not be modified in place during inference."""
        original_copy = sample_bgr_64.copy()
        _ = upscale_image(sample_bgr_64, scale=2)
        assert np.array_equal(sample_bgr_64, original_copy)


# =====================================================================
# 6. Pipeline Integration & Backward Compatibility Tests
# =====================================================================


class TestPipelineIntegration:
    """Verify integration into `enhance_image` and backward compatibility."""

    def test_enhance_image_upscale_disabled_by_default(self, sample_bgr_64):
        """upscale=False must be default and image dimensions must be preserved."""
        out = enhance_image(sample_bgr_64, denoise=False, contrast=False, sharpen=False)
        assert out.shape == sample_bgr_64.shape
        assert np.array_equal(out, sample_bgr_64)

    def test_enhance_image_with_2x_upscale(self, sample_bgr_64):
        """When upscale=True and scale=2, output must be 2x larger."""
        h, w = sample_bgr_64.shape[:2]
        out = enhance_image(
            sample_bgr_64,
            denoise=False,
            contrast=False,
            sharpen=False,
            upscale=True,
            scale=2,
        )
        assert out.shape == (h * 2, w * 2, 3)

    def test_enhance_image_with_4x_upscale(self, sample_bgr_64):
        """When upscale=True and scale=4, output must be 4x larger."""
        h, w = sample_bgr_64.shape[:2]
        out = enhance_image(
            sample_bgr_64,
            denoise=False,
            contrast=False,
            sharpen=False,
            upscale=True,
            scale=4,
        )
        assert out.shape == (h * 4, w * 4, 3)

    def test_full_pipeline_with_all_stages_enabled(self, sample_bgr_64):
        """All stages (repair + adaptive denoise + contrast + sharpen + upscale) execute cleanly."""
        h, w = sample_bgr_64.shape[:2]
        out = enhance_image(
            sample_bgr_64,
            denoise=True,
            contrast=True,
            sharpen=True,
            adaptive_denoise=True,
            repair=True,
            upscale=True,
            scale=2,
        )
        assert out.shape == (h * 2, w * 2, 3)
        assert out.dtype == np.uint8
        assert np.all(np.isfinite(out))

