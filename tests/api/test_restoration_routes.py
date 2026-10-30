"""Tests for POST /api/v1/restoration/process."""

import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.src.api.dependencies import get_model_service
from backend.src.core.exceptions import ModelUnavailableError
from backend.src.main import app
from backend.src.processing.colorization.base import BaseColorizer
import numpy as np

client = TestClient(app)


class MockFastColorizer(BaseColorizer):
    """Fast in-memory colorizer stub for fast API testing."""

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
def valid_png_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (80, 60), color=(120, 140, 160))
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestRestorationEndpoints:
    def test_process_single_image_restoration_only(self, valid_png_bytes):
        files = {"file": ("test_photo.png", valid_png_bytes, "image/png")}
        data = {
            "denoise": "true",
            "contrast": "true",
            "sharpen": "true",
            "colorize": "false",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["status"] == "success"
        assert json_data["filename"] == "test_photo.png"
        assert json_data["original_width"] == 80
        assert json_data["original_height"] == 60
        assert json_data["processed_width"] == 80
        assert json_data["processed_height"] == 60
        assert json_data["was_resized"] is False
        assert json_data["image_base64"].startswith("data:image/png;base64,")
        assert "metrics" in json_data
        assert json_data["options_applied"]["colorize"] is False

    def test_process_single_image_with_colorizer_stub(self, valid_png_bytes, monkeypatch):
        # Override model service to use the fast mock colorizer
        model_service = get_model_service()
        monkeypatch.setattr(model_service, "get_colorizer", lambda name: MockFastColorizer())

        files = {"file": ("test_photo.png", valid_png_bytes, "image/png")}
        data = {
            "denoise": "false",
            "contrast": "false",
            "sharpen": "false",
            "colorize": "true",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["status"] == "success"
        assert json_data["options_applied"]["colorize"] is True

    def test_process_missing_file_raises_422(self):
        response = client.post("/api/v1/restoration/process", data={"denoise": "true"})
        assert response.status_code == 422

    def test_process_unsupported_format_raises_415(self):
        files = {"file": ("document.txt", b"plain text content", "text/plain")}
        response = client.post("/api/v1/restoration/process", files=files)
        assert response.status_code == 415
        assert "Unsupported file format" in response.json()["detail"]

    def test_process_corrupted_image_raises_400(self):
        files = {"file": ("damaged.png", b"not a real png header or data", "image/png")}
        response = client.post("/api/v1/restoration/process", files=files)
        assert response.status_code == 400
        assert "Could not read image content" in response.json()["detail"]

    def test_process_model_unavailable_raises_503(self, valid_png_bytes, monkeypatch):
        model_service = get_model_service()

        def mock_unavailable(name):
            raise ModelUnavailableError("Model weights are missing from disk.")

        monkeypatch.setattr(model_service, "get_colorizer", mock_unavailable)

        files = {"file": ("test.png", valid_png_bytes, "image/png")}
        data = {"colorize": "true"}
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 503
        assert "Model weights are missing" in response.json()["detail"]

