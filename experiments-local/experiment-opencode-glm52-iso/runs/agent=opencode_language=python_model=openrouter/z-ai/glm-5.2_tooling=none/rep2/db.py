import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

DB_PATH = "books.db"


def _resolve(db_path: Optional[str]) -> str:
    return db_path if db_path is not None else DB_PATH


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor(db_path: Optional[str] = None) -> Iterator[sqlite3.Cursor]:
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    with db_cursor(db_path) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


def insert_book(data: dict, db_path: Optional[str] = None) -> dict:
    with db_cursor(db_path) as cur:
        cur.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn")),
        )
        book_id = cur.lastrowid
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        return dict(row)


def list_books(author: Optional[str] = None, db_path: Optional[str] = None) -> list[dict]:
    with db_cursor(db_path) as cur:
        if author:
            cur.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,))
        else:
            cur.execute("SELECT * FROM books ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def get_book(book_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    with db_cursor(db_path) as cur:
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_book(book_id: int, data: dict, db_path: Optional[str] = None) -> Optional[dict]:
    existing = get_book(book_id, db_path)
    if not existing:
        return None
    merged = {**existing, **{k: v for k, v in data.items() if v is not None}}
    with db_cursor(db_path) as cur:
        cur.execute(
            """
            UPDATE books
            SET title = ?, author = ?, year = ?, isbn = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (merged["title"], merged["author"], merged.get("year"),
             merged.get("isbn"), book_id),
        )
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        return dict(cur.fetchone())


def delete_book(book_id: int, db_path: Optional[str] = None) -> bool:
    with db_cursor(db_path) as cur:
        cur.execute("SELECT id FROM books WHERE id = ?", (book_id,))
        if cur.fetchone() is None:
            return False
        cur.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return True
