"""Tests for ColorizerFactory and BaseColorizer in backend.src.processing.colorization."""

import numpy as np
import pytest

from backend.src.processing.colorization.base import BaseColorizer
from backend.src.processing.colorization.factory import ColorizerFactory
from backend.src.processing.colorization.models.zhang_caffe import ZhangCaffeColorizer


class CustomStubColorizer(BaseColorizer):
    """A valid custom BaseColorizer implementation for testing factory registration."""

    def __init__(self):
        self._loaded = False

    def load_model(self) -> None:
        self._loaded = True

    def colorize(self, image_bgr: np.ndarray) -> np.ndarray:
        return image_bgr.astype("float32") / 255.0

    @property
    def model_name(self) -> str:
        return "custom_stub"

    @property
    def is_loaded(self) -> bool:
        return self._loaded


@pytest.fixture(autouse=True)
def reset_factory():
    """Reset the factory registry to default state before each test."""
    ColorizerFactory.reset_registry()
    yield
    ColorizerFactory.reset_registry()


class TestColorizerFactory:
    def test_default_models_registered(self):
        models = ColorizerFactory.list_supported_models()
        assert "zhang_caffe" in models

    def test_get_colorizer_returns_instance(self):
        colorizer = ColorizerFactory.get_colorizer("zhang_caffe")
        assert isinstance(colorizer, ZhangCaffeColorizer)
        assert colorizer.model_name == "zhang_caffe"

    def test_get_colorizer_reuses_singleton_instance(self):
        inst1 = ColorizerFactory.get_colorizer("zhang_caffe")
        inst2 = ColorizerFactory.get_colorizer("zhang_caffe")
        assert inst1 is inst2

    def test_unsupported_model_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported colorization model: 'non_existent'"):
            ColorizerFactory.get_colorizer("non_existent")

    def test_register_custom_colorizer(self):
        ColorizerFactory.register("custom_stub", CustomStubColorizer)
        assert "custom_stub" in ColorizerFactory.list_supported_models()

        colorizer = ColorizerFactory.get_colorizer("custom_stub")
        assert isinstance(colorizer, CustomStubColorizer)
        assert colorizer.model_name == "custom_stub"

    def test_register_non_subclass_raises_type_error(self):
        class NotAColorizer:
            pass

        with pytest.raises(TypeError, match="must be a subclass of BaseColorizer"):
            ColorizerFactory.register("invalid", NotAColorizer)

    def test_register_duplicate_without_override_raises(self):
        ColorizerFactory.register("custom_stub", CustomStubColorizer)
        with pytest.raises(ValueError, match="already registered"):
            ColorizerFactory.register("custom_stub", CustomStubColorizer, allow_override=False)

    def test_register_duplicate_with_override_succeeds(self):
        ColorizerFactory.register("custom_stub", CustomStubColorizer)
        ColorizerFactory.register("custom_stub", CustomStubColorizer, allow_override=True)
        assert "custom_stub" in ColorizerFactory.list_supported_models()

    def test_empty_registration_name_raises(self):
        with pytest.raises(ValueError, match="must be a non-empty string"):
            ColorizerFactory.register("", CustomStubColorizer)

