"""Book collection REST API service.

Provides CRUD endpoints for books backed by SQLite.
"""
import os
import sqlite3

from flask import Flask, g, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BOOKS_DB_PATH", os.path.join(BASE_DIR, "books.db"))

app = Flask(__name__)


def get_db():
    """Return a SQLite connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the books table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    try:
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
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_payload(data, partial=False):
    """Validate book payload. Returns (errors, cleaned_data)."""
    errors = {}
    if not isinstance(data, dict):
        return ({"payload": "JSON object required"}, {})

    title = data.get("title")
    author = data.get("author")
    year = data.get("year")
    isbn = data.get("isbn")

    if not partial:
        if not title or not str(title).strip():
            errors["title"] = "title is required"
        if not author or not str(author).strip():
            errors["author"] = "author is required"
    else:
        if "title" in data and (not title or not str(title).strip()):
            errors["title"] = "title must not be empty"
        if "author" in data and (not author or not str(author).strip()):
            errors["author"] = "author must not be empty"

    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            errors["year"] = "year must be an integer"

    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "isbn must be a string"

    cleaned = {}
    if "title" in data:
        cleaned["title"] = str(data["title"]).strip() if title else ""
    if "author" in data:
        cleaned["author"] = str(data["author"]).strip() if author else ""
    if year is not None and "year" in data:
        cleaned["year"] = year
    if "isbn" in data:
        cleaned["isbn"] = isbn

    return errors, cleaned


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True)
    errors, cleaned = validate_payload(data, partial=False)
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (
            cleaned.get("title"),
            cleaned.get("author"),
            cleaned.get("year"),
            cleaned.get("isbn"),
        ),
    )
    db.commit()
    book_id = cur.lastrowid
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(row_to_dict(row)), 201


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
    return jsonify([row_to_dict(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(row_to_dict(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True)
    errors, cleaned = validate_payload(data, partial=True)
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404

    title = cleaned.get("title", row["title"])
    author = cleaned.get("author", row["author"])
    year = cleaned.get("year", row["year"])
    isbn = cleaned.get("isbn", row["isbn"])

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(row_to_dict(row)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return jsonify({"deleted": book_id}), 200


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
