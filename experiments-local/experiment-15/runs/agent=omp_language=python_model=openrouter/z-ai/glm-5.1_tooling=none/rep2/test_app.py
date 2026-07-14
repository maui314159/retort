"""Integration tests for the Book Collection API."""

import os
import pytest
from fastapi.testclient import TestClient

# Ensure a fresh in-memory DB for every test module run
os.environ.setdefault("TESTING", "1")

import app as _app
from app import app, init_db, DB_PATH

# Point at a temp file so tests are isolated
_TEST_DB = "test_books.db"


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Each test gets its own clean database."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(_app, "DB_PATH", db_file)
    init_db()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestCreateBook:
    def test_create(self, client):
        r = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
        assert r.status_code == 201
        data = r.json()
        assert data["id"] == 1
        assert data["title"] == "Dune"
        assert data["author"] == "Frank Herbert"
        assert data["year"] == 1965
        assert data["isbn"] is None

    def test_create_validation_missing_title(self, client):
        r = client.post("/books", json={"author": "Someone"})
        assert r.status_code == 422

    def test_create_validation_missing_author(self, client):
        r = client.post("/books", json={"title": "Something"})
        assert r.status_code == 422

    def test_create_validation_empty_title(self, client):
        r = client.post("/books", json={"title": "", "author": "Someone"})
        assert r.status_code == 422


class TestListBooks:
    def test_list_empty(self, client):
        r = client.get("/books")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_all(self, client):
        client.post("/books", json={"title": "A", "author": "Alice"})
        client.post("/books", json={"title": "B", "author": "Bob"})
        r = client.get("/books")
        assert len(r.json()) == 2

    def test_filter_by_author(self, client):
        client.post("/books", json={"title": "A", "author": "Alice"})
        client.post("/books", json={"title": "B", "author": "Bob"})
        r = client.get("/books", params={"author": "Alice"})
        assert len(r.json()) == 1
        assert r.json()[0]["author"] == "Alice"


class TestGetBook:
    def test_get_existing(self, client):
        created = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"}).json()
        r = client.get(f"/books/{created['id']}")
        assert r.status_code == 200
        assert r.json()["title"] == "Dune"

    def test_get_missing(self, client):
        r = client.get("/books/9999")
        assert r.status_code == 404


class TestUpdateBook:
    def test_update_title(self, client):
        created = client.post("/books", json={"title": "Old", "author": "A"}).json()
        r = client.put(f"/books/{created['id']}", json={"title": "New"})
        assert r.status_code == 200
        assert r.json()["title"] == "New"
        assert r.json()["author"] == "A"  # unchanged

    def test_update_missing(self, client):
        r = client.put("/books/9999", json={"title": "X"})
        assert r.status_code == 404


class TestDeleteBook:
    def test_delete(self, client):
        created = client.post("/books", json={"title": "Bye", "author": "A"}).json()
        r = client.delete(f"/books/{created['id']}")
        assert r.status_code == 204

        # Confirm gone
        assert client.get(f"/books/{created['id']}").status_code == 404

    def test_delete_missing(self, client):
        r = client.delete("/books/9999")
        assert r.status_code == 404
