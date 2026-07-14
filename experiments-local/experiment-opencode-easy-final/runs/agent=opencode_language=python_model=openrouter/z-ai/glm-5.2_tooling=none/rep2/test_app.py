import os
import tempfile
import sqlite3
import pytest

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_books.db"
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path))
    app_module.init_db()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def make_book(client, title="Refactoring", author="Martin Fowler", year=1999, isbn="123"):
    return client.post(
        "/books",
        json={"title": title, "author": author, "year": year, "isbn": isbn},
    )


def test_create_and_get_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == "Refactoring"
    assert body["author"] == "Martin Fowler"
    assert body["year"] == 1999
    assert body["isbn"] == "123"
    assert "id" in body

    book_id = body["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Refactoring"


def test_validation_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)


def test_list_with_author_filter(client):
    make_book(client, title="Book A", author="Alice")
    make_book(client, title="Book B", author="Bob")
    make_book(client, title="Book C", author="Alice")

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)

    resp = client.get("/books")
    assert len(resp.get_json()) == 3


def test_update_and_delete(client):
    resp = make_book(client, title="Old Title", author="Old Author")
    book_id = resp.get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "New Title"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "New Title"
    assert resp.get_json()["author"] == "Old Author"

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_get_nonexistent_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
