"""Request utilities for handling proxy headers."""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Get real client IP address from request.

    When behind a reverse proxy, the real client IP is in forwarding headers.
    This function checks headers in order of preference:
    1. X-Forwarded-For (standard, may contain chain of IPs)
    2. X-Real-IP (nginx, contains single IP)
    3. request.client.host (direct connection)

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address as string, or "unknown" if not available
    """
    # Check X-Forwarded-For first (most common proxy header)
    # Format: "client, proxy1, proxy2" - we want the first (original client)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (the original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP (used by nginx and others)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client connection
    if request.client:
        return request.client.host

    return "unknown"
