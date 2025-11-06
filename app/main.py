"""Main FastAPI application."""

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.schema import init_db

# Initialize database on startup
init_db()

app = FastAPI(title="URL Shortener")

# HTTPS configuration - set FORCE_HTTPS=true when behind a reverse proxy
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "true").lower() == "true"


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle proxy headers for proper HTTPS and IP forwarding.

    When behind a reverse proxy (nginx, caddy, etc.), this middleware ensures:
    - Correct scheme (http/https) is detected from X-Forwarded-Proto
    - Real client IP is available from X-Forwarded-For or X-Real-IP
    - Correct host is used from X-Forwarded-Host

    Enable this by setting FORCE_HTTPS=true in environment variables.
    """
    async def dispatch(self, request: Request, call_next):
        # Get forwarded protocol (http/https)
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto:
            request.scope["scheme"] = forwarded_proto

        # Get forwarded host
        forwarded_host = request.headers.get("X-Forwarded-Host")
        if forwarded_host:
            request.scope["server"] = (forwarded_host, None)

        response = await call_next(request)
        return response


# Add middleware when behind HTTPS reverse proxy
if FORCE_HTTPS:
    app.add_middleware(ProxyHeadersMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request})


# Import routers
from app.routers import dashboard, redirect

app.include_router(dashboard.router)

# Redirect router must be last to catch all remaining root-level paths
app.include_router(redirect.router)
