"""Book collection REST API.

A small Flask service backed by SQLite that manages a collection of books.
"""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DATABASE = os.environ.get("BOOKS_DB", "books.db")

app = Flask(__name__)


def get_db():
    """Return a per-request SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(app.config.get("DATABASE", DATABASE))
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the books table if it does not exist."""
    db = sqlite3.connect(app.config.get("DATABASE", DATABASE))
    db.execute(
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
    db.commit()
    db.close()


def row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(data, require_fields=True):
    """Validate an incoming book payload.

    Returns (cleaned_data, errors). Title and author are required when
    ``require_fields`` is True.
    """
    errors = []
    if not isinstance(data, dict):
        return None, ["Request body must be a JSON object"]

    cleaned = {}

    title = data.get("title")
    author = data.get("author")

    if require_fields or "title" in data:
        if not title or not str(title).strip():
            errors.append("title is required")
        else:
            cleaned["title"] = str(title).strip()

    if require_fields or "author" in data:
        if not author or not str(author).strip():
            errors.append("author is required")
        else:
            cleaned["author"] = str(author).strip()

    if "year" in data and data["year"] is not None:
        try:
            cleaned["year"] = int(data["year"])
        except (TypeError, ValueError):
            errors.append("year must be an integer")

    if "isbn" in data and data["isbn"] is not None:
        cleaned["isbn"] = str(data["isbn"]).strip()

    return cleaned, errors


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True)
    cleaned, errors = validate_book_payload(data)
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


@app.route("/books", methods=["GET"])
def list_books():
    db = get_db()
    author = request.args.get("author")
    if author:
        rows = db.execute(
            "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
    return jsonify([row_to_book(row) for row in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(row_to_book(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404

    data = request.get_json(silent=True)
    cleaned, errors = validate_book_payload(data, require_fields=False)
    if errors:
        return jsonify({"errors": errors}), 400

    # Fields not provided keep their existing values.
    title = cleaned.get("title", row["title"])
    author = cleaned.get("author", row["author"])
    year = cleaned.get("year", row["year"]) if "year" in data else row["year"]
    isbn = cleaned.get("isbn", row["isbn"]) if "isbn" in data else row["isbn"]

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(row_to_book(updated)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return "", 204


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
