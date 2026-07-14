"""SQLite persistence layer for the book collection."""
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

DEFAULT_DB_PATH = "books.db"


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                title   TEXT    NOT NULL,
                author  TEXT    NOT NULL,
                year    INTEGER,
                isbn    TEXT
            )
            """
        )
        conn.commit()


class BookStore:
    """Thin data-access object over the books table."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        init_db(db_path)

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        conn = _connect(self.db_path)
        try:
            yield conn.cursor()
            conn.commit()
        finally:
            conn.close()

    def create(self, title: str, author: str,
               year: Optional[int], isbn: Optional[str]) -> dict:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (title, author, year, isbn),
            )
            return self._get_with_cursor(cur, cur.lastrowid)

    def list(self, author: Optional[str] = None) -> list[dict]:
        with self._cursor() as cur:
            if author is not None:
                cur.execute(
                    "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
                )
            else:
                cur.execute("SELECT * FROM books ORDER BY id")
            return [dict(row) for row in cur.fetchall()]

    def get(self, book_id: int) -> Optional[dict]:
        with self._cursor() as cur:
            return self._get_with_cursor(cur, book_id)

    def update(self, book_id: int, title: str, author: str,
               year: Optional[int], isbn: Optional[str]) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (title, author, year, isbn, book_id),
            )
            if cur.rowcount == 0:
                return None
            return self._get_with_cursor(cur, book_id)

    def delete(self, book_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    @staticmethod
    def _get_with_cursor(cur: sqlite3.Cursor, book_id: int) -> Optional[dict]:
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        return dict(row) if row else None
