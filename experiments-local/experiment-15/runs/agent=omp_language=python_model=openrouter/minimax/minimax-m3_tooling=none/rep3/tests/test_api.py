import pytest
from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_book_returns_201_and_persists(client: TestClient) -> None:
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
    response = client.post("/books", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978-0441172719"

    fetched = client.get(f"/books/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_create_book_rejects_missing_title_and_author(client: TestClient) -> None:
    for bad in (
        {"author": "Anonymous"},
        {"title": ""},
        {"title": "x", "author": ""},
        {"title": "x", "author": "y", "year": -1},
        {"title": "x", "author": "y", "year": 10000},
    ):
        response = client.post("/books", json=bad)
        assert response.status_code == 422, f"expected 422 for payload {bad!r}"


def test_list_books_supports_author_filter(client: TestClient) -> None:
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
    client.post("/books", json={"title": "Children of Dune", "author": "Frank Herbert", "year": 1976})
    client.post("/books", json={"title": "Neuromancer", "author": "William Gibson", "year": 1984})

    all_books = client.get("/books")
    assert all_books.status_code == 200
    assert len(all_books.json()) == 3

    filtered = client.get("/books", params={"author": "frank"})
    assert filtered.status_code == 200
    titles = {book["title"] for book in filtered.json()}
    assert titles == {"Dune", "Children of Dune"}


def test_get_missing_book_returns_404(client: TestClient) -> None:
    response = client.get("/books/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


def test_update_book_replaces_fields(client: TestClient) -> None:
    created = client.post(
        "/books", json={"title": "Old", "author": "A", "year": 2000, "isbn": "111"}
    ).json()

    updated = client.put(
        f"/books/{created['id']}",
        json={"title": "New", "author": "B", "year": 2010, "isbn": "222"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body == {
        "id": created["id"],
        "title": "New",
        "author": "B",
        "year": 2010,
        "isbn": "222",
    }


def test_update_missing_book_returns_404(client: TestClient) -> None:
    response = client.put("/books/999", json={"title": "x", "author": "y"})
    assert response.status_code == 404


def test_delete_book_removes_it(client: TestClient) -> None:
    created = client.post("/books", json={"title": "Temp", "author": "Z"}).json()
    delete = client.delete(f"/books/{created['id']}")
    assert delete.status_code == 204
    assert delete.content == b""
    follow_up = client.get(f"/books/{created['id']}")
    assert follow_up.status_code == 404


def test_delete_missing_book_returns_404(client: TestClient) -> None:
    response = client.delete("/books/999")
    assert response.status_code == 404


@pytest.mark.parametrize("bad_year", [0, -5, 10000])
def test_year_bounds_are_enforced(client: TestClient, bad_year: int) -> None:
    response = client.post("/books", json={"title": "x", "author": "y", "year": bad_year})
    assert response.status_code == 422
