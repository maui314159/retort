"""Unit and integration tests for the Book Collection API."""

from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_and_get_book(client):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    r = client.post("/books", json=payload)
    assert r.status_code == 201
    created = r.json()
    assert created["id"] is not None
    assert created["title"] == "Dune"
    assert created["author"] == "Frank Herbert"
    assert created["year"] == 1965
    assert created["isbn"] == "9780441172719"

    r = client.get(f"/books/{created['id']}")
    assert r.status_code == 200
    assert r.json() == created


def test_create_validation_missing_fields(client):
    r = client.post("/books", json={"year": 2000})
    assert r.status_code == 422
    body = r.json()
    # both title and author should be flagged
    fields = {e["loc"][-1] for e in body.get("detail", [])}
    assert "title" in fields
    assert "author" in fields


def test_create_validation_blank_strings(client):
    r = client.post("/books", json={"title": "   ", "author": ""})
    assert r.status_code == 422


def test_list_and_filter_by_author(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
    client.post("/books", json={"title": "1984", "author": "George Orwell", "year": 1949})
    client.post("/books", json={"title": "Animal Farm", "author": "George Orwell", "year": 1945})

    r = client.get("/books")
    assert r.status_code == 200
    assert len(r.json()) == 3

    r = client.get("/books", params={"author": "George Orwell"})
    assert r.status_code == 200
    titles = [b["title"] for b in r.json()]
    assert titles == ["1984", "Animal Farm"]

    r = client.get("/books", params={"author": "Nobody"})
    assert r.status_code == 200
    assert r.json() == []


def test_update_book(client):
    r = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
    book_id = r.json()["id"]

    r = client.put(f"/books/{book_id}", json={"year": 1966})
    assert r.status_code == 200
    updated = r.json()
    assert updated["year"] == 1966
    assert updated["title"] == "Dune"

    r = client.put("/books/{book_id}".format(book_id=99999), json={"year": 2000})
    assert r.status_code == 404


def test_delete_book(client):
    r = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = r.json()["id"]

    r = client.delete(f"/books/{book_id}")
    assert r.status_code == 204

    r = client.get(f"/books/{book_id}")
    assert r.status_code == 404

    r = client.delete(f"/books/{book_id}")
    assert r.status_code == 404


def test_get_missing_book_404(client):
    r = client.get("/books/12345")
    assert r.status_code == 404
