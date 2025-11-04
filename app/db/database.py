"""Database utilities for cursor-based operations."""

import sqlite3
from contextlib import contextmanager
from typing import Any, Generator, Optional

from app.db.schema import DATABASE_PATH


@contextmanager
def get_cursor() -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager for database cursor operations.

    Yields:
        sqlite3.Cursor: Database cursor

    Example:
        with get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def execute_query(
    query: str,
    params: tuple = (),
    fetch_one: bool = False,
    fetch_all: bool = False
) -> Optional[Any]:
    """
    Execute a query with parameters using cursor.

    Args:
        query: SQL query string with ? placeholders
        params: Tuple of parameters to bind to query
        fetch_one: If True, return single row
        fetch_all: If True, return all rows

    Returns:
        Query results or None
    """
    with get_cursor() as cursor:
        cursor.execute(query, params)

        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()

        return cursor.lastrowid


def execute_many(query: str, params_list: list[tuple]) -> int:
    """
    Execute a query with multiple parameter sets.

    Args:
        query: SQL query string with ? placeholders
        params_list: List of parameter tuples

    Returns:
        Number of rows affected
    """
    with get_cursor() as cursor:
        cursor.executemany(query, params_list)
        return cursor.rowcount
