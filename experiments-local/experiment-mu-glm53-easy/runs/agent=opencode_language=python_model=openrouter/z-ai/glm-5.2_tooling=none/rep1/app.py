"""Book collection REST API using Flask and SQLite."""

import os
import sqlite3
import uuid

from flask import Flask, current_app, g, jsonify, request

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def _connect(db_uri, uri):
    """Open a SQLite connection that obeys the shared-cache convention for
    in-memory databases (``:memory:``) so multiple connections see the same DB."""
    conn = sqlite3.connect(db_uri, uri=uri, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_db_uri(db_path):
    """Return ``(uri, is_memory)``. ``:memory:`` is converted to a shared-cache
    URI so separate connections in the same process see the same schema/data."""
    if db_path == ":memory:":
        return f"file:books_db_{uuid.uuid4().hex}?mode=memory&cache=shared", True
    return db_path, False


def create_app(db_path=None):
    """Application factory.

    Args:
        db_path: Path to the SQLite file. When ``None`` (default), falls back to
            the ``BOOKS_DB_PATH`` env var, then to ``books.db``. Passing
            ``:memory:`` makes the app suitable for tests.
    """
    app = Flask(__name__)
    if db_path is None:
        db_path = os.environ.get("BOOKS_DB_PATH", "books.db")
    uri, is_memory = _resolve_db_uri(db_path)
    app.config["DB_URI"] = uri
    app.config["DB_IS_MEMORY"] = is_memory

    @app.teardown_appcontext
    def close_db(exc):
        conn = getattr(g, "_db_conn", None)
        if conn is not None:
            conn.close()

    init_db(app)
    register_routes(app)
    return app


def get_db():
    """Return a per-request SQLite connection, opening one if necessary."""
    if "_db_conn" not in g.__dict__:
        g._db_conn = _connect(current_app.config["DB_URI"], uri=True)
    return g._db_conn


def init_db(app):
    """Create the schema if it does not already exist.

    For in-memory databases the connection opened here is kept alive for the
    lifetime of the app (stored on ``app.config``); otherwise the in-memory DB
    would be destroyed as soon as this connection closes.
    """
    conn = _connect(app.config["DB_URI"], uri=True)
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
    if app.config["DB_IS_MEMORY"]:
        app.config["_PIN_CONN"] = conn
    else:
        conn.close()


def book_from_row(row):
    """Serialize a sqlite3.Row into a JSON-friendly dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(data, partial=False):
    """Validate the request body for create/update.

    Args:
        data: Parsed JSON body (dict).
        partial: When ``True`` (PUT updates), allow missing fields.

    Returns:
        ``(payload, error_message)`` — ``error_message`` is ``None`` on success.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    payload = {}
    title = data.get("title")
    author = data.get("author")
    year = data.get("year")
    isbn = data.get("isbn")

    if partial:
        if title is None and author is None and year is None and isbn is None:
            return None, "No fields supplied to update."
    else:
        if not title or not str(title).strip():
            return None, "'title' is required."
        if not author or not str(author).strip():
            return None, "'author' is required."

    if title is not None:
        if not str(title).strip():
            return None, "'title' must not be empty."
        payload["title"] = str(title).strip()

    if author is not None:
        if not str(author).strip():
            return None, "'author' must not be empty."
        payload["author"] = str(author).strip()

    if year is not None:
        try:
            payload["year"] = int(year)
        except (TypeError, ValueError):
            return None, "'year' must be an integer."

    if isbn is not None:
        payload["isbn"] = str(isbn)

    return payload, None


def register_routes(app):
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        payload, err = validate_book_payload(data, partial=False)
        if err:
            return jsonify({"error": err}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (payload["title"], payload["author"], payload.get("year"), payload.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(book_from_row(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_from_row(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_from_row(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True)
        payload, err = validate_book_payload(data, partial=True)
        if err:
            return jsonify({"error": err}), 400

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
        return jsonify(book_from_row(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
