import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_book(client):
    payload = {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937}
    response = client.post("/books", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["author"] == payload["author"]
    assert data["year"] == payload["year"]
    assert "id" in data


def test_create_book_missing_title(client):
    response = client.post("/books", json={"author": "Anonymous"})
    assert response.status_code == 422


def test_get_book(client):
    create_resp = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965}
    )
    book_id = create_resp.json()["id"]

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Dune"


def test_get_book_not_found(client):
    response = client.get("/books/9999")
    assert response.status_code == 404


def test_list_books_with_author_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})

    response = client.get("/books?author=Alice")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "Alice"


def test_update_book(client):
    create_resp = client.post(
        "/books", json={"title": "Old Title", "author": "Old Author"}
    )
    book_id = create_resp.json()["id"]

    response = client.put(
        f"/books/{book_id}", json={"title": "New Title", "year": 2020}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["author"] == "Old Author"
    assert data["year"] == 2020


def test_delete_book(client):
    create_resp = client.post("/books", json={"title": "To Delete", "author": "X"})
    book_id = create_resp.json()["id"]

    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204

    get_resp = client.get(f"/books/{book_id}")
    assert get_resp.status_code == 404
