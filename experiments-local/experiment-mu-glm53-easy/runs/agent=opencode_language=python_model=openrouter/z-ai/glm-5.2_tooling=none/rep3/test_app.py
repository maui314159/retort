"""Tests for the books API. Uses an in-memory SQLite DB per test."""

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture()
def client():
    # Use a temp file DB so each test starts fresh.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    os.unlink(path)


def make_book(**overrides):
    base = {"title": "The Pragmatic Programmer", "author": "Hunt", "year": 1999, "isbn": "978-0201616224"}
    base.update(overrides)
    return base


def test_create_get_and_delete_book(client):
    resp = client.post("/books", json=make_book())
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["title"] == "The Pragmatic Programmer"
    assert book["id"] is not None

    # GET list
    resp = client.get("/books")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 1

    # GET single
    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Hunt"

    # DELETE
    resp = client.delete(f"/books/{book['id']}")
    assert resp.status_code == 204

    # GET after delete -> 404
    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 404


def test_validation_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2000})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "title" in errors
    assert "author" in errors


def test_update_book_partial_and_404(client):
    resp = client.post("/books", json=make_book())
    book_id = resp.get_json()["id"]

    # Partial update of title only
    resp = client.put(f"/books/{book_id}", json={"title": "Refactoring"})
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["title"] == "Refactoring"
    assert updated["author"] == "Hunt"

    # Put on non-existent id -> 404
    resp = client.put("/books/9999", json={"title": "Nope"})
    assert resp.status_code == 404


def test_author_filter(client):
    client.post("/books", json=make_book(title="A", author="Alice"))
    client.post("/books", json=make_book(title="B", author="Bob"))
    client.post("/books", json=make_book(title="C", author="Alice"))

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    rows = resp.get_json()
    assert len(rows) == 2
    assert all(r["author"] == "Alice" for r in rows)


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
