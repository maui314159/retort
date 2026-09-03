"""Tests for the Book Collection API."""

import os
import sqlite3
import sys
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

# Ensure workspace is importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module  # noqa: E402


@pytest.fixture(autouse=True)
def temp_database(tmp_path, monkeypatch) -> Generator[None, None, None]:
    """Point the app at a fresh temporary database for every test."""
    db_path = tmp_path / "test_books.db"
    monkeypatch.setattr(app_module, "DATABASE_PATH", str(db_path))
    app_module.init_db()
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app_module.app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_health_check(client: TestClient) -> None:
    """The health endpoint should return 200 with an ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


def test_create_list_get_update_delete_book(client: TestClient) -> None:
    """Full CRUD lifecycle on a book."""
    # Create
    payload = {"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "year": 1999, "isbn": "978-0201616224"}
    response = client.post("/books", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "The Pragmatic Programmer"
    assert created["author"] == "Andrew Hunt"
    assert created["id"] is not None
    book_id = created["id"]

    # List (contains our book)
    response = client.get("/books")
    assert response.status_code == 200
    listing = response.json()
    assert listing["count"] >= 1
    assert any(b["id"] == book_id for b in listing["books"])

    # Get single
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json()["isbn"] == "978-0201616224"

    # Update
    response = client.put(f"/books/{book_id}", json={"year": 2000})
    assert response.status_code == 200
    assert response.json()["year"] == 2000
    assert response.json()["title"] == "The Pragmatic Programmer"

    # Delete
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204

    # Get after delete -> 404
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404


def test_author_filter(client: TestClient) -> None:
    """The ?author= query should filter books case-insensitively."""
    client.post("/books", json={"title": "Clean Code", "author": "Robert C. Martin", "year": 2008})
    client.post("/books", json={"title": "Refactoring", "author": "Martin Fowler", "year": 1999})

    # Substring match on "martin" should return both books.
    response = client.get("/books", params={"author": "martin"})
    assert response.status_code == 200
    titles = {b["title"] for b in response.json()["books"]}
    assert "Clean Code" in titles
    assert "Refactoring" in titles

    # Exact-ish on "Fowler" should only return Refactoring.
    response = client.get("/books", params={"author": "Fowler"})
    assert response.status_code == 200
    titles = {b["title"] for b in response.json()["books"]}
    assert titles == {"Refactoring"}


def test_input_validation(client: TestClient) -> None:
    """Missing or blank title/author must be rejected with 422."""
    # Missing required fields.
    response = client.post("/books", json={"year": 2020})
    assert response.status_code == 422

    # Blank title.
    response = client.post("/books", json={"title": "   ", "author": "Author"})
    assert response.status_code == 422

    # Blank author.
    response = client.post("/books", json={"title": "Title", "author": ""})
    assert response.status_code == 422

    # Invalid year.
    response = client.post("/books", json={"title": "Title", "author": "Author", "year": 99999})
    assert response.status_code == 422


def test_404_on_missing_book(client: TestClient) -> None:
    """GET, PUT, and DELETE on a non-existent book return 404."""
    response = client.get("/books/9999")
    assert response.status_code == 404

    response = client.put("/books/9999", json={"title": "Whatever"})
    assert response.status_code == 404

    response = client.delete("/books/9999")
    assert response.status_code == 404


def test_database_is_sqlite(tmp_path, monkeypatch) -> None:
    """Data should be persisted to a real SQLite database file."""
    db_path = tmp_path / "persist.db"
    monkeypatch.setattr(app_module, "DATABASE_PATH", str(db_path))
    app_module.init_db()

    with app_module.get_db() as conn:
        conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            ("Persisted", "Tester", 2021, "111"),
        )

    # Verify via a fresh, independent connection.
    raw = sqlite3.connect(str(db_path))
    raw.row_factory = sqlite3.Row
    row = raw.execute("SELECT title, author FROM books WHERE title = 'Persisted'").fetchone()
    raw.close()
    assert row is not None
    assert row["author"] == "Tester"
