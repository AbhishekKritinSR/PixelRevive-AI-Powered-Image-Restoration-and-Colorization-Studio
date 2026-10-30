"""Tests for the Health and Root API endpoints."""

from fastapi.testclient import TestClient
import pytest

from backend.src.main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_root_endpoint_returns_ok(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "application" in data
        assert "version" in data
        assert data["documentation"] == "/docs"

    def test_health_endpoint_returns_healthy(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["application"] == "PixelRevive – AI-Powered Image Restoration"
        assert data["version"] == "1.0.0"
        assert data["device"] in ("CPU", "CUDA")

