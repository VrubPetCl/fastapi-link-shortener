"""Tests for short code utilities."""

import pytest
from app.utils.short_code import generate_short_code, is_valid_short_code


def test_generate_short_code_default_length():
    """Test generating short code with default length."""
    code = generate_short_code()

    assert len(code) == 7
    assert code.isalnum()


def test_generate_short_code_custom_length():
    """Test generating short code with custom length."""
    code = generate_short_code(length=10)

    assert len(code) == 10
    assert code.isalnum()


def test_generate_short_code_uniqueness():
    """Test that generated codes are different."""
    codes = set()
    for _ in range(100):
        codes.add(generate_short_code())

    # All codes should be unique (with very high probability)
    assert len(codes) == 100


def test_is_valid_short_code_valid():
    """Test validation of valid short codes."""
    valid_codes = [
        "abc123",
        "my-link",
        "test_code",
        "ABC",
        "123",
        "a-b_c-1_2_3"
    ]

    for code in valid_codes:
        assert is_valid_short_code(code) is True


def test_is_valid_short_code_invalid():
    """Test validation of invalid short codes."""
    invalid_codes = [
        "",  # Empty
        "ab",  # Too short
        "a" * 51,  # Too long
        "test code",  # Space
        "test@code",  # Special character
        "test.code",  # Period
        "test/code",  # Slash
    ]

    for code in invalid_codes:
        assert is_valid_short_code(code) is False
