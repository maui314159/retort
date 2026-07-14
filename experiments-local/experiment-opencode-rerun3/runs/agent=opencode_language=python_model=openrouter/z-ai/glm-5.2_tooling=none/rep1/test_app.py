import os
import tempfile
import sqlite3
import pytest

import app as app_module


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app_module.DATABASE = db_path
    app_module.init_db()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c
    os.close(db_fd)
    os.unlink(db_path)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    r = client.post(
        "/books",
        json={"title": "T", "author": "A", "year": 2020, "isbn": "123"},
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["title"] == "T"
    assert data["id"] is not None
    bid = data["id"]
    r2 = client.get(f"/books/{bid}")
    assert r2.status_code == 200
    assert r2.get_json()["author"] == "A"


def test_validation_missing_fields(client):
    r = client.post("/books", json={"year": 2020})
    assert r.status_code == 400
    errors = r.get_json()["errors"]
    assert "title" in errors
    assert "author" in errors


def test_list_filter_by_author(client):
    client.post("/books", json={"title": "A", "author": "X"})
    client.post("/books", json={"title": "B", "author": "Y"})
    client.post("/books", json={"title": "C", "author": "X"})
    r = client.get("/books?author=X")
    assert r.status_code == 200
    rows = r.get_json()
    assert len(rows) == 2
    assert all(row["author"] == "X" for row in rows)


def test_update_and_delete(client):
    r = client.post("/books", json={"title": "T", "author": "A"})
    bid = r.get_json()["id"]
    r2 = client.put(f"/books/{bid}", json={"title": "T2"})
    assert r2.status_code == 200
    assert r2.get_json()["title"] == "T2"
    r3 = client.delete(f"/books/{bid}")
    assert r3.status_code == 200
    r4 = client.get(f"/books/{bid}")
    assert r4.status_code == 404


def test_get_not_found(client):
    r = client.get("/books/9999")
    assert r.status_code == 404
