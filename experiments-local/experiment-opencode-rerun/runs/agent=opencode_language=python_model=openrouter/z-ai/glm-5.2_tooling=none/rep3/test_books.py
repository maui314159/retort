import os
import tempfile

import pytest

from app import app, init_db


@pytest.fixture()
def client(tmp_path):
    db_path = os.path.join(tmp_path, "test_books.db")
    init_db(db_path)
    os.environ["BOOKS_DB_PATH"] = db_path
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    os.environ.pop("BOOKS_DB_PATH", None)


def test_create_get_and_delete_book(client):
    resp = client.post("/books", json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "1"})
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["title"] == "Dune"
    bid = book["id"]

    resp = client.get(f"/books/{bid}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Herbert"

    resp = client.delete(f"/books/{bid}")
    assert resp.status_code == 204
    resp = client.get(f"/books/{bid}")
    assert resp.status_code == 404


def test_validation_errors(client):
    resp = client.post("/books", json={"year": 1999})
    assert resp.status_code == 400
    body = resp.get_json()
    assert "title is required" in body["errors"]
    assert "author is required" in body["errors"]

    resp = client.post("/books", json={"title": "X", "author": "Y", "year": "abc"})
    assert resp.status_code == 400


def test_list_filter_and_update(client):
    client.post("/books", json={"title": "A", "author": "Asimov", "year": 1951})
    client.post("/books", json={"title": "B", "author": "Clarke", "year": 1968})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2

    resp = client.get("/books?author=Asimov")
    assert len(resp.get_json()) == 1
    assert resp.get_json()[0]["title"] == "A"

    books = client.get("/books").get_json()
    bid = books[0]["id"]
    resp = client.put(f"/books/{bid}", json={"title": "A2"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "A2"

    resp = client.put(f"/books/{bid}", json={"title": ""})
    assert resp.status_code == 400


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}
