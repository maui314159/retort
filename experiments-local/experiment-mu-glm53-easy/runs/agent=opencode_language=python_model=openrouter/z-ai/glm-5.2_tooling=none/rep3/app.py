"""Book collection REST API built with Flask and SQLite."""

import os
import sqlite3
from flask import Flask, jsonify, request

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def get_db_connection(db_path=DB_PATH):
    """Return a SQLite connection configured for row-as-dict and FK support."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=DB_PATH):
    """Create the books table if it does not already exist."""
    conn = get_db_connection(db_path)
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


def create_app(db_path=DB_PATH):
    """Application factory. Uses an in-memory or file-backed SQLite DB."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path
    init_db(db_path)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify(status="ok"), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True) or {}
        errors = validate_book(data, partial=False)
        if errors:
            return jsonify(errors=errors), 400

        conn = get_db_connection(db_path)
        try:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data.get("year"), data.get("isbn")),
            )
            conn.commit()
            book = fetch_book(conn, cur.lastrowid)
            return jsonify(book), 201
        finally:
            conn.close()

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        conn = get_db_connection(db_path)
        try:
            if author:
                rows = conn.execute(
                    "SELECT * FROM books WHERE author = ? ORDER BY id",
                    (author,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            return jsonify([row_to_dict(r) for r in rows]), 200
        finally:
            conn.close()

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        conn = get_db_connection(db_path)
        try:
            book = fetch_book(conn, book_id)
            if book is None:
                return jsonify(error="Book not found"), 404
            return jsonify(book), 200
        finally:
            conn.close()

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        data = request.get_json(silent=True) or {}
        errors = validate_book(data, partial=True)
        if errors:
            return jsonify(errors=errors), 400
        if not data:
            return jsonify(errors={"body": "No fields to update"}), 400

        conn = get_db_connection(db_path)
        try:
            if fetch_book(conn, book_id) is None:
                return jsonify(error="Book not found"), 404

            fields = []
            values = []
            for key in ("title", "author", "year", "isbn"):
                if key in data:
                    fields.append(f"{key} = ?")
                    values.append(data[key])
            values.append(book_id)
            conn.execute(
                f"UPDATE books SET {', '.join(fields)} WHERE id = ?", tuple(values)
            )
            conn.commit()
            return jsonify(fetch_book(conn, book_id)), 200
        finally:
            conn.close()

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        conn = get_db_connection(db_path)
        try:
            if fetch_book(conn, book_id) is None:
                return jsonify(error="Book not found"), 404
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
            return "", 204
        finally:
            conn.close()

    @app.errorhandler(404)
    def handle_404(_):
        return jsonify(error="Not found"), 404

    @app.errorhandler(405)
    def handle_405(_):
        return jsonify(error="Method not allowed"), 405

    return app


def validate_book(data, partial=False):
    """Validate request body. Returns a dict of field -> message."""
    errors = {}
    if not partial or "title" in data:
        if not data.get("title") or not str(data["title"]).strip():
            errors["title"] = "Title is required"
    if not partial or "author" in data:
        if not data.get("author") or not str(data["author"]).strip():
            errors["author"] = "Author is required"
    if "year" in data and data["year"] is not None:
        try:
            int(data["year"])
        except (TypeError, ValueError):
            errors["year"] = "Year must be an integer"
    return errors


def fetch_book(conn, book_id):
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return row_to_dict(row) if row else None


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
