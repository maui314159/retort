"""SQLite database layer for the book collection service.

The path is configurable at runtime via :func:`set_db_path` so tests can
target an isolated temporary file. The default is read from the
``BOOKS_DB_PATH`` environment variable, falling back to ``books.db`` in
the working directory.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")

_db_path: str = DEFAULT_DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT    NOT NULL,
    author TEXT   NOT NULL,
    year  INTEGER,
    isbn  TEXT
);
"""


def get_db_path() -> str:
    """Return the current SQLite file path."""
    return _db_path


def set_db_path(path: str) -> None:
    """Override the SQLite file path. Used by tests."""
    global _db_path
    _db_path = path


def init_db() -> None:
    """Create the ``books`` table if it does not exist."""
    with sqlite3.connect(get_db_path()) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Yield a configured connection; commits on clean exit, closes always."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
