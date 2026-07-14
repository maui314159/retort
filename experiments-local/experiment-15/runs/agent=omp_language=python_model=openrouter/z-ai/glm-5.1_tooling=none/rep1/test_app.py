"""Integration tests for the Book Collection API."""

import os
import pytest
from httpx import ASGITransport, AsyncClient

# Force in-memory SQLite so tests never touch the on-disk DB
os.environ["TESTING"] = "1"

from app import app, DB_PATH, _init_db, _get_db  # noqa: E402


# Use a fresh in-memory database per test by patching the connection factory
# before the app's startup event runs.

@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def client(tmp_path, monkeypatch):
    """Provide an async test client backed by a temp SQLite file."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("app.DB_PATH", db_file)
    _init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _book_payload(**overrides):
    payload = {"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "year": 1999, "isbn": "978-0201616224"}
    payload.update(overrides)
    return payload


# ── Tests ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_create_and_get_book(client):
    resp = await client.post("/books", json=_book_payload())
    assert resp.status_code == 201
    book = resp.json()
    assert book["id"] == 1
    assert book["title"] == "The Pragmatic Programmer"

    resp = await client.get("/books/1")
    assert resp.status_code == 200
    assert resp.json()["author"] == "Andrew Hunt"


@pytest.mark.anyio
async def test_list_books_and_author_filter(client):
    await client.post("/books", json=_book_payload())
    await client.post("/books", json=_book_payload(title="Clean Code", author="Robert C. Martin", year=2008))

    resp = await client.get("/books")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = await client.get("/books", params={"author": "Robert C. Martin"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Clean Code"


@pytest.mark.anyio
async def test_update_book(client):
    await client.post("/books", json=_book_payload())
    resp = await client.put("/books/1", json={"year": 2020})
    assert resp.status_code == 200
    assert resp.json()["year"] == 2020
    assert resp.json()["title"] == "The Pragmatic Programmer"  # unchanged


@pytest.mark.anyio
async def test_delete_book(client):
    await client.post("/books", json=_book_payload())
    resp = await client.delete("/books/1")
    assert resp.status_code == 204

    resp = await client.get("/books/1")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_nonexistent_book(client):
    resp = await client.get("/books/999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_book_validation(client):
    resp = await client.post("/books", json={"title": "", "author": "Someone"})
    assert resp.status_code == 422

    resp = await client.post("/books", json={"title": "A Book"})
    assert resp.status_code == 422
