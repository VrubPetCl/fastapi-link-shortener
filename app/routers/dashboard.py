"""Dashboard routes."""

import os
import httpx
from fastapi import APIRouter, Request, Form, HTTPException, Cookie, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.database import execute_query
from app.utils.auth import verify_token, hash_password, verify_password, create_token, delete_token, FORCE_HTTPS
from app.utils.short_code import generate_short_code, is_valid_short_code

router = APIRouter(prefix="/d", tags=["dashboard"])
templates = Jinja2Templates(directory="templates")

# Get limiter from main app (will be injected)
limiter = Limiter(key_func=get_remote_address)

# Registration configuration
REGISTRATION_ENABLED = os.getenv("ENABLE_REGISTRATION", "false").lower() == "true"

# Cloudflare Turnstile configuration
CF_TURNSTILE_SITE_KEY = os.getenv("CF_TURNSTILE_SITE_KEY")
CF_TURNSTILE_SECRET_KEY = os.getenv("CF_TURNSTILE_SECRET_KEY")


async def verify_turnstile(token: str, remote_ip: str) -> bool:
    """Verify Cloudflare Turnstile token."""
    if not CF_TURNSTILE_SECRET_KEY:
        return True  # Skip verification if not configured

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                json={
                    "secret": CF_TURNSTILE_SECRET_KEY,
                    "response": token,
                    "remoteip": remote_ip
                },
                timeout=5.0
            )
            result = response.json()
            return result.get("success", False)
        except Exception:
            # If verification fails due to network issues, allow the request
            # This prevents Turnstile outages from blocking legitimate users
            return True


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
        SELECT id, short_code, original_url, password_hash, created_at, clicks, last_accessed
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
@limiter.limit("10/minute")
async def create_link(
    request: Request,
    original_url: str = Form(...),
    custom_code: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
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

    # Handle password
    password_hash_val = None
    if password and password.strip():
        if len(password) < 4:
            raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
        password_hash_val = hash_password(password)

    # Create link
    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url, password_hash) VALUES (?, ?, ?, ?)",
        (user_id, short_code, original_url, password_hash_val)
    )

    # Get the newly created link
    link = execute_query(
        "SELECT id, short_code, original_url, password_hash, created_at, clicks FROM links WHERE id = ?",
        (link_id,),
        fetch_one=True
    )

    # Return HTMX partial with the new link row
    return templates.TemplateResponse(
        "partials/link_row.html",
        {"request": request, "link": link}
    )


@router.get("/links/{link_id}/edit", response_class=HTMLResponse)
async def edit_link_form(
    request: Request,
    link_id: int,
    user_id: int = Depends(get_current_user)
):
    """Get the form to edit a link."""
    link = execute_query(
        "SELECT id, short_code, original_url, password_hash FROM links WHERE id = ? AND user_id = ?",
        (link_id, user_id),
        fetch_one=True
    )
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    return templates.TemplateResponse(
        "partials/link_edit_row.html",
        {"request": request, "link": link}
    )


@router.put("/links/{link_id}", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def update_link(
    request: Request,
    link_id: int,
    original_url: str = Form(...),
    password: Optional[str] = Form(None),
    remove_password: Optional[str] = Form(None),
    user_id: int = Depends(get_current_user)
):
    """Update a link."""
    link = execute_query(
        "SELECT id, user_id FROM links WHERE id = ?",
        (link_id,),
        fetch_one=True
    )
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not original_url or not original_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")

    update_sql = "UPDATE links SET original_url = ?"
    params = [original_url]

    if remove_password:
        update_sql += ", password_hash = NULL"
    elif password and password.strip():
        if len(password) < 4:
            raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
        update_sql += ", password_hash = ?"
        params.append(hash_password(password))

    update_sql += " WHERE id = ? AND user_id = ?"
    params.extend([link_id, user_id])

    execute_query(update_sql, tuple(params))

    updated_link = execute_query(
        "SELECT id, short_code, original_url, password_hash, created_at, clicks FROM links WHERE id = ?",
        (link_id,),
        fetch_one=True
    )

    return templates.TemplateResponse(
        "partials/link_row.html",
        {"request": request, "link": updated_link}
    )


@router.get("/links/{link_id}/row", response_class=HTMLResponse)
async def get_link_row(
    request: Request,
    link_id: int,
    user_id: int = Depends(get_current_user)
):
    """Get the display row for a link (used when cancelling edit)."""
    link = execute_query(
        "SELECT id, short_code, original_url, password_hash, created_at, clicks FROM links WHERE id = ? AND user_id = ?",
        (link_id, user_id),
        fetch_one=True
    )
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

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


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "registration_enabled": REGISTRATION_ENABLED,
        "cf_turnstile_site_key": CF_TURNSTILE_SITE_KEY
    })


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    cf_turnstile_response: Optional[str] = Form(None, alias="cf-turnstile-response")
):
    """Login user."""
    # Verify Turnstile if configured
    if CF_TURNSTILE_SECRET_KEY and CF_TURNSTILE_SITE_KEY:
        if not cf_turnstile_response:
            raise HTTPException(status_code=400, detail="Turnstile verification required")

        # Get client IP
        client_ip = request.client.host if request.client else "0.0.0.0"

        # Verify Turnstile token
        if not await verify_turnstile(cf_turnstile_response, client_ip):
            raise HTTPException(status_code=400, detail="Turnstile verification failed")

    # Get user
    user = execute_query(
        "SELECT id, password_hash FROM users WHERE email = ?",
        (email,),
        fetch_one=True
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create token
    token = create_token(user["id"])

    # Set cookie and redirect to dashboard
    response = RedirectResponse(url="/d/", status_code=303)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=FORCE_HTTPS,  # Enable secure cookies when behind HTTPS reverse proxy
        samesite="lax",
        max_age=30 * 60  # 30 minutes
    )

    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Register page."""
    if not REGISTRATION_ENABLED:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
@limiter.limit("3/hour")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """Register a new user."""
    if not REGISTRATION_ENABLED:
        raise HTTPException(status_code=403, detail="Registration is disabled")

    # Validate email and password
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")

    if not password or len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Check if user exists
    existing_user = execute_query(
        "SELECT id FROM users WHERE email = ?",
        (email,),
        fetch_one=True
    )

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    password_hash_value = hash_password(password)
    user_id = execute_query(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, password_hash_value)
    )

    # Create token
    token = create_token(user_id)

    # Set cookie and redirect to dashboard
    response = RedirectResponse(url="/d/", status_code=303)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=FORCE_HTTPS,  # Enable secure cookies when behind HTTPS reverse proxy
        samesite="lax",
        max_age=30 * 60  # 30 minutes
    )

    return response


@router.post("/logout")
async def logout(auth_token: Optional[str] = Cookie(None)):
    """Logout user."""
    if auth_token:
        delete_token(auth_token)

    response = RedirectResponse(url="/d/login", status_code=303)
    response.delete_cookie("auth_token")

    return response
