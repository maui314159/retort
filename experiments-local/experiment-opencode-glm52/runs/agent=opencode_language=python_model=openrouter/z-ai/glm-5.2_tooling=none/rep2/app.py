"""Book collection REST API.

A small Flask service backed by SQLite for managing a collection of books.
"""

import os
import sqlite3
from contextlib import closing

from flask import Flask, g, jsonify, request

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def get_db():
    """Return a SQLite connection bound to the current request context."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path=None):
    """Create the books table if it does not already exist.

    Accepts an optional ``db_path`` so tests can point at an isolated file
    without touching the module-level ``DB_PATH``.
    """
    path = db_path or DB_PATH
    with closing(sqlite3.connect(path)) as conn:
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


def create_app(db_path=None):
    """Application factory.

    ``db_path`` lets tests supply an isolated database path.
    """
    global DB_PATH
    if db_path is not None:
        DB_PATH = db_path

    app = Flask(__name__)
    app.teardown_appcontext(close_db)

    init_db()

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        author = (data.get("author") or "").strip()
        if not title or not author:
            return (
                jsonify(
                    error="title and author are required",
                    fields={"title": "required", "author": "required"},
                ),
                400,
            )

        year = data.get("year")
        if year is not None and not isinstance(year, int):
            return jsonify(error="year must be an integer"), 400
        if isinstance(year, bool):
            return jsonify(error="year must be an integer"), 400

        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            return jsonify(error="isbn must be a string"), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        db.commit()
        book_id = cur.lastrowid
        book = dict(
            db.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
        )
        return jsonify(book), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT id, title, author, year, isbn FROM books "
                "WHERE author = ? ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT id, title, author, year, isbn FROM books ORDER BY id"
            ).fetchall()
        return jsonify([dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        if row is None:
            return jsonify(error="book not found"), 404
        return jsonify(dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True) or {}
        db = get_db()
        row = db.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        if row is None:
            return jsonify(error="book not found"), 404

        title = (data.get("title") or "").strip()
        author = (data.get("author") or "").strip()
        if "title" in data and not title:
            return jsonify(error="title cannot be empty"), 400
        if "author" in data and not author:
            return jsonify(error="author cannot be empty"), 400

        year = data.get("year")
        if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
            return jsonify(error="year must be an integer"), 400

        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            return jsonify(error="isbn must be a string"), 400

        new_title = title if title else row["title"]
        new_author = author if author else row["author"]
        new_year = year if "year" in data else row["year"]
        new_isbn = isbn if "isbn" in data else row["isbn"]

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (new_title, new_author, new_year, new_isbn, book_id),
        )
        db.commit()
        updated = dict(
            db.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
        )
        return jsonify(updated), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT id FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify(error="book not found"), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return jsonify(status="deleted", id=book_id), 200

    return app


# Module-level app for `flask run` / `python app.py`.
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
