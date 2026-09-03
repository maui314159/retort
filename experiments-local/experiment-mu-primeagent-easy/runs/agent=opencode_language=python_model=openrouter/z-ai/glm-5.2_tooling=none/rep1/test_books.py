"""Tests for the health check and book CRUD endpoints."""


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"},
    )
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["year"] == 1965
    assert book["isbn"] == "9780441172719"
    assert isinstance(book["id"], int)

    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"


def test_create_missing_fields_rejected(client):
    resp = client.post("/books", json={"year": 1999})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_create_empty_title_rejected(client):
    resp = client.post("/books", json={"title": "  ", "author": "A"})
    assert resp.status_code == 400


def test_create_non_json_rejected(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    client.post("/books", json={"title": "Book C", "author": "Alice"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert titles == ["Book A", "Book C"]


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
    assert "not found" in resp.get_json()["error"].lower()


def test_update_book(client):
    resp = client.post("/books", json={"title": "Old", "author": "Old Author", "year": 2000})
    book_id = resp.get_json()["id"]

    resp = client.put(
        f"/books/{book_id}",
        json={"title": "New", "author": "New Author", "year": 2010, "isbn": "111"},
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["title"] == "New"
    assert updated["author"] == "New Author"
    assert updated["year"] == 2010
    assert updated["isbn"] == "111"


def test_update_book_partial_rejected(client):
    """PUT requires a full body, so missing fields must be rejected."""
    resp = client.post("/books", json={"title": "T", "author": "A"})
    book_id = resp.get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": "T2"})
    assert resp.status_code == 400


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_delete_book(client):
    resp = client.post("/books", json={"title": "T", "author": "A"})
    book_id = resp.get_json()["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert resp.data == b""

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
