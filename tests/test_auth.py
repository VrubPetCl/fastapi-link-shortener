"""Tests for authentication utilities."""

import pytest
from app.utils.auth import (
    hash_password,
    verify_password,
    create_token,
    verify_token,
    delete_token
)


def test_hash_password():
    """Test password hashing."""
    password = "mysecretpassword"
    hashed = hash_password(password)

    assert hashed != password
    assert len(hashed) > 0
    assert hashed.startswith("$argon2")


def test_verify_password():
    """Test password verification."""
    password = "mysecretpassword"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_create_token():
    """Test token creation."""
    user_id = 123
    token = create_token(user_id)

    assert len(token) > 0
    assert isinstance(token, str)


def test_verify_token():
    """Test token verification."""
    user_id = 123
    token = create_token(user_id)

    verified_user_id = verify_token(token)
    assert verified_user_id == user_id


def test_verify_invalid_token():
    """Test verification of invalid token."""
    invalid_token = "invalid_token_12345"
    result = verify_token(invalid_token)

    assert result is None


def test_delete_token():
    """Test token deletion."""
    user_id = 123
    token = create_token(user_id)

    # Verify token exists
    assert verify_token(token) == user_id

    # Delete token
    delete_token(token)

    # Verify token no longer exists
    assert verify_token(token) is None
