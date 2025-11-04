"""Short code generation utilities."""

import secrets
import string

# Character set for short codes (alphanumeric)
CHARSET = string.ascii_letters + string.digits


def generate_short_code(length: int = 7) -> str:
    """
    Generate a random short code.

    Args:
        length: Length of the short code (default 7)

    Returns:
        Random short code string
    """
    return ''.join(secrets.choice(CHARSET) for _ in range(length))


def is_valid_short_code(code: str) -> bool:
    """
    Validate a short code format.

    Args:
        code: Short code to validate

    Returns:
        True if valid, False otherwise
    """
    if not code:
        return False

    # Check length (between 3 and 50 characters)
    if len(code) < 3 or len(code) > 50:
        return False

    # Check characters (alphanumeric, hyphens, underscores)
    allowed = set(CHARSET + '-_')
    return all(c in allowed for c in code)
