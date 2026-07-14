"""Integration tests for the book collection API.

These tests exercise the Flask test client against a per-test temporary
SQLite database, so they never touch the developer's `books.db`.
"""
import json
import os
import tempfile

import pytest

import app as app_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test_books.db"
    monkeypatch.setenv("BOOKS_DB_PATH", str(db_file))
    application = app_module.create_app()
    application.testing = True
    with application.test_client() as c:
        yield c


def _create(client, **fields):
    return client.post(
        "/books",
        data=json.dumps(fields),
        content_type="application/json",
    )


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "healthy"}


def test_create_list_get_update_delete_lifecycle(client):
    # Create
    res = _create(
        client, title="The Pragmatic Programmer", author="Hunt", year=1999, isbn="9780201616224"
    )
    assert res.status_code == 201
    book = res.get_json()
    assert book["id"] is not None
    assert book["title"] == "The Pragmatic Programmer"
    assert book["author"] == "Hunt"
    assert book["year"] == 1999
    assert book["isbn"] == "9780201616224"
    book_id = book["id"]

    # List (two books to prove ordering + filtering)
    _create(client, title="Clean Code", author="Martin", year=2008, isbn="9780132350884")

    res = client.get("/books")
    assert res.status_code == 200
    assert len(res.get_json()) == 2

    # Author filter
    res = client.get("/books?author=Martin")
    assert res.status_code == 200
    rows = res.get_json()
    assert len(rows) == 1
    assert rows[0]["title"] == "Clean Code"

    # Get single
    res = client.get(f"/books/{book_id}")
    assert res.status_code == 200
    assert res.get_json()["title"] == "The Pragmatic Programmer"

    # Get unknown -> 404
    assert client.get("/books/9999").status_code == 404

    # Update
    res = client.put(
        f"/books/{book_id}",
        data=json.dumps({"title": "The Pragmatic Programmer 2", "author": "Hunt & Thomas", "year": 2019, "isbn": "9780135957059"}),
        content_type="application/json",
    )
    assert res.status_code == 200
    updated = res.get_json()
    assert updated["title"] == "The Pragmatic Programmer 2"
    assert updated["author"] == "Hunt & Thomas"
    assert updated["year"] == 2019

    # Delete
    res = client.delete(f"/books/{book_id}")
    assert res.status_code == 204
    assert res.data == b""
    assert client.get(f"/books/{book_id}").status_code == 404
    # Deleting again -> 404
    assert client.delete(f"/books/{book_id}").status_code == 404


def test_validation_rejects_missing_or_empty_fields(client):
    # No body
    res = client.post("/books", data="", content_type="application/json")
    assert res.status_code == 400
    assert "error" in res.get_json()

    # Missing author
    res = _create(client, title="Only Title")
    assert res.status_code == 400

    # Empty title
    res = _create(client, title="   ", author="Someone")
    assert res.status_code == 400

    # year not an integer
    res = _create(client, title="T", author="A", year="ninety")
    assert res.status_code == 400

    # Optional fields omitted should succeed
    res = _create(client, title="Minimal", author="Anon")
    assert res.status_code == 201
    created = res.get_json()
    assert created["year"] is None
    assert created["isbn"] is None

    # Update with missing required field -> 400 (book exists first)
    bid = created["id"]
    bad = client.put(f"/books/{bid}", data=json.dumps({"author": "x"}), content_type="application/json")
    assert bad.status_code == 400


def test_update_nonexistent_returns_404(client):
    res = client.put(
        "/books/777",
        data=json.dumps({"title": "x", "author": "y"}),
        content_type="application/json",
    )
    assert res.status_code == 404


def test_invalid_route_and_method(client):
    # Non-numeric id on a typed route -> 404
    assert client.get("/books/abc").status_code == 404
    # Unsupported method on a known path -> 405
    assert client.patch("/books").status_code == 405
