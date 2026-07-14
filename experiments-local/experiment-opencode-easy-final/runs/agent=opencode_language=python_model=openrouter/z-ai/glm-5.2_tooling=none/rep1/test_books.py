"""Tests for the books REST API."""
import os
import tempfile
import pytest

import db as db_mod
import app as app_mod


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test_books.db")

    app_mod.app.config["TESTING"] = True
    app_mod.app.config["DB_PATH"] = db_path
    db_mod.init_db(db_path)
    with app_mod.app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    payload = {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937,
               "isbn": "9780261102217"}
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["id"] is not None
    assert book["title"] == "The Hobbit"
    assert book["author"] == "J.R.R. Tolkien"

    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "The Hobbit"


def test_create_requires_title_and_author(client):
    resp = client.post("/books", json={"author": "No Title"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"].lower()

    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"].lower()


def test_list_and_filter_by_author(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    client.post("/books", json={"title": "Book C", "author": "Alice"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert sorted(titles) == ["Book A", "Book C"]


def test_update_book(client):
    resp = client.post("/books", json={"title": "Old", "author": "Auth"})
    book_id = resp.get_json()["id"]

    resp = client.put(f"/books/{book_id}",
                      json={"title": "New", "author": "Auth", "year": 2020})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New"
    assert body["year"] == 2020


def test_delete_book(client):
    resp = client.post("/books", json={"title": "Gone", "author": "Auth"})
    book_id = resp.get_json()["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
