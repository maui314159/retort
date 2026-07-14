import os

import pytest
from fastapi.testclient import TestClient

import app as app_module
import db

# Use a separate DB for tests
TEST_DB = "test_books.db"


@pytest.fixture(scope="function", autouse=True)
def isolated_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_books.db")
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.reset_db()
    yield
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture()
def client():
    return TestClient(app_module.app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_and_get_book(client):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}
    r = client.post("/books", json=payload)
    assert r.status_code == 201
    created = r.json()
    assert created["id"] == 1
    assert created["title"] == "Dune"
    assert created["author"] == "Frank Herbert"
    assert created["year"] == 1965
    assert created["isbn"] == "123"

    # GET single
    r = client.get("/books/1")
    assert r.status_code == 200
    assert r.json()["title"] == "Dune"


def test_create_validation_required_fields(client):
    # missing author
    r = client.post("/books", json={"title": "Foo"})
    assert r.status_code == 422
    # missing title
    r = client.post("/books", json={"author": "Bar"})
    assert r.status_code == 422
    # empty title
    r = client.post("/books", json={"title": "   ", "author": "Bar"})
    assert r.status_code == 422


def test_list_books_and_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    r = client.get("/books")
    assert r.status_code == 200
    assert len(r.json()) == 3

    r = client.get("/books", params={"author": "Alice"})
    assert r.status_code == 200
    titles = [b["title"] for b in r.json()]
    assert titles == ["A", "C"]


def test_update_book(client):
    client.post("/books", json={"title": "Old", "author": "OldAuth", "year": 2000})
    r = client.put(
        "/books/1",
        json={"title": "New", "author": "NewAuth", "year": 2020, "isbn": "999"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "New"
    assert body["author"] == "NewAuth"
    assert body["year"] == 2020
    assert body["isbn"] == "999"


def test_update_book_not_found(client):
    r = client.put("/books/999", json={"title": "X", "author": "Y"})
    assert r.status_code == 404


def test_update_book_validation(client):
    client.post("/books", json={"title": "Old", "author": "OldAuth"})
    r = client.put("/books/1", json={"title": "", "author": "Y"})
    assert r.status_code == 422


def test_delete_book(client):
    client.post("/books", json={"title": "ToDelete", "author": "A"})
    r = client.delete("/books/1")
    assert r.status_code == 204
    r = client.get("/books/1")
    assert r.status_code == 404


def test_delete_book_not_found(client):
    r = client.delete("/books/999")
    assert r.status_code == 404


def test_get_book_not_found(client):
    r = client.get("/books/999")
    assert r.status_code == 404
