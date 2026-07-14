import sqlite3
from contextlib import contextmanager
from pathlib import Path


DB_PATH = Path(__file__).parent / "books.db"


def get_connection():
    """Get a SQLite connection with row factory and ensure schema exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Ensure schema exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def init_db():
    """Initialize the database schema."""
    with get_connection() as conn:
        pass  # Schema created in get_connection


def reset_db():
    """Reset the database (drop and recreate tables)."""
    with get_connection() as conn:
        conn.execute("DROP TABLE IF EXISTS books")
        conn.commit()
    # Table will be recreated on next get_connection call


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
