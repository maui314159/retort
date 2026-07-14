import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_book():
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
    response = client.post("/books", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert data["year"] == 1965
    assert data["isbn"] == "978-0441172719"
    assert "id" in data


def test_create_book_missing_title():
    response = client.post("/books", json={"author": "Author"})
    assert response.status_code == 422


def test_create_book_missing_author():
    response = client.post("/books", json={"title": "Title"})
    assert response.status_code == 422


def test_create_duplicate_isbn():
    client.post("/books", json={"title": "Book1", "author": "A", "isbn": "123"})
    response = client.post("/books", json={"title": "Book2", "author": "B", "isbn": "123"})
    assert response.status_code == 409


def test_list_books():
    client.post("/books", json={"title": "Book A", "author": "Author1"})
    client.post("/books", json={"title": "Book B", "author": "Author2"})
    response = client.get("/books")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_books_filter_author():
    client.post("/books", json={"title": "Book A", "author": "Author1"})
    client.post("/books", json={"title": "Book B", "author": "Author2"})
    response = client.get("/books?author=Author1")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["author"] == "Author1"


def test_get_book():
    res = client.post("/books", json={"title": "1984", "author": "George Orwell"})
    book_id = res.json()["id"]
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "1984"


def test_get_book_not_found():
    response = client.get("/books/9999")
    assert response.status_code == 404


def test_update_book():
    res = client.post("/books", json={"title": "Old", "author": "Auth"})
    book_id = res.json()["id"]
    response = client.put(f"/books/{book_id}", json={"title": "New"})
    assert response.status_code == 200
    assert response.json()["title"] == "New"
    assert response.json()["author"] == "Auth"


def test_delete_book():
    res = client.post("/books", json={"title": "ToDelete", "author": "Auth"})
    book_id = res.json()["id"]
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_book_not_found():
    response = client.delete("/books/9999")
    assert response.status_code == 404
