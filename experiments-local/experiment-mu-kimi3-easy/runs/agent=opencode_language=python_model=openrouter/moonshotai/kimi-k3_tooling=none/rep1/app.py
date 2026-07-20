"""Book collection REST API.

A small Flask + SQLite service for managing a book collection.

Endpoints:
    GET    /health       — health check
    POST   /books        — create a book (title, author, year, isbn)
    GET    /books        — list all books (?author= filter supported)
    GET    /books/<id>   — get a single book
    PUT    /books/<id>   — update a book
    DELETE /books/<id>   — delete a book
"""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


def get_db():
    """Return the request-scoped SQLite connection (created lazily)."""
    if "db" not in g:
        g.db = sqlite3.connect(g.db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def row_to_book(row):
    """Convert a sqlite3.Row into a JSON-serializable book dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(data, partial=False):
    """Validate a book payload.

    Args:
        data:    The decoded JSON body (must be a dict).
        partial: When True (PUT), only validate fields that are present;
                 title/author are not required.

    Returns:
        (errors, cleaned) — errors is a list of message strings (empty when
        valid); cleaned is a dict of validated fields to persist.
    """
    errors = []
    cleaned = {}

    if not isinstance(data, dict):
        return ["Request body must be a JSON object"], cleaned

    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"'{field}' must be a non-empty string")
            else:
                cleaned[field] = value.strip()
        elif not partial:
            errors.append(f"'{field}' is required")

    if "year" in data:
        year = data["year"]
        if year is None:
            cleaned["year"] = None
        elif isinstance(year, bool) or not isinstance(year, int):
            errors.append("'year' must be an integer")
        else:
            cleaned["year"] = year

    if "isbn" in data:
        isbn = data["isbn"]
        if isbn is None:
            cleaned["isbn"] = None
        elif not isinstance(isbn, str):
            errors.append("'isbn' must be a string")
        else:
            cleaned["isbn"] = isbn

    if partial and not cleaned and not errors:
        errors.append("No updatable fields provided")

    return errors, cleaned


def create_app(db_path=None):
    """Application factory. db_path defaults to DEFAULT_DB_PATH."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DEFAULT_DB_PATH

    @app.before_request
    def open_db():
        # Stash the path so get_db() can open a connection per app instance.
        g.db_path = app.config["DB_PATH"]

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        g.db_path = app.config["DB_PATH"]
        get_db().execute(SCHEMA)
        get_db().commit()

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        errors, cleaned = validate_book_payload(data)
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                cleaned["title"],
                cleaned["author"],
                cleaned.get("year"),
                cleaned.get("isbn"),
            ),
        )
        db.commit()
        book = db.execute(
            "SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(row_to_book(book)), 201

    @app.get("/books")
    def list_books():
        db = get_db()
        author = request.args.get("author")
        if author is not None:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_book(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        data = request.get_json(silent=True)
        errors, cleaned = validate_book_payload(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400

        assignments = ", ".join(f"{field} = ?" for field in cleaned)
        db.execute(
            f"UPDATE books SET {assignments} WHERE id = ?",
            (*cleaned.values(), book_id),
        )
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(row_to_book(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
