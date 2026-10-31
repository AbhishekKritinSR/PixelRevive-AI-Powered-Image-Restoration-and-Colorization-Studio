"""Integration tests for POST /api/v1/restoration/quality endpoint."""

import io
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.src.core.config import settings
from backend.src.main import app
from backend.src.processing.evaluation.brisque import clear_brisque_instance

client = TestClient(app)


@pytest.fixture
def sample_png_bytes():
    """Generate valid 64x64 color PNG bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=(140, 100, 60))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_reference_png_bytes():
    """Generate valid 64x64 reference PNG bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=(145, 105, 65))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def mismatched_reference_png_bytes():
    """Generate 80x80 reference PNG bytes to test dimension mismatch."""
    buf = io.BytesIO()
    img = Image.new("RGB", (80, 80), color=(140, 100, 60))
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestQualityAssessmentEndpoint:
    """Tests for POST /api/v1/restoration/quality."""

    def test_assess_quality_single_image_without_reference(self, sample_png_bytes):
        files = {"file": ("target.png", sample_png_bytes, "image/png")}
        response = client.post("/api/v1/restoration/quality", files=files)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["filename"] == "target.png"
        assert data["reference_filename"] is None
        assert data["image"]["width"] == 64
        assert data["image"]["height"] == 64
        assert data["image"]["channels"] == 3
        assert data["elapsed_seconds"] >= 0.0

        metrics = data["metrics"]

        # BRISQUE
        assert "brisque" in metrics
        assert metrics["brisque"]["available"] is True
        assert isinstance(metrics["brisque"]["score"], (int, float))

        # SSIM (must be unavailable when reference omitted)
        assert "ssim" in metrics
        assert metrics["ssim"]["available"] is False
        assert metrics["ssim"]["score"] is None
        assert "requires a reference" in metrics["ssim"]["interpretation"]

        # Colorfulness
        assert "colorfulness" in metrics
        assert metrics["colorfulness"]["available"] is True
        assert isinstance(metrics["colorfulness"]["score"], (int, float))

        # Additional metrics
        assert "sharpness" in metrics
        assert "contrast" in metrics
        assert "noise" in metrics

        # Confirm no image payload leaked
        assert "image_base64" not in data

    def test_assess_quality_with_matching_reference_image(
        self, sample_png_bytes, sample_reference_png_bytes
    ):
        files = {
            "file": ("target.png", sample_png_bytes, "image/png"),
            "reference_file": ("ref.png", sample_reference_png_bytes, "image/png"),
        }
        response = client.post("/api/v1/restoration/quality", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["reference_filename"] == "ref.png"

        ssim_metric = data["metrics"]["ssim"]
        assert ssim_metric["available"] is True
        assert isinstance(ssim_metric["score"], (int, float))
        assert 0.90 <= ssim_metric["score"] <= 1.0
        assert ssim_metric["details"]["comparison_mode"] == "color"
        assert "blue" in ssim_metric["details"]["channel_scores"]

    def test_assess_quality_dimension_mismatch_raises_400(
        self, sample_png_bytes, mismatched_reference_png_bytes
    ):
        files = {
            "file": ("target.png", sample_png_bytes, "image/png"),
            "reference_file": ("mismatched.png", mismatched_reference_png_bytes, "image/png"),
        }
        response = client.post("/api/v1/restoration/quality", files=files)

        assert response.status_code == 400
        assert "Dimension mismatch" in response.json()["detail"]

    def test_assess_quality_missing_target_file_raises_422(self):
        response = client.post("/api/v1/restoration/quality", files={})
        assert response.status_code == 422

    def test_assess_quality_unsupported_format_raises_415(self):
        files = {"file": ("data.txt", b"plain text", "text/plain")}
        response = client.post("/api/v1/restoration/quality", files=files)
        assert response.status_code == 415
        assert "unsupported file format" in response.json()["detail"].lower()

    def test_assess_quality_corrupted_image_raises_400(self):
        files = {"file": ("broken.png", b"not_a_valid_png_stream", "image/png")}
        response = client.post("/api/v1/restoration/quality", files=files)
        assert response.status_code == 400
        assert "Could not read" in response.json()["detail"]

    def test_assess_quality_when_brisque_assets_missing(self, sample_png_bytes, monkeypatch):
        monkeypatch.setattr(settings, "BRISQUE_MODEL_PATH", Path("/tmp/does_not_exist.yml"))
        clear_brisque_instance()

        files = {"file": ("target.png", sample_png_bytes, "image/png")}
        response = client.post("/api/v1/restoration/quality", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["brisque"]["available"] is False
        assert data["metrics"]["brisque"]["score"] is None
        assert "unavailable" in data["metrics"]["brisque"]["interpretation"]
        clear_brisque_instance()
