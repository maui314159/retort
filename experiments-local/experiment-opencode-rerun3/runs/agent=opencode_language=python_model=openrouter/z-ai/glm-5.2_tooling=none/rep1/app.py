import sqlite3
from flask import Flask, request, jsonify, g

DATABASE = "books.db"

app = Flask(__name__)


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
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


def validate_book(data):
    errors = {}
    if not data.get("title") or not str(data.get("title")).strip():
        errors["title"] = "title is required"
    if not data.get("author") or not str(data.get("author")).strip():
        errors["author"] = "author is required"
    year = data.get("year")
    if year is not None:
        try:
            year_int = int(year)
            if year_int < 0 or year_int > 9999:
                errors["year"] = "year must be a valid integer between 0 and 9999"
        except (ValueError, TypeError):
            errors["year"] = "year must be an integer"
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
    data = request.get_json(silent=True) or {}
    errors = validate_book(data)
    if errors:
        return jsonify({"errors": errors}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (
            data["title"],
            data["author"],
            int(data["year"]) if data.get("year") is not None else None,
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
        return jsonify({"error": "book not found"}), 404
    return jsonify(serialize_book(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    merged = {
        "title": data.get("title", row["title"]),
        "author": data.get("author", row["author"]),
        "year": data.get("year", row["year"]),
        "isbn": data.get("isbn", row["isbn"]),
    }
    errors = validate_book(merged)
    if errors:
        return jsonify({"errors": errors}), 400
    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (
            merged["title"],
            merged["author"],
            int(merged["year"]) if merged["year"] is not None else None,
            merged["isbn"],
            book_id,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(serialize_book(row)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return jsonify({"message": "deleted"}), 200


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
