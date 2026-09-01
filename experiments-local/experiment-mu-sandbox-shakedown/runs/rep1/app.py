"""REST API service for managing a book collection.

Built entirely with the Python standard library:
  * http.server  - HTTP server
  * sqlite3      - embedded storage
  * json         - (de)serialization

Endpoints:
  GET    /health          -> 200 {"status": "ok"}
  POST   /books           -> 201 created book | 400 invalid payload
  GET    /books           -> 200 list of books (supports ?author= filter)
  GET    /books/{id}      -> 200 book | 404
  PUT    /books/{id}      -> 200 updated book | 400 invalid payload | 404
  DELETE /books/{id}      -> 204 | 404
"""

import json
import os
import re
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")
DEFAULT_PORT = int(os.environ.get("PORT", "8000"))

_BOOK_ID_RE = re.compile(r"^/books/(\d+)$")


class ValidationError(ValueError):
    """Raised when a request payload fails validation."""


def validate_book_payload(data):
    """Validate a book payload and return (title, author, year, isbn).

    Both POST and PUT replace the full resource, so 'title' and 'author'
    are mandatory non-empty strings. 'year' (optional) must be a JSON
    integer and 'isbn' (optional) must be a string.
    """
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")

    title = data.get("title")
    author = data.get("author")
    year = data.get("year")
    isbn = data.get("isbn")

    if not isinstance(title, str) or not title.strip():
        raise ValidationError("'title' is required and must be a non-empty string")
    if not isinstance(author, str) or not author.strip():
        raise ValidationError("'author' is required and must be a non-empty string")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        raise ValidationError("'year' must be an integer")
    if isbn is not None and not isinstance(isbn, str):
        raise ValidationError("'isbn' must be a string")

    return title.strip(), author.strip(), year, isbn


class BookDatabase:
    """SQLite-backed store for books. Safe for concurrent use because a
    fresh connection is opened per operation."""

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )
    """

    def __init__(self, path=DEFAULT_DB_PATH):
        self.path = path
        with closing(self._connect()) as conn:
            conn.execute(self._SCHEMA)
            conn.commit()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _to_book(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def insert(self, title, author, year, isbn):
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (title, author, year, isbn),
            )
            conn.commit()
            return {
                "id": cur.lastrowid,
                "title": title,
                "author": author,
                "year": year,
                "isbn": isbn,
            }

    def list_books(self, author=None):
        query = "SELECT * FROM books"
        params = []
        if author:
            # Case-insensitive substring match on the author name.
            query += " WHERE lower(author) LIKE lower(?)"
            params.append(f"%{author}%")
        query += " ORDER BY id"
        with closing(self._connect()) as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._to_book(row) for row in rows]

    def get(self, book_id):
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            return self._to_book(row) if row else None

    def update(self, book_id, title, author, year, isbn):
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (title, author, year, isbn, book_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            return {
                "id": book_id,
                "title": title,
                "author": author,
                "year": year,
                "isbn": isbn,
            }

    def delete(self, book_id):
        with closing(self._connect()) as conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
            return cur.rowcount > 0


class BookAPIServer(ThreadingHTTPServer):
    """HTTP server carrying the book database."""

    daemon_threads = True

    def __init__(self, address, handler_class, database):
        super().__init__(address, handler_class)
        self.database = database


class BookAPIHandler(BaseHTTPRequestHandler):
    server_version = "BooksAPI/1.0"
    protocol_version = "HTTP/1.1"

    @property
    def db(self):
        return self.server.database

    # ------------------------------------------------------------------ #
    # Routing                                                            #
    # ------------------------------------------------------------------ #

    def do_GET(self):
        path = self._route_path()
        if path == "/health":
            self._send_json(200, {"status": "ok"})
        elif path == "/books":
            books = self.db.list_books(self._author_filter())
            self._send_json(200, books)
        else:
            book_id = self._book_id(path)
            if book_id is None:
                self._send_json(404, {"error": "Not found"})
                return
            book = self.db.get(book_id)
            if book is None:
                self._send_json(404, {"error": f"Book {book_id} not found"})
            else:
                self._send_json(200, book)

    def do_POST(self):
        path = self._route_path()
        if path == "/books":
            body = self._read_json()
            if body is None:
                return
            try:
                title, author, year, isbn = validate_book_payload(body)
            except ValidationError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            book = self.db.insert(title, author, year, isbn)
            self._send_json(
                201, book, extra_headers={"Location": f"/books/{book['id']}"}
            )
        else:
            self._drain_body()
            if self._book_id(path) is not None:
                self._send_json(
                    405,
                    {"error": "Method not allowed"},
                    extra_headers={"Allow": "GET, PUT, DELETE"},
                )
            else:
                self._send_json(404, {"error": "Not found"})

    def do_PUT(self):
        path = self._route_path()
        book_id = self._book_id(path)
        if book_id is None:
            self._drain_body()
            if path == "/books":
                self._send_json(
                    405,
                    {"error": "Method not allowed"},
                    extra_headers={"Allow": "GET, POST"},
                )
            else:
                self._send_json(404, {"error": "Not found"})
            return

        body = self._read_json()
        if body is None:
            return
        try:
            title, author, year, isbn = validate_book_payload(body)
        except ValidationError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        book = self.db.update(book_id, title, author, year, isbn)
        if book is None:
            self._send_json(404, {"error": f"Book {book_id} not found"})
        else:
            self._send_json(200, book)

    def do_DELETE(self):
        path = self._route_path()
        book_id = self._book_id(path)
        self._drain_body()
        if book_id is None:
            if path == "/books":
                self._send_json(
                    405,
                    {"error": "Method not allowed"},
                    extra_headers={"Allow": "GET, POST"},
                )
            else:
                self._send_json(404, {"error": "Not found"})
            return
        if self.db.delete(book_id):
            self._send_json(204)
        else:
            self._send_json(404, {"error": f"Book {book_id} not found"})

    def do_PATCH(self):
        self._drain_body()
        self._send_json(
            405,
            {"error": "Method not allowed"},
            extra_headers={"Allow": "GET, POST, PUT, DELETE"},
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _route_path(self):
        path = urlparse(self.path).path
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")
        return path or "/"

    @staticmethod
    def _book_id(path):
        match = _BOOK_ID_RE.match(path)
        return int(match.group(1)) if match else None

    def _author_filter(self):
        query = parse_qs(urlparse(self.path).query)
        values = query.get("author")
        return values[0] if values else None

    def _read_json(self):
        """Read and parse the JSON request body, responding with 400 on
        failure. Returns the parsed value or None if a response was sent."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            self._send_json(400, {"error": "Request body is required"})
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Invalid JSON in request body"})
            return None

    def _drain_body(self):
        """Consume an unread request body so keep-alive connections stay
        in sync."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > 0:
            self.rfile.read(length)

    def _send_json(self, status, payload=None, extra_headers=None):
        body = b""
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if payload is not None:
            self.wfile.write(body)


def main():
    database = BookDatabase(DEFAULT_DB_PATH)
    server = BookAPIServer(("0.0.0.0", DEFAULT_PORT), BookAPIHandler, database)
    print(f"Books API listening on http://0.0.0.0:{server.server_address[1]} "
          f"(db: {database.path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
