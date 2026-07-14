"""Book collection REST API service."""
import sqlite3
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_PATH = "books.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
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
    conn.close()


def serialize_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book(data, partial=False):
    errors = {}
    if not partial or "title" in data:
        if not data.get("title"):
            errors["title"] = "title is required"
    if not partial or "author" in data:
        if not data.get("author"):
            errors["author"] = "author is required"
    if "year" in data and data["year"] is not None:
        if not isinstance(data["year"], int):
            errors["year"] = "year must be an integer"
    return errors


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True) or {}
    errors = validate_book(data)
    if errors:
        return jsonify({"errors": errors}), 400
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (data["title"], data["author"], data.get("year"), data.get("isbn")),
    )
    conn.commit()
    book_id = cur.lastrowid
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return jsonify(serialize_book(row)), 201


@app.route("/books", methods=["GET"])
def list_books():
    author = request.args.get("author")
    conn = get_db()
    if author:
        rows = conn.execute(
            "SELECT * FROM books WHERE author = ?", (author,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return jsonify([serialize_book(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(serialize_book(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "book not found"}), 404
    errors = validate_book(data, partial=True)
    if errors:
        conn.close()
        return jsonify({"errors": errors}), 400
    title = data.get("title", row["title"])
    author = data.get("author", row["author"])
    year = data.get("year", row["year"])
    isbn = data.get("isbn", row["isbn"])
    conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return jsonify(serialize_book(row)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "book not found"}), 404
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    return "", 204


init_db()


if __name__ == "__main__":
    app.run(debug=True)
