"""Integration tests for the books API.

Each test gets a fresh in-memory SQLite database so tests are isolated.
"""

import json

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app(db_path=":memory:")
    app.testing = True
    with app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_validation_error(client):
    resp = client.post("/books", json={"author": "Nobody"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"].lower()


def test_full_crud_lifecycle(client):
    # Create
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"},
    )
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["title"] == "Dune"
    assert book["id"] == 1

    # List with author filter
    client.post("/books", json={"title": "Another", "author": "Other Author"})
    resp = client.get("/books?author=Frank%20Herbert")
    assert resp.status_code == 200
    rows = resp.get_json()
    assert len(rows) == 1
    assert rows[0]["title"] == "Dune"

    # Get single
    resp = client.get("/books/1")
    assert resp.status_code == 200
    assert resp.get_json()["isbn"] == "9780441172719"

    # Update
    resp = client.put("/books/1", json={"year": 1966})
    assert resp.status_code == 200
    assert resp.get_json()["year"] == 1966
    assert resp.get_json()["title"] == "Dune"  # unchanged

    # Delete
    resp = client.delete("/books/1")
    assert resp.status_code == 204
    resp = client.get("/books/1")
    assert resp.status_code == 404


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/999", json={"title": "X"})
    assert resp.status_code == 404


def test_list_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_delete_missing_returns_404(client):
    resp = client.delete("/books/999")
    assert resp.status_code == 404


def test_year_must_be_integer(client):
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "year": "not-a-number"}
    )
    assert resp.status_code == 400
    assert "year" in resp.get_json()["error"].lower()
