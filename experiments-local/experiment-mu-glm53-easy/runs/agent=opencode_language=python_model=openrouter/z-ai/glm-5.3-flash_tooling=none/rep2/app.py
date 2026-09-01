"""REST API for managing a book collection, backed by SQLite.

Endpoints:
    GET    /health          - health check
    POST   /books           - create a book (title, author required; year, isbn optional)
    GET    /books           - list books (optional ?author= filter)
    GET    /books/{id}      - fetch one book
    PUT    /books/{id}      - replace a book (title, author required; year, isbn optional)
    DELETE /books/{id}      - delete a book

Run with ``python app.py`` or ``flask --app app run``.
"""

import os

from flask import Blueprint, Flask, jsonify, request

from db import (
    fetch_book,
    fetch_books,
    init_db,
    insert_book,
    remove_book,
    replace_book,
)


class ValidationError(Exception):
    """Raised when a request payload fails validation."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or []


def validate_book_payload(data):
    """Validate a create/update payload and return cleaned fields.

    ``title`` and ``author`` are required non-empty strings. ``year`` is an
    optional integer (int or numeric string, coerced to int). ``isbn`` is an
    optional string. Unknown fields are ignored. Raises ValidationError with
    a list of human-readable problems when anything is wrong.
    """
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")

    details = []
    cleaned = {}

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        details.append("'title' is required and must be a non-empty string")
    else:
        cleaned["title"] = title.strip()

    author = data.get("author")
    if not isinstance(author, str) or not author.strip():
        details.append("'author' is required and must be a non-empty string")
    else:
        cleaned["author"] = author.strip()

    year = data.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, (int, str)):
            details.append("'year' must be an integer")
        elif isinstance(year, str):
            try:
                cleaned["year"] = int(year.strip())
            except ValueError:
                details.append("'year' must be an integer")
        else:
            cleaned["year"] = year

    isbn = data.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            details.append("'isbn' must be a string")
        else:
            cleaned["isbn"] = isbn.strip()

    if details:
        raise ValidationError("Validation failed", details)
    return cleaned


bp = Blueprint("books", __name__)


@bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@bp.post("/books")
def create_book():
    data = request.get_json(silent=True)
    if data is None:
        raise ValidationError(
            "Request body must be valid JSON with Content-Type: application/json"
        )
    fields = validate_book_payload(data)
    book_id = insert_book(
        fields["title"], fields["author"], fields.get("year"), fields.get("isbn")
    )
    return jsonify(fetch_book(book_id)), 201


@bp.get("/books")
def list_books():
    return jsonify(fetch_books(request.args.get("author"))), 200


@bp.get("/books/<int:book_id>")
def get_book(book_id):
    book = fetch_book(book_id)
    if book is None:
        return jsonify({"error": "Book not found", "details": []}), 404
    return jsonify(book), 200


@bp.put("/books/<int:book_id>")
def update_book(book_id):
    data = request.get_json(silent=True)
    if data is None:
        raise ValidationError(
            "Request body must be valid JSON with Content-Type: application/json"
        )
    # PUT replaces the whole resource: omitted year/isbn become null.
    fields = validate_book_payload(data)
    if not replace_book(
        book_id, fields["title"], fields["author"], fields.get("year"), fields.get("isbn")
    ):
        return jsonify({"error": "Book not found", "details": []}), 404
    return jsonify(fetch_book(book_id)), 200


@bp.delete("/books/<int:book_id>")
def delete_book(book_id):
    if not remove_book(book_id):
        return jsonify({"error": "Book not found", "details": []}), 404
    return "", 204


def create_app(database_path=None):
    """Application factory.

    ``database_path`` overrides the DATABASE config for testing; otherwise
    the DATABASE environment variable or ``<project dir>/books.db`` is used.
    """
    app = Flask(__name__)
    app.config["DATABASE"] = (
        database_path
        or os.environ.get("DATABASE")
        or os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")
    )
    init_db(app)
    app.register_blueprint(bp)

    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return jsonify({"error": err.message, "details": err.details}), 400

    @app.errorhandler(404)
    def handle_not_found(_err):
        return jsonify({"error": "Not found", "details": []}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_err):
        return jsonify({"error": "Method not allowed", "details": []}), 405

    @app.errorhandler(500)
    def handle_internal_error(_err):
        return jsonify({"error": "Internal server error", "details": []}), 500

    return app


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app = create_app()
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
