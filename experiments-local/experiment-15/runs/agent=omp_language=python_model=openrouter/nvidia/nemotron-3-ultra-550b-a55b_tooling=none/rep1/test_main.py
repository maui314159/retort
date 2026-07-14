import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from main import app
import database


@pytest.fixture(scope="function")
def client():
    """Create a test client with a fresh database."""
    # Use a temporary file database for tests (shared across connections)
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    original_db_path = database.DB_PATH
    database.DB_PATH = database.Path(db_path)
    database.init_db()
    
    with TestClient(app) as c:
        yield c
    
    # Cleanup
    database.DB_PATH = original_db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def sample_book():
    return {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "9780743273565",
    }


class TestHealthCheck:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCreateBook:
    def test_create_book_success(self, client, sample_book):
        response = client.post("/books", json=sample_book)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_book["title"]
        assert data["author"] == sample_book["author"]
        assert data["year"] == sample_book["year"]
        assert data["isbn"] == sample_book["isbn"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_book_missing_title(self, client):
        book = {"author": "Author", "year": 2020}
        response = client.post("/books", json=book)
        assert response.status_code == 422

    def test_create_book_missing_author(self, client):
        book = {"title": "Title", "year": 2020}
        response = client.post("/books", json=book)
        assert response.status_code == 422

    def test_create_book_empty_title(self, client):
        book = {"title": "", "author": "Author"}
        response = client.post("/books", json=book)
        assert response.status_code == 422

    def test_create_book_empty_author(self, client):
        book = {"title": "Title", "author": ""}
        response = client.post("/books", json=book)
        assert response.status_code == 422

    def test_create_book_invalid_year(self, client):
        book = {"title": "Title", "author": "Author", "year": 999}
        response = client.post("/books", json=book)
        assert response.status_code == 422

    def test_create_book_invalid_isbn(self, client):
        book = {"title": "Title", "author": "Author", "isbn": "invalid"}
        response = client.post("/books", json=book)
        assert response.status_code == 422


class TestListBooks:
    def test_list_books_empty(self, client):
        response = client.get("/books")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_books_with_data(self, client, sample_book):
        client.post("/books", json=sample_book)
        response = client.get("/books")
        assert response.status_code == 200
        books = response.json()
        assert len(books) == 1
        assert books[0]["title"] == sample_book["title"]

    def test_list_books_filter_by_author(self, client):
        book1 = {"title": "Book 1", "author": "Author A"}
        book2 = {"title": "Book 2", "author": "Author B"}
        client.post("/books", json=book1)
        client.post("/books", json=book2)

        response = client.get("/books?author=Author A")
        assert response.status_code == 200
        books = response.json()
        assert len(books) == 1
        assert books[0]["author"] == "Author A"

    def test_list_books_filter_partial_author(self, client):
        book1 = {"title": "Book 1", "author": "John Smith"}
        book2 = {"title": "Book 2", "author": "Jane Doe"}
        client.post("/books", json=book1)
        client.post("/books", json=book2)

        response = client.get("/books?author=John")
        assert response.status_code == 200
        books = response.json()
        assert len(books) == 1
        assert books[0]["author"] == "John Smith"


class TestGetBook:
    def test_get_book_success(self, client, sample_book):
        create_response = client.post("/books", json=sample_book)
        book_id = create_response.json()["id"]

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id
        assert data["title"] == sample_book["title"]

    def test_get_book_not_found(self, client):
        response = client.get("/books/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Book not found"


class TestUpdateBook:
    def test_update_book_success(self, client, sample_book):
        create_response = client.post("/books", json=sample_book)
        book_id = create_response.json()["id"]

        update_data = {"title": "Updated Title", "year": 2024}
        response = client.put(f"/books/{book_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["year"] == 2024
        assert data["author"] == sample_book["author"]  # unchanged

    def test_update_book_not_found(self, client):
        response = client.put("/books/999", json={"title": "New Title"})
        assert response.status_code == 404

    def test_update_book_no_fields(self, client, sample_book):
        create_response = client.post("/books", json=sample_book)
        book_id = create_response.json()["id"]

        response = client.put(f"/books/{book_id}", json={})
        assert response.status_code == 400
        assert response.json()["detail"] == "No fields to update"

    def test_update_book_invalid_year(self, client, sample_book):
        create_response = client.post("/books", json=sample_book)
        book_id = create_response.json()["id"]

        response = client.put(f"/books/{book_id}", json={"year": 999})
        assert response.status_code == 422

    def test_update_book_empty_title(self, client, sample_book):
        create_response = client.post("/books", json=sample_book)
        book_id = create_response.json()["id"]

        response = client.put(f"/books/{book_id}", json={"title": ""})
        assert response.status_code == 422


class TestDeleteBook:
    def test_delete_book_success(self, client, sample_book):
        create_response = client.post("/books", json=sample_book)
        book_id = create_response.json()["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == 404

    def test_delete_book_not_found(self, client):
        response = client.delete("/books/999")
        assert response.status_code == 404


class TestIntegration:
    def test_full_crud_flow(self, client):
        # Create
        book = {"title": "Integration Test", "author": "Test Author", "year": 2023}
        create_response = client.post("/books", json=book)
        assert create_response.status_code == 201
        book_id = create_response.json()["id"]

        # Read
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "Integration Test"

        # Update
        update_response = client.put(f"/books/{book_id}", json={"year": 2024})
        assert update_response.status_code == 200
        assert update_response.json()["year"] == 2024

        # List
        list_response = client.get("/books")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        # Delete
        delete_response = client.delete(f"/books/{book_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        final_list = client.get("/books")
        assert final_list.json() == []
