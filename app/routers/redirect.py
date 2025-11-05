"""Link redirection routes."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from datetime import datetime

from app.db.database import execute_query, get_connection

router = APIRouter(tags=["redirect"])


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.

    Checks X-Forwarded-For header first (for proxies), falls back to client host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/{short_code}")
async def redirect_link(short_code: str, request: Request):
    """
    Redirect to original URL and track click.

    This catches all root-level paths except those defined elsewhere.
    """
    # Get link
    link = execute_query(
        "SELECT id, original_url FROM links WHERE short_code = ?",
        (short_code,),
        fetch_one=True
    )

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Track click with IP address
    ip_address = get_client_ip(request)
    referrer = request.headers.get("Referer", "")
    user_agent = request.headers.get("User-Agent", "")

    # Use connection for atomic transaction (both operations commit together)
    with get_connection() as conn:
        # Insert click record
        conn.execute(
            """
            INSERT INTO clicks (link_id, ip_address, referrer, user_agent)
            VALUES (?, ?, ?, ?)
            """,
            (link["id"], ip_address, referrer, user_agent)
        )

        # Update link click count and last accessed time
        conn.execute(
            """
            UPDATE links
            SET clicks = clicks + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (link["id"],)
        )

    # Redirect to original URL
    return RedirectResponse(url=link["original_url"], status_code=307)
