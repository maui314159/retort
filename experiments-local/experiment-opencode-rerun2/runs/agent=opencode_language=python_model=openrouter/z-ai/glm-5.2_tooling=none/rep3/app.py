import os
import sqlite3
from flask import Flask, request, jsonify, g

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
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


def validate_book_payload(data, partial=False):
    errors = {}
    if not isinstance(data, dict):
        return {"body": "expected a JSON object"}
    if not partial:
        if not data.get("title") or not str(data.get("title")).strip():
            errors["title"] = "title is required"
        if not data.get("author") or not str(data.get("author")).strip():
            errors["author"] = "author is required"
    else:
        if "title" in data and not str(data.get("title")).strip():
            errors["title"] = "title must not be empty"
        if "author" in data and not str(data.get("author")).strip():
            errors["author"] = "author must not be empty"
    if "year" in data and data["year"] is not None:
        try:
            year = int(data["year"])
            if year < 0 or year > 9999:
                errors["year"] = "year must be between 0 and 9999"
        except (TypeError, ValueError):
            errors["year"] = "year must be an integer"
    if "isbn" in data and data["isbn"] is not None and not isinstance(data["isbn"], str):
        errors["isbn"] = "isbn must be a string"
    return errors


def book_to_dict(row):
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
    data = request.get_json(silent=True)
    errors = validate_book_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (
            data["title"].strip(),
            data["author"].strip(),
            int(data["year"]) if data.get("year") is not None else None,
            data.get("isbn"),
        ),
    )
    db.commit()
    book_id = cur.lastrowid
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(book_to_dict(row)), 201


@app.route("/books", methods=["GET"])
def list_books():
    author = request.args.get("author")
    db = get_db()
    if author:
        rows = db.execute(
            "SELECT * FROM books WHERE author LIKE ? ORDER BY id",
            (f"%{author}%",),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
    return jsonify([book_to_dict(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(book_to_dict(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True)
    errors = validate_book_payload(data, partial=True)
    if errors:
        return jsonify({"errors": errors}), 400
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    title = data.get("title", row["title"])
    author = data.get("author", row["author"])
    year = data.get("year", row["year"])
    if year is not None:
        year = int(year)
    isbn = data.get("isbn", row["isbn"])
    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(book_to_dict(row)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)
