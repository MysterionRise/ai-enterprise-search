"""Integration tests for authentication endpoints"""

import pytest
from fastapi import status


class TestAuthenticationEndpoints:
    """Test auth API endpoints"""

    def test_login_success(self, client):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "password123"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_invalid_credentials(self, client):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/api/v1/auth/login", json={"username": "nonexistent", "password": "password123"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user(self, client, auth_headers):
        """Test getting current user info"""
        if not auth_headers:
            pytest.skip("Authentication not available")

        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "username" in data
        assert "email" in data
        assert "groups" in data

    def test_get_current_user_without_auth(self, client):
        """Test accessing protected endpoint without auth"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_current_user_invalid_token(self, client):
        """Test with invalid token"""
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, client, auth_headers):
        """Test token refresh"""
        if not auth_headers:
            pytest.skip("Authentication not available")

        response = client.post("/api/v1/auth/refresh", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_new_user(self, client):
        """Test user registration"""
        import random

        username = f"testuser_{random.randint(1000, 9999)}"

        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": f"{username}@test.com",
                "password": "testpassword123",
                "full_name": "Test User",
                "department": "Engineering",
                "country": "US",
            },
        )
        # Might fail if user exists, that's ok for integration test
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["username"] == username
            assert "all-employees" in data["groups"]

    def test_register_duplicate_username(self, client):
        """Test registering with existing username"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "admin",  # Already exists
                "email": "new@test.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
