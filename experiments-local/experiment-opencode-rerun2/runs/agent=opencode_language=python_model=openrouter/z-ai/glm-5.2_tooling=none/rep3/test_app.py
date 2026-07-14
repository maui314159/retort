import os
import tempfile
import pytest

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("BOOKS_DB_PATH", str(db_path))
    app_module.DB_PATH = str(db_path)
    app_module.init_db(str(db_path))
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965

    resp = client.get("/books/1")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"


def test_validation_missing_required_fields(client):
    resp = client.post("/books", json={"year": 1999})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "title" in errors
    assert "author" in errors


def test_list_with_author_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    client.post("/books", json={"title": "Book C", "author": "Alice"})

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert titles == ["Book A", "Book C"]


def test_update_book(client):
    client.post("/books", json={"title": "Old", "author": "Author"})
    resp = client.put("/books/1", json={"title": "New Title"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "New Title"
    assert resp.get_json()["author"] == "Author"


def test_delete_book(client):
    client.post("/books", json={"title": "To Delete", "author": "Author"})
    resp = client.delete("/books/1")
    assert resp.status_code == 204
    resp = client.get("/books/1")
    assert resp.status_code == 404


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
