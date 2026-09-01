"""Books REST API built entirely with the Python standard library.

Endpoints:
    GET    /health          -> service health check
    GET    /books           -> list all books (optional ?author= filter)
    POST   /books           -> create a book
    GET    /books/{id}      -> fetch a single book
    PUT    /books/{id}      -> update a book
    DELETE /books/{id}      -> delete a book

Books are stored in SQLite. The database location can be configured with the
BOOKS_DB environment variable (defaults to books.db next to this file).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.environ.get("BOOKS_DB", "books.db"),
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

_BOOK_ID_PATTERN = re.compile(r"^/books/([^/]+)$")


class ValidationError(Exception):
    """Raised when a book payload fails validation."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


class _BadPayload(Exception):
    """Internal signal: the request body could not be turned into a payload."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def validate_book_payload(data):
    """Validate a JSON payload for create/update and return clean fields.

    Rules:
      * the payload must be a JSON object
      * title and author are required non-empty strings
      * year, when present and not null, must be an integer (bools rejected)
      * isbn, when present and not null, must be a string
      * unknown fields are ignored

    Raises ValidationError (with a list of human-readable messages) or
    returns a dict with keys: title, author, year, isbn.
    """
    if not isinstance(data, dict):
        raise ValidationError(["Request body must be a JSON object."])

    errors = []

    def clean_text(field, required):
        value = data.get(field)
        if value is None:
            if required:
                errors.append(f"'{field}' is required.")
            return None
        if not isinstance(value, str):
            errors.append(f"'{field}' must be a string.")
            return None
        value = value.strip()
        if required and not value:
            errors.append(f"'{field}' must not be empty.")
            return None
        return value

    title = clean_text("title", required=True)
    author = clean_text("author", required=True)

    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("'year' must be an integer.")

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("'isbn' must be a string.")

    if errors:
        raise ValidationError(errors)

    return {"title": title, "author": author, "year": year, "isbn": isbn}


class BookStore:
    """SQLite-backed storage for books.

    Every operation opens its own connection, so a single instance can safely
    be shared by the server's worker threads.
    """

    def __init__(self, db_path=_DEFAULT_DB_PATH):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def init_schema(self):
        with closing(self._connect()) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    @staticmethod
    def _as_book(row):
        if row is None:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "year": row[3],
            "isbn": row[4],
        }

    @staticmethod
    def _get_with(conn, book_id):
        row = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        return BookStore._as_book(row)

    def create(self, fields):
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (fields["title"], fields["author"], fields["year"], fields["isbn"]),
            )
            conn.commit()
            return self._get_with(conn, cur.lastrowid)

    def get(self, book_id):
        with closing(self._connect()) as conn:
            return self._get_with(conn, book_id)

    def list(self, author=None):
        query = "SELECT id, title, author, year, isbn FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ?"
            params = (author,)
        query += " ORDER BY id"
        with closing(self._connect()) as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._as_book(row) for row in rows]

    def update(self, book_id, fields):
        with closing(self._connect()) as conn:
            if self._get_with(conn, book_id) is None:
                return None
            conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (fields["title"], fields["author"], fields["year"], fields["isbn"], book_id),
            )
            conn.commit()
            return self._get_with(conn, book_id)

    def delete(self, book_id):
        with closing(self._connect()) as conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
            return cur.rowcount > 0


class BookAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the books API.

    The handler class (or a per-server subclass) must expose a `store`
    attribute holding a BookStore instance.
    """

    store = None
    server_version = "BooksAPI/1.0"

    # ------------------------------------------------------------------ #
    # Routing
    # ------------------------------------------------------------------ #
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            return self._route_health(method)
        if path in ("/books", "/books/"):
            return self._route_books(method, parsed)
        match = _BOOK_ID_PATTERN.match(path)
        if match:
            return self._route_book(method, match.group(1))

        self._send_json(404, {"error": "Not found."})

    def _route_health(self, method):
        if method != "GET":
            return self._send_405("GET")
        self._send_json(200, {"status": "ok"})

    def _route_books(self, method, parsed):
        if method == "POST":
            return self._handle_create()
        if method == "GET":
            values = parse_qs(parsed.query).get("author")
            author = values[0] if values else None
            return self._send_json(200, self.store.list(author=author))
        self._send_405("GET, POST")

    def _route_book(self, method, raw_id):
        try:
            book_id = int(raw_id)
        except ValueError:
            return self._send_json(404, {"error": "Not found."})

        if method == "GET":
            book = self.store.get(book_id)
            if book is None:
                return self._send_json(404, {"error": f"Book {book_id} not found."})
            return self._send_json(200, book)
        if method == "PUT":
            return self._handle_update(book_id)
        if method == "DELETE":
            return self._handle_delete(book_id)
        self._send_405("GET, PUT, DELETE")

    # ------------------------------------------------------------------ #
    # Endpoint implementations
    # ------------------------------------------------------------------ #
    def _handle_create(self):
        try:
            fields = self._read_json_payload()
        except _BadPayload as exc:
            return self._send_json(400, {"errors": exc.errors})
        book = self.store.create(fields)
        self._send_json(201, book, headers={"Location": f"/books/{book['id']}"})

    def _handle_update(self, book_id):
        if self.store.get(book_id) is None:
            return self._send_json(404, {"error": f"Book {book_id} not found."})
        try:
            fields = self._read_json_payload()
        except _BadPayload as exc:
            return self._send_json(400, {"errors": exc.errors})
        self._send_json(200, self.store.update(book_id, fields))

    def _handle_delete(self, book_id):
        if not self.store.delete(book_id):
            return self._send_json(404, {"error": f"Book {book_id} not found."})
        self._send_no_content()

    # ------------------------------------------------------------------ #
    # Request/response helpers
    # ------------------------------------------------------------------ #
    def _read_json_payload(self):
        length_header = self.headers.get("Content-Length")
        try:
            length = int(length_header) if length_header is not None else 0
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""

        if not raw:
            raise _BadPayload(["A JSON request body is required."])
        try:
            data = json.loads(raw)
        except (UnicodeDecodeError, ValueError):
            raise _BadPayload(["Request body must be valid JSON."])
        try:
            return validate_book_payload(data)
        except ValidationError as exc:
            raise _BadPayload(exc.errors)

    def _send_json(self, status, payload, headers=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_no_content(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_405(self, allow):
        self._send_json(405, {"error": "Method not allowed."}, headers={"Allow": allow})

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass  # keep server output quiet


def create_server(host="127.0.0.1", port=8000, db_path=None):
    """Create (but do not start) a Books API HTTP server."""
    store = BookStore(db_path if db_path is not None else _DEFAULT_DB_PATH)
    store.init_schema()
    handler = type("BoundBookAPIHandler", (BookAPIHandler,), {"store": store})
    return ThreadingHTTPServer((host, port), handler)


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", _DEFAULT_DB_PATH)
    server = create_server(host, port, db_path)
    print(f"Books API listening on http://{host}:{port} (db: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
