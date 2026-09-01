"""Book collection REST API.

A Flask service exposing CRUD endpoints for a book collection stored in
SQLite. Run with ``python app.py`` (see README.md for details).
"""

import os
import sqlite3

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from db import Database

BOOK_FIELDS = ("title", "author", "year", "isbn")


def create_app(config=None):
    """Create and configure the Flask application.

    ``config`` is an optional dict merged over the defaults. The database
    location defaults to the ``BOOKS_DB`` environment variable, falling
    back to ``books.db`` in the working directory; ``:memory:`` keeps the
    database in RAM (useful for tests).
    """
    app = Flask(__name__)
    app.config.setdefault("DATABASE", os.environ.get("BOOKS_DB", "books.db"))
    if config:
        app.config.update(config)

    db = Database(app.config["DATABASE"])
    app.extensions["books_db"] = db

    @app.get("/health")
    def health():
        try:
            db.ping()
        except sqlite3.Error:
            return jsonify({"status": "error"}), 503
        return jsonify({"status": "ok"})

    @app.get("/books")
    def list_books():
        author = request.args.get("author", "").strip()
        return jsonify(db.list_books(author=author or None))

    @app.post("/books")
    def create_book():
        data, error = _json_object_or_error()
        if error is not None:
            return error
        errors = validate_book_payload(data, partial=False)
        if errors:
            return _validation_error(errors)
        book = db.create_book(
            title=data["title"],
            author=data["author"],
            year=data.get("year"),
            isbn=data.get("isbn"),
        )
        return jsonify(book), 201

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = db.get_book(book_id)
        if book is None:
            return _not_found()
        return jsonify(book)

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data, error = _json_object_or_error()
        if error is not None:
            return error
        errors = validate_book_payload(data, partial=True)
        if errors:
            return _validation_error(errors)
        fields = {name: data[name] for name in BOOK_FIELDS if name in data}
        book = db.update_book(book_id, fields)
        if book is None:
            return _not_found()
        return jsonify(book)

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        if not db.delete_book(book_id):
            return _not_found()
        return "", 204

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        return jsonify({"error": exc.description or exc.name}), exc.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        return jsonify({"error": "Internal server error"}), 500

    return app


def validate_book_payload(data, partial):
    """Validate a book payload.

    ``title`` and ``author`` are required unless ``partial`` is true (used
    by PUT, where only supplied fields are validated). Returns a dict of
    field name -> error message; an empty dict means the payload is valid.
    """
    errors = {}
    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                errors[field] = f"{field} must be a non-empty string"
        elif not partial:
            errors[field] = f"{field} is required"
    if "year" in data and data["year"] is not None:
        year = data["year"]
        if isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "year must be an integer"
    if "isbn" in data and data["isbn"] is not None:
        if not isinstance(data["isbn"], str):
            errors["isbn"] = "isbn must be a string"
    return errors


def _json_object_or_error():
    """Parse the request body as a JSON object.

    Returns ``(data, None)`` on success, or ``(None, (response, status))``
    when the body is missing, is not valid JSON, or is not an object.
    """
    data = request.get_json(force=True, silent=True)
    if data is None:
        return None, (jsonify({"error": "Request body must be valid JSON"}), 400)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "Request body must be a JSON object"}), 400)
    return data, None


def _validation_error(details):
    return jsonify({"error": "Validation failed", "details": details}), 400


def _not_found():
    return jsonify({"error": "Book not found"}), 404


if __name__ == "__main__":
    application = create_app()
    application.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
