"""Book collection REST API.

A Flask service that manages a collection of books stored in SQLite.

Endpoints:
    GET    /health       Liveness/readiness probe.
    POST   /books        Create a book.
    GET    /books        List books (optional ?author= exact-match filter).
    GET    /books/<id>   Retrieve a single book.
    PUT    /books/<id>   Replace a book.
    DELETE /books/<id>   Delete a book.
"""

import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request

MIN_YEAR = 1
MAX_YEAR = 2200

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""


def default_db_path():
    """Resolve the SQLite file: BOOKS_DB_PATH env var, else books.db next to this module."""
    return os.environ.get(
        "BOOKS_DB_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db"),
    )


def _connect(db_path):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    """Create the books table if it does not exist yet."""
    conn = _connect(db_path)
    try:
        conn.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db():
    """Return a SQLite connection scoped to the current application context."""
    if "db" not in g:
        g.db = _connect(current_app.config["DB_PATH"])
    return g.db


def serialize_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def fetch_book(db, book_id):
    return db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()


def parse_year(value):
    """Coerce a JSON value to a year integer, or None when impossible."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        candidate = value.strip()
        if candidate and candidate.lstrip("+-").isdigit():
            return int(candidate)
    return None


def validate_book_payload(data):
    """Validate a book create/update payload.

    Returns an (errors, book) tuple: errors is a JSON-ready error object when
    the payload is invalid (book is then None), otherwise errors is None and
    book holds the normalised fields.
    """
    if not isinstance(data, dict):
        return (
            {"error": "Validation failed", "details": ["Request body must be a JSON object."]},
            None,
        )

    errors = []
    book = {"title": None, "author": None, "year": None, "isbn": None}

    for field in ("title", "author"):
        value = data.get(field)
        if value is None:
            errors.append(f"Field '{field}' is required.")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"Field '{field}' must be a non-empty string.")
        else:
            book[field] = value.strip()

    if data.get("year") is not None:
        year = parse_year(data["year"])
        if year is None:
            errors.append("Field 'year' must be an integer.")
        elif not MIN_YEAR <= year <= MAX_YEAR:
            errors.append(f"Field 'year' must be between {MIN_YEAR} and {MAX_YEAR}.")
        else:
            book["year"] = year

    isbn = data.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str) or not isbn.strip():
            errors.append("Field 'isbn' must be a non-empty string.")
        else:
            book["isbn"] = isbn.strip()

    if errors:
        return {"error": "Validation failed", "details": errors}, None
    return None, book


def book_not_found(book_id):
    return jsonify({"error": f"Book with id {book_id} not found."}), 404


def register_routes(app):
    @app.route("/health", methods=["GET"])
    def health():
        try:
            get_db().execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return jsonify({"status": "error"}), 503
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON."}), 400
        errors, book = validate_book_payload(data)
        if errors:
            return jsonify(errors), 400
        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book["title"], book["author"], book["year"], book["isbn"]),
        )
        db.commit()
        created = fetch_book(db, cursor.lastrowid)
        return (
            jsonify(serialize_book(created)),
            201,
            {"Location": f"/books/{created['id']}"},
        )

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author", "").strip()
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([serialize_book(row) for row in rows])

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        book = fetch_book(get_db(), book_id)
        if book is None:
            return book_not_found(book_id)
        return jsonify(serialize_book(book))

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        db = get_db()
        if fetch_book(db, book_id) is None:
            return book_not_found(book_id)
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON."}), 400
        errors, book = validate_book_payload(data)
        if errors:
            return jsonify(errors), 400
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (book["title"], book["author"], book["year"], book["isbn"], book_id),
        )
        db.commit()
        return jsonify(serialize_book(fetch_book(db, book_id)))

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cursor.rowcount == 0:
            return book_not_found(book_id)
        return "", 204


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request."}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({"error": "Internal server error."}), 500


def create_app(db_path=None):
    """Application factory. An explicit db_path overrides BOOKS_DB_PATH/default."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path if db_path is not None else default_db_path()
    init_db(app.config["DB_PATH"])

    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    register_routes(app)
    register_error_handlers(app)
    return app


if __name__ == "__main__":
    application = create_app()
    application.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
