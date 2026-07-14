"""Tests for the books REST API.

Uses a temporary SQLite database per test via the BOOKS_DB_PATH env var.
"""
import os
import tempfile

import pytest

import app as app_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_books.db")
    monkeypatch.setenv("BOOKS_DB_PATH", db_path)
    app_module.DB_PATH = db_path
    app_module.init_db()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def create_book(client, title="Refactoring", author="Martin Fowler", year=1999, isbn="9780134757999"):
    return client.post(
        "/books",
        json={"title": title, "author": author, "year": year, "isbn": isbn},
    )


def test_create_and_get_book(client):
    resp = create_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == "Refactoring"
    assert body["author"] == "Martin Fowler"
    assert body["year"] == 1999
    assert body["isbn"] == "9780134757999"
    assert body["id"] is not None

    # fetch the created book
    get_resp = client.get(f"/books/{body['id']}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["title"] == "Refactoring"


def test_validation_requires_title_and_author(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "title" in errors

    resp2 = client.post("/books", json={"title": "T"})
    assert resp2.status_code == 400
    assert "author" in resp2.get_json()["errors"]

    # invalid JSON / missing body
    resp3 = client.post("/books", json=None)
    assert resp3.status_code == 400


def test_list_with_author_filter(client):
    create_book(client, title="A", author="Alice")
    create_book(client, title="B", author="Bob")
    create_book(client, title="C", author="Alice")

    all_resp = client.get("/books")
    assert all_resp.status_code == 200
    assert len(all_resp.get_json()) == 3

    filtered = client.get("/books?author=Alice")
    assert filtered.status_code == 200
    titles = [b["title"] for b in filtered.get_json()]
    assert titles == ["A", "C"]
    assert all(b["author"] == "Alice" for b in filtered.get_json())


def test_update_book(client):
    resp = create_book(client, title="Old", author="Old Author", year=2000)
    book_id = resp.get_json()["id"]

    upd = client.put(
        f"/books/{book_id}",
        json={"title": "New Title", "year": 2021},
    )
    assert upd.status_code == 200
    body = upd.get_json()
    assert body["title"] == "New Title"
    assert body["author"] == "Old Author"  # unchanged
    assert body["year"] == 2021

    # update on missing book
    miss = client.put("/books/9999", json={"title": "X"})
    assert miss.status_code == 404


def test_delete_book(client):
    resp = create_book(client, title="To Delete", author="Author")
    book_id = resp.get_json()["id"]

    dele = client.delete(f"/books/{book_id}")
    assert dele.status_code == 200
    assert dele.get_json()["deleted"] == book_id

    # subsequent get should 404
    assert client.get(f"/books/{book_id}").status_code == 404
    # deleting again should 404
    assert client.delete(f"/books/{book_id}").status_code == 404


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_get_missing_book_returns_404(client):
    assert client.get("/books/404").status_code == 404
