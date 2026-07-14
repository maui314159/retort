import os
import tempfile
import pytest

import app as app_module


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    old_path = app_module.DB_PATH
    app_module.DB_PATH = path
    app_module.init_db()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c
    app_module.DB_PATH = old_path
    os.unlink(path)


def sample_book(**overrides):
    base = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    base.update(overrides)
    return base


def test_create_and_get_book(client):
    resp = client.post("/books", json=sample_book())
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] is not None
    assert data["title"] == "Dune"
    book_id = data["id"]

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Frank Herbert"


def test_validation_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2000})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "title" in errors
    assert "author" in errors


def test_list_with_author_filter(client):
    client.post("/books", json=sample_book(title="Book A", author="Alice"))
    client.post("/books", json=sample_book(title="Book B", author="Bob"))
    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    rows = resp.get_json()
    assert len(rows) == 1
    assert rows[0]["author"] == "Alice"


def test_update_and_delete(client):
    resp = client.post("/books", json=sample_book())
    book_id = resp.get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "Dune Updated"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune Updated"
    # author preserved
    assert resp.get_json()["author"] == "Frank Herbert"

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
