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

    def test_model_status_includes_metadata_and_default(self):
        response = client.get("/api/v1/models/status?model_name=zhang_caffe")
        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True
        assert data["metadata"] is not None
        assert data["metadata"]["model_id"] == "zhang_caffe"
        assert "render_factor" in data["metadata"]["supported_parameters"]
        assert data["metadata"]["supported_parameters"]["render_factor"]["default"] == 14

    def test_models_discovery_endpoint(self):
        response = client.get("/api/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["default_model"] == "zhang_caffe"
        assert len(data["models"]) >= 1
        caffe_model = next(m for m in data["models"] if m["model_id"] == "zhang_caffe")
        assert caffe_model["is_default"] is True
        assert caffe_model["supported_task"] == "Image Colorization"
        assert caffe_model["authors"] == "Richard Zhang, Phillip Isola, Alexei A. Efros"
        assert caffe_model["publication"] == "Colorful Image Colorization, ECCV 2016"
        assert caffe_model["supported_parameters"]["render_factor"]["min"] == 10
        assert caffe_model["supported_parameters"]["render_factor"]["max"] == 40

    def test_model_status_unregistered_model(self):
        response = client.get("/api/v1/models/status?model_name=non_registered_model")
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "non_registered_model"
        assert data["files_available"] is False
        assert data["ready_for_inference"] is False

