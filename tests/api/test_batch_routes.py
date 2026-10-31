"""Tests for POST /api/v1/restoration/batch."""

import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.src.main import app

client = TestClient(app)


@pytest.fixture
def sample_png():
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color="green").save(buf, format="PNG")
    return buf.getvalue()


class TestBatchEndpoints:
    def test_process_batch_successful(self, sample_png):
        files = [
            ("files", ("image1.png", sample_png, "image/png")),
            ("files", ("image2.png", sample_png, "image/png")),
        ]
        data = {"colorize": "false"}
        response = client.post("/api/v1/restoration/batch", files=files, data=data)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total_submitted"] == 2
        assert json_data["total_succeeded"] == 2
        assert json_data["total_failed"] == 0
        assert len(json_data["items"]) == 2
        assert json_data["items"][0]["status"] == "success"
        assert json_data["items"][1]["status"] == "success"
        assert json_data["zip_base64"].startswith("data:application/zip;base64,")

    def test_process_batch_with_partial_failure(self, sample_png):
        files = [
            ("files", ("good.png", sample_png, "image/png")),
            ("files", ("bad.png", b"corrupted garbage bytes", "image/png")),
        ]
        data = {"colorize": "false"}
        response = client.post("/api/v1/restoration/batch", files=files, data=data)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total_submitted"] == 2
        assert json_data["total_succeeded"] == 1
        assert json_data["total_failed"] == 1
        assert json_data["items"][0]["status"] == "success"
        assert json_data["items"][1]["status"] == "failed"
        assert json_data["items"][1]["error"] is not None
        # ZIP should still be generated with the 1 successful image
        assert json_data["zip_base64"] is not None

    def test_process_batch_exceeds_limit_raises_400(self, sample_png):
        # Create 11 files (exceeding MAX_BATCH_FILES = 10)
        files = [
            ("files", (f"img_{i}.png", sample_png, "image/png"))
            for i in range(11)
        ]
        response = client.post("/api/v1/restoration/batch", files=files)
        assert response.status_code == 400
        assert "exceeds the maximum allowed limit of 10 images" in response.json()["detail"]

    def test_process_batch_with_adaptive_denoise(self, sample_png):
        files = [
            ("files", ("clean_img.png", sample_png, "image/png")),
            ("files", ("second_img.png", sample_png, "image/png")),
        ]
        data = {
            "denoise": "true",
            "adaptive_denoise": "true",
            "colorize": "false",
        }
        response = client.post("/api/v1/restoration/batch", files=files, data=data)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total_succeeded"] == 2
        assert len(json_data["items"]) == 2
        assert json_data["items"][0]["status"] == "success"
        assert json_data["items"][1]["status"] == "success"
        assert json_data["zip_base64"].startswith("data:application/zip;base64,")

