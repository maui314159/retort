import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    response = client.post(
        "/books",
        json={"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "9780451524935"},
    )
    assert response.status_code == 201
    book = response.get_json()
    assert book["title"] == "1984"
    assert book["author"] == "George Orwell"
    assert book["year"] == 1949
    assert book["isbn"] == "9780451524935"
    assert book["id"] == 1

    fetched = client.get(f"/books/{book['id']}")
    assert fetched.status_code == 200
    assert fetched.get_json() == book


def test_create_book_requires_title_and_author(client):
    response = client.post("/books", json={"year": 2000})
    assert response.status_code == 400
    assert "title" in response.get_json()["error"]

    response = client.post("/books", json={"title": "Some Title"})
    assert response.status_code == 400
    assert "author" in response.get_json()["error"]

    response = client.post("/books", json={"title": "", "author": "A"})
    assert response.status_code == 400


def test_create_book_rejects_invalid_types(client):
    response = client.post("/books", json={"title": "T", "author": "A", "year": "1949"})
    assert response.status_code == 400
    assert "year" in response.get_json()["error"]

    response = client.post("/books", json={"title": "T", "author": "A", "isbn": 12345})
    assert response.status_code == 400

    response = client.post("/books", json={"title": 42, "author": "A"})
    assert response.status_code == 400


def test_create_book_rejects_non_json_body(client):
    response = client.post("/books", data="not json", content_type="text/plain")
    assert response.status_code == 400

    response = client.post("/books")
    assert response.status_code == 400


def test_create_book_allows_omitting_optional_fields(client):
    response = client.post("/books", json={"title": "T", "author": "A"})
    assert response.status_code == 201
    book = response.get_json()
    assert book["year"] is None
    assert book["isbn"] is None


def test_list_books_with_author_filter(client):
    client.post("/books", json={"title": "1984", "author": "George Orwell"})
    client.post("/books", json={"title": "Animal Farm", "author": "George Orwell"})
    client.post("/books", json={"title": "Brave New World", "author": "Aldous Huxley"})

    response = client.get("/books")
    assert response.status_code == 200
    assert len(response.get_json()) == 3

    response = client.get("/books", query_string={"author": "orwell"})
    books = response.get_json()
    assert {b["title"] for b in books} == {"1984", "Animal Farm"}

    response = client.get("/books", query_string={"author": "Nobody"})
    assert response.get_json() == []


def test_get_missing_book_returns_404(client):
    response = client.get("/books/999")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old Title", "author": "Old Author"}
    ).get_json()
    response = client.put(
        f"/books/{created['id']}",
        json={"title": "New Title", "author": "New Author", "year": 2020},
    )
    assert response.status_code == 200
    assert response.get_json() == {
        "id": created["id"],
        "title": "New Title",
        "author": "New Author",
        "year": 2020,
        "isbn": None,
    }


def test_update_book_requires_title_and_author(client):
    created = client.post("/books", json={"title": "T", "author": "A"}).get_json()
    response = client.put(f"/books/{created['id']}", json={"title": "Only Title"})
    assert response.status_code == 400


def test_update_missing_book_returns_404(client):
    response = client.put("/books/999", json={"title": "T", "author": "A"})
    assert response.status_code == 404


def test_delete_book(client):
    created = client.post("/books", json={"title": "T", "author": "A"}).get_json()
    response = client.delete(f"/books/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/999")
    assert response.status_code == 404
