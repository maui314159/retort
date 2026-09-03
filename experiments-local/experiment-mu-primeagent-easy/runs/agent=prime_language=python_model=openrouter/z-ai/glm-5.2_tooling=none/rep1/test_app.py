"""Unit and integration tests for the Book Collection REST API."""

import os
import tempfile

import pytest

import app as app_module


@pytest.fixture
def client(tmp_path):
    """A Flask test client backed by a fresh SQLite database."""
    db_path = str(tmp_path / "test_books.db")
    app_module.DB_PATH = db_path
    app_module.init_db(db_path)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    payload = {"title": "Clean Code", "author": "Robert C. Martin",
               "year": 2008, "isbn": "978-0-13-235088-4"}
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["id"] == 1
    assert book["title"] == "Clean Code"

    resp = client.get("/books/1")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Robert C. Martin"


def test_create_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "title" in errors
    assert "author" in errors


def test_list_books_with_author_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice", "year": 2010})
    client.post("/books", json={"title": "Book B", "author": "Bob", "year": 2011})
    client.post("/books", json={"title": "Book C", "author": "Alice", "year": 2012})

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert titles == ["Book A", "Book C"]


def test_update_and_delete_book(client):
    resp = client.post("/books", json={"title": "Old", "author": "Auth"})
    book_id = resp.get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "New"
    assert resp.get_json()["author"] == "Auth"

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 200

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_get_nonexistent_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404


def test_list_all_books(client):
    client.post("/books", json={"title": "X", "author": "Y"})
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1
