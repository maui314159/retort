"""Book Collection REST API.

A small REST service for managing a book collection, built entirely with the
Python standard library: ``http.server`` for HTTP and ``sqlite3`` for storage.

Endpoints:
    GET    /health       Health check.
    GET    /books        List books; optional ``?author=<text>`` filter.
    POST   /books        Create a book.
    GET    /books/{id}   Fetch one book.
    PUT    /books/{id}   Update a book (any subset of its fields).
    DELETE /books/{id}   Delete a book.

Configuration via environment variables:
    PORT      TCP port to listen on (default: 8000)
    HOST      Interface to bind (default: 0.0.0.0)
    BOOKS_DB  SQLite database file (default: books.db next to this file)
"""

import json
import os
import re
import sqlite3
import traceback
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""


class ApiError(Exception):
    """An error that maps directly to an HTTP error response."""

    def __init__(self, status: int, message: str, headers: dict | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers or {}


def validate_book_payload(payload, *, partial: bool = False):
    """Validate a JSON payload for a book.

    Returns ``(fields, errors)`` where ``fields`` maps column names to cleaned
    values and ``errors`` is a list of human-readable messages. With
    ``partial=True`` (updates) every field is optional; otherwise ``title``
    and ``author`` are required.
    """
    errors: list[str] = []
    fields: dict = {}
    if not isinstance(payload, dict):
        return fields, ["request body must be a JSON object"]

    for name in ("title", "author"):
        if name in payload:
            value = payload[name]
            if isinstance(value, str) and value.strip():
                fields[name] = value.strip()
            else:
                errors.append(f"'{name}' must be a non-empty string")
        elif not partial:
            errors.append(f"'{name}' is required")

    if "year" in payload:
        raw = payload["year"]
        if raw is None:
            fields["year"] = None
        elif isinstance(raw, bool):
            errors.append("'year' must be an integer")
        elif isinstance(raw, int):
            fields["year"] = raw
        elif isinstance(raw, str) and raw.strip().isdigit():
            fields["year"] = int(raw.strip())
        else:
            errors.append("'year' must be an integer")

    if "isbn" in payload:
        raw = payload["isbn"]
        if raw is None:
            fields["isbn"] = None
        elif isinstance(raw, str):
            fields["isbn"] = raw.strip()
        elif isinstance(raw, int) and not isinstance(raw, bool):
            fields["isbn"] = str(raw)
        else:
            errors.append("'isbn' must be a string")

    return fields, errors


class BookStore:
    """SQLite-backed storage for books. One connection per operation, so the
    store is safe to share across the server's worker threads."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _to_book(row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def create(self, *, title: str, author: str, year: int | None = None,
               isbn: str | None = None) -> dict:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (title, author, year, isbn),
            )
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return self._to_book(row)

    def list_books(self, author: str | None = None) -> list[dict]:
        query = "SELECT * FROM books"
        params: list = []
        if author:
            escaped = (
                author.lower()
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            query += " WHERE lower(author) LIKE ? ESCAPE '\\'"
            params.append(f"%{escaped}%")
        query += " ORDER BY id"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._to_book(row) for row in rows]

    def get(self, book_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return self._to_book(row) if row else None

    def update(self, book_id: int, fields: dict) -> dict | None:
        if not fields:
            return self.get(book_id)
        assignments = ", ".join(f"{column} = ?" for column in fields)
        params = list(fields.values()) + [book_id]
        with self._connect() as conn:
            cursor = conn.execute(f"UPDATE books SET {assignments} WHERE id = ?", params)
            if cursor.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return self._to_book(row)

    def delete(self, book_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0


class BookAPIHandler(BaseHTTPRequestHandler):
    """Routes HTTP requests to the BookStore attached to the server."""

    protocol_version = "HTTP/1.1"
    server_version = "BooksAPI/1.0"
    max_body_bytes = 1_000_000

    @property
    def store(self) -> BookStore:
        return self.server.store

    def do_GET(self) -> None:
        self._handle_request("GET")

    def do_POST(self) -> None:
        self._handle_request("POST")

    def do_PUT(self) -> None:
        self._handle_request("PUT")

    def do_DELETE(self) -> None:
        self._handle_request("DELETE")

    def _handle_request(self, method: str) -> None:
        try:
            self._dispatch(method)
        except ApiError as error:
            self._send_json(error.status, {"error": error.message}, error.headers)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception:
            traceback.print_exc()
            try:
                self._send_json(500, {"error": "internal server error"})
            except OSError:
                self.close_connection = True

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        body = self._read_body()

        if re.fullmatch(r"/health/?", path):
            if method != "GET":
                raise ApiError(405, "method not allowed", {"Allow": "GET"})
            self._send_json(200, {"status": "ok"})
            return

        if re.fullmatch(r"/books/?", path):
            if method == "GET":
                self._list_books(query)
            elif method == "POST":
                self._create_book(body)
            else:
                raise ApiError(405, "method not allowed", {"Allow": "GET, POST"})
            return

        match = re.fullmatch(r"/books/([^/]+)/?", path)
        if match:
            if method not in ("GET", "PUT", "DELETE"):
                raise ApiError(405, "method not allowed", {"Allow": "GET, PUT, DELETE"})
            try:
                book_id = int(unquote(match.group(1)))
            except ValueError:
                raise ApiError(404, "book not found")
            if method == "GET":
                self._get_book(book_id)
            elif method == "PUT":
                self._update_book(book_id, body)
            else:
                self._delete_book(book_id)
            return

        raise ApiError(404, "not found")

    def _read_body(self):
        transfer_encoding = (self.headers.get("Transfer-Encoding") or "").strip()
        if transfer_encoding and transfer_encoding.lower() != "identity":
            self.close_connection = True
            raise ApiError(411, "content-length required")
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            return None
        try:
            length = int(length_header)
        except ValueError:
            self.close_connection = True
            raise ApiError(400, "invalid content-length header")
        if length < 0:
            self.close_connection = True
            raise ApiError(400, "invalid content-length header")
        if length > self.max_body_bytes:
            if not self._drain_body(length):
                self.close_connection = True
            raise ApiError(413, "request body too large")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, "request body must be valid JSON")

    def _drain_body(self, length: int) -> bool:
        """Discard an oversized request body so the client can finish sending
        and read the error response. Returns False when the body exceeds the
        drain cap, in which case the connection must be closed."""
        drain_cap = 64 * 1024 * 1024
        to_read = min(length, drain_cap)
        while to_read > 0:
            chunk = self.rfile.read(min(65536, to_read))
            if not chunk:
                break
            to_read -= len(chunk)
        return length <= drain_cap

    def _list_books(self, query) -> None:
        values = query.get("author")
        author = values[0] if values else None
        self._send_json(200, self.store.list_books(author=author))

    def _create_book(self, body) -> None:
        fields, errors = validate_book_payload(body)
        if errors:
            raise ApiError(400, "; ".join(errors))
        book = self.store.create(
            title=fields["title"],
            author=fields["author"],
            year=fields.get("year"),
            isbn=fields.get("isbn"),
        )
        self._send_json(201, book, {"Location": f"/books/{book['id']}"})

    def _get_book(self, book_id: int) -> None:
        book = self.store.get(book_id)
        if book is None:
            raise ApiError(404, "book not found")
        self._send_json(200, book)

    def _update_book(self, book_id: int, body) -> None:
        if self.store.get(book_id) is None:
            raise ApiError(404, "book not found")
        fields, errors = validate_book_payload(body, partial=True)
        if errors:
            raise ApiError(400, "; ".join(errors))
        self._send_json(200, self.store.update(book_id, fields))

    def _delete_book(self, book_id: int) -> None:
        if not self.store.delete(book_id):
            raise ApiError(404, "book not found")
        self._send_json(204)

    def _send_json(self, status: int, payload=None, headers: dict | None = None) -> None:
        body = b""
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
        elif status not in (204, 304):
            self.send_header("Content-Length", "0")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", DEFAULT_DB_PATH)

    server = ThreadingHTTPServer((host, port), BookAPIHandler)
    server.store = BookStore(db_path)
    print(f"Book API listening on http://{host}:{port} (database: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
