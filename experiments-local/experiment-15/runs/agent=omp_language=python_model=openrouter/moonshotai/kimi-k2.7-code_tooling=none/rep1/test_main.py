import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("BOOKS_DB_PATH", ":memory:")

from main import app, init_db


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("main.DATABASE", str(db_path))
    init_db()
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_book(client):
    payload = {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "year": 1937,
        "isbn": "978-0547928227",
    }
    response = client.post("/books", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["author"] == payload["author"]
    assert data["year"] == payload["year"]
    assert data["isbn"] == payload["isbn"]
    assert "id" in data


def test_create_book_validation(client):
    response = client.post("/books", json={"author": "Anonymous"})
    assert response.status_code == 422

    response = client.post("/books", json={"title": "Untitled"})
    assert response.status_code == 422

    response = client.post("/books", json={"title": "", "author": " "})
    assert response.status_code == 422


def test_get_book(client):
    create_response = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965},
    )
    book_id = create_response.json()["id"]

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"


def test_get_book_not_found(client):
    response = client.get("/books/9999")
    assert response.status_code == 404


def test_list_books_and_author_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    client.post("/books", json={"title": "Book C", "author": "Alice"})

    response = client.get("/books")
    assert response.status_code == 200
    assert len(response.json()) == 3

    response = client.get("/books?author=Alice")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(book["author"] == "Alice" for book in data)


def test_update_book(client):
    create_response = client.post(
        "/books",
        json={"title": "Old Title", "author": "Old Author", "year": 2000},
    )
    book_id = create_response.json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"title": "New Title"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["author"] == "Old Author"
    assert data["year"] == 2000


def test_update_book_not_found(client):
    response = client.put("/books/9999", json={"title": "Does Not Matter"})
    assert response.status_code == 404


def test_delete_book(client):
    create_response = client.post(
        "/books",
        json={"title": "To Delete", "author": "Deleter"},
    )
    book_id = create_response.json()["id"]

    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404


def test_delete_book_not_found(client):
    response = client.delete("/books/9999")
    assert response.status_code == 404
