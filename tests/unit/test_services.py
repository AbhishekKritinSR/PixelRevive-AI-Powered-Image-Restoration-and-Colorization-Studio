"""Unit tests for RestorationService, BatchService, and ModelService."""

import io
import numpy as np
from PIL import Image
import pytest

from backend.src.core.exceptions import (
    BatchSizeExceededError,
    CorruptedImageError,
    FileTooLargeError,
    UnsupportedFormatError,
)
from backend.src.processing.colorization.base import BaseColorizer
from backend.src.schemas.restoration import RestorationOptions
from backend.src.services.batch_service import BatchService
from backend.src.services.model_service import ModelService
from backend.src.services.restoration_service import RestorationService


class MockColorizer(BaseColorizer):
    def load_model(self) -> None:
        pass

    def colorize(self, image_bgr: np.ndarray) -> np.ndarray:
        return image_bgr.astype("float32") / 255.0

    @property
    def model_name(self) -> str:
        return "zhang_caffe"

    @property
    def is_loaded(self) -> bool:
        return True


@pytest.fixture
def model_service():
    return ModelService()


@pytest.fixture
def restoration_service(model_service, monkeypatch):
    monkeypatch.setattr(model_service, "get_colorizer", lambda name: MockColorizer())
    return RestorationService(model_service=model_service)


@pytest.fixture
def batch_service(restoration_service):
    return BatchService(restoration_service=restoration_service)


class TestModelService:
    def test_get_model_status_returns_valid_structure(self, model_service):
        status = model_service.get_model_status()
        assert status.model_name == "zhang_caffe"
        assert isinstance(status.files_available, bool)
        assert isinstance(status.ready_for_inference, bool)

    def test_get_colorizer_returns_base_colorizer(self, model_service):
        colorizer = model_service.get_colorizer("zhang_caffe")
        assert isinstance(colorizer, BaseColorizer)
        assert colorizer.model_name == "zhang_caffe"


class TestRestorationServiceValidation:
    def test_validate_file_metadata_valid_formats(self, restoration_service):
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            restoration_service.validate_file_metadata(f"test{ext}", 1024)

    def test_validate_file_metadata_unsupported_format(self, restoration_service):
        with pytest.raises(UnsupportedFormatError, match="Unsupported file format"):
            restoration_service.validate_file_metadata("test.bmp", 1024)

    def test_validate_file_metadata_exceeds_size(self, restoration_service):
        with pytest.raises(FileTooLargeError, match="exceeds maximum allowed limit"):
            restoration_service.validate_file_metadata("test.png", 30 * 1024 * 1024)

    def test_decode_image_bytes_empty_raises(self, restoration_service):
        with pytest.raises(CorruptedImageError, match="empty"):
            restoration_service.decode_image_bytes(b"")

    def test_decode_image_bytes_corrupt_raises(self, restoration_service):
        with pytest.raises(CorruptedImageError, match="Could not read image content"):
            restoration_service.decode_image_bytes(b"not an image")

    def test_decode_image_bytes_valid_returns_array(self, restoration_service):
        buf = io.BytesIO()
        Image.new("RGB", (30, 30), color="red").save(buf, format="PNG")
        arr = restoration_service.decode_image_bytes(buf.getvalue())
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (30, 30, 3)
        assert arr.dtype == np.uint8


class TestBatchServiceValidation:
    def test_empty_batch_raises_value_error(self, batch_service):
        with pytest.raises(ValueError, match="No files provided"):
            batch_service.process_batch([], RestorationOptions())

    def test_batch_size_exceeded_raises_error(self, batch_service):
        files = [(f"f_{i}.png", b"data") for i in range(11)]
        with pytest.raises(BatchSizeExceededError, match="exceeds the maximum allowed limit"):
            batch_service.process_batch(files, RestorationOptions())

