"""Integration tests for the book collection API.

Each test session uses a fresh SQLite file in a temporary directory, so
the suite is fully isolated from any developer machine state and from
other test runs.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import db
from app import app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "test_books.db"
    db.set_db_path(str(db_path))
    db.init_db()
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Create / Read
# ---------------------------------------------------------------------------


def test_create_and_get_book(client: TestClient) -> None:
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "9780201616224",
    }
    created = client.post("/books", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["id"] > 0
    assert body["title"] == payload["title"]
    assert body["author"] == payload["author"]
    assert body["year"] == payload["year"]
    assert body["isbn"] == payload["isbn"]

    fetched = client.get(f"/books/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_create_book_without_optional_fields(client: TestClient) -> None:
    resp = client.post("/books", json={"title": "Untitled", "author": "Anonymous"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_rejects_missing_title(client: TestClient) -> None:
    resp = client.post("/books", json={"author": "Anonymous"})
    assert resp.status_code == 422


def test_create_book_rejects_blank_title(client: TestClient) -> None:
    resp = client.post("/books", json={"title": "   ", "author": "Anonymous"})
    assert resp.status_code == 422


def test_get_missing_book_returns_404(client: TestClient) -> None:
    resp = client.get("/books/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# List + filter
# ---------------------------------------------------------------------------


def test_list_books_with_author_filter(client: TestClient) -> None:
    client.post("/books", json={"title": "A", "author": "Tolkien"})
    client.post("/books", json={"title": "B", "author": "Tolkien"})
    client.post("/books", json={"title": "C", "author": "Rowling"})

    all_resp = client.get("/books")
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 3

    filtered = client.get("/books", params={"author": "tolkien"})  # case-insensitive
    assert filtered.status_code == 200
    titles = [b["title"] for b in filtered.json()]
    assert titles == ["A", "B"]


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_book_partial(client: TestClient) -> None:
    created = client.post(
        "/books",
        json={"title": "Old", "author": "Someone", "year": 2000, "isbn": "111"},
    ).json()
    book_id = created["id"]

    updated = client.put(f"/books/{book_id}", json={"title": "New"})
    assert updated.status_code == 200
    body = updated.json()
    assert body["title"] == "New"
    # other fields preserved
    assert body["author"] == "Someone"
    assert body["year"] == 2000
    assert body["isbn"] == "111"


def test_update_missing_book_returns_404(client: TestClient) -> None:
    resp = client.put("/books/9999", json={"title": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_book(client: TestClient) -> None:
    created = client.post(
        "/books", json={"title": "Doomed", "author": "X"}
    ).json()
    book_id = created["id"]

    deleted = client.delete(f"/books/{book_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = client.get(f"/books/{book_id}")
    assert missing.status_code == 404


def test_delete_missing_book_returns_404(client: TestClient) -> None:
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
