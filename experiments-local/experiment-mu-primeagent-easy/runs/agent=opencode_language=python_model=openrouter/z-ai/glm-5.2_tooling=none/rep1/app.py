"""Book collection REST API service."""
import os
import sqlite3
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def get_db_path():
    """Return the configured database path."""
    return DB_PATH


def get_db():
    """Open a new SQLite connection for the current request."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the books table if it does not exist."""
    conn = get_db()
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


def row_to_book(row):
    """Convert a sqlite Row into a book dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(data, partial=False):
    """Validate incoming JSON. Returns (payload, error_message)."""
    if data is None:
        return None, "Request body must be JSON."
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    title = data.get("title")
    author = data.get("author")

    if not partial:
        if not title or not str(title).strip():
            return None, "title is required."
        if not author or not str(author).strip():
            return None, "author is required."
    else:
        if "title" in data and (not data["title"] or not str(data["title"]).strip()):
            return None, "title must not be empty."
        if "author" in data and (not data["author"] or not str(data["author"]).strip()):
            return None, "author must not be empty."

    payload = {}
    if "title" in data:
        payload["title"] = str(data["title"]).strip()
    if "author" in data:
        payload["author"] = str(data["author"]).strip()
    if "year" in data:
        year = data["year"]
        if year is not None:
            if not isinstance(year, int) or isinstance(year, bool):
                return None, "year must be an integer."
        payload["year"] = year
    if "isbn" in data:
        isbn = data["isbn"]
        if isbn is not None:
            isbn = str(isbn).strip()
        payload["isbn"] = isbn
    return payload, None


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    try:
        conn = get_db()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return jsonify({"status": "ok"}), 200
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"status": "error", "error": str(exc)}), 500


@app.route("/books", methods=["POST"])
def create_book():
    """Create a new book."""
    payload, err = validate_book_payload(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (payload["title"], payload["author"], payload.get("year"), payload.get("isbn")),
        )
        conn.commit()
        book_id = cur.lastrowid
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(row)), 201
    finally:
        conn.close()


@app.route("/books", methods=["GET"])
def list_books():
    """List all books, optionally filtered by author."""
    author = request.args.get("author")
    conn = get_db()
    try:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_book(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    """Get a single book by ID."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        return jsonify(row_to_book(row)), 200
    finally:
        conn.close()


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    """Update a book. All fields are required for full update."""
    payload, err = validate_book_payload(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                payload["title"],
                payload["author"],
                payload.get("year"),
                payload.get("isbn"),
                book_id,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(row)), 200
    finally:
        conn.close()


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    """Delete a book by ID."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        return "", 204
    finally:
        conn.close()


@app.errorhandler(404)
def handle_404(_exc):
    return jsonify({"error": "Not found."}), 404


@app.errorhandler(405)
def handle_405(_exc):
    return jsonify({"error": "Method not allowed."}), 405


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
