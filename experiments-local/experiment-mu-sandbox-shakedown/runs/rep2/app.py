"""REST API service for managing a book collection.

Endpoints:
    GET    /health         Health check
    POST   /books          Create a new book
    GET    /books          List all books (optional ?author= filter)
    GET    /books/<id>     Get a single book
    PUT    /books/<id>     Update a book
    DELETE /books/<id>     Delete a book

Data is stored in an embedded SQLite database (path configurable via the
BOOKS_DB environment variable, defaults to ./books.db).
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from flask import Blueprint, Flask, current_app, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
)
"""

bp = Blueprint("books", __name__)


def _validate_payload(data: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Validate a book payload.

    Returns (book, None) on success or (None, error_message) on failure.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    errors: list[str] = []

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("'title' is required and must be a non-empty string.")

    author = data.get("author")
    if not isinstance(author, str) or not author.strip():
        errors.append("'author' is required and must be a non-empty string.")

    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("'year' must be an integer.")

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("'isbn' must be a string.")

    if errors:
        return None, " ".join(errors)

    return (
        {
            "title": title.strip(),
            "author": author.strip(),
            "year": year,
            "isbn": isbn,
        },
        None,
    )


def _row_to_book(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def get_db() -> sqlite3.Connection:
    """Return the SQLite connection for the current request context."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute(SCHEMA)
        g.db.commit()
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


@bp.route("/health", methods=["GET"])
def health():
    try:
        get_db().execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return jsonify({"status": "error", "database": "unavailable"}), 500
    return jsonify({"status": "ok"}), 200


@bp.route("/books", methods=["POST"])
def create_book():
    book, error = _validate_payload(request.get_json(silent=True))
    if error:
        return jsonify({"error": error}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book["title"], book["author"], book["year"], book["isbn"]),
    )
    db.commit()
    row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(_row_to_book(row)), 201


@bp.route("/books", methods=["GET"])
def list_books():
    db = get_db()
    author = request.args.get("author")
    if author:
        escaped = (
            author.strip().lower()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        rows = db.execute(
            "SELECT * FROM books WHERE lower(author) LIKE ? ESCAPE '\\' ORDER BY id",
            (f"%{escaped}%",),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
    return jsonify([_row_to_book(row) for row in rows]), 200


@bp.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id: int):
    row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found."}), 404
    return jsonify(_row_to_book(row)), 200


@bp.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id: int):
    db = get_db()
    row = db.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found."}), 404
    book, error = _validate_payload(request.get_json(silent=True))
    if error:
        return jsonify({"error": error}), 400
    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (book["title"], book["author"], book["year"], book["isbn"], book_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(_row_to_book(updated)), 200


@bp.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id: int):
    db = get_db()
    cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Book not found."}), 404
    return "", 204


def create_app(db_path: str | None = None) -> Flask:
    """Application factory. Pass db_path to use a custom SQLite file."""
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or DEFAULT_DB_PATH
    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "Internal server error."}), 500

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
