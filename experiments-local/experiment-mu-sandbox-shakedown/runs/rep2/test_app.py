import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def _create(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = _create(client)
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["year"] == 1965
    assert book["isbn"] == "978-0441172719"

    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == book


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2000})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "X", "author": ""})
    assert resp.status_code == 400

    resp = client.post("/books", json={"title": "X", "author": "A", "year": "old"})
    assert resp.status_code == 400

    resp = client.post("/books", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_list_books_with_author_filter(client):
    _create(client)
    _create(client, title="1984", author="George Orwell", year=1949, isbn=None)
    _create(client, title="Animal Farm", author="George Orwell", year=1945, isbn=None)

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books", query_string={"author": "orwell"})
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert {b["title"] for b in books} == {"1984", "Animal Farm"}

    resp = client.get("/books", query_string={"author": "nobody"})
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_update_book(client):
    book = _create(client).get_json()
    resp = client.put(
        f"/books/{book['id']}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] == 1969
    assert updated["id"] == book["id"]

    resp = client.put(f"/books/{book['id']}", json={"title": "No author"})
    assert resp.status_code == 400

    resp = client.put("/books/9999", json={"title": "T", "author": "A"})
    assert resp.status_code == 404


def test_delete_book(client):
    book = _create(client).get_json()
    resp = client.delete(f"/books/{book['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{book['id']}").status_code == 404

    resp = client.delete(f"/books/{book['id']}")
    assert resp.status_code == 404


def test_get_unknown_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
    assert resp.get_json()["error"]
