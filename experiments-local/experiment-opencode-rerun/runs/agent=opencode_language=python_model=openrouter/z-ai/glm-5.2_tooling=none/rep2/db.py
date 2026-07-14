import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
            """
        )


def reset_db() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()


def insert_book(title: str, author: str, year: Optional[int], isbn: Optional[str]) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        book_id = cur.lastrowid
        return get_book(book_id, conn=conn)


def list_books(author: Optional[str] = None) -> list[dict]:
    with get_conn() as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [_row_to_dict(r) for r in rows]


def get_book(book_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[dict]:
    own_conn = conn is None
    if own_conn:
        conn = _connect()
    try:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        if own_conn:
            conn.close()


def update_book(
    book_id: int,
    title: Optional[str],
    author: Optional[str],
    year: Optional[int],
    isbn: Optional[str],
) -> Optional[dict]:
    existing = get_book(book_id)
    if not existing:
        return None
    new_title = title if title is not None else existing["title"]
    new_author = author if author is not None else existing["author"]
    new_year = year if year is not None else existing["year"]
    new_isbn = isbn if isbn is not None else existing["isbn"]
    with get_conn() as conn:
        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (new_title, new_author, new_year, new_isbn, book_id),
        )
    return get_book(book_id)


def delete_book(book_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }
