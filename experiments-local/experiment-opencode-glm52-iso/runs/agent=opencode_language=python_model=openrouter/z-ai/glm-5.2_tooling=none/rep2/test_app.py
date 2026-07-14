import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import app as app_module
import db as db_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_file))
    db_module.init_db(str(db_file))
    with TestClient(app_module.app) as c:
        yield c


def _create(client, title="Dune", author="Frank Herbert", year=1965, isbn="9780441172719"):
    resp = client.post(
        "/books",
        json={"title": title, "author": author, "year": year, "isbn": isbn},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_get_list_delete(client):
    book = _create(client)
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["id"] is not None

    # GET single
    got = client.get(f"/books/{book['id']}")
    assert got.status_code == 200
    assert got.json()["isbn"] == "9780441172719"

    # GET 404
    assert client.get("/books/9999").status_code == 404

    # LIST
    _create(client, title="1984", author="George Orwell", year=1949)
    books = client.get("/books").json()
    assert len(books) == 2

    # DELETE
    del_resp = client.delete(f"/books/{book['id']}")
    assert del_resp.status_code == 204
    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.delete(f"/books/{book['id']}").status_code == 404


def test_author_filter(client):
    _create(client, title="Dune", author="Frank Herbert")
    _create(client, title="1984", author="George Orwell")
    _create(client, title="The Hobbit", author="J.R.R. Tolkien")

    filtered = client.get("/books?author=Frank Herbert").json()
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Dune"

    # Non-matching author returns empty list, not error
    assert client.get("/books?author=Nobody").json() == []


def test_update(client):
    book = _create(client)
    resp = client.put(
        f"/books/{book['id']}",
        json={"year": 1970, "title": "Dune Updated"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["year"] == 1970
    assert body["title"] == "Dune Updated"
    assert body["author"] == "Frank Herbert"  # unchanged

    assert client.put("/books/9999", json={"title": "x"}).status_code == 404


def test_validation_errors(client):
    # Missing required title
    resp = client.post("/books", json={"author": "X"})
    assert resp.status_code == 422

    # Blank author
    resp = client.post("/books", json={"title": "T", "author": "   "})
    assert resp.status_code == 422

    # Empty update body
    book = _create(client)
    resp = client.put(f"/books/{book['id']}", json={})
    assert resp.status_code == 400
