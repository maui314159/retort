import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Point DB to a temp file before importing app
TEST_DB_URL = "sqlite:///./test_books.db"

from database import Base, get_db
from main import app

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_book(client):
    payload = {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273565"}
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["title"] == "The Great Gatsby"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1925
    assert data["isbn"] == "9780743273565"

    # GET single
    resp = client.get("/books/1")
    assert resp.status_code == 200
    assert resp.json()["title"] == "The Great Gatsby"


def test_list_books_and_author_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})

    # All books
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Filter by author
    resp = client.get("/books", params={"author": "Alice"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Book A"


def test_update_book(client):
    client.post("/books", json={"title": "Old Title", "author": "Author"})
    resp = client.put("/books/1", json={"title": "New Title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"
    assert resp.json()["author"] == "Author"


def test_delete_book(client):
    client.post("/books", json={"title": "To Delete", "author": "Author"})
    resp = client.delete("/books/1")
    assert resp.status_code == 204

    resp = client.get("/books/1")
    assert resp.status_code == 404


def test_404_on_missing_book(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404


def test_validation_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 422

    resp = client.post("/books", json={"title": "  ", "author": "Author"})
    assert resp.status_code == 422

    resp = client.post("/books", json={"title": "Title", "author": "   "})
    assert resp.status_code == 422
