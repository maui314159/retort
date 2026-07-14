"""REST API service for managing a book collection.

Built with Flask and the stdlib `sqlite3` module. Data is stored in a
local SQLite database file whose path can be overridden with the
``BOOKS_DB_PATH`` environment variable (useful for tests).
"""
import os
import sqlite3

from flask import Flask, g, jsonify, request


def _db_path() -> str:
    return os.environ.get("BOOKS_DB_PATH", "books.db")


def get_db() -> sqlite3.Connection:
    """Return a per-request SQLite connection cached on ``flask.g``."""
    if "db" not in g:
        g.db = sqlite3.connect(_db_path())
        g.db.row_factory = sqlite3.Row
        # Enforce FK / concurrency hygiene.
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db(path: str | None = None) -> None:
    """Create the schema if it does not yet exist.

    Safe to call multiple times. ``path`` overrides the env-derived path
    so callers (e.g. tests) can target a specific file.
    """
    target = path or _db_path()
    conn = sqlite3.connect(target)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _validate(body: dict | None) -> tuple[dict, str | None]:
    """Return (cleaned_body, error_message).

    ``title`` and ``author`` are required and must be non-empty strings.
    ``year`` and ``isbn`` are optional; ``year`` must be an integer if given.
    """
    if not isinstance(body, dict):
        return {}, "request body must be a JSON object"

    title = body.get("title")
    author = body.get("author")

    if not isinstance(title, str) or not title.strip():
        return {}, "title is required and must be a non-empty string"
    if not isinstance(author, str) or not author.strip():
        return {}, "author is required and must be a non-empty string"

    cleaned = {"title": title.strip(), "author": author.strip()}

    year = body.get("year")
    if year is not None:
        if not isinstance(year, int) or isinstance(year, bool):
            return {}, "year must be an integer if provided"
        cleaned["year"] = year
    else:
        cleaned["year"] = None

    isbn = body.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            return {}, "isbn must be a string if provided"
        cleaned["isbn"] = isbn.strip()
    else:
        cleaned["isbn"] = None

    return cleaned, None


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    @app.before_request
    def _ensure_schema() -> None:
        # Make sure the table exists even on a fresh DB file (e.g. tests
        # pointing at an empty temp file). Cheap and idempotent.
        init_db()

    @app.teardown_appcontext
    def _close_db(exc) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy"}), 200

    @app.post("/books")
    def create_book():
        body = request.get_json(silent=True)
        cleaned, err = _validate(body)
        if err is not None:
            return jsonify({"error": err}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (cleaned["title"], cleaned["author"], cleaned["year"], cleaned["isbn"]),
        )
        db.commit()
        book_id = cur.lastrowid
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(_row_to_book(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author is not None and author != "":
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_row_to_book(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(_row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        db = get_db()
        existing = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            return jsonify({"error": "book not found"}), 404

        body = request.get_json(silent=True)
        cleaned, err = _validate(body)
        if err is not None:
            return jsonify({"error": err}), 400

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (cleaned["title"], cleaned["author"], cleaned["year"], cleaned["isbn"], book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(_row_to_book(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        db = get_db()
        existing = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    @app.errorhandler(404)
    def _not_found(_):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def _method_not_allowed(_):
        return jsonify({"error": "method not allowed"}), 405

    return app


app = create_app()


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000, debug=False)
