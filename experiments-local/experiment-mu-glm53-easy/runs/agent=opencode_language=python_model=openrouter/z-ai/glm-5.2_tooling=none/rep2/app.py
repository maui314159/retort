"""REST API for a book collection.

Why: satisfy TASK.md — CRUD + health, JSON responses, input validation, SQLite.
What: a stdlib-only HTTP service exposing /health and /books, delegating
      persistence to BookDB.

The request handling is split into a pure `dispatch` function (method, path,
query, body) so tests can exercise it without spinning up a socket server.
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from bookdb import BookDB


_BOOK_RE = re.compile(r"^/books/(\d+)$")


class APIError(Exception):
    """Raised by the handler for non-2xx responses."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _validate_book_payload(payload, *, partial=False):
    """Validate an incoming book JSON body.

    Why: title and author are required per TASK.md.
    What: in full-create mode both must be present and non-empty; in partial
          update mode only type correctness is checked for provided fields.
    Returns a cleaned dict with year coerced to int|None.
    """
    if not isinstance(payload, dict):
        raise APIError(400, "Request body must be a JSON object")

    cleaned = {}
    for key in ("title", "author", "isbn"):
        if key in payload:
            val = payload[key]
            if val is None and partial:
                continue
            if not isinstance(val, str):
                raise APIError(400, f"'{key}' must be a string")
            if key in ("title", "author") and not val.strip():
                raise APIError(400, f"'{key}' is required and must not be empty")
            cleaned[key] = val

    if "year" in payload and payload["year"] is not None:
        year = payload["year"]
        if isinstance(year, bool) or not isinstance(year, int):
            raise APIError(400, "'year' must be an integer")
        if year < 0:
            raise APIError(400, "'year' must be non-negative")
        cleaned["year"] = year
    elif partial:
        pass
    else:
        cleaned["year"] = None

    if not partial:
        if "title" not in cleaned:
            raise APIError(400, "'title' is required")
        if "author" not in cleaned:
            raise APIError(400, "'author' is required")
        cleaned.setdefault("isbn", None)

    return cleaned


class BookAPI:
    """Dispatches HTTP-style requests to the BookDB.

    Keeping this separate from BaseHTTPRequestHandler makes the API unit
    testable without sockets.
    """

    def __init__(self, db=None):
        self.db = db or BookDB()

    def dispatch(self, method, path, query=None, body=None):
        """Return (status_code, response_body_obj_or_None).

        `query` is a dict of parsed query params; `body` is a parsed JSON
        object or None. Raises APIError for client errors.
        """
        parsed = urlparse(path)
        route = parsed.path
        params = query or {}

        if route == "/health" and method == "GET":
            return 200, {"status": "ok"}

        if route == "/books":
            if method == "GET":
                author = params.get("author", [None])[0]
                books = self.db.list(author=author)
                return 200, books
            if method == "POST":
                if body is None:
                    raise APIError(400, "Request body is required")
                cleaned = _validate_book_payload(body, partial=False)
                new_id = self.db.insert(
                    cleaned["title"],
                    cleaned["author"],
                    cleaned.get("year"),
                    cleaned.get("isbn"),
                )
                created = self.db.get(new_id)
                return 201, created

        m = _BOOK_RE.match(route)
        if m:
            book_id = int(m.group(1))
            if method == "GET":
                book = self.db.get(book_id)
                if book is None:
                    raise APIError(404, f"Book {book_id} not found")
                return 200, book
            if method == "PUT":
                if body is None:
                    raise APIError(400, "Request body is required")
                cleaned = _validate_book_payload(body, partial=True)
                updated = self.db.update(book_id, cleaned)
                if updated is None:
                    raise APIError(404, f"Book {book_id} not found")
                return 200, updated
            if method == "DELETE":
                existed = self.db.delete(book_id)
                if not existed:
                    raise APIError(404, f"Book {book_id} not found")
                return 204, None

        raise APIError(404, "Not found")


class BookHTTPRequestHandler(BaseHTTPRequestHandler):
    """Thin adapter: parse HTTP -> call BookAPI.dispatch -> write response."""

    api = None  # set on the class before serve_forever

    def log_message(self, *args):
        pass  # silence default stderr logging

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return None
        raw = self.rfile.read(length)
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise APIError(400, "Invalid JSON body")

    def _write(self, status, payload):
        if payload is None:
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            body = None
            if method in ("POST", "PUT"):
                body = self._read_body()
            status, payload = self.api.dispatch(method, parsed.path, query, body)
        except APIError as e:
            status, payload = e.status, {"error": e.message}
        except Exception:
            status, payload = 500, {"error": "Internal server error"}
        self._write(status, payload)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")


def make_server(host="127.0.0.1", port=8000, db_path=":memory:"):
    """Build a ThreadingHTTPServer wired to a fresh BookDB.

    Useful for `python app.py` and for tests that want a live socket.
    """
    db = BookDB(db_path)
    api = BookAPI(db=db)
    handler = type(
        "BoundHandler",
        (BookHTTPRequestHandler,),
        {"api": api},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.api = api
    server.db = db
    return server


def main():
    import argparse

    p = argparse.ArgumentParser(description="Book collection REST API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument(
        "--db", default="books.db", help="SQLite path (default: books.db)"
    )
    args = p.parse_args()

    server = make_server(host=args.host, port=args.port, db_path=args.db)
    print(f"Book API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
