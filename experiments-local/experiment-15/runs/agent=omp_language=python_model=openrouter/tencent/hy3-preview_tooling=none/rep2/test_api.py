import pytest
from fastapi.testclient import TestClient
from main import app
import database
import os

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    """Clean up and initialize database before each test."""
    # Remove existing database
    if os.path.exists("books.db"):
        os.remove("books.db")
    # Initialize fresh database
    database.init_db()
    yield
    # Cleanup after test
    if os.path.exists("books.db"):
        os.remove("books.db")

class TestHealthEndpoint:
    def test_health_check(self):
        """Test that health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

class TestCreateBook:
    def test_create_book_success(self):
        """Test creating a book with all fields."""
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
        assert data["isbn"] == "9780743273565"
        assert "id" in data
        assert "created_at" in data

    def test_create_book_minimal(self):
        """Test creating a book with only required fields."""
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

    def test_create_book_missing_title(self):
        """Test that creating a book without title fails."""
        response = client.post("/books", json={
            "author": "George Orwell"
        })
        assert response.status_code == 422

    def test_create_book_missing_author(self):
        """Test that creating a book without author fails."""
        response = client.post("/books", json={
            "title": "1984"
        })
        assert response.status_code == 422

    def test_create_book_empty_title(self):
        """Test that creating a book with empty title fails."""
        response = client.post("/books", json={
            "title": "",
            "author": "George Orwell"
        })
        assert response.status_code == 422

    def test_create_book_invalid_year(self):
        """Test that creating a book with invalid year fails."""
        response = client.post("/books", json={
            "title": "Test Book",
            "author": "Test Author",
            "year": 3000
        })
        assert response.status_code == 422

class TestListBooks:
    def test_list_books_empty(self):
        """Test listing books when database is empty."""
        response = client.get("/books")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_books_multiple(self):
        """Test listing multiple books."""
        # Create some books
        client.post("/books", json={"title": "Book 1", "author": "Author A"})
        client.post("/books", json={"title": "Book 2", "author": "Author B"})
        client.post("/books", json={"title": "Book 3", "author": "Author A"})

        response = client.get("/books")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_list_books_filter_by_author(self):
        """Test filtering books by author."""
        client.post("/books", json={"title": "Book 1", "author": "Author A"})
        client.post("/books", json={"title": "Book 2", "author": "Author B"})
        client.post("/books", json={"title": "Book 3", "author": "Author A"})

        response = client.get("/books?author=Author A")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for book in data:
            assert "Author A" in book["author"]

    def test_list_books_filter_no_results(self):
        """Test filtering with author that doesn't exist."""
        client.post("/books", json={"title": "Book 1", "author": "Author A"})

        response = client.get("/books?author=NonExistent")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

class TestGetBook:
    def test_get_book_by_id(self):
        """Test getting a single book by ID."""
        create_response = client.post("/books", json={
            "title": "Test Book",
            "author": "Test Author"
        })
        book_id = create_response.json()["id"]

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id
        assert data["title"] == "Test Book"

    def test_get_book_not_found(self):
        """Test getting a non-existent book returns 404."""
        response = client.get("/books/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

class TestUpdateBook:
    def test_update_book_success(self):
        """Test updating a book's fields."""
        create_response = client.post("/books", json={
            "title": "Old Title",
            "author": "Old Author",
            "year": 2000
        })
        book_id = create_response.json()["id"]

        response = client.put(f"/books/{book_id}", json={
            "title": "New Title",
            "year": 2023
        })
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["author"] == "Old Author"  # Unchanged
        assert data["year"] == 2023

    def test_update_book_not_found(self):
        """Test updating a non-existent book returns 404."""
        response = client.put("/books/999", json={"title": "New Title"})
        assert response.status_code == 404

    def test_update_book_empty_title(self):
        """Test that updating with empty title fails."""
        create_response = client.post("/books", json={
            "title": "Test Book",
            "author": "Test Author"
        })
        book_id = create_response.json()["id"]

        response = client.put(f"/books/{book_id}", json={"title": ""})
        assert response.status_code == 422

    def test_update_book_no_fields(self):
        """Test updating with no fields returns current book."""
        create_response = client.post("/books", json={
            "title": "Test Book",
            "author": "Test Author"
        })
        book_id = create_response.json()["id"]

        response = client.put(f"/books/{book_id}", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Book"

class TestDeleteBook:
    def test_delete_book_success(self):
        """Test deleting a book."""
        create_response = client.post("/books", json={
            "title": "Test Book",
            "author": "Test Author"
        })
        book_id = create_response.json()["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == 404

    def test_delete_book_not_found(self):
        """Test deleting a non-existent book returns 404."""
        response = client.delete("/books/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_book_then_list(self):
        """Test that deleted book doesn't appear in list."""
        client.post("/books", json={"title": "Book 1", "author": "Author A"})
        create_response = client.post("/books", json={"title": "Book 2", "author": "Author B"})
        book_id = create_response.json()["id"]
        client.post("/books", json={"title": "Book 3", "author": "Author C"})

        client.delete(f"/books/{book_id}")

        response = client.get("/books")
        data = response.json()
        assert len(data) == 2
        book_ids = [b["id"] for b in data]
        assert book_id not in book_ids
