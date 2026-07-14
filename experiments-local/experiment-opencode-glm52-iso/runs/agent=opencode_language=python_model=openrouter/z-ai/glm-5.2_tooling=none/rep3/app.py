"""Book collection REST API."""
from flask import Flask, request, jsonify
import sqlite3
import os

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
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


def create_app():
    app = Flask(__name__)
    init_db()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True) or {}
        title = data.get("title")
        author = data.get("author")
        if not title or not author:
            return (
                jsonify({"error": "title and author are required"}),
                400,
            )
        year = data.get("year")
        isbn = data.get("isbn")

        conn = get_db_connection()
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        book_id = cur.lastrowid
        conn.commit()
        book = {
            "id": book_id,
            "title": title,
            "author": author,
            "year": year,
            "isbn": isbn,
        }
        conn.close()
        return jsonify(book), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        conn = get_db_connection()
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ?", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books").fetchall()
        conn.close()
        books = [dict(r) for r in rows]
        return jsonify(books), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        data = request.get_json(silent=True) or {}
        title = data.get("title")
        author = data.get("author")
        if not title or not author:
            return (
                jsonify({"error": "title and author are required"}),
                400,
            )
        year = data.get("year")
        isbn = data.get("isbn")

        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            conn.close()
            return jsonify({"error": "book not found"}), 404
        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id),
        )
        conn.commit()
        book = {
            "id": book_id,
            "title": title,
            "author": author,
            "year": year,
            "isbn": isbn,
        }
        conn.close()
        return jsonify(book), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            conn.close()
            return jsonify({"error": "book not found"}), 404
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "deleted"}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
