"""SQLite-backed storage for books.

A thin helper around the stdlib `sqlite3` module. The active database
path is the module-level `DB_PATH` (tests override it for isolation).
The schema is created on first use via `init_db`, which supports a
`fresh=True` reset that the test suite relies on.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""

DB_PATH = "books.db"
def init_db(fresh: bool = False, path: str | None = None) -> None:
    """Create the schema at `path` (defaults to the current `DB_PATH`).
    With `fresh=True`, drop the table first.
    """
    target = path or DB_PATH
    conn = sqlite3.connect(target)
    try:
        if fresh:
            conn.execute("DROP TABLE IF EXISTS books")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_book(data: dict) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn")),
        )
        bid = cur.lastrowid
    return {**data, "id": bid}


def list_books(author: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_book(bid: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
    return dict(row) if row else None


def update_book(bid: int, data: dict) -> dict | None:
    if get_book(bid) is None:
        return None
    with get_conn() as conn:
        conn.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (data["title"], data["author"], data.get("year"), data.get("isbn"), bid),
        )
    return {**data, "id": bid}


def delete_book(bid: int) -> bool:
    if get_book(bid) is None:
        return False
    with get_conn() as conn:
        conn.execute("DELETE FROM books WHERE id = ?", (bid,))
    return True
