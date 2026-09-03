"""REST API service for managing a book collection.

Built with Flask and SQLite. Exposes CRUD endpoints for books plus a
health check. Run with ``python app.py`` or via the WSGI app
``create_app``.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from flask import Flask, g, jsonify, request


def create_app(db_path: str = "books.db") -> Flask:
    """Application factory.

    Args:
        db_path: Path to the SQLite database file. Use ``:memory:`` for an
            in-process database (handy for tests with a single worker).

    Returns:
        A configured Flask application instance.
    """

    app = Flask(__name__)
    app.config["DATABASE"] = db_path

    # ------------------------------------------------------------------ #
    # Database helpers
    # ------------------------------------------------------------------ #
    def init_db() -> None:
        db = sqlite3.connect(app.config["DATABASE"])
        try:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year  INTEGER,
                    isbn  TEXT
                )
                """
            )
            db.commit()
        finally:
            db.close()

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_exc: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        init_db()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate_payload(
        data: Any, *, partial: bool = False
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Validate an incoming JSON body for create/update.

        Returns a tuple of ``(errors, cleaned)``. ``errors`` is empty when the
        payload is valid. When ``partial`` is ``True`` (used by ``PUT``),
        omitted fields are skipped rather than reported as missing; present
        fields are still type/emptiness checked.
        """
        errors: dict[str, str] = {}
        if not isinstance(data, dict):
            errors["body"] = "Request body must be a JSON object."
            return errors, {}

        cleaned: dict[str, Any] = {}

        title = data.get("title")
        if "title" in data:
            if title is None or (isinstance(title, str) and title.strip() == ""):
                errors["title"] = "title must not be empty."
            elif not isinstance(title, str):
                errors["title"] = "title must be a string."
            else:
                cleaned["title"] = title.strip()
        elif not partial:
            errors["title"] = "title is required."

        author = data.get("author")
        if "author" in data:
            if author is None or (isinstance(author, str) and author.strip() == ""):
                errors["author"] = "author must not be empty."
            elif not isinstance(author, str):
                errors["author"] = "author must be a string."
            else:
                cleaned["author"] = author.strip()
        elif not partial:
            errors["author"] = "author is required."

        if "year" in data:
            year = data["year"]
            if isinstance(year, bool) or not isinstance(year, int):
                errors["year"] = "year must be an integer."
            elif year < 0:
                errors["year"] = "year must be a non-negative integer."
            else:
                cleaned["year"] = year

        if "isbn" in data:
            isbn = data["isbn"]
            if not isinstance(isbn, str):
                errors["isbn"] = "isbn must be a string."
            else:
                cleaned["isbn"] = isbn.strip()

        return errors, cleaned

    def serialize(book: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "year": book["year"],
            "isbn": book["isbn"],
        }

    # ------------------------------------------------------------------ #
    # Routes
    # ------------------------------------------------------------------ #
    @app.route("/health", methods=["GET"])
    def health() -> Any:
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book() -> Any:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON."}), 400

        errors, cleaned = validate_payload(data)
        if errors:
            return jsonify({"error": "Validation failed.", "details": errors}), 400

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
        return jsonify(serialize(book)), 201

    @app.route("/books", methods=["GET"])
    def list_books() -> Any:
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([serialize(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id: int) -> Any:
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        return jsonify(serialize(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id: int) -> Any:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON."}), 400

        db = get_db()
        existing = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found."}), 404

        errors, cleaned = validate_payload(data, partial=True)
        if errors:
            return jsonify({"error": "Validation failed.", "details": errors}), 400
        merged = {
            "title": cleaned.get("title", existing["title"]),
            "author": cleaned.get("author", existing["author"]),
            "year": cleaned.get("year", existing["year"]),
            "isbn": cleaned.get("isbn", existing["isbn"]),
        }
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                merged["title"],
                merged["author"],
                merged["year"],
                merged["isbn"],
                book_id,
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(serialize(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id: int) -> Any:
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


# Module-level app for ``flask run`` and direct execution.
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
