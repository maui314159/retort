import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_books.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_book(client):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
    response = client.post("/books", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert data["year"] == 1965
    assert data["isbn"] == "978-0441172719"
    assert "id" in data


def test_create_book_missing_title(client):
    payload = {"author": "Frank Herbert"}
    response = client.post("/books", json=payload)
    assert response.status_code == 422


def test_create_book_missing_author(client):
    payload = {"title": "Dune"}
    response = client.post("/books", json=payload)
    assert response.status_code == 422


def test_list_books(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "1984", "author": "George Orwell"})
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_books_filter_by_author(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "1984", "author": "George Orwell"})
    response = client.get("/books?author=Orwell")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "George Orwell"


def test_get_book(client):
    create_response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = create_response.json()["id"]
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json()["id"] == book_id


def test_get_book_not_found(client):
    response = client.get("/books/999")
    assert response.status_code == 404


def test_update_book(client):
    create_response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = create_response.json()["id"]
    response = client.put(f"/books/{book_id}", json={"title": "Dune Messiah"})
    assert response.status_code == 200
    assert response.json()["title"] == "Dune Messiah"
    assert response.json()["author"] == "Frank Herbert"


def test_update_book_not_found(client):
    response = client.put("/books/999", json={"title": "Dune Messiah"})
    assert response.status_code == 404


def test_delete_book(client):
    create_response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = create_response.json()["id"]
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_book_not_found(client):
    response = client.delete("/books/999")
    assert response.status_code == 404
