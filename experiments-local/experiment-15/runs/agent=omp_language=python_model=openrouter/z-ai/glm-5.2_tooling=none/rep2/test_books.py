"""Integration tests for the books API.

Each test runs against a fresh SQLite database (tests set `db.DB_PATH`
to an isolated file and `init_db(fresh=True)` it). Uses FastAPI's
TestClient so the full request pipeline — validation, routing,
serialization — is exercised end-to-end.
"""
from __future__ import annotations

import os

import db
from fastapi.testclient import TestClient

import app as app_module


client = TestClient(app_module.app)


def setup_function() -> None:
    db.DB_PATH = f"/tmp/books_test_{os.getpid()}.db"
    db.init_db(fresh=True)


# --- Tests ----------------------------------------------------------------


def test_create_get_update_delete_lifecycle() -> None:
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"},
    )
    assert resp.status_code == 201
    book = resp.json()
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["id"] >= 1
    bid = book["id"]

    assert client.get(f"/books/{bid}").status_code == 200

    assert len(client.get("/books").json()) == 1

    resp = client.put(f"/books/{bid}", json={"title": "Dune: Revised", "author": "Frank Herbert"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Dune: Revised"
    assert resp.json()["year"] is None

    assert client.delete(f"/books/{bid}").status_code == 204
    assert client.delete(f"/books/{bid}").status_code == 404


def test_author_filter_and_not_found() -> None:
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    assert len(client.get("/books").json()) == 3
    alice = client.get("/books?author=Alice").json()
    assert len(alice) == 2
    assert {b["title"] for b in alice} == {"A", "C"}

    assert client.get("/books/999").status_code == 404


def test_input_validation_required_fields() -> None:
    assert client.post("/books", json={"author": "X"}).status_code == 422
    assert client.post("/books", json={"title": "X"}).status_code == 422
    assert client.post("/books", json={"title": "   ", "author": "X"}).status_code == 422
    assert client.post("/books", json={"title": "T", "author": "Au"}).status_code == 201


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_update_nonexistent_returns_404() -> None:
    assert client.put("/books/123", json={"title": "T", "author": "A"}).status_code == 404
