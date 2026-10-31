"""Tests for the Model Status API endpoint."""

from fastapi.testclient import TestClient

from backend.src.main import app

client = TestClient(app)


class TestModelsEndpoints:
    def test_model_status_returns_valid_structure(self):
        response = client.get("/api/v1/models/status")
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "zhang_caffe"
        assert isinstance(data["files_available"], bool)
        assert isinstance(data["is_loaded"], bool)
        assert isinstance(data["ready_for_inference"], bool)
        assert "detail" in data

    def test_model_status_fsrcnn_x2(self):
        response = client.get("/api/v1/models/status?model_name=fsrcnn_x2")
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "fsrcnn_x2"
        assert data["files_available"] is True
        assert isinstance(data["is_loaded"], bool)
        assert data["ready_for_inference"] is True

    def test_model_status_fsrcnn_x4(self):
        response = client.get("/api/v1/models/status?model_name=fsrcnn_x4")
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "fsrcnn_x4"
        assert data["files_available"] is True
        assert isinstance(data["is_loaded"], bool)
        assert data["ready_for_inference"] is True

