"""Tests for API endpoints."""

import pytest
from fastapi import status


def test_home_page(client):
    """Test home page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert "URL Shortener" in response.text


def test_register_success(client):
    """Test user registration."""
    response = client.post(
        "/auth/register",
        data={
            "email": "newuser@example.com",
            "password": "securepassword123"
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/d/"
    assert "auth_token" in response.cookies


def test_register_invalid_email(client):
    """Test registration with invalid email."""
    response = client.post(
        "/auth/register",
        data={
            "email": "invalidemail",
            "password": "securepassword123"
        }
    )

    assert response.status_code == 400


def test_register_short_password(client):
    """Test registration with short password."""
    response = client.post(
        "/auth/register",
        data={
            "email": "user@example.com",
            "password": "short"
        }
    )

    assert response.status_code == 400


def test_register_duplicate_email(client, sample_user):
    """Test registration with duplicate email."""
    response = client.post(
        "/auth/register",
        data={
            "email": sample_user["email"],
            "password": "anotherpassword123"
        }
    )

    assert response.status_code == 400


def test_login_success(client, sample_user):
    """Test user login."""
    response = client.post(
        "/auth/login",
        data={
            "email": sample_user["email"],
            "password": sample_user["password"]
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/d/"
    assert "auth_token" in response.cookies


def test_login_invalid_credentials(client, sample_user):
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        data={
            "email": sample_user["email"],
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    response = client.post(
        "/auth/login",
        data={
            "email": "nonexistent@example.com",
            "password": "somepassword"
        }
    )

    assert response.status_code == 401


def test_logout(authenticated_client):
    """Test user logout."""
    response = authenticated_client.post("/auth/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_dashboard_authenticated(authenticated_client):
    """Test dashboard access for authenticated user."""
    response = authenticated_client.get("/d/")

    assert response.status_code == 200
    assert "Dashboard" in response.text


def test_dashboard_unauthenticated(client):
    """Test dashboard access for unauthenticated user."""
    response = client.get("/d/")

    assert response.status_code == 401


def test_create_link(authenticated_client):
    """Test creating a shortened link."""
    response = authenticated_client.post(
        "/d/links",
        data={
            "original_url": "https://example.com/very/long/url/here",
            "custom_code": ""
        }
    )

    assert response.status_code == 200
    assert "example.com" in response.text


def test_create_link_custom_code(authenticated_client):
    """Test creating a link with custom code."""
    custom_code = "my-custom-link"
    response = authenticated_client.post(
        "/d/links",
        data={
            "original_url": "https://example.com/custom",
            "custom_code": custom_code
        }
    )

    assert response.status_code == 200
    assert custom_code in response.text


def test_create_link_invalid_url(authenticated_client):
    """Test creating a link with invalid URL."""
    response = authenticated_client.post(
        "/d/links",
        data={
            "original_url": "not-a-valid-url",
            "custom_code": ""
        }
    )

    assert response.status_code == 400


def test_create_link_duplicate_code(authenticated_client):
    """Test creating a link with duplicate custom code."""
    custom_code = "duplicate-code"

    # Create first link
    authenticated_client.post(
        "/d/links",
        data={
            "original_url": "https://example.com/first",
            "custom_code": custom_code
        }
    )

    # Try to create second link with same code
    response = authenticated_client.post(
        "/d/links",
        data={
            "original_url": "https://example.com/second",
            "custom_code": custom_code
        }
    )

    assert response.status_code == 400


def test_delete_link(authenticated_client):
    """Test deleting a link."""
    # Create a link first
    from app.db.database import execute_query

    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (authenticated_client.user_id, "test-delete", "https://example.com")
    )

    # Delete the link
    response = authenticated_client.delete(f"/d/links/{link_id}")

    assert response.status_code == 200

    # Verify link is deleted
    link = execute_query(
        "SELECT id FROM links WHERE id = ?",
        (link_id,),
        fetch_one=True
    )
    assert link is None


def test_delete_link_unauthorized(authenticated_client, sample_user):
    """Test deleting another user's link."""
    from app.db.database import execute_query
    from app.utils.auth import hash_password

    # Create another user
    other_user_id = execute_query(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        ("other@example.com", hash_password("password123"))
    )

    # Create a link for the other user
    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (other_user_id, "other-link", "https://example.com")
    )

    # Try to delete it
    response = authenticated_client.delete(f"/d/links/{link_id}")

    assert response.status_code == 403


def test_redirect_success(client, sample_user):
    """Test link redirection."""
    from app.db.database import execute_query

    short_code = "redirect-test"
    original_url = "https://example.com/destination"

    # Create a link
    execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (sample_user["id"], short_code, original_url)
    )

    # Test redirect
    response = client.get(f"/{short_code}", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == original_url


def test_redirect_not_found(client):
    """Test redirect with non-existent short code."""
    response = client.get("/nonexistent-code")

    assert response.status_code == 404


def test_redirect_tracks_click(client, sample_user):
    """Test that redirect tracks click with IP."""
    from app.db.database import execute_query

    short_code = "track-test"
    original_url = "https://example.com/tracking"

    # Create a link
    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (sample_user["id"], short_code, original_url)
    )

    # Test redirect
    response = client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 307

    # Verify click was tracked
    clicks = execute_query(
        "SELECT COUNT(*) as count FROM clicks WHERE link_id = ?",
        (link_id,),
        fetch_one=True
    )
    assert clicks["count"] == 1

    # Verify IP was stored
    click = execute_query(
        "SELECT ip_address FROM clicks WHERE link_id = ?",
        (link_id,),
        fetch_one=True
    )
    assert click["ip_address"] is not None

    # Verify link click count was updated
    link = execute_query(
        "SELECT clicks FROM links WHERE id = ?",
        (link_id,),
        fetch_one=True
    )
    assert link["clicks"] == 1


def test_link_stats(authenticated_client):
    """Test getting link statistics."""
    from app.db.database import execute_query

    # Create a link
    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (authenticated_client.user_id, "stats-test", "https://example.com")
    )

    # Add some clicks
    execute_query(
        "INSERT INTO clicks (link_id, ip_address) VALUES (?, ?)",
        (link_id, "192.168.1.1")
    )

    # Get stats
    response = authenticated_client.get(f"/d/links/{link_id}/stats")

    assert response.status_code == 200
    assert "stats-test" in response.text
    assert "192.168.1.1" in response.text
