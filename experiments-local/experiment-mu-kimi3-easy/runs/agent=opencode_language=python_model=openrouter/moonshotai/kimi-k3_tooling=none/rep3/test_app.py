"""Tests for the book collection REST API."""

import os
import tempfile

# Point the module-level database initialization at a throwaway file so
# importing the app during tests never creates books.db in the workspace.
_session_db_fd, _session_db_path = tempfile.mkstemp(suffix=".db")
os.close(_session_db_fd)
os.environ["BOOKS_DB"] = _session_db_path

import pytest

import app as book_app


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    book_app.app.config["DATABASE"] = db_path
    book_app.app.config["TESTING"] = True
    book_app.init_db()

    with book_app.app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_book_success(client):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    response = client.post("/books", json=payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441172719"


def test_create_book_missing_required_fields(client):
    response = client.post("/books", json={"year": 2000})
    assert response.status_code == 400
    body = response.get_json()
    assert "title is required" in body["errors"]
    assert "author is required" in body["errors"]


def test_create_book_invalid_year(client):
    response = client.post("/books", json={"title": "T", "author": "A", "year": "abc"})
    assert response.status_code == 400
    assert "year must be an integer" in response.get_json()["errors"]


def test_list_books_with_author_filter(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Dune Messiah", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Neuromancer", "author": "William Gibson"})

    all_books = client.get("/books").get_json()
    assert len(all_books) == 3

    filtered = client.get("/books?author=Frank Herbert").get_json()
    assert len(filtered) == 2
    assert all(b["author"] == "Frank Herbert" for b in filtered)


def test_get_book_by_id(client):
    created = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"}).get_json()
    response = client.get(f"/books/{created['id']}")
    assert response.status_code == 200
    assert response.get_json()["title"] == "Dune"

    assert client.get("/books/9999").status_code == 404


def test_update_book(client):
    created = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"}).get_json()
    response = client.put(
        f"/books/{created['id']}",
        json={"title": "Dune (Revised)", "year": 1965},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["title"] == "Dune (Revised)"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965

    assert client.put("/books/9999", json={"title": "X", "author": "Y"}).status_code == 404
    assert client.put(f"/books/{created['id']}", json={"title": ""}).status_code == 400


def test_delete_book(client):
    created = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"}).get_json()
    assert client.delete(f"/books/{created['id']}").status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.delete(f"/books/{created['id']}").status_code == 404
