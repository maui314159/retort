"""
Book Collection REST API.

A small Flask service for managing a collection of books stored in SQLite.
"""

import os
import sqlite3
from flask import Flask, jsonify, request, g

app = Flask(__name__)

# Allow the database path to be overridden (e.g. for tests using a temp file).
DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


# --------------------------------------------------------------------------- #
# Database helpers
# --------------------------------------------------------------------------- #
def get_db():
    """Return a SQLite connection bound to the Flask request context."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        # Ensure foreign-key / constraint behaviour is predictable.
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path=None):
    """Create the books table if it does not already exist."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT    NOT NULL,
                author TEXT    NOT NULL,
                year   INTEGER,
                isbn   TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_book(data, partial=False):
    """Validate the incoming book payload.

    Returns (payload, errors). When `partial` is True (used by PUT), only the
    provided fields are validated and required-field checks are skipped.
    """
    errors = {}
    if not isinstance(data, dict):
        return None, {"body": "Request body must be a JSON object."}

    title = data.get("title")
    author = data.get("author")
    year = data.get("year")
    isbn = data.get("isbn")

    if not partial:
        if title is None or str(title).strip() == "":
            errors["title"] = "title is required"
        if author is None or str(author).strip() == "":
            errors["author"] = "author is required"

    if title is not None and str(title).strip() == "":
        errors["title"] = "title must not be empty"
    if author is not None and str(author).strip() == "":
        errors["author"] = "author must not be empty"

    if year is not None:
        if not isinstance(year, int):
            errors["year"] = "year must be an integer"
        elif year < 0:
            errors["year"] = "year must be a non-negative integer"

    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "isbn must be a string"

    payload = {}
    if title is not None:
        payload["title"] = str(title).strip()
    if author is not None:
        payload["author"] = str(author).strip()
    if year is not None:
        payload["year"] = year
    if isbn is not None:
        payload["isbn"] = isbn

    return payload, errors


def row_to_book(row):
    """Convert a sqlite3.Row to a plain dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    payload, errors = validate_book(data)
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (payload["title"], payload["author"], payload.get("year"), payload.get("isbn")),
    )
    db.commit()
    book_id = cur.lastrowid
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(row_to_book(row)), 201


@app.route("/books", methods=["GET"])
def list_books():
    author = request.args.get("author")
    db = get_db()
    if author:
        rows = db.execute(
            "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
    return jsonify([row_to_book(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(row_to_book(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    payload, errors = validate_book(data, partial=True)
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404

    merged = {
        "title": payload.get("title", row["title"]),
        "author": payload.get("author", row["author"]),
        "year": payload.get("year", row["year"]),
        "isbn": payload.get("isbn", row["isbn"]),
    }
    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(row_to_book(updated)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return jsonify({"message": "Book deleted", "id": book_id}), 200


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
