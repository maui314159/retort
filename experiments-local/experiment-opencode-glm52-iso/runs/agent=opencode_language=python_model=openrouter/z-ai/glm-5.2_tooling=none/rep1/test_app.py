"""Test suite for the book collection API.

Uses a temporary on-disk SQLite database so each test run is isolated.
"""
import os
import tempfile

import pytest

import app as app_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_books.db"
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path))
    app_module.init_db(str(db_path))

    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as c:
        with app_module.app.app_context():
            yield c


def make_book(client, title="Dune", author="Frank Herbert", year=1965, isbn="9780441172719"):
    return client.post(
        "/books",
        json={"title": title, "author": author, "year": year, "isbn": isbn},
    )


def test_create_and_get_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert data["year"] == 1965
    assert data["isbn"] == "9780441172719"
    assert isinstance(data["id"], int)

    get_resp = client.get(f"/books/{data['id']}")
    assert get_resp.status_code == 200
    assert get_resp.get_json() == data


def test_list_and_filter_by_author(client):
    make_book(client, title="Dune", author="Frank Herbert")
    make_book(client, title="1984", author="George Orwell")
    make_book(client, title="Animal Farm", author="George Orwell")

    all_resp = client.get("/books")
    assert all_resp.status_code == 200
    assert len(all_resp.get_json()) == 3

    filtered = client.get("/books?author=George Orwell")
    assert filtered.status_code == 200
    titles = {b["title"] for b in filtered.get_json()}
    assert titles == {"1984", "Animal Farm"}


def test_update_and_delete_book(client):
    create = make_book(client, title="Old Title", author="Author A")
    bid = create.get_json()["id"]

    upd = client.put(f"/books/{bid}", json={"title": "New Title"})
    assert upd.status_code == 200
    assert upd.get_json()["title"] == "New Title"
    assert upd.get_json()["author"] == "Author A"

    dele = client.delete(f"/books/{bid}")
    assert dele.status_code == 200
    assert dele.get_json()["deleted"] == bid

    missing = client.get(f"/books/{bid}")
    assert missing.status_code == 404


def test_validation_errors(client):
    bad = client.post("/books", json={"author": "No Title"})
    assert bad.status_code == 400
    assert "title" in bad.get_json()["error"]

    bad2 = client.post("/books", json={"title": "No Author"})
    assert bad2.status_code == 400
    assert "author" in bad2.get_json()["error"]

    bad_year = client.post(
        "/books",
        json={"title": "T", "author": "A", "year": "not-a-year"},
    )
    assert bad_year.status_code == 400


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}
