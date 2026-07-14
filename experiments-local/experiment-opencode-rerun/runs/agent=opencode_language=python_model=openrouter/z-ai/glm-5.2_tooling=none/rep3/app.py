import os
import sqlite3

from flask import Flask, g, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "books.db")

app = Flask(__name__)


def db_path():
    return os.environ.get("BOOKS_DB_PATH", DEFAULT_DB_PATH)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(db_path())
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path=None):
    if path is None:
        path = db_path()
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True) or {}
    errors = []
    if not data.get("title"):
        errors.append("title is required")
    if not data.get("author"):
        errors.append("author is required")
    if errors:
        return jsonify({"errors": errors}), 400

    title = str(data["title"]).strip()
    author = str(data["author"]).strip()
    year = data.get("year")
    isbn = data.get("isbn")

    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            return jsonify({"errors": ["year must be an integer"]}), 400
    if isbn is not None:
        isbn = str(isbn).strip()

    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (title, author, year, isbn),
    )
    db.commit()
    book_id = cur.lastrowid
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(to_dict(row)), 201


@app.route("/books", methods=["GET"])
def list_books():
    author = request.args.get("author")
    db = get_db()
    if author:
        rows = db.execute(
            "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
    return jsonify([to_dict(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(to_dict(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404

    data = request.get_json(silent=True) or {}
    title = row["title"]
    author = row["author"]
    year = row["year"]
    isbn = row["isbn"]

    errors = []
    if "title" in data:
        if not str(data["title"]).strip():
            errors.append("title must not be empty")
        else:
            title = str(data["title"]).strip()
    if "author" in data:
        if not str(data["author"]).strip():
            errors.append("author must not be empty")
        else:
            author = str(data["author"]).strip()
    if "year" in data and data["year"] is not None:
        try:
            year = int(data["year"])
        except (TypeError, ValueError):
            errors.append("year must be an integer")
    if "isbn" in data and data["isbn"] is not None:
        isbn = str(data["isbn"]).strip()

    if errors:
        return jsonify({"errors": errors}), 400

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(to_dict(row)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return "", 204


def main():
    init_db()
    app.run(host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
