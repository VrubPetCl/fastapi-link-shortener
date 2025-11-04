"""Test fixtures and configuration."""

import os
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Set test database path before importing app
TEST_DB_PATH = Path(__file__).parent / "test_shortener.db"
os.environ["DATABASE_PATH"] = str(TEST_DB_PATH)


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test."""
    # Remove existing test database
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    # Import after setting DATABASE_PATH
    from app.db.schema import init_db, DATABASE_PATH

    # Override DATABASE_PATH for tests
    import app.db.schema
    import app.db.database
    app.db.schema.DATABASE_PATH = TEST_DB_PATH
    app.db.database.DATABASE_PATH = TEST_DB_PATH

    # Initialize database
    init_db()

    yield TEST_DB_PATH

    # Cleanup
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client."""
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_user(test_db):
    """Create a sample user for testing."""
    from app.db.database import execute_query
    from app.utils.auth import hash_password

    email = "test@example.com"
    password = "testpassword123"
    password_hash = hash_password(password)

    user_id = execute_query(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, password_hash)
    )

    return {
        "id": user_id,
        "email": email,
        "password": password
    }


@pytest.fixture
def authenticated_client(test_db, sample_user):
    """Create an authenticated test client."""
    from app.main import app
    from app.utils.auth import create_token

    # Create auth token
    token = create_token(sample_user["id"])

    # Create client with auth cookie
    with TestClient(app, cookies={"auth_token": token}) as auth_client:
        auth_client.user_id = sample_user["id"]
        yield auth_client
