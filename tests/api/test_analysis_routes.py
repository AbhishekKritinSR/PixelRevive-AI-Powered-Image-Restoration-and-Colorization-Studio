"""Module: test_analysis_routes.py

Purpose:
Integration test suite for POST /api/v1/restoration/analyze endpoint.

Verifies:
- Successful analysis of valid images (JPEG, PNG).
- Accurate monochrome identification and recommendation triggers.
- Correct handling of validation errors (unsupported formats, corrupt files, missing uploads).
- Independence from Caffe colorization model and restoration execution.
"""

import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.processing.colorization.factory import ColorizerFactory

client = TestClient(app)


@pytest.fixture
def valid_color_png_bytes() -> bytes:
    """Fixture producing valid 80x60 RGB PNG bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (80, 60), color=(200, 80, 40))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def valid_monochrome_png_bytes() -> bytes:
    """Fixture producing valid 80x60 pure grayscale PNG bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (80, 60), color=(128, 128, 128))
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestAnalysisEndpoint:
    """Tests for POST /api/v1/restoration/analyze."""

    def test_analyze_color_image_successful(self, valid_color_png_bytes: bytes):
        files = {"file": ("test_color.png", valid_color_png_bytes, "image/png")}
        response = client.post("/api/v1/restoration/analyze", files=files)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["filename"] == "test_color.png"
        assert data["image"]["width"] == 80
        assert data["image"]["height"] == 60
        assert data["image"]["channels"] == 3
        assert data["image"]["was_resized"] is False

        # Metrics check
        analysis = data["analysis"]
        assert isinstance(analysis["noise"]["noise_score"], (int, float))
        assert analysis["noise"]["noise_level"] in ("low", "medium", "high")
        assert isinstance(analysis["sharpness"]["sharpness_score"], (int, float))
        assert isinstance(analysis["contrast"]["contrast_score"], (int, float))
        assert analysis["monochrome"]["is_monochrome"] is False

        # Recommendations check
        recs = data["recommended_options"]
        assert "denoise" in recs
        assert "contrast" in recs
        assert "sharpen" in recs
        assert "colorize" in recs
        assert recs["colorize"]["recommended"] is False
        assert data["elapsed_seconds"] >= 0.0

    def test_analyze_monochrome_image_recommends_colorization(
        self, valid_monochrome_png_bytes: bytes
    ):
        files = {"file": ("historic_bw.png", valid_monochrome_png_bytes, "image/png")}
        response = client.post("/api/v1/restoration/analyze", files=files)

        assert response.status_code == 200
        data = response.json()

        assert data["analysis"]["monochrome"]["is_monochrome"] is True
        assert "Monochrome / Black & White" in data["detected_issues"]
        assert data["recommended_options"]["colorize"]["recommended"] is True
        assert "image_is_monochrome" in data["recommended_options"]["colorize"]["evidence"]

    def test_analyze_missing_file_raises_422(self):
        response = client.post("/api/v1/restoration/analyze", files={})
        assert response.status_code == 422

    def test_analyze_unsupported_format_raises_415(self):
        files = {"file": ("document.pdf", b"%PDF-1.4 dummy content", "application/pdf")}
        response = client.post("/api/v1/restoration/analyze", files=files)
        assert response.status_code == 415
        assert "Unsupported file format" in response.json()["detail"]

    def test_analyze_corrupted_image_raises_400(self):
        files = {"file": ("corrupt.jpg", b"corrupted bytes", "image/jpeg")}
        response = client.post("/api/v1/restoration/analyze", files=files)
        assert response.status_code == 400
        assert "Could not read image content" in response.json()["detail"]

    def test_analyze_empty_file_raises_400(self):
        files = {"file": ("empty.jpg", b"", "image/jpeg")}
        response = client.post("/api/v1/restoration/analyze", files=files)
        assert response.status_code == 400
        assert "Uploaded file is empty" in response.json()["detail"]

    def test_analyze_does_not_load_caffe_model(self, valid_color_png_bytes: bytes):
        ColorizerFactory.clear_instances()
        assert "zhang_caffe" not in ColorizerFactory._instances

        files = {"file": ("test.png", valid_color_png_bytes, "image/png")}
        response = client.post("/api/v1/restoration/analyze", files=files)

        assert response.status_code == 200
        # Verify colorizer model was NEVER loaded during analysis
        assert "zhang_caffe" not in ColorizerFactory._instances

    def test_analyze_response_contains_no_base64_image(self, valid_color_png_bytes: bytes):
        files = {"file": ("test.png", valid_color_png_bytes, "image/png")}
        response = client.post("/api/v1/restoration/analyze", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "image_base64" not in data

