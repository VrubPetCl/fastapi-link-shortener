"""Tests for database operations."""

import pytest
from app.db.database import execute_query, execute_many, get_connection


def test_execute_query_insert(test_db):
    """Test inserting data with execute_query."""
    from app.utils.auth import hash_password

    email = "newuser@example.com"
    password_hash = hash_password("password123")

    user_id = execute_query(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, password_hash)
    )

    assert user_id is not None
    assert user_id > 0


def test_execute_query_fetch_one(test_db):
    """Test fetching one row with execute_query."""
    from app.utils.auth import hash_password

    email = "fetchone@example.com"
    password_hash = hash_password("password123")

    user_id = execute_query(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, password_hash)
    )

    user = execute_query(
        "SELECT id, email FROM users WHERE id = ?",
        (user_id,),
        fetch_one=True
    )

    assert user is not None
    assert user["id"] == user_id
    assert user["email"] == email


def test_execute_query_fetch_all(test_db):
    """Test fetching all rows with execute_query."""
    from app.utils.auth import hash_password

    users_data = [
        ("user1@example.com", hash_password("pass1")),
        ("user2@example.com", hash_password("pass2")),
        ("user3@example.com", hash_password("pass3")),
    ]

    for email, password_hash in users_data:
        execute_query(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )

    users = execute_query(
        "SELECT email FROM users ORDER BY email",
        fetch_all=True
    )

    assert len(users) == 3
    assert users[0]["email"] == "user1@example.com"
    assert users[1]["email"] == "user2@example.com"
    assert users[2]["email"] == "user3@example.com"


def test_execute_many(test_db):
    """Test batch insert with execute_many."""
    from app.utils.auth import hash_password

    users_data = [
        ("batch1@example.com", hash_password("pass1")),
        ("batch2@example.com", hash_password("pass2")),
        ("batch3@example.com", hash_password("pass3")),
    ]

    rows_affected = execute_many(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        users_data
    )

    assert rows_affected == 3

    # Verify data was inserted
    users = execute_query(
        "SELECT COUNT(*) as count FROM users",
        fetch_one=True
    )
    assert users["count"] == 3


def test_get_connection_context_manager(test_db):
    """Test using get_connection as context manager."""
    from app.utils.auth import hash_password

    email = "connection@example.com"
    password_hash = hash_password("password123")

    with get_connection() as conn:
        result = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        user_id = result.lastrowid

    # Verify data was committed
    user = execute_query(
        "SELECT id, email FROM users WHERE id = ?",
        (user_id,),
        fetch_one=True
    )

    assert user is not None
    assert user["email"] == email


def test_get_connection_rollback_on_error(test_db):
    """Test that get_connection rolls back on error."""
    from app.utils.auth import hash_password

    email = "rollback@example.com"
    password_hash = hash_password("password123")

    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, password_hash)
            )
            # Cause an error
            raise ValueError("Test error")
    except ValueError:
        pass

    # Verify data was not committed
    users = execute_query(
        "SELECT COUNT(*) as count FROM users WHERE email = ?",
        (email,),
        fetch_one=True
    )
    assert users["count"] == 0
