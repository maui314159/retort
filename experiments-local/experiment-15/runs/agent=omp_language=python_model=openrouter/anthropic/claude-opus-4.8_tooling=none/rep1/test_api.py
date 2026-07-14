"""Integration tests for the book collection API.

Each test gets a fresh in-memory database via the ``client`` fixture so tests
are independent of one another and of any on-disk ``books.db``.
"""

import pytest
from fastapi.testclient import TestClient

import db
import main


@pytest.fixture
def client():
    db.init_db(":memory:")  # fresh schema, no persistence
    with TestClient(main.app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "111"},
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"] >= 1
    assert created["title"] == "Dune"

    got = client.get(f"/books/{created['id']}")
    assert got.status_code == 200
    assert got.json() == created


def test_create_requires_title_and_author(client):
    # Missing author -> 422 from validation.
    assert client.post("/books", json={"title": "X"}).status_code == 422
    # Blank/whitespace title -> rejected by the custom validator.
    assert (
        client.post("/books", json={"title": "   ", "author": "A"}).status_code == 422
    )


def test_list_and_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    all_books = client.get("/books").json()
    assert len(all_books) == 3

    alice = client.get("/books", params={"author": "Alice"}).json()
    assert len(alice) == 2
    assert {b["title"] for b in alice} == {"A", "C"}


def test_update_book(client):
    book_id = client.post(
        "/books", json={"title": "Old", "author": "Auth"}
    ).json()["id"]

    resp = client.put(
        f"/books/{book_id}",
        json={"title": "New", "author": "Auth", "year": 2020, "isbn": "999"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"
    assert resp.json()["year"] == 2020

    assert client.get(f"/books/{book_id}").json()["title"] == "New"


def test_delete_book(client):
    book_id = client.post(
        "/books", json={"title": "Temp", "author": "Auth"}
    ).json()["id"]

    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_missing_book_returns_404(client):
    assert client.get("/books/9999").status_code == 404
    assert client.delete("/books/9999").status_code == 404
    assert (
        client.put(
            "/books/9999", json={"title": "T", "author": "A"}
        ).status_code
        == 404
    )
