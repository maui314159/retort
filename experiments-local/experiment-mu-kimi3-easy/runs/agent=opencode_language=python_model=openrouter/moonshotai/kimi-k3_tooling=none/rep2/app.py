"""REST API service for managing a book collection.

Flask + SQLite (stdlib). Run with: python app.py (or: flask --app app run).
The database path is configurable via the BOOKS_DB environment variable.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from flask import Flask, jsonify, request


DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_book_payload(data: Any) -> tuple[list[str], dict]:
    """Validate a create/update payload.

    Returns (errors, cleaned): ``errors`` is a list of human-readable problems
    (empty when valid); ``cleaned`` holds normalized title/author/year/isbn.
    """
    if not isinstance(data, dict):
        return ["request body must be a JSON object"], {}

    errors: list[str] = []
    cleaned: dict[str, Optional[Any]] = {}

    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"'{field}' is required and must be a non-empty string")
        else:
            cleaned[field] = value.strip()

    year = data.get("year")
    if year is None:
        cleaned["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors.append("'year' must be an integer")
    else:
        cleaned["year"] = year

    isbn = data.get("isbn")
    if isbn is None:
        cleaned["isbn"] = None
    elif not isinstance(isbn, str):
        errors.append("'isbn' must be a string")
    else:
        cleaned["isbn"] = isbn

    return errors, cleaned


def _row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


@contextmanager
def _db(db_path: str) -> Iterator[sqlite3.Connection]:
    """Yield a connection with row access by name; commit and close on exit."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with _db(db_path) as conn:
        conn.execute(
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


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


def create_app(db_path: str = DEFAULT_DB_PATH) -> Flask:
    app = Flask(__name__)
    init_db(db_path)

    def fetch_book(book_id: int) -> Optional[dict]:
        with _db(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return _row_to_book(row) if row else None

    @app.get("/health")
    def health():
        try:
            with _db(db_path) as conn:
                conn.execute("SELECT 1")
        except sqlite3.Error:
            return jsonify({"status": "error", "detail": "database unavailable"}), 503
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        errors, cleaned = validate_book_payload(request.get_json(silent=True))
        if errors:
            return jsonify({"errors": errors}), 400
        with _db(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (cleaned["title"], cleaned["author"], cleaned["year"], cleaned["isbn"]),
            )
            book_id = cur.lastrowid
        return jsonify(fetch_book(book_id)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        with _db(db_path) as conn:
            if author is not None:
                rows = conn.execute(
                    "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_row_to_book(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        book = fetch_book(book_id)
        if book is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(book), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        if fetch_book(book_id) is None:
            return jsonify({"error": "book not found"}), 404
        errors, cleaned = validate_book_payload(request.get_json(silent=True))
        if errors:
            return jsonify({"errors": errors}), 400
        with _db(db_path) as conn:
            conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (cleaned["title"], cleaned["author"], cleaned["year"], cleaned["isbn"], book_id),
            )
        return jsonify(fetch_book(book_id)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        with _db(db_path) as conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "book not found"}), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8000, debug=True)
