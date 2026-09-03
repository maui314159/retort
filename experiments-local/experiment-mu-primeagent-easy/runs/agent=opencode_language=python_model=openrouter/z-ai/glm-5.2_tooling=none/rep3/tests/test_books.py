"""Integration tests for the books REST API using Flask's test client."""

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture()
def client():
    """Create a fresh app instance backed by an isolated temp SQLite file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=path)
    app.config["TESTING"] = True
    with app.test_client() as test_client, app.app_context():
        yield test_client
    os.remove(path)


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    payload = {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "year": 1937,
        "isbn": "978-0261102217",
    }
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] is not None
    assert body["title"] == "The Hobbit"
    assert body["author"] == "J.R.R. Tolkien"
    assert body["year"] == 1937
    assert body["isbn"] == "978-0261102217"

    # Fetch it back by id.
    resp = client.get(f"/books/{body['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "The Hobbit"


def test_create_validation_missing_fields(client):
    # Missing both required fields.
    resp = client.post("/books", json={"year": 1990})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "details" in data
    assert "title" in data["details"]
    assert "author" in data["details"]

    # Empty title rejected.
    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400

    # Invalid JSON rejected.
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_books_with_author_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    client.post("/books", json={"title": "Book C", "author": "Alice"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = {b["title"] for b in resp.get_json()}
    assert titles == {"Book A", "Book C"}

    resp = client.get("/books?author=Nobody")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_update_book(client):
    resp = client.post("/books", json={"title": "Old", "author": "Auth"})
    book_id = resp.get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "New Title"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New Title"
    # author preserved from existing record.
    assert body["author"] == "Auth"

    # Update a non-existent book.
    resp = client.put("/books/99999", json={"title": "x", "author": "y"})
    assert resp.status_code == 404


def test_delete_book(client):
    resp = client.post("/books", json={"title": "ToDelete", "author": "Auth"})
    book_id = resp.get_json()["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert resp.data == b""

    # Deleting again is a 404.
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 404

    # GET on deleted book is 404.
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_get_nonexistent_book(client):
    resp = client.get("/books/99999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_year_validation(client):
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "year": "ninety"}
    )
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert "year" in details
