"""SQLite persistence layer for the books REST API.

Uses one connection per request (stored on ``flask.g``) against the SQLite
database configured on the Flask app (``app.config["DATABASE"]``).
"""

import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def get_db():
    """Return this request's SQLite connection, creating it if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    """Close the per-request connection at teardown."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create the schema if needed and register connection teardown."""
    conn = sqlite3.connect(app.config["DATABASE"], timeout=10)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    app.teardown_appcontext(close_db)


def _row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def insert_book(title, author, year, isbn):
    """Insert a book and return its new id."""
    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (title, author, year, isbn),
    )
    db.commit()
    return cur.lastrowid


def fetch_book(book_id):
    """Return a book dict or None if not found."""
    row = get_db().execute(
        "SELECT * FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return _row_to_book(row) if row else None


def fetch_books(author=None):
    """Return all books, optionally filtered by author.

    The author filter is a case-insensitive substring match.
    """
    rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
    books = [_row_to_book(row) for row in rows]
    if author:
        needle = author.strip().lower()
        books = [b for b in books if needle in b["author"].lower()]
    return books


def replace_book(book_id, title, author, year, isbn):
    """Fully replace a book's fields. Returns True if a row was updated."""
    db = get_db()
    cur = db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    db.commit()
    return cur.rowcount > 0


def remove_book(book_id):
    """Delete a book. Returns True if a row was deleted."""
    db = get_db()
    cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return cur.rowcount > 0
