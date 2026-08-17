"""Link redirection routes."""

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.database import execute_query, get_connection
from app.utils.auth import verify_password
from app.utils.request import get_client_ip

router = APIRouter(tags=["redirect"])
templates = Jinja2Templates(directory="templates")

# Get limiter from main app (will be injected)
limiter = Limiter(key_func=get_remote_address)


def _record_click(link_id: int, request: Request) -> None:
    """Record a click and bump the link counters atomically."""
    ip_address = get_client_ip(request)
    referrer = request.headers.get("Referer", "")
    user_agent = request.headers.get("User-Agent", "")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO clicks (link_id, ip_address, referrer, user_agent)
            VALUES (?, ?, ?, ?)
            """,
            (link_id, ip_address, referrer, user_agent)
        )
        conn.execute(
            """
            UPDATE links
            SET clicks = clicks + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (link_id,)
        )


@router.get("/{short_code}")
@limiter.limit("60/minute")
async def redirect_link(short_code: str, request: Request):
    """
    Redirect to original URL and track click.

    Password-protected links render a password prompt instead and are not
    counted as a click until the password is verified.

    This catches all root-level paths except those defined elsewhere.
    Rate limited to prevent abuse: 60 requests per minute per IP.
    """
    link = execute_query(
        "SELECT id, original_url, password_hash FROM links WHERE short_code = ?",
        (short_code,),
        fetch_one=True
    )

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link["password_hash"]:
        return templates.TemplateResponse(
            "password_prompt.html",
            {"request": request, "short_code": short_code, "error": None},
            status_code=401
        )

    _record_click(link["id"], request)
    return RedirectResponse(url=link["original_url"], status_code=307)


@router.post("/{short_code}")
@limiter.limit("10/minute")
async def redirect_link_post(short_code: str, request: Request, password: str = Form(...)):
    """
    Verify the password for a protected link and redirect on success.

    Always redirects with 303 so the browser issues a GET to the target
    instead of replaying this POST. Rate limited to 10 attempts per minute
    per IP to slow down password guessing.
    """
    link = execute_query(
        "SELECT id, original_url, password_hash FROM links WHERE short_code = ?",
        (short_code,),
        fetch_one=True
    )

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if not link["password_hash"]:
        # Password was removed while the prompt page was open. 303 so the
        # browser follows up with a GET rather than POSTing to the target.
        _record_click(link["id"], request)
        return RedirectResponse(url=link["original_url"], status_code=303)

    try:
        is_valid = verify_password(password, link["password_hash"])
    except Exception:
        is_valid = False

    if not is_valid:
        return templates.TemplateResponse(
            "password_prompt.html",
            {"request": request, "short_code": short_code, "error": "Incorrect password"},
            status_code=401
        )

    _record_click(link["id"], request)
    return RedirectResponse(url=link["original_url"], status_code=303)
