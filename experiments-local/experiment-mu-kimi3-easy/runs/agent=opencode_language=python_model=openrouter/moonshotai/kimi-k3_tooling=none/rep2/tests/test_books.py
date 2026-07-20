import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    """A Flask test client backed by a fresh, temporary SQLite DB per test."""
    app = create_app(str(tmp_path / "test_books.db"))
    return app.test_client()


SAMPLE_BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post("/books", json=SAMPLE_BOOK)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] >= 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441172719"


def test_create_book_requires_title_and_author(client):
    assert client.post("/books", json={"author": "X"}).status_code == 400
    assert client.post("/books", json={"title": "X"}).status_code == 400
    assert client.post("/books", json={"title": "   ", "author": "X"}).status_code == 400
    assert client.post("/books", json={}).status_code == 400
    assert client.post("/books").status_code == 400  # no JSON body at all


def test_list_books_and_author_filter(client):
    client.post("/books", json=SAMPLE_BOOK)
    client.post("/books", json={"title": "Dune Messiah", "author": "Frank Herbert"})
    client.post("/books", json={"title": "The Hobbit", "author": "J.R.R. Tolkien"})

    all_books = client.get("/books").get_json()
    assert len(all_books) == 3

    resp = client.get("/books?author=Frank Herbert")
    assert resp.status_code == 200
    titles = {b["title"] for b in resp.get_json()}
    assert titles == {"Dune", "Dune Messiah"}

    assert client.get("/books?author=Nobody").get_json() == []


def test_get_book_and_404(client):
    created = client.post("/books", json=SAMPLE_BOOK).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"

    assert client.get("/books/9999").status_code == 404


def test_update_book(client):
    created = client.post("/books", json=SAMPLE_BOOK).get_json()
    update = {"title": "Dune (Revised)", "author": "Frank Herbert", "year": 1966, "isbn": "9780441172719"}
    resp = client.put(f"/books/{created['id']}", json=update)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == created["id"]
    assert body["title"] == "Dune (Revised)"
    assert body["year"] == 1966

    # Validation still applies on update
    assert client.put(f"/books/{created['id']}", json={"title": "Only"}).status_code == 400
    # Updating a missing book returns 404
    assert client.put("/books/9999", json=update).status_code == 404


def test_delete_book(client):
    created = client.post("/books", json=SAMPLE_BOOK).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.delete(f"/books/{created['id']}").status_code == 404
