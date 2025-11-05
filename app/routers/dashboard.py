"""Dashboard routes."""

from fastapi import APIRouter, Request, Form, HTTPException, Cookie, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from app.db.database import execute_query
from app.utils.auth import verify_token
from app.utils.short_code import generate_short_code, is_valid_short_code

router = APIRouter(prefix="/d", tags=["dashboard"])
templates = Jinja2Templates(directory="templates")


async def get_current_user(auth_token: Optional[str] = Cookie(None)) -> int:
    """Dependency to get current user from cookie token."""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(auth_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_id


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user_id: int = Depends(get_current_user)
):
    """Dashboard page showing user's links."""
    # Get user's links
    links = execute_query(
        """
        SELECT id, short_code, original_url, created_at, clicks, last_accessed
        FROM links
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
        fetch_all=True
    )

    # Get user email
    user = execute_query(
        "SELECT email FROM users WHERE id = ?",
        (user_id,),
        fetch_one=True
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "links": links,
            "user_email": user["email"] if user else ""
        }
    )


@router.post("/links", response_class=HTMLResponse)
async def create_link(
    request: Request,
    original_url: str = Form(...),
    custom_code: Optional[str] = Form(None),
    user_id: int = Depends(get_current_user)
):
    """Create a new shortened link."""
    # Validate URL
    if not original_url or not original_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")

    # Handle custom or generated short code
    if custom_code:
        if not is_valid_short_code(custom_code):
            raise HTTPException(status_code=400, detail="Invalid custom code")
        short_code = custom_code
    else:
        # Generate unique short code
        max_attempts = 10
        for _ in range(max_attempts):
            short_code = generate_short_code()
            existing = execute_query(
                "SELECT id FROM links WHERE short_code = ?",
                (short_code,),
                fetch_one=True
            )
            if not existing:
                break
        else:
            raise HTTPException(status_code=500, detail="Could not generate unique code")

    # Check if short code already exists
    existing = execute_query(
        "SELECT id FROM links WHERE short_code = ?",
        (short_code,),
        fetch_one=True
    )

    if existing:
        raise HTTPException(status_code=400, detail="Short code already exists")

    # Create link
    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (user_id, short_code, original_url)
    )

    # Get the newly created link
    link = execute_query(
        "SELECT id, short_code, original_url, created_at, clicks FROM links WHERE id = ?",
        (link_id,),
        fetch_one=True
    )

    # Return HTMX partial with the new link row
    return templates.TemplateResponse(
        "partials/link_row.html",
        {"request": request, "link": link}
    )


@router.delete("/links/{link_id}")
async def delete_link(
    link_id: int,
    user_id: int = Depends(get_current_user)
):
    """Delete a link."""
    # Verify ownership
    link = execute_query(
        "SELECT user_id FROM links WHERE id = ?",
        (link_id,),
        fetch_one=True
    )

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete link (cascades to clicks)
    execute_query("DELETE FROM links WHERE id = ?", (link_id,))

    # Return empty response for HTMX to remove the element
    return Response(status_code=200)


@router.get("/links/{link_id}/stats", response_class=HTMLResponse)
async def link_stats(
    request: Request,
    link_id: int,
    user_id: int = Depends(get_current_user)
):
    """Get link statistics."""
    # Verify ownership
    link = execute_query(
        """
        SELECT l.*, u.email as user_email
        FROM links l
        JOIN users u ON l.user_id = u.id
        WHERE l.id = ? AND l.user_id = ?
        """,
        (link_id, user_id),
        fetch_one=True
    )

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Get click history
    clicks = execute_query(
        """
        SELECT ip_address, timestamp, referrer, user_agent
        FROM clicks
        WHERE link_id = ?
        ORDER BY timestamp DESC
        LIMIT 100
        """,
        (link_id,),
        fetch_all=True
    )

    return templates.TemplateResponse(
        "partials/link_stats.html",
        {
            "request": request,
            "link": link,
            "clicks": clicks
        }
    )
