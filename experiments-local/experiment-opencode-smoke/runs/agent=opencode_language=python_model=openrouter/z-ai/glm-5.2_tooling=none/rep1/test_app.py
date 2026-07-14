import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path):
    db_path = str(tmp_path / "test_books.db")
    application = create_app(db_path=db_path)
    with TestClient(application) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_get_list_update_delete_book(client):
    # create
    resp = client.post("/books", json={
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0441172719",
    })
    assert resp.status_code == 201
    book = resp.json()
    assert book["id"] is not None
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"

    book_id = book["id"]

    # get by id
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Dune"

    # list
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # update
    resp = client.put(f"/books/{book_id}", json={
        "title": "Dune Updated",
        "author": "Frank Herbert",
        "year": 1966,
        "isbn": "978-0441172719",
    })
    assert resp.status_code == 200
    assert resp.json()["title"] == "Dune Updated"
    assert resp.json()["year"] == 1966

    # delete
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    # confirm gone
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_author_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    client.post("/books", json={"title": "Book C", "author": "Alice"})

    resp = client.get("/books", params={"author": "Alice"})
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)


def test_validation_missing_required_fields(client):
    resp = client.post("/books", json={"author": "Nobody"})
    assert resp.status_code == 422

    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 422


def test_get_nonexistent_book(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
