import os
import sqlite3

from flask import Flask, g, jsonify, request

from db import connect, init_db

REQUIRED_FIELDS = ("title", "author")


def create_app(database_path=None):
    if database_path is None:
        database_path = os.environ.get("BOOKS_DB", "books.db")

    app = Flask(__name__)
    app.config["DATABASE"] = database_path

    with app.app_context():
        init_db(app.config["DATABASE"])

    def get_db():
        if "db" not in g:
            g.db = connect(app.config["DATABASE"])
        return g.db

    @app.teardown_appcontext
    def close_db(exception):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.errorhandler(sqlite3.Error)
    def handle_db_error(exception):
        return jsonify({"error": "Database error"}), 500

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/books")
    def list_books():
        author = request.args.get("author", "").strip()
        if author:
            rows = get_db().execute(
                "SELECT * FROM books WHERE lower(author) LIKE lower(?) ORDER BY id",
                (f"%{author}%",),
            ).fetchall()
        else:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        error = validate_book(data)
        if error is not None:
            return error
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn")),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(dict(row)), 201

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found"}), 404
        return jsonify(dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        conn = get_db()
        row = conn.execute(
            "SELECT id FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found"}), 404
        data = request.get_json(silent=True)
        error = validate_book(data)
        if error is not None:
            return error
        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data.get("year"), data.get("isbn"), book_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(dict(row))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        conn = get_db()
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": f"Book {book_id} not found"}), 404
        return "", 204

    return app


def validate_book(data):
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400
    for field in REQUIRED_FIELDS:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return jsonify({"error": f"'{field}' is required and must be a non-empty string"}), 400
        if not isinstance(value, str):
            return jsonify({"error": f"'{field}' must be a string"}), 400
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return jsonify({"error": "'year' must be an integer"}), 400
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return jsonify({"error": "'isbn' must be a string"}), 400
    return None


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
