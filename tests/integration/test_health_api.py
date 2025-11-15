"""Integration tests for health check endpoints"""
import pytest
from fastapi import status


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_check(self, client):
        """Test main health check endpoint"""
        response = client.get("/health")
        # Might be degraded if services aren't running, that's ok
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "version" in data

    def test_readiness_check(self, client):
        """Test Kubernetes readiness probe"""
        response = client.get("/health/ready")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"

    def test_liveness_check(self, client):
        """Test Kubernetes liveness probe"""
        response = client.get("/health/live")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "alive"

    def test_root_endpoint(self, client):
        """Test root endpoint returns HTML or API info"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        # Either HTML UI or JSON API info
        assert response.headers.get("content-type") in [
            "text/html; charset=utf-8",
            "application/json"
        ]

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == status.HTTP_200_OK
        # Should return Prometheus format
        assert "text/plain" in response.headers.get("content-type", "")

    def test_openapi_docs(self, client):
        """Test API documentation is accessible"""
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK

    def test_openapi_spec(self, client):
        """Test OpenAPI specification is available"""
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
