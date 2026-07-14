import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, Base, engine, SessionLocal, BookDB, get_db

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_books.db"
test_engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def setup_database():
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Cleanup
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(setup_database):
    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestHealthEndpoint:
    def test_health_check(self):
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}


class TestCreateBook:
    def test_create_book_success(self, client):
        response = client.post("/books", json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "9780743273565"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert data["year"] == 1925
        assert "id" in data

    def test_create_book_minimal(self, client):
        response = client.post("/books", json={
            "title": "1984",
            "author": "George Orwell"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "1984"
        assert data["author"] == "George Orwell"
        assert data["year"] is None
        assert data["isbn"] is None

    def test_create_book_missing_title(self, client):
        response = client.post("/books", json={
            "author": "George Orwell"
        })
        assert response.status_code == 422

    def test_create_book_missing_author(self, client):
        response = client.post("/books", json={
            "title": "1984"
        })
        assert response.status_code == 422

    def test_create_book_empty_title(self, client):
        response = client.post("/books", json={
            "title": "",
            "author": "George Orwell"
        })
        assert response.status_code == 422

    def test_create_book_duplicate_isbn(self, client):
        book_data = {
            "title": "Book 1",
            "author": "Author 1",
            "isbn": "1234567890"
        }
        response1 = client.post("/books", json=book_data)
        assert response1.status_code == 201

        # Try to create another with same ISBN
        book_data2 = {
            "title": "Book 2",
            "author": "Author 2",
            "isbn": "1234567890"
        }
        response2 = client.post("/books", json=book_data2)
        assert response2.status_code == 400
        assert "ISBN already exists" in response2.json()["detail"]


class TestListBooks:
    def test_list_books_empty(self, client):
        response = client.get("/books")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_books_multiple(self, client):
        # Create some books
        client.post("/books", json={"title": "Book 1", "author": "Author A"})
        client.post("/books", json={"title": "Book 2", "author": "Author B"})
        client.post("/books", json={"title": "Book 3", "author": "Author A"})

        response = client.get("/books")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client):
        client.post("/books", json={"title": "Book 1", "author": "George Orwell"})
        client.post("/books", json={"title": "Book 2", "author": "Aldous Huxley"})

        response = client.get("/books?author=orwell")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["author"] == "George Orwell"


class TestGetBook:
    def test_get_book_success(self, client):
        create_response = client.post("/books", json={
            "title": "1984",
            "author": "George Orwell"
        })
        book_id = create_response.json()["id"]

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id
        assert data["title"] == "1984"

    def test_get_book_not_found(self, client):
        response = client.get("/books/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Book not found"


class TestUpdateBook:
    def test_update_book_success(self, client):
        create_response = client.post("/books", json={
            "title": "1984",
            "author": "George Orwell",
            "year": 1949
        })
        book_id = create_response.json()["id"]

        response = client.put(f"/books/{book_id}", json={
            "title": "1984 (Updated)",
            "year": 1950
        })
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "1984 (Updated)"
        assert data["author"] == "George Orwell"  # Unchanged
        assert data["year"] == 1950

    def test_update_book_not_found(self, client):
        response = client.put("/books/999", json={"title": "Updated"})
        assert response.status_code == 404

    def test_update_book_duplicate_isbn(self, client):
        client.post("/books", json={
            "title": "Book 1",
            "author": "Author 1",
            "isbn": "1234567890"
        })
        create_response2 = client.post("/books", json={
            "title": "Book 2",
            "author": "Author 2",
            "isbn": "0987654321"
        })
        book_id_2 = create_response2.json()["id"]

        # Try to update book 2 with book 1's ISBN
        response = client.put(f"/books/{book_id_2}", json={
            "isbn": "1234567890"
        })
        assert response.status_code == 400
        assert "ISBN already exists" in response.json()["detail"]


class TestDeleteBook:
    def test_delete_book_success(self, client):
        create_response = client.post("/books", json={
            "title": "To Delete",
            "author": "Author"
        })
        book_id = create_response.json()["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == 404

    def test_delete_book_not_found(self, client):
        response = client.delete("/books/999")
        assert response.status_code == 404
