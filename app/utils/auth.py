"""Authentication utilities using pwdlib."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from pwdlib import PasswordHash

# Initialize password hasher with Argon2
pwd_hash = PasswordHash.recommended()

# In-memory token storage (for production, use Redis or database)
# Format: {token: {"user_id": int, "expires": datetime}}
_token_store: dict[str, dict] = {}

TOKEN_EXPIRY_DAYS = 30


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        password: Plain text password to verify
        password_hash: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_hash.verify(password, password_hash)


def create_token(user_id: int) -> str:
    """
    Create a new authentication token for a user.

    Args:
        user_id: User ID to associate with token

    Returns:
        New token string
    """
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(days=TOKEN_EXPIRY_DAYS)

    _token_store[token] = {
        "user_id": user_id,
        "expires": expires
    }

    return token


def verify_token(token: str) -> Optional[int]:
    """
    Verify a token and return associated user ID.

    Args:
        token: Token to verify

    Returns:
        User ID if token is valid, None otherwise
    """
    if token not in _token_store:
        return None

    token_data = _token_store[token]

    # Check if token has expired
    if datetime.utcnow() > token_data["expires"]:
        del _token_store[token]
        return None

    return token_data["user_id"]


def delete_token(token: str) -> None:
    """
    Delete a token (for logout).

    Args:
        token: Token to delete
    """
    if token in _token_store:
        del _token_store[token]
