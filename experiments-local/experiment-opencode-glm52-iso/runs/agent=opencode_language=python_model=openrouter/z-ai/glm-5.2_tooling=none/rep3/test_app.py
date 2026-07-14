"""Tests for the book collection API."""
import os
import tempfile
import pytest

os.environ["BOOKS_DB_PATH"] = tempfile.NamedTemporaryFile(
    suffix=".db", delete=False
).name

from app import create_app, init_db  # noqa: E402


@pytest.fixture()
def client():
    db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    os.environ["BOOKS_DB_PATH"] = db_path

    import importlib
    import app as app_module
    importlib.reload(app_module)
    app = app_module.create_app()
    app_module.init_db()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    payload = {
        "title": "The Hobbit",
        "author": "Tolkien",
        "year": 1937,
        "isbn": "978-0123",
    }
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["id"]
    assert book["title"] == "The Hobbit"

    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Tolkien"


def test_create_validation_error(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400


def test_list_filter_and_delete(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 1
    assert books[0]["author"] == "Alice"

    resp = client.get("/books")
    assert len(resp.get_json()) == 2

    bid = books[0]["id"]
    resp = client.delete(f"/books/{bid}")
    assert resp.status_code == 200

    resp = client.get(f"/books/{bid}")
    assert resp.status_code == 404


def test_update_book(client):
    resp = client.post(
        "/books", json={"title": "Old", "author": "Auth", "year": 2000}
    )
    bid = resp.get_json()["id"]
    resp = client.put(
        f"/books/{bid}",
        json={"title": "New", "author": "Auth2", "year": 2020, "isbn": "X"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New"
    assert body["year"] == 2020

    resp = client.put(
        "/books/99999", json={"title": "X", "author": "Y"}
    )
    assert resp.status_code == 404
