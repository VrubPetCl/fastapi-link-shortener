"""Database utilities for connection-based operations."""

import sqlite3
from contextlib import contextmanager
from typing import Any, Generator, Optional

from app.db.schema import DATABASE_PATH


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connection operations.

    Yields:
        sqlite3.Connection: Database connection with row factory enabled

    Example:
        with get_connection() as conn:
            conn.execute("INSERT INTO users (email) VALUES (?)", (email,))
            result = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = result.fetchone()
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(
    query: str,
    params: tuple = (),
    fetch_one: bool = False,
    fetch_all: bool = False
) -> Optional[Any]:
    """
    Execute a query with parameters.

    Args:
        query: SQL query string with ? placeholders
        params: Tuple of parameters to bind to query
        fetch_one: If True, return single row
        fetch_all: If True, return all rows

    Returns:
        Query results or None (for INSERTs, returns lastrowid)
    """
    with get_connection() as conn:
        result = conn.execute(query, params)

        if fetch_one:
            return result.fetchone()
        elif fetch_all:
            return result.fetchall()

        return result.lastrowid


def execute_many(query: str, params_list: list[tuple]) -> int:
    """
    Execute a query with multiple parameter sets.

    Args:
        query: SQL query string with ? placeholders
        params_list: List of parameter tuples

    Returns:
        Number of rows affected
    """
    with get_connection() as conn:
        cursor = conn.executemany(query, params_list)
        return cursor.rowcount
