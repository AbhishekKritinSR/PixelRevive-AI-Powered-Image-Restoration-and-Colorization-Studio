"""Unit tests for Colorization Registry, Metadata, and Render Factor Tuning (Phase 5.5)."""

from pathlib import Path
import numpy as np
import pytest

from backend.src.core.exceptions import (
    InvalidRenderFactorError,
    UnsupportedColorizationModelError,
)
from backend.src.processing.colorization.base import BaseColorizer
from backend.src.processing.colorization.factory import ColorizerFactory
from backend.src.processing.colorization.metadata import (
    ColorizerMetadata,
    ZHANG_CAFFE_METADATA,
)
from backend.src.processing.colorization.models.zhang_caffe import (
    ZhangCaffeColorizer,
    colorize_image,
    load_caffe_model,
    validate_render_factor,
)
from src.config import (
    DEFAULT_RENDER_FACTOR,
    MAX_RENDER_FACTOR,
    MIN_RENDER_FACTOR,
    MODEL_PATH,
    POINTS_PATH,
    PROTOTXT_PATH,
)


class DummyCustomColorizer(BaseColorizer):
    """Custom colorizer for testing registry extension."""

    def __init__(self, multiplier: float = 1.0):
        self._loaded = False
        self.multiplier = multiplier

    def load_model(self) -> None:
        self._loaded = True

    def colorize(self, image_bgr: np.ndarray, **kwargs) -> np.ndarray:
        return np.clip((image_bgr.astype("float32") / 255.0) * self.multiplier, 0.0, 1.0)

    @property
    def model_name(self) -> str:
        return "dummy_custom"

    @property
    def is_loaded(self) -> bool:
        return self._loaded


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset ColorizerFactory before and after each test."""
    ColorizerFactory.reset_registry()
    yield
    ColorizerFactory.reset_registry()


class TestColorizerMetadataAndRegistry:
    """Tests for ColorizerMetadata and registry discovery operations."""

    def test_default_model_is_zhang_caffe(self):
        assert ColorizerFactory.get_default_model() == "zhang_caffe"
        assert "zhang_caffe" in ColorizerFactory.list_supported_models()

    def test_zhang_caffe_metadata_content(self):
        meta = ColorizerFactory.get_metadata("zhang_caffe")
        assert meta.model_id == "zhang_caffe"
        assert meta.display_name == "Zhang et al. ECCV 2016 (Caffe)"
        assert "8-block" in meta.architecture
        assert meta.authors == "Richard Zhang, Phillip Isola, Alexei A. Efros"
        assert meta.publication == "Colorful Image Colorization, ECCV 2016"
        assert meta.is_default is True
        assert meta.supported_task == "Image Colorization"
        assert "render_factor" in meta.supported_parameters
        param = meta.supported_parameters["render_factor"]
        assert param["min"] == 10
        assert param["default"] == 14
        assert param["max"] == 40

    def test_list_models_metadata(self):
        metas = ColorizerFactory.list_models_metadata()
        assert len(metas) >= 1
        ids = [m.model_id for m in metas]
        assert "zhang_caffe" in ids

    def test_register_new_model_with_metadata(self):
        custom_meta = ColorizerMetadata(
            model_id="dummy_custom",
            display_name="Dummy Custom Colorizer",
            architecture="Test Stub",
            authors="Test Author",
            publication="Test Paper 2026",
            model_format="PyTorch / ONNX",
            is_default=False,
        )
        ColorizerFactory.register("dummy_custom", DummyCustomColorizer, metadata=custom_meta)
        assert "dummy_custom" in ColorizerFactory.list_supported_models()

        meta = ColorizerFactory.get_metadata("dummy_custom")
        assert meta.model_id == "dummy_custom"
        assert meta.display_name == "Dummy Custom Colorizer"
        assert meta.is_default is False

    def test_unsupported_model_lookup_raises_typed_error(self):
        with pytest.raises(UnsupportedColorizationModelError, match="Unsupported colorization model"):
            ColorizerFactory.get_colorizer("non_existent_colorizer")

        with pytest.raises(UnsupportedColorizationModelError):
            ColorizerFactory.get_metadata("non_existent_colorizer")

    def test_singleton_instance_caching_and_clear(self):
        inst1 = ColorizerFactory.get_colorizer("zhang_caffe")
        inst2 = ColorizerFactory.get_colorizer("zhang_caffe")
        assert inst1 is inst2

        ColorizerFactory.clear_instances()
        assert "zhang_caffe" not in ColorizerFactory._instances
        inst3 = ColorizerFactory.get_colorizer("zhang_caffe")
        assert inst3 is not inst1


class TestRenderFactorValidation:
    """Tests for render_factor validation logic."""

    def test_valid_default_render_factor(self):
        assert validate_render_factor(14) == 14
        assert validate_render_factor(DEFAULT_RENDER_FACTOR) == 14

    def test_valid_boundary_render_factors(self):
        assert validate_render_factor(MIN_RENDER_FACTOR) == 10
        assert validate_render_factor(MAX_RENDER_FACTOR) == 40
        assert validate_render_factor(20) == 20
        assert validate_render_factor(28) == 28

    def test_render_factor_below_minimum_raises(self):
        with pytest.raises(InvalidRenderFactorError, match="outside valid range"):
            validate_render_factor(9)
        with pytest.raises(InvalidRenderFactorError):
            validate_render_factor(0)
        with pytest.raises(InvalidRenderFactorError):
            validate_render_factor(-14)

    def test_render_factor_above_maximum_raises(self):
        with pytest.raises(InvalidRenderFactorError, match="outside valid range"):
            validate_render_factor(41)
        with pytest.raises(InvalidRenderFactorError):
            validate_render_factor(100)

    def test_render_factor_invalid_types_raise(self):
        with pytest.raises(InvalidRenderFactorError, match="must be an integer"):
            validate_render_factor(14.0)  # float
        with pytest.raises(InvalidRenderFactorError, match="must be an integer"):
            validate_render_factor("14")  # string
        with pytest.raises(InvalidRenderFactorError, match="must be an integer"):
            validate_render_factor(True)  # bool (subclass of int in Python)
        with pytest.raises(InvalidRenderFactorError, match="must be an integer"):
            validate_render_factor(None)


class TestColorizationTuningInference:
    """Tests for colorize_image with varying render factors."""

    def test_colorize_image_default_matches_call_without_args(self, stub_net, sample_image):
        res1 = colorize_image(sample_image, stub_net)
        res2 = colorize_image(sample_image, stub_net, render_factor=14)
        np.testing.assert_array_equal(res1, res2)

    def test_colorize_image_with_custom_render_factor(self, stub_net, sample_image):
        res_min = colorize_image(sample_image, stub_net, render_factor=10)
        res_max = colorize_image(sample_image, stub_net, render_factor=40)

        assert res_min.shape == (sample_image.shape[0], sample_image.shape[1], 3)
        assert res_max.shape == (sample_image.shape[0], sample_image.shape[1], 3)
        assert res_min.dtype == np.float32
        assert res_max.dtype == np.float32
        assert not np.isnan(res_min).any()
        assert not np.isnan(res_max).any()
        assert res_min.min() >= 0.0 and res_min.max() <= 1.0
        assert res_max.min() >= 0.0 and res_max.max() <= 1.0

    def test_colorize_image_rejects_invalid_render_factor(self, stub_net, sample_image):
        with pytest.raises(InvalidRenderFactorError):
            colorize_image(sample_image, stub_net, render_factor=5)

    def test_colorizer_instance_colorize_with_render_factor(self):
        colorizer = ColorizerFactory.get_colorizer("zhang_caffe")
        # Ensure model is instantiated without failing
        assert colorizer.model_name == "zhang_caffe"
        assert colorizer.are_assets_present() is True


class TestRealCaffeModelInference:
    """Inference tests using the real Caffe weights if present on disk."""

    @pytest.fixture
    def real_net(self):
        if not (PROTOTXT_PATH.is_file() and MODEL_PATH.is_file() and POINTS_PATH.is_file()):
            pytest.skip("Real Caffe model weight assets not present on disk.")
        return load_caffe_model(PROTOTXT_PATH, MODEL_PATH, POINTS_PATH)

    def test_real_inference_default_factor(self, real_net):
        test_img = np.full((64, 64, 3), 128, dtype=np.uint8)
        colorized = colorize_image(test_img, real_net, render_factor=14)

        assert colorized.shape == (64, 64, 3)
        assert colorized.dtype == np.float32
        assert not np.isnan(colorized).any()
        assert not np.isinf(colorized).any()
        assert colorized.min() >= 0.0
        assert colorized.max() <= 1.0

    def test_real_inference_tuned_factors(self, real_net):
        test_img = np.full((48, 48, 3), 100, dtype=np.uint8)

        # Factor 10 (160x160 internal)
        res_10 = colorize_image(test_img, real_net, render_factor=10)
        assert res_10.shape == (48, 48, 3)
        assert not np.isnan(res_10).any()

        # Factor 20 (320x320 internal)
        res_20 = colorize_image(test_img, real_net, render_factor=20)
        assert res_20.shape == (48, 48, 3)
        assert not np.isnan(res_20).any()

