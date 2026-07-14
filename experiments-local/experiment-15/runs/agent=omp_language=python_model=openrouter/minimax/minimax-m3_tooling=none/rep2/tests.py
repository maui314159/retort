"""Tests for the Book Collection REST API.

Uses pytest with FastAPI's TestClient. A module-scoped temporary SQLite
file backs the app for the duration of the test session, and an
autouse fixture clears the books table between tests.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from typing import Iterator

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Test database setup (must happen before importing app.py)
# ---------------------------------------------------------------------------

_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(prefix="books-test-", suffix=".db")
os.close(_TEST_DB_FD)
os.environ["BOOKS_DB"] = _TEST_DB_PATH

# Imports are intentionally below the env var override so the app picks up
# the test database path.
from app import app, get_db, init_db  # noqa: E402

init_db(_TEST_DB_PATH)


def _override_get_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_db() -> Iterator[None]:
    conn = sqlite3.connect(_TEST_DB_PATH)
    conn.execute("DELETE FROM books")
    conn.execute("DELETE FROM sqlite_sequence WHERE name='books'")
    conn.commit()
    conn.close()
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0-7432-7356-5",
    }
    payload.update(overrides)
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_book_persists_all_fields(client: TestClient) -> None:
    book = _create(client)
    assert isinstance(book["id"], int) and book["id"] > 0
    assert book["title"] == "The Great Gatsby"
    assert book["author"] == "F. Scott Fitzgerald"
    assert book["year"] == 1925
    assert book["isbn"] == "978-0-7432-7356-5"


def test_create_book_without_optional_fields(client: TestClient) -> None:
    resp = client.post("/books", json={"title": "Untitled", "author": "Anonymous"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Untitled"
    assert body["author"] == "Anonymous"
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_trims_whitespace(client: TestClient) -> None:
    resp = client.post("/books", json={"title": "  Trimmed  ", "author": " Author "})
    assert resp.status_code == 201
    assert resp.json()["title"] == "Trimmed"
    assert resp.json()["author"] == "Author"


def test_create_book_missing_title_returns_422(client: TestClient) -> None:
    resp = client.post("/books", json={"author": "Anonymous"})
    assert resp.status_code == 422


def test_create_book_blank_title_returns_422(client: TestClient) -> None:
    resp = client.post("/books", json={"title": "   ", "author": "Anonymous"})
    assert resp.status_code == 422


def test_create_book_missing_author_returns_422(client: TestClient) -> None:
    resp = client.post("/books", json={"title": "Only Title"})
    assert resp.status_code == 422


def test_create_book_invalid_year_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/books",
        json={"title": "Bad Year", "author": "Author", "year": -5},
    )
    assert resp.status_code == 422


def test_create_book_rejects_garbage_body(client: TestClient) -> None:
    resp = client.post(
        "/books",
        content=b"not json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List + filter
# ---------------------------------------------------------------------------


def test_list_books_empty(client: TestClient) -> None:
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_books_returns_all_in_order(client: TestClient) -> None:
    _create(client, title="A", author="Author A")
    _create(client, title="B", author="Author B")
    _create(client, title="C", author="Author C")
    resp = client.get("/books")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.json()]
    assert titles == ["A", "B", "C"]


def test_list_books_filter_by_author(client: TestClient) -> None:
    _create(client, title="A1", author="Author A")
    _create(client, title="B1", author="Author B")
    _create(client, title="A2", author="Author A")
    resp = client.get("/books", params={"author": "Author A"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert {b["title"] for b in body} == {"A1", "A2"}


def test_list_books_filter_by_author_is_case_insensitive(client: TestClient) -> None:
    _create(client, title="A1", author="Author A")
    _create(client, title="B1", author="Author B")
    resp = client.get("/books", params={"author": "author a"})
    assert resp.status_code == 200
    assert [b["title"] for b in resp.json()] == ["A1"]


def test_list_books_filter_by_unknown_author_returns_empty(client: TestClient) -> None:
    _create(client, title="A1", author="Author A")
    resp = client.get("/books", params={"author": "Nobody"})
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Get one
# ---------------------------------------------------------------------------


def test_get_book_returns_stored_book(client: TestClient) -> None:
    created = _create(client, title="Solo", author="Solo Author")
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Solo"


def test_get_book_missing_returns_404(client: TestClient) -> None:
    resp = client.get("/books/9999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_book_partial_keeps_untouched_fields(client: TestClient) -> None:
    created = _create(client)
    resp = client.put(f"/books/{created['id']}", json={"title": "Renamed"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Renamed"
    assert body["author"] == created["author"]
    assert body["year"] == created["year"]


def test_update_book_full_replacement(client: TestClient) -> None:
    created = _create(client)
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New", "author": "New Author", "year": 2024, "isbn": "123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "id": created["id"],
        "title": "New",
        "author": "New Author",
        "year": 2024,
        "isbn": "123",
    }


def test_update_book_missing_returns_404(client: TestClient) -> None:
    resp = client.put("/books/9999", json={"title": "Nope"})
    assert resp.status_code == 404


def test_update_book_empty_body_returns_400(client: TestClient) -> None:
    created = _create(client)
    resp = client.put(f"/books/{created['id']}", json={})
    assert resp.status_code == 400


def test_update_book_blank_title_returns_422(client: TestClient) -> None:
    created = _create(client)
    resp = client.put(f"/books/{created['id']}", json={"title": "  "})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_book_removes_it(client: TestClient) -> None:
    created = _create(client)
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert resp.content == b""
    follow_up = client.get(f"/books/{created['id']}")
    assert follow_up.status_code == 404


def test_delete_book_missing_returns_404(client: TestClient) -> None:
    resp = client.delete("/books/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# End-to-end lifecycle
# ---------------------------------------------------------------------------


def test_full_crud_lifecycle(client: TestClient) -> None:
    # Create
    resp = client.post(
        "/books",
        json={"title": "1984", "author": "George Orwell", "year": 1949},
    )
    assert resp.status_code == 201
    book = resp.json()
    book_id = book["id"]

    # Read
    assert client.get(f"/books/{book_id}").json()["title"] == "1984"

    # Update
    resp = client.put(f"/books/{book_id}", json={"year": 1950})
    assert resp.status_code == 200
    assert resp.json()["year"] == 1950

    # Filter
    assert client.get("/books", params={"author": "George Orwell"}).status_code == 200
    body = client.get("/books", params={"author": "george orwell"}).json()
    assert len(body) == 1 and body[0]["id"] == book_id

    # Delete
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get("/books").json() == []
