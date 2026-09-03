"""Book Collection REST API.

A small Flask service for managing a book collection backed by SQLite.
"""

from flask import Flask, jsonify, request

from db import get_db, init_db, close_db

app = Flask(__name__)
app.teardown_appcontext(close_db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BOOK_FIELDS = ("title", "author", "year", "isbn")


def serialize_book(row):
    """Turn a sqlite3.Row into a JSON-friendly dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book(payload, partial=False):
    """Validate an incoming book payload.

    Returns (data, errors). When ``partial`` is True (used for PUT updates),
    only fields that are present are validated and required-field checks are
    relaxed so a client can update a subset of fields.
    """
    if not isinstance(payload, dict):
        return None, {"error": "Request body must be a JSON object."}

    data = {}
    errors = {}

    title = payload.get("title")
    if title is None and not partial:
        errors["title"] = "Title is required."
    elif title is not None:
        if not isinstance(title, str) or not title.strip():
            errors["title"] = "Title must be a non-empty string."
        else:
            data["title"] = title.strip()

    author = payload.get("author")
    if author is None and not partial:
        errors["author"] = "Author is required."
    elif author is not None:
        if not isinstance(author, str) or not author.strip():
            errors["author"] = "Author must be a non-empty string."
        else:
            data["author"] = author.strip()

    year = payload.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "Year must be an integer."
        elif year < 0 or year > 9999:
            errors["year"] = "Year must be between 0 and 9999."
        else:
            data["year"] = year

    isbn = payload.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str) or not isbn.strip():
            errors["isbn"] = "ISBN must be a non-empty string."
        else:
            data["isbn"] = isbn.strip()

    if not partial:
        # Ensure sensible defaults for optional fields on create.
        data.setdefault("year", None)
        data.setdefault("isbn", None)

    return data, errors


init_db()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    data, errors = validate_book(payload, partial=False)
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (data["title"], data["author"], data["year"], data["isbn"]),
    )
    db.commit()
    book = serialize_book(
        db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    )
    return jsonify(book), 201


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
        return jsonify({"error": "Book not found."}), 404
    return jsonify(serialize_book(row)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found."}), 404

    data, errors = validate_book(payload, partial=True)
    if errors:
        return jsonify({"errors": errors}), 400

    if not data:
        return jsonify({"error": "No valid fields to update."}), 400

    # Merge existing values with the new ones.
    merged = {
        "title": data.get("title", row["title"]),
        "author": data.get("author", row["author"]),
        "year": data.get("year", row["year"]),
        "isbn": data.get("isbn", row["isbn"]),
    }
    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
    )
    db.commit()
    updated = db.execute(
        "SELECT * FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return jsonify(serialize_book(updated)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found."}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return jsonify({"message": "Book deleted.", "id": book_id}), 200


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(err):
    return jsonify({"error": "Not found."}), 404


@app.errorhandler(405)
def method_not_allowed(err):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(500)
def server_error(err):
    return jsonify({"error": "Internal server error."}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000, debug=True)
