"""Unit tests for security utilities"""

import pytest
from datetime import timedelta
from src.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    check_permission,
)
from src.models.auth import TokenData
from fastapi import HTTPException


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        password = "test123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        password = "test123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        password = "test123"
        hashed = get_password_hash(password)
        assert verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self):
        password = "test123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        # bcrypt uses salt, so hashes should be different
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """Test JWT token creation and validation"""

    def test_create_token(self):
        data = {"sub": "testuser", "groups": ["users"]}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_expiry(self):
        data = {"sub": "testuser"}
        expires = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires)
        assert isinstance(token, str)

    def test_decode_valid_token(self):
        username = "testuser"
        groups = ["users", "admins"]
        data = {"sub": username, "groups": groups, "department": "Engineering", "country": "US"}
        token = create_access_token(data)

        decoded = decode_token(token)
        assert decoded.username == username
        assert decoded.groups == groups
        assert decoded.department == "Engineering"
        assert decoded.country == "US"

    def test_decode_invalid_token(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_decode_token_missing_subject(self):
        # Create token without 'sub' claim
        data = {"groups": ["users"]}
        token = create_access_token(data)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401


class TestPermissionChecking:
    """Test permission and group checking"""

    def test_user_has_required_group(self):
        user = TokenData(
            username="testuser", groups=["users", "admins"], department=None, country=None
        )
        required = ["admins"]
        assert check_permission(user, required) is True

    def test_user_missing_required_group(self):
        user = TokenData(username="testuser", groups=["users"], department=None, country=None)
        required = ["admins"]
        assert check_permission(user, required) is False

    def test_user_has_one_of_multiple_required_groups(self):
        user = TokenData(
            username="testuser", groups=["users", "developers"], department=None, country=None
        )
        required = ["admins", "developers", "managers"]
        assert check_permission(user, required) is True

    def test_empty_required_groups_always_passes(self):
        user = TokenData(username="testuser", groups=["users"], department=None, country=None)
        assert check_permission(user, []) is True

    def test_user_with_no_groups(self):
        user = TokenData(username="testuser", groups=[], department=None, country=None)
        required = ["admins"]
        assert check_permission(user, required) is False
