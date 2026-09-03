"""Unit/integration tests for the Book Collection API."""

import os
import tempfile

import pytest

import app as app_module
from db import reset_db


@pytest.fixture
def client():
    """Provide a Flask test client backed by a temporary SQLite DB."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["BOOKS_DB_PATH"] = path
    # Re-import-side: the module reads DB_PATH at import time, so set it on
    # the db module directly as well.
    import db as db_module
    db_module.DB_PATH = path
    reset_db(path)

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c

    os.environ.pop("BOOKS_DB_PATH", None)
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Create + retrieve
# ---------------------------------------------------------------------------

def test_create_and_get_book(client):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] is not None
    assert body["title"] == payload["title"]
    assert body["author"] == payload["author"]
    assert body["year"] == payload["year"]
    assert body["isbn"] == payload["isbn"]

    # Retrieve it back.
    resp = client.get(f"/books/{body['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == body


def test_create_book_validation_missing_required(client):
    # Missing title and author.
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "title" in errors
    assert "author" in errors


def test_create_book_validation_empty_strings(client):
    resp = client.post("/books", json={"title": "   ", "author": ""})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "title" in errors
    assert "author" in errors


def test_create_book_invalid_json(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# List + filter
# ---------------------------------------------------------------------------

def test_list_books_and_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice", "year": 2001})
    client.post("/books", json={"title": "Book B", "author": "Bob", "year": 2002})
    client.post("/books", json={"title": "Book C", "author": "Alice", "year": 2003})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert sorted(titles) == ["Book A", "Book C"]

    resp = client.get("/books?author=Nobody")
    assert resp.status_code == 200
    assert resp.get_json() == []


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def test_update_book_partial(client):
    resp = client.post("/books", json={"title": "Old", "author": "A", "year": 2000})
    book_id = resp.get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"year": 2024})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["year"] == 2024
    assert body["title"] == "Old"
    assert body["author"] == "A"


def test_update_book_not_found(client):
    resp = client.put("/books/99999", json={"title": "X"})
    assert resp.status_code == 404


def test_update_book_invalid_field(client):
    resp = client.post("/books", json={"title": "T", "author": "A"})
    book_id = resp.get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"year": "not-a-number"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def test_delete_book(client):
    resp = client.post("/books", json={"title": "ToDelete", "author": "A"})
    book_id = resp.get_json()["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 200

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------

def test_get_book_not_found(client):
    resp = client.get("/books/99999")
    assert resp.status_code == 404
