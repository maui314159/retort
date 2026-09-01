"""Integration tests for the Books REST API.

Each test boots a real HTTP server on an ephemeral port backed by a
throwaway SQLite database, then exercises the API over HTTP.
"""

import json
import threading
import urllib.error
import urllib.request

import pytest

from app import BookAPIHandler, BookAPIServer, BookDatabase


@pytest.fixture()
def base_url(tmp_path):
    database = BookDatabase(str(tmp_path / "books_test.db"))
    server = BookAPIServer(("127.0.0.1", 0), BookAPIHandler, database)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def http_request(base, method, path, payload=None, raw_body=None):
    """Perform an HTTP request against the test server.

    Returns (status_code, parsed_json_body_or_None)."""
    if raw_body is not None:
        data = raw_body
    elif payload is not None:
        data = json.dumps(payload).encode("utf-8")
    else:
        data = None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = urllib.request.Request(
        base + path, data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(request) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read()
    return status, json.loads(body) if body else None


def create_book(base, **overrides):
    payload = {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "year": 1813,
        "isbn": "9780141439518",
    }
    payload.update(overrides)
    status, body = http_request(base, "POST", "/books", payload)
    assert status == 201
    return body


# --------------------------------------------------------------------- #
# Health check                                                          #
# --------------------------------------------------------------------- #

def test_health_check(base_url):
    status, body = http_request(base_url, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


# --------------------------------------------------------------------- #
# Create                                                                #
# --------------------------------------------------------------------- #

def test_create_book_returns_201_with_fields(base_url):
    status, body = http_request(
        base_url,
        "POST",
        "/books",
        {"title": "Dune", "author": "Frank Herbert", "year": 1965,
         "isbn": "9780441172719"},
    )
    assert status == 201
    assert body["id"] >= 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441172719"


def test_create_book_optional_fields_default_to_null(base_url):
    status, body = http_request(
        base_url, "POST", "/books", {"title": "Fahrenheit 451",
                                     "author": "Ray Bradbury"}
    )
    assert status == 201
    assert body["year"] is None
    assert body["isbn"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "Jane Austen"},                      # missing title
        {"title": "Some Title"},                        # missing author
        {"title": "", "author": "Jane Austen"},         # empty title
        {"title": "  ", "author": "Jane Austen"},       # whitespace title
        {"title": "T", "author": "Jane Austen", "year": "1813"},  # bad year
        {"title": "T", "author": "Jane Austen", "isbn": 12345},   # bad isbn
    ],
)
def test_create_book_validation_errors(base_url, payload):
    status, body = http_request(base_url, "POST", "/books", payload)
    assert status == 400
    assert "error" in body


def test_create_book_invalid_json_is_400(base_url):
    status, body = http_request(base_url, "POST", "/books",
                                raw_body=b"this is not json")
    assert status == 400
    assert "error" in body


def test_create_book_empty_body_is_400(base_url):
    status, body = http_request(base_url, "POST", "/books")
    assert status == 400
    assert "error" in body


# --------------------------------------------------------------------- #
# Read                                                                  #
# --------------------------------------------------------------------- #

def test_get_book_by_id(base_url):
    created = create_book(base_url)
    status, body = http_request(base_url, "GET", f"/books/{created['id']}")
    assert status == 200
    assert body == created


def test_get_missing_book_returns_404(base_url):
    status, body = http_request(base_url, "GET", "/books/9999")
    assert status == 404
    assert "error" in body


def test_list_books(base_url):
    create_book(base_url, title="Emma")
    create_book(base_url, title="Persuasion")
    status, body = http_request(base_url, "GET", "/books")
    assert status == 200
    assert [book["title"] for book in body] == ["Emma", "Persuasion"]


def test_list_books_author_filter_is_case_insensitive_substring(base_url):
    create_book(base_url)
    create_book(base_url, title="1984", author="George Orwell")
    status, body = http_request(base_url, "GET", "/books?author=jane")
    assert status == 200
    assert len(body) == 1
    assert body[0]["author"] == "Jane Austen"

    status, body = http_request(base_url, "GET", "/books?author=orwell")
    assert status == 200
    assert len(body) == 1
    assert body[0]["title"] == "1984"

    status, body = http_request(base_url, "GET", "/books?author=nobody")
    assert status == 200
    assert body == []


# --------------------------------------------------------------------- #
# Update                                                                #
# --------------------------------------------------------------------- #

def test_update_book(base_url):
    created = create_book(base_url)
    status, body = http_request(
        base_url,
        "PUT",
        f"/books/{created['id']}",
        {"title": "Pride and Prejudice (2nd ed.)", "author": "Jane Austen",
         "year": 2002, "isbn": None},
    )
    assert status == 200
    assert body["title"] == "Pride and Prejudice (2nd ed.)"
    assert body["year"] == 2002
    assert body["isbn"] is None

    status, fetched = http_request(base_url, "GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == body


def test_update_missing_book_returns_404(base_url):
    status, body = http_request(
        base_url, "PUT", "/books/9999",
        {"title": "X", "author": "Y"},
    )
    assert status == 404


def test_update_book_validation_errors(base_url):
    created = create_book(base_url)
    status, body = http_request(
        base_url, "PUT", f"/books/{created['id']}", {"title": "No author"}
    )
    assert status == 400
    assert "error" in body


# --------------------------------------------------------------------- #
# Delete                                                                #
# --------------------------------------------------------------------- #

def test_delete_book(base_url):
    created = create_book(base_url)
    status, body = http_request(base_url, "DELETE", f"/books/{created['id']}")
    assert status == 204
    assert body is None

    status, _ = http_request(base_url, "GET", f"/books/{created['id']}")
    assert status == 404


def test_delete_missing_book_returns_404(base_url):
    status, body = http_request(base_url, "DELETE", "/books/9999")
    assert status == 404
    assert "error" in body


# --------------------------------------------------------------------- #
# Routing errors                                                        #
# --------------------------------------------------------------------- #

def test_unknown_route_returns_404(base_url):
    status, body = http_request(base_url, "GET", "/nope")
    assert status == 404


def test_method_not_allowed(base_url):
    status, body = http_request(base_url, "PATCH", "/books")
    assert status == 405
    assert "error" in body
