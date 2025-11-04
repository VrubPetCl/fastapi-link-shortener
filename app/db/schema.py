"""Database schema definition and initialization."""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent.parent / "shortener.db"


def init_db() -> None:
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Links table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0,
            last_accessed TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Create index on short_code for fast lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_links_short_code
        ON links(short_code)
    """)

    # Clicks table for analytics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            ip_address TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referrer TEXT,
            user_agent TEXT,
            FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE
        )
    """)

    # Create index on link_id for fast analytics queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_clicks_link_id
        ON clicks(link_id)
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DATABASE_PATH}")
