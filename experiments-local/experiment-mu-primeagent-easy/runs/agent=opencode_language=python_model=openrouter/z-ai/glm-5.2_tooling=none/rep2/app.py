"""Book collection REST API backed by SQLite."""

import os
import sqlite3

from flask import Flask, g, jsonify, request

app = Flask(__name__)

DB_PATH = os.environ.get("BOOKS_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db"))
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
    """Return a SQLite connection bound to the current request context."""
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path=DB_PATH):
    """Create the schema at the given path (safe to call repeatedly)."""
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def serialize(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book(data):
    """Return a list of validation error messages for the given payload."""
    errors = []
    if not isinstance(data, dict):
        errors.append("request body must be a JSON object")
        return errors
    if not data.get("title"):
        errors.append("title is required")
    if not data.get("author"):
        errors.append("author is required")
    year = data.get("year")
    if year is not None:
        try:
            int(year)
        except (ValueError, TypeError):
            errors.append("year must be an integer")
    return errors


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True)
    errors = validate_book(data)
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (
            data["title"],
            data["author"],
            int(data["year"]) if data.get("year") is not None else None,
            data.get("isbn"),
        ),
    )
    db.commit()
    book = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(serialize(book)), 201


@app.route("/books", methods=["GET"])
def list_books():
    db = get_db()
    author = request.args.get("author")
    if author:
        rows = db.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
    return jsonify([serialize(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(serialize(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True)
    errors = validate_book(data)
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (
            data["title"],
            data["author"],
            int(data["year"]) if data.get("year") is not None else None,
            data.get("isbn"),
            book_id,
        ),
    )
    db.commit()
    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(serialize(updated)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return "", 204


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_e):
    return jsonify({"error": "method not allowed"}), 405


def main():
    init_db()
    app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "5000")))


if __name__ == "__main__":
    main()
