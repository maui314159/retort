"""Integration tests for the Book Collection API.

Uses FastAPI's TestClient against a per-test temporary SQLite database so
the suite is hermetic and parallel-safe.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import app, init_db


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    db_path = str(tmp_path / "test_books.db")
    monkeypatch.setattr(app_module, "DB_PATH", db_path)
    init_db(db_path)
    with TestClient(app) as c:
        yield c


def _create(client: TestClient, **overrides) -> dict:
    payload = {"title": "The Pragmatic Programmer", "author": "Hunt", **overrides}
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


# --------------------------------------------------------------------------- #
# Create + read
# --------------------------------------------------------------------------- #
def test_create_and_get_book(client: TestClient) -> None:
    book = _create(client, title="Refactoring", author="Fowler", year=1999, isbn="123")
    assert book["title"] == "Refactoring"
    assert book["author"] == "Fowler"
    assert book["year"] == 1999
    assert book["isbn"] == "123"
    assert isinstance(book["id"], int)

    got = client.get(f"/books/{book['id']}")
    assert got.status_code == 200
    assert got.json()["title"] == "Refactoring"


# --------------------------------------------------------------------------- #
# List + filter
# --------------------------------------------------------------------------- #
def test_list_and_filter_by_author(client: TestClient) -> None:
    _create(client, title="Book A", author="Alice")
    _create(client, title="Book B", author="Bob")
    _create(client, title="Book C", author="Alice")

    all_books = client.get("/books").json()
    assert len(all_books) == 3

    alice = client.get("/books", params={"author": "Alice"}).json()
    assert {b["title"] for b in alice} == {"Book A", "Book C"}

    bob = client.get("/books", params={"author": "Bob"}).json()
    assert len(bob) == 1
    assert bob[0]["title"] == "Book B"


# --------------------------------------------------------------------------- #
# Update
# --------------------------------------------------------------------------- #
def test_update_book(client: TestClient) -> None:
    book = _create(client, title="Old Title", author="Old Author", year=2000)
    resp = client.put(
        f"/books/{book['id']}",
        json={"title": "New Title", "year": 2020},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New Title"
    assert body["author"] == "Old Author"  # unchanged
    assert body["year"] == 2020


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #
def test_delete_book(client: TestClient) -> None:
    book = _create(client, title="Doomed", author="X")
    resp = client.delete(f"/books/{book['id']}")
    assert resp.status_code == 204
    assert resp.content == b""

    # Gone after delete
    assert client.get(f"/books/{book['id']}").status_code == 404
    # Idempotency: deleting again is 404
    assert client.delete(f"/books/{book['id']}").status_code == 404


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "payload",
    [
        {},  # missing both required
        {"title": "T"},  # missing author
        {"author": "A"},  # missing title
        {"title": "   ", "author": "A"},  # blank title
        {"title": "T", "author": ""},  # blank author
    ],
)
def test_create_rejects_invalid(client: TestClient, payload: dict) -> None:
    resp = client.post("/books", json=payload)
    assert resp.status_code == 422


def test_create_rejects_bad_year(client: TestClient) -> None:
    resp = client.post("/books", json={"title": "T", "author": "A", "year": 10000})
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# 404 handling
# --------------------------------------------------------------------------- #
def test_get_missing_returns_404(client: TestClient) -> None:
    assert client.get("/books/9999").status_code == 404


def test_update_missing_returns_404(client: TestClient) -> None:
    resp = client.put("/books/9999", json={"title": "X"})
    assert resp.status_code == 404


def test_update_empty_body_rejected(client: TestClient) -> None:
    book = _create(client, title="T", author="A")
    resp = client.put(f"/books/{book['id']}", json={})
    assert resp.status_code == 422
