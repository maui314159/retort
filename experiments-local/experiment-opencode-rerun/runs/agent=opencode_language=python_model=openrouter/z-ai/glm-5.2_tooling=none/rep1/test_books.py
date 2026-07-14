import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_books.db"
    monkeypatch.setenv("BOOKS_DB_PATH", str(db_path))
    import importlib

    import main as app_module

    importlib.reload(app_module)
    app_module.init_db()
    with TestClient(app_module.app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_get_book(client):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172710"}
    r = client.post("/books", json=payload)
    assert r.status_code == 201
    book = r.json()
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["year"] == 1965
    assert book["id"] is not None

    r2 = client.get(f"/books/{book['id']}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "Dune"


def test_list_and_filter_by_author(client):
    client.post("/books", json={"title": "Book A", "author": "Alice", "year": 2001})
    client.post("/books", json={"title": "Book B", "author": "Bob", "year": 2002})
    client.post("/books", json={"title": "Book C", "author": "Alice", "year": 2003})

    all_books = client.get("/books")
    assert all_books.status_code == 200
    assert len(all_books.json()) == 3

    filtered = client.get("/books", params={"author": "Alice"})
    assert filtered.status_code == 200
    titles = [b["title"] for b in filtered.json()]
    assert titles == ["Book A", "Book C"]


def test_validation_errors(client):
    r = client.post("/books", json={"author": "Nobody", "year": 1999})
    assert r.status_code == 422

    r2 = client.post("/books", json={"title": "", "author": "X"})
    assert r2.status_code == 422


def test_update_and_delete(client):
    r = client.post("/books", json={"title": "Old", "author": "A", "year": 1900})
    bid = r.json()["id"]

    upd = client.put(f"/books/{bid}", json={"title": "New", "author": "B", "year": 2000, "isbn": "i1"})
    assert upd.status_code == 200
    assert upd.json()["title"] == "New"
    assert upd.json()["author"] == "B"

    gone = client.delete(f"/books/{bid}")
    assert gone.status_code == 204

    missing = client.get(f"/books/{bid}")
    assert missing.status_code == 404


def test_404_on_missing(client):
    r = client.get("/books/9999")
    assert r.status_code == 404
    r2 = client.delete("/books/9999")
    assert r2.status_code == 404
