"""Books collection REST API built with Flask + SQLite."""
import os
from flask import Flask, request, jsonify

import db as db_mod

app = Flask(__name__)
app.config["DB_PATH"] = os.environ.get("BOOKS_DB_PATH", "books.db")
app.teardown_appcontext(db_mod.close_db)


def _row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _validate(payload):
    """Validate the incoming JSON payload.

    Returns (data, error_message). `data` is None when validation fails.
    """
    if not payload or not isinstance(payload, dict):
        return None, "Request body must be a JSON object."

    title = payload.get("title")
    author = payload.get("author")
    if not title or not str(title).strip():
        return None, "Field 'title' is required."
    if not author or not str(author).strip():
        return None, "Field 'author' is required."

    year = payload.get("year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            return None, "Field 'year' must be an integer."
        if year < 0 or year > 9999:
            return None, "Field 'year' is out of range."

    isbn = payload.get("isbn")
    if isbn is not None:
        isbn = str(isbn).strip() or None

    return {
        "title": str(title).strip(),
        "author": str(author).strip(),
        "year": year,
        "isbn": isbn,
    }, None


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    data, err = _validate(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400

    conn = db_mod.get_db()
    cur = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (data["title"], data["author"], data["year"], data["isbn"]),
    )
    conn.commit()
    book_id = cur.lastrowid
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(_row_to_book(row)), 201


@app.route("/books", methods=["GET"])
def list_books():
    author = request.args.get("author")
    conn = db_mod.get_db()
    if author:
        rows = conn.execute(
            "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return jsonify([_row_to_book(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    conn = db_mod.get_db()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(_row_to_book(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data, err = _validate(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400

    conn = db_mod.get_db()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404

    conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (data["title"], data["author"], data["year"], data["isbn"], book_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(_row_to_book(row)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    conn = db_mod.get_db()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    return "", 204


@app.errorhandler(404)
def not_found(_err):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_err):
    return jsonify({"error": "Method not allowed"}), 405


if __name__ == "__main__":
    db_mod.init_db()
    app.run(host="127.0.0.1", port=8000, debug=True)
