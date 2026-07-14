"""SQLite database helpers for the books API."""
import os
import sqlite3
from flask import g

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def get_db(db_path=None):
    """Return a SQLite connection bound to the Flask request context."""
    if "db" not in g:
        path = db_path
        if path is None:
            from flask import current_app

            try:
                path = current_app.config.get("DB_PATH") or os.environ.get(
                    "BOOKS_DB_PATH", "books.db"
                )
            except RuntimeError:
                path = os.environ.get("BOOKS_DB_PATH", "books.db")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db


def init_db(db_path=DEFAULT_DB_PATH):
    """Create the schema. Safe to call multiple times."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
