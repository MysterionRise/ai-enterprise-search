"""Pytest configuration and fixtures"""
import pytest
import os
import sys
from typing import Generator

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi.testclient import TestClient
from src.api.main import app
from src.core.config import settings


@pytest.fixture
def client() -> Generator:
    """FastAPI test client"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client) -> dict:
    """Get authentication headers for test user"""
    # Login with test user
    response = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"username": "admin", "password": "password123"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.fixture
def mock_document():
    """Sample document for testing"""
    return {
        "source": "test",
        "source_id": "TEST-001",
        "title": "Test Document",
        "content": "This is a test document for unit testing purposes.",
        "content_type": "text/plain",
        "acl_allow": ["all-employees"],
        "country_tags": ["US"],
        "department": "Engineering",
        "tags": ["test", "automation"]
    }


@pytest.fixture
def mock_search_request():
    """Sample search request"""
    return {
        "query": "test document",
        "size": 10,
        "use_hybrid": True,
        "boost_personalization": False
    }
