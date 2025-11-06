"""Authentication routes."""

from fastapi import APIRouter, Form, HTTPException, Response, Cookie
from fastapi.responses import RedirectResponse
from typing import Optional

from app.db.database import execute_query
from app.utils.auth import hash_password, verify_password, create_token, delete_token, FORCE_HTTPS

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    email: str = Form(...),
    password: str = Form(...)
):
    """Register a new user."""
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
        max_age=30 * 24 * 60 * 60  # 30 days
    )

    return response


@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    """Login user."""
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
        max_age=30 * 24 * 60 * 60  # 30 days
    )

    return response


@router.post("/logout")
async def logout(auth_token: Optional[str] = Cookie(None)):
    """Logout user."""
    if auth_token:
        delete_token(auth_token)

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("auth_token")

    return response
