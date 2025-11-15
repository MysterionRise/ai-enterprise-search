"""Test configuration and utilities"""
import os
import pytest

# Test configuration
TEST_ENV = {
    "OPENSEARCH_HOST": os.getenv("TEST_OPENSEARCH_HOST", "localhost"),
    "POSTGRES_HOST": os.getenv("TEST_POSTGRES_HOST", "localhost"),
    "REDIS_HOST": os.getenv("TEST_REDIS_HOST", "localhost"),
    "JWT_SECRET_KEY": "test-secret-key-not-for-production",
}
