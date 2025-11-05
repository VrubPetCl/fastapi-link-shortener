"""Main FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db.schema import init_db

# Initialize database on startup
init_db()

app = FastAPI(title="URL Shortener")

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
