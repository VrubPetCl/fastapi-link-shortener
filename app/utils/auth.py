"""Authentication utilities using pwdlib and JWT."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pwdlib import PasswordHash

# Initialize password hasher with Argon2
pwd_hash = PasswordHash.recommended()

# JWT configuration
# In production, use environment variable and keep secret!
JWT_SECRET_KEY = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
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
    Create a new JWT authentication token for a user.

    Args:
        user_id: User ID to associate with token

    Returns:
        JWT token string
    """
    expires = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS)

    payload = {
        "user_id": user_id,
        "exp": expires,
        "iat": datetime.now(timezone.utc)
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Optional[int]:
    """
    Verify a JWT token and return associated user ID.

    Args:
        token: JWT token to verify

    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        # Token has expired
        return None
    except jwt.InvalidTokenError:
        # Token is invalid
        return None


def delete_token(token: str) -> None:
    """
    Delete a token (for logout).

    Note: With JWT, tokens cannot be truly "deleted" as they are stateless.
    This function is kept for API compatibility but does nothing.
    Tokens will expire naturally based on their expiration time.

    Args:
        token: Token to delete (no-op for JWT)
    """
    # JWT tokens are stateless and cannot be revoked without a blacklist
    # They will expire naturally after TOKEN_EXPIRY_DAYS
    pass
