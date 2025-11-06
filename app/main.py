"""Main FastAPI application."""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from app.db.schema import init_db
from app.utils.request import get_client_ip


# Rate limiter configuration
def rate_limit_key_func(request: Request) -> str:
    """Get the client IP for rate limiting, respecting proxy headers."""
    return get_client_ip(request)


limiter = Limiter(key_func=rate_limit_key_func)


async def cleanup_rate_limiter():
    """Background task to clean up rate limiter memory every 24 hours."""
    while True:
        await asyncio.sleep(86400)  # 24 hours
        try:
            # Reset the rate limiter storage to free memory
            limiter.reset()
            print("✓ Rate limiter memory cleaned up", flush=True)
        except Exception as e:
            print(f"⚠️  Error cleaning rate limiter: {e}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    init_db()

    # Start background cleanup task
    cleanup_task = asyncio.create_task(cleanup_rate_limiter())

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="URL Shortener", lifespan=lifespan)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
