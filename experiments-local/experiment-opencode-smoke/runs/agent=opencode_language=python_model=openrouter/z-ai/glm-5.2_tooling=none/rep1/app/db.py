import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional


DB_PATH = "books.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def get_db_path() -> str:
    return DB_PATH


def init_db(db_path: Optional[str] = None) -> None:
    path = db_path or DB_PATH
    with sqlite3.connect(path) as conn:
        conn.execute(SCHEMA)


@contextmanager
def get_connection(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
