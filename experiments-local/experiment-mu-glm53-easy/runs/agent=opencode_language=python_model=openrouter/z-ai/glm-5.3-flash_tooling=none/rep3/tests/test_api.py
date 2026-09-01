"""Integration tests: start the real HTTP server and exercise it end to end."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from app import BookAPIHandler, BookStore


def header(headers, name):
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


class Client:
    def __init__(self, base_url):
        self.base_url = base_url

    def request(self, method, path, payload=None, raw_body=None):
        data = None
        if raw_body is not None:
            data = raw_body.encode("utf-8")
        elif payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request_headers = {"Content-Type": "application/json"} if data is not None else {}
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers=request_headers,
        )
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        body = response.read()
        parsed = json.loads(body) if body else None
        return response.status, parsed, dict(response.headers)


@pytest.fixture()
def client(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), BookAPIHandler)
    server.store = BookStore(str(tmp_path / "books.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield Client(f"http://127.0.0.1:{server.server_address[1]}")
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def make_book(client, **overrides):
    payload = {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0441172719",
    }
    payload.update(overrides)
    status, book, _ = client.request("POST", "/books", payload)
    assert status == 201
    return book


def test_health(client):
    status, body, _ = client.request("GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_create_book_returns_201_with_location(client):
    status, book, headers = client.request(
        "POST",
        "/books",
        {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"},
    )
    assert status == 201
    assert isinstance(book["id"], int)
    assert book["title"] == "1984"
    assert book["author"] == "George Orwell"
    assert book["year"] == 1949
    assert book["isbn"] == "978-0451524935"
    assert header(headers, "Location") == f"/books/{book['id']}"


def test_created_book_is_fetchable(client):
    book = make_book(client)
    status, fetched, _ = client.request("GET", f"/books/{book['id']}")
    assert status == 200
    assert fetched == book


def test_create_allows_omitting_optional_fields(client):
    status, book, _ = client.request("POST", "/books", {"title": "Fahrenheit 451", "author": "Ray Bradbury"})
    assert status == 201
    assert book["year"] is None
    assert book["isbn"] is None


def test_create_ignores_unknown_fields(client):
    status, book, _ = client.request(
        "POST", "/books", {"title": "Dune", "author": "Frank Herbert", "rating": 5}
    )
    assert status == 201
    assert "rating" not in book


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "Frank Herbert"},
        {"title": "Dune"},
        {"title": "", "author": "Frank Herbert"},
        {"title": "   ", "author": "Frank Herbert"},
        {"title": "Dune", "author": ""},
        {"title": "Dune", "author": 42},
    ],
)
def test_create_rejects_missing_or_blank_title_or_author(client, payload):
    status, body, _ = client.request("POST", "/books", payload)
    assert status == 400
    assert "error" in body


def test_create_rejects_malformed_json(client):
    status, body, _ = client.request("POST", "/books", raw_body='{"title": "Dune", ')
    assert status == 400
    assert "error" in body


def test_create_rejects_non_object_body(client):
    status, body, _ = client.request("POST", "/books", raw_body='["not", "an", "object"]')
    assert status == 400


def test_create_rejects_non_integer_year(client):
    status, body, _ = client.request(
        "POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": "1965!"}
    )
    assert status == 400


def test_create_accepts_year_as_digit_string(client):
    status, book, _ = client.request(
        "POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": "1965"}
    )
    assert status == 201
    assert book["year"] == 1965


def test_list_books_is_empty_initially(client):
    status, books, _ = client.request("GET", "/books")
    assert status == 200
    assert books == []


def test_list_books_returns_created_books(client):
    make_book(client, title="Dune")
    make_book(client, title="Dune Messiah")
    status, books, _ = client.request("GET", "/books")
    assert status == 200
    assert isinstance(books, list)
    assert [book["title"] for book in books] == ["Dune", "Dune Messiah"]


def test_list_books_filters_by_author_case_insensitively(client):
    make_book(client, title="Dune", author="Frank Herbert")
    make_book(client, title="The Hobbit", author="J. R. R. Tolkien")
    make_book(client, title="The Two Towers", author="J. R. R. Tolkien")

    status, books, _ = client.request("GET", "/books?author=tolkien")
    assert status == 200
    assert [book["title"] for book in books] == ["The Hobbit", "The Two Towers"]

    status, books, _ = client.request("GET", "/books?author=Herbert")
    assert status == 200
    assert [book["title"] for book in books] == ["Dune"]

    status, books, _ = client.request("GET", "/books?author=nobody")
    assert status == 200
    assert books == []


def test_get_missing_book_returns_404(client):
    status, body, _ = client.request("GET", "/books/999")
    assert status == 404


def test_get_non_numeric_id_returns_404(client):
    status, body, _ = client.request("GET", "/books/not-a-number")
    assert status == 404


def test_update_replaces_provided_fields(client):
    book = make_book(client)
    status, updated, _ = client.request(
        "PUT",
        f"/books/{book['id']}",
        {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": None},
    )
    assert status == 200
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] == 1969
    assert updated["isbn"] is None
    _, fetched, _ = client.request("GET", f"/books/{book['id']}")
    assert fetched == updated


def test_update_supports_partial_payload(client):
    book = make_book(client)
    status, updated, _ = client.request("PUT", f"/books/{book['id']}", {"year": 1976})
    assert status == 200
    assert updated["title"] == "Dune"
    assert updated["author"] == "Frank Herbert"
    assert updated["year"] == 1976


def test_update_missing_book_returns_404(client):
    status, _, _ = client.request("PUT", "/books/999", {"title": "Nope"})
    assert status == 404


def test_update_rejects_blank_title(client):
    book = make_book(client)
    status, body, _ = client.request("PUT", f"/books/{book['id']}", {"title": "   "})
    assert status == 400


def test_delete_returns_204_and_removes_book(client):
    book = make_book(client)
    status, body, _ = client.request("DELETE", f"/books/{book['id']}")
    assert status == 204
    assert body is None
    status, _, _ = client.request("GET", f"/books/{book['id']}")
    assert status == 404


def test_delete_missing_book_returns_404(client):
    status, _, _ = client.request("DELETE", "/books/999")
    assert status == 404


def test_unknown_route_returns_404(client):
    status, body, _ = client.request("GET", "/nope")
    assert status == 404


def test_method_not_allowed_on_collection(client):
    status, body, headers = client.request(
        "PUT", "/books", {"title": "Dune", "author": "Frank Herbert"}
    )
    assert status == 405
    assert "GET" in header(headers, "Allow")


def test_request_body_too_large_returns_413(client):
    big = "x" * (BookAPIHandler.max_body_bytes + 1)
    status, body, _ = client.request("POST", "/books", raw_body='{"title": "' + big + '"}')
    assert status == 413
