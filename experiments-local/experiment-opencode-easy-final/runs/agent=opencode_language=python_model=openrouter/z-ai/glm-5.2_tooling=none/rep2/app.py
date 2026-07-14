import sqlite3
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DB_PATH = "books.db"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    errors = []
    if not isinstance(data, dict):
        return ["Request body must be a JSON object"]

    if not partial or "title" in data:
        title = data.get("title")
        if not title or not isinstance(title, str) or not title.strip():
            errors.append("title is required and must be a non-empty string")

    if not partial or "author" in data:
        author = data.get("author")
        if not author or not isinstance(author, str) or not author.strip():
            errors.append("author is required and must be a non-empty string")

    if "year" in data and data["year"] is not None:
        if not isinstance(data["year"], int):
            errors.append("year must be an integer")

    if "isbn" in data and data["isbn"] is not None:
        if not isinstance(data["isbn"], str):
            errors.append("isbn must be a string")

    return errors


def serialize_book(row):
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
            data.get("year"),
            data.get("isbn"),
        ),
    )
    db.commit()
    book_id = cur.lastrowid
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(serialize_book(row)), 201


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
    return jsonify([serialize_book(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(serialize_book(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True)
    errors = validate_book_payload(data, partial=True)
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404

    title = data.get("title", row["title"])
    author = data.get("author", row["author"])
    year = data.get("year", row["year"])
    isbn = data.get("isbn", row["isbn"])

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(serialize_book(row)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
