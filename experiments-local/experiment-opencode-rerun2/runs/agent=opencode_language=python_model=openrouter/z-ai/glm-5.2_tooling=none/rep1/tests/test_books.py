import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_books.db")
    monkeypatch.setenv("BOOKS_DB_PATH", db_file)
    # Import the app fresh so the module-level DB_PATH picks up the env var.
    import importlib
    import main as main_module
    importlib.reload(main_module)
    main_module.init_db(main_module.get_connection())
    with TestClient(main_module.app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_get_list_filter_delete(client):
    # Create
    r = client.post(
        "/books",
        json={"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0-00-000000-1"},
    )
    assert r.status_code == 201
    book = r.json()
    assert book["title"] == "The Hobbit"
    assert book["author"] == "J.R.R. Tolkien"
    assert book["year"] == 1937
    book_id = book["id"]
    assert isinstance(book_id, int)

    # Get single
    r = client.get(f"/books/{book_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "The Hobbit"

    # Get missing -> 404
    r = client.get("/books/9999999")
    assert r.status_code == 404

    # Create a second book by a different author
    r = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
    assert r.status_code == 201
    second_id = r.json()["id"]
    assert second_id != book_id

    # List all -> 2 books
    r = client.get("/books")
    assert r.status_code == 200
    all_books = r.json()
    assert len(all_books) == 2

    # Filter by author -> 1 book
    r = client.get("/books?author=J.R.R. Tolkien")
    assert r.status_code == 200
    filtered = r.json()
    assert len(filtered) == 1
    assert filtered[0]["title"] == "The Hobbit"

    # Filter by unknown author -> empty
    r = client.get("/books?author=Nobody")
    assert r.status_code == 200
    assert r.json() == []

    # Update
    r = client.put(f"/books/{book_id}", json={"year": 1938, "title": "The Hobbit Revised"})
    assert r.status_code == 200
    updated = r.json()
    assert updated["title"] == "The Hobbit Revised"
    assert updated["year"] == 1938
    # author unchanged
    assert updated["author"] == "J.R.R. Tolkien"

    # Update missing -> 404
    r = client.put("/books/9999999", json={"year": 1900})
    assert r.status_code == 404

    # Delete
    r = client.delete(f"/books/{book_id}")
    assert r.status_code == 204
    assert r.content in (b"", None)

    # Delete again -> 404
    r = client.delete(f"/books/{book_id}")
    assert r.status_code == 404

    # List remaining -> 1 book
    r = client.get("/books")
    assert len(r.json()) == 1


def test_input_validation(client):
    # Missing title
    r = client.post("/books", json={"author": "X", "year": 2000})
    assert r.status_code == 422

    # Missing author
    r = client.post("/books", json={"title": "Y"})
    assert r.status_code == 422

    # Blank title (whitespace only) -> rejected by custom validator
    r = client.post("/books", json={"title": "   ", "author": "X"})
    assert r.status_code == 422

    # Invalid year (negative)
    r = client.post("/books", json={"title": "T", "author": "A", "year": -1})
    assert r.status_code == 422

    # ISBN too long
    r = client.post("/books", json={"title": "T", "author": "A", "isbn": "x" * 33})
    assert r.status_code == 422
