"""Book collection REST API.

A small Flask application that stores books in SQLite and exposes
CRUD endpoints plus a health check.
"""
import os
import sqlite3
from flask import Flask, g, jsonify, request

app = Flask(__name__)

# Allow overriding the database path via environment variable so that
# tests can use an in-memory or temporary database.
DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def get_db():
    """Return a SQLite connection bound to the request context."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path=None):
    """Create the books table if it does not yet exist."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
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


@app.context_processor
def inject_setup():
    return {}


@app.before_request
def ensure_schema():
    # Make sure the table exists on every request so the app works even
    # if init_db() was never called (e.g. first run against an empty file).
    if "schema_initialized" not in g:
        init_db()
        g.schema_initialized = True


def serialize_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(data, partial=False):
    """Validate incoming JSON. Returns (payload, error_message)."""
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"
    title = data.get("title")
    author = data.get("author")
    if not partial:
        if not title or not str(title).strip():
            return None, "title is required"
        if not author or not str(author).strip():
            return None, "author is required"
    else:
        if "title" in data and (data["title"] is None or not str(data["title"]).strip()):
            return None, "title must not be blank"
        if "author" in data and (data["author"] is None or not str(data["author"]).strip()):
            return None, "author must not be blank"

    payload = {}
    if "title" in data:
        payload["title"] = str(data["title"]).strip()
    if "author" in data:
        payload["author"] = str(data["author"]).strip()
    if "year" in data:
        year = data["year"]
        if year is None:
            payload["year"] = None
        else:
            try:
                payload["year"] = int(year)
            except (TypeError, ValueError):
                return None, "year must be an integer"
    if "isbn" in data:
        payload["isbn"] = None if data["isbn"] is None else str(data["isbn"])
    return payload, None


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True)
    payload, err = validate_book_payload(data)
    if err:
        return jsonify({"error": err}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (payload["title"], payload["author"], payload.get("year"), payload.get("isbn")),
    )
    db.commit()
    book = db.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return jsonify(serialize_book(book)), 201


@app.route("/books", methods=["GET"])
def list_books():
    author = request.args.get("author")
    db = get_db()
    if author:
        rows = db.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
            (author,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT id, title, author, year, isbn FROM books ORDER BY id"
        ).fetchall()
    return jsonify([serialize_book(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = get_db()
    row = db.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
        (book_id,),
    ).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(serialize_book(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True)
    payload, err = validate_book_payload(data, partial=True)
    if err:
        return jsonify({"error": err}), 400

    db = get_db()
    row = db.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
        (book_id,),
    ).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404

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
    updated = db.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
        (book_id,),
    ).fetchone()
    return jsonify(serialize_book(updated)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return jsonify({"deleted": book_id}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
