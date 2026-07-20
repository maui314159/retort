"""Integration tests for the book collection API.

Each test gets a fresh app instance backed by a temporary SQLite database.
"""

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def create_book(client, title="Dune", author="Frank Herbert", year=1965, isbn="9780441172719"):
    payload = {"title": title, "author": author}
    if year is not None:
        payload["year"] = year
    if isbn is not None:
        payload["isbn"] = isbn
    return client.post("/books", json=payload)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_book_returns_201_with_body(client):
    response = create_book(client)
    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441172719"


def test_create_book_requires_title_and_author(client):
    response = client.post("/books", json={"year": 2000})
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)


def test_create_book_rejects_empty_or_wrong_types(client):
    response = client.post("/books", json={"title": "  ", "author": "X"})
    assert response.status_code == 400

    response = client.post(
        "/books", json={"title": "T", "author": "A", "year": "not-a-year"}
    )
    assert response.status_code == 400


def test_get_book_by_id(client):
    create_book(client)
    response = client.get("/books/1")
    assert response.status_code == 200
    assert response.get_json()["title"] == "Dune"


def test_get_missing_book_returns_404(client):
    response = client.get("/books/999")
    assert response.status_code == 404


def test_list_books_and_author_filter(client):
    create_book(client, title="Dune", author="Frank Herbert")
    create_book(client, title="Dune Messiah", author="Frank Herbert")
    create_book(client, title="The Left Hand of Darkness", author="Ursula K. Le Guin")

    all_books = client.get("/books").get_json()
    assert len(all_books) == 3

    filtered = client.get("/books?author=Frank Herbert").get_json()
    assert len(filtered) == 2
    assert all(b["author"] == "Frank Herbert" for b in filtered)


def test_update_book(client):
    create_book(client)
    response = client.put("/books/1", json={"year": 1966, "isbn": "9780441172719"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["year"] == 1966
    assert body["title"] == "Dune"  # untouched fields preserved


def test_update_missing_book_returns_404(client):
    response = client.put("/books/999", json={"title": "New Title"})
    assert response.status_code == 404


def test_update_with_invalid_data_returns_400(client):
    create_book(client)
    response = client.put("/books/1", json={"title": ""})
    assert response.status_code == 400


def test_delete_book(client):
    create_book(client)
    assert client.delete("/books/1").status_code == 204
    assert client.get("/books/1").status_code == 404


def test_delete_missing_book_returns_404(client):
    assert client.delete("/books/999").status_code == 404
