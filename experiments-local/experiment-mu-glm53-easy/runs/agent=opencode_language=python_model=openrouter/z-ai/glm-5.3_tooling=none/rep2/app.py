"""Book collection REST API.

A Flask service backed by SQLite that manages a collection of books.

Endpoints:
    GET    /health      liveness probe
    POST   /books       create a book
    GET    /books       list books (optional ?author= filter)
    GET    /books/<id>  fetch a single book
    PUT    /books/<id>  update a book (partial updates supported)
    DELETE /books/<id>  delete a book

Run with `python app.py` or `flask --app app run --debug`.
The database path defaults to ./books.db and can be overridden with the
BOOKS_DB environment variable (must be a file path, not :memory:).
"""

import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request
from werkzeug.exceptions import HTTPException

SCHEMA = """
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


def get_db():
    """Return a SQLite connection scoped to the current app context."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def validate_payload(data, *, creating):
    """Validate a book payload.

    Returns (cleaned_fields, errors) where errors maps field name to a
    human-readable message. On create, title and author are required;
    on update only the fields present in the payload are validated.
    """
    errors = {}
    cleaned = {}

    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                errors[field] = f"{field} must be a non-empty string"
            else:
                cleaned[field] = value.strip()
        elif creating:
            errors[field] = f"{field} is required"

    if data.get("year") is not None:
        value = data["year"]
        if isinstance(value, bool) or not isinstance(value, int):
            errors["year"] = "year must be an integer"
        elif not 0 <= value <= 9999:
            errors["year"] = "year must be between 0 and 9999"
        else:
            cleaned["year"] = value

    if data.get("isbn") is not None:
        value = data["isbn"]
        if not isinstance(value, str) or not value.strip():
            errors["isbn"] = "isbn must be a non-empty string"
        else:
            cleaned["isbn"] = value.strip()

    return cleaned, errors


def create_app(db_path=None):
    if db_path is None:
        db_path = os.environ.get("BOOKS_DB", "books.db")
    init_db(db_path)

    app = Flask(__name__)
    app.config["DATABASE"] = db_path
    app.teardown_appcontext(close_db)

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        return jsonify({"error": exc.description}), exc.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        app.logger.exception("Unhandled error")
        return jsonify({"error": "internal server error"}), 500

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/books")
    def list_books():
        author = request.args.get("author", "").strip()
        if author:
            escaped = author.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            rows = get_db().execute(
                "SELECT * FROM books WHERE author LIKE ? ESCAPE '\\' ORDER BY id",
                (f"%{escaped}%",),
            ).fetchall()
        else:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(row) for row in rows])

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400
        cleaned, errors = validate_payload(data, creating=True)
        if errors:
            return jsonify({"error": "validation failed", "fields": errors}), 400
        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (cleaned.get("title"), cleaned.get("author"),
             cleaned.get("year"), cleaned.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(book_to_dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400
        db = get_db()
        if db.execute("SELECT 1 FROM books WHERE id = ?", (book_id,)).fetchone() is None:
            return jsonify({"error": "book not found"}), 404
        cleaned, errors = validate_payload(data, creating=False)
        if errors:
            return jsonify({"error": "validation failed", "fields": errors}), 400
        if not cleaned:
            return jsonify({"error": "no valid fields to update"}), 400
        assignments = ", ".join(f"{field} = ?" for field in cleaned)
        db.execute(
            f"UPDATE books SET {assignments}, updated_at = datetime('now') WHERE id = ?",
            (*cleaned.values(), book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "book not found"}), 404
        return "", 204

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=5000, debug=True)
