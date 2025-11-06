#!/usr/bin/env python3
"""
Generate a secure random secret key for JWT token signing.

Usage:
    python generate-secret.py

The generated secret should be stored in your environment variables:
    export JWT_SECRET_KEY="<generated-secret>"

Or add it to a .env file:
    JWT_SECRET_KEY=<generated-secret>
"""

import secrets
import sys


def generate_secret_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure random secret key.

    Args:
        length: Number of bytes for the secret (default: 32)

    Returns:
        URL-safe base64-encoded secret key
    """
    return secrets.token_urlsafe(length)


def main():
    """Generate and print a new secret key."""
    secret = generate_secret_key()

    print("=" * 70)
    print("Generated JWT Secret Key:")
    print("=" * 70)
    print()
    print(secret)
    print()
    print("=" * 70)
    print("Add this to your environment variables:")
    print("=" * 70)
    print()
    print(f"export JWT_SECRET_KEY='{secret}'")
    print()
    print("Or add to .env file:")
    print()
    print(f"JWT_SECRET_KEY={secret}")
    print()
    print("⚠️  WARNING: Keep this secret safe! Never commit it to version control.")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
