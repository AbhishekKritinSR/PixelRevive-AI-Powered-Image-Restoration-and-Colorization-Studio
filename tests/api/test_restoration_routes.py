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

    def colorize(self, image_bgr: np.ndarray, **kwargs) -> np.ndarray:
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
        assert json_data["options_applied"]["adaptive_denoise"] is True
        assert json_data["options_applied"]["repair"] is False
        assert json_data["options_applied"]["upscale"] is False
        assert json_data["options_applied"]["scale"] == 2

    def test_process_single_image_super_resolution_2x(self, valid_png_bytes):
        files = {"file": ("test_photo.png", valid_png_bytes, "image/png")}
        data = {
            "denoise": "false",
            "contrast": "false",
            "sharpen": "false",
            "colorize": "false",
            "repair": "false",
            "upscale": "true",
            "scale": "2",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["options_applied"]["upscale"] is True
        assert json_data["options_applied"]["scale"] == 2
        # Original was 80x60 -> 2x should be 160x120
        assert json_data["original_width"] == 80
        assert json_data["original_height"] == 60
        assert json_data["processed_width"] == 160
        assert json_data["processed_height"] == 120

    def test_process_single_image_super_resolution_4x(self, valid_png_bytes):
        files = {"file": ("test_photo.png", valid_png_bytes, "image/png")}
        data = {
            "denoise": "false",
            "contrast": "false",
            "sharpen": "false",
            "colorize": "false",
            "repair": "false",
            "upscale": "true",
            "scale": "4",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["options_applied"]["upscale"] is True
        assert json_data["options_applied"]["scale"] == 4
        # Original was 80x60 -> 4x should be 320x240
        assert json_data["processed_width"] == 320
        assert json_data["processed_height"] == 240

    def test_process_single_image_unsupported_scale_raises_400(self, valid_png_bytes):
        files = {"file": ("test_photo.png", valid_png_bytes, "image/png")}
        data = {
            "upscale": "true",
            "scale": "3",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 400
        assert "Unsupported scaling factor" in response.json()["detail"]

    def test_process_single_image_repair_toggles(self, valid_png_bytes):
        # 1. Explicit repair=false
        files = {"file": ("test_photo.png", valid_png_bytes, "image/png")}
        data = {
            "denoise": "false",
            "contrast": "false",
            "sharpen": "false",
            "colorize": "false",
            "repair": "false",
        }
        res_false = client.post("/api/v1/restoration/process", files=files, data=data)
        assert res_false.status_code == 200
        assert res_false.json()["options_applied"]["repair"] is False

        # 2. Explicit repair=true
        files = {"file": ("test_photo.png", valid_png_bytes, "image/png")}
        data["repair"] = "true"
        res_true = client.post("/api/v1/restoration/process", files=files, data=data)
        assert res_true.status_code == 200
        assert res_true.json()["options_applied"]["repair"] is True

    def test_process_single_image_adaptive_denoise_explicit(self, valid_png_bytes):
        files = {"file": ("test_photo.png", valid_png_bytes, "image/png")}
        data = {
            "denoise": "true",
            "adaptive_denoise": "false",
            "contrast": "false",
            "sharpen": "false",
            "colorize": "false",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["options_applied"]["denoise"] is True
        assert json_data["options_applied"]["adaptive_denoise"] is False

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

    def test_process_with_valid_render_factor(self, valid_png_bytes, monkeypatch):
        model_service = get_model_service()
        monkeypatch.setattr(model_service, "get_colorizer", lambda name: MockFastColorizer())

        files = {"file": ("test.png", valid_png_bytes, "image/png")}
        data = {
            "colorize": "true",
            "colorization_model": "zhang_caffe",
            "render_factor": "20",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["options_applied"]["render_factor"] == 20
        assert json_data["options_applied"]["colorization_model"] == "zhang_caffe"

    def test_process_with_unsupported_colorization_model_raises_400(self, valid_png_bytes):
        files = {"file": ("test.png", valid_png_bytes, "image/png")}
        data = {
            "colorize": "true",
            "colorization_model": "unknown_experimental_model",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 400
        assert "Unsupported colorization model" in response.json()["detail"]

    def test_process_with_invalid_render_factor_low_raises_400(self, valid_png_bytes):
        files = {"file": ("test.png", valid_png_bytes, "image/png")}
        data = {
            "colorize": "true",
            "render_factor": "5",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 400
        assert "render_factor" in response.json()["detail"]

    def test_process_with_invalid_render_factor_high_raises_400(self, valid_png_bytes):
        files = {"file": ("test.png", valid_png_bytes, "image/png")}
        data = {
            "colorize": "true",
            "render_factor": "45",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 400
        assert "render_factor" in response.json()["detail"]

    def test_process_colorize_disabled_ignores_model_name(self, valid_png_bytes):
        files = {"file": ("test.png", valid_png_bytes, "image/png")}
        data = {
            "colorize": "false",
            "colorization_model": "any_unregistered_model",
        }
        response = client.post("/api/v1/restoration/process", files=files, data=data)
        assert response.status_code == 200
        assert response.json()["options_applied"]["colorize"] is False

