"""Tests for the books REST API.

Each test runs against a fresh temporary SQLite database to avoid
cross-test contamination.
"""

import os

import pytest

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_books.db")
    application = app_module.create_app(db_path=db_path)
    application.config.update(TESTING=True)
    with application.test_client() as c:
        yield c


def create_book(client, **overrides):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andy Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_create_get_and_list_book(client):
    # Create
    resp = create_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["title"] == "The Pragmatic Programmer"
    assert body["author"] == "Andy Hunt"
    assert body["year"] == 1999
    assert body["isbn"] == "978-0201616224"

    # Get by id
    resp = client.get("/books/1")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "The Pragmatic Programmer"

    # List
    create_book(client, title="Clean Code", author="Robert C. Martin", year=2008)
    resp = client.get("/books")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert books[0]["id"] == 1
    assert books[1]["title"] == "Clean Code"


def test_validation_errors(client):
    # Missing required fields
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"author": "No Title"})
    assert resp.status_code == 400

    # Empty body
    resp = client.post("/books", json={})
    assert resp.status_code == 400

    # 404 for unknown id
    resp = client.get("/books/999")
    assert resp.status_code == 404


def test_update_and_delete_and_filter(client):
    a = create_book(client, title="Book A", author="Alice", year=2001).get_json()
    b = create_book(client, title="Book B", author="Bob", year=2002).get_json()
    c = create_book(client, title="Book C", author="Alice", year=2003).get_json()

    # Author filter
    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = [book["title"] for book in resp.get_json()]
    assert titles == ["Book A", "Book C"]

    # Update
    resp = client.put(f"/books/{a['id']}", json={"year": 2010})
    assert resp.status_code == 200
    assert resp.get_json()["year"] == 2010
    assert resp.get_json()["title"] == "Book A"

    # Update validation: empty title rejected
    resp = client.put(f"/books/{a['id']}", json={"title": ""})
    assert resp.status_code == 400

    # Delete
    resp = client.delete(f"/books/{b['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "deleted"

    # Deleted book is gone
    resp = client.get(f"/books/{b['id']}")
    assert resp.status_code == 404

    # Delete unknown -> 404
    resp = client.delete("/books/9999")
    assert resp.status_code == 404


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
