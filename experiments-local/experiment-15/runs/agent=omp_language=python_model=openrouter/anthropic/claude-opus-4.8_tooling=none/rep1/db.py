"""SQLite persistence for the book collection.

A single connection is shared across requests. SQLite serializes writes with
its own lock, and FastAPI's default threadpool means handlers may run on
different threads, so the connection is opened with ``check_same_thread=False``
and guarded by a module-level lock for the few multi-statement operations.
"""

import sqlite3
import threading
from contextlib import contextmanager

_DEFAULT_PATH = "books.db"

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def init_db(path: str = _DEFAULT_PATH) -> sqlite3.Connection:
    """Open (or reopen) the database and ensure the schema exists.

    Passing ``":memory:"`` yields an isolated in-memory DB, used by the tests.
    """
    global _conn
    if _conn is not None:
        _conn.close()
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )
        """
    )
    _conn.commit()
    return _conn


def get_conn() -> sqlite3.Connection:
    if _conn is None:
        return init_db()
    return _conn


@contextmanager
def transaction():
    """Serialize a write and commit it atomically."""
    conn = get_conn()
    with _lock:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
