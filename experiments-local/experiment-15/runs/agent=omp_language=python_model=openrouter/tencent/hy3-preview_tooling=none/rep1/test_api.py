import pytest
from fastapi.testclient import TestClient
from main import app
import database
import os

@pytest.fixture(autouse=True)
def setup_database():
    """Set up a fresh database for each test."""
    # Remove existing db
    if os.path.exists(database.DB_PATH):
        os.remove(database.DB_PATH)
    # Initialize fresh database
    database.init_db()
    yield
    # Cleanup
    if os.path.exists(database.DB_PATH):
        os.remove(database.DB_PATH)

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test that health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "book-collection-api"

class TestCreateBook:
    """Tests for creating books."""

    def test_create_book_success(self, client):
        """Test successful book creation."""
        book_data = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "9780743273565"
        }
        response = client.post("/books", json=book_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert data["year"] == 1925
        assert data["isbn"] == "9780743273565"
        assert "id" in data

    def test_create_book_minimal(self, client):
        """Test creating a book with only required fields."""
        book_data = {
            "title": "1984",
            "author": "George Orwell"
        }
        response = client.post("/books", json=book_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "1984"
        assert data["author"] == "George Orwell"
        assert data["year"] is None
        assert data["isbn"] is None

    def test_create_book_missing_title(self, client):
        """Test that creating a book without title fails."""
        book_data = {
            "author": "George Orwell"
        }
        response = client.post("/books", json=book_data)
        assert response.status_code == 422  # Validation error

    def test_create_book_missing_author(self, client):
        """Test that creating a book without author fails."""
        book_data = {
            "title": "1984"
        }
        response = client.post("/books", json=book_data)
        assert response.status_code == 422  # Validation error

    def test_create_book_duplicate_isbn(self, client):
        """Test that creating books with duplicate ISBN fails."""
        book_data = {
            "title": "Book 1",
            "author": "Author 1",
            "isbn": "1234567890"
        }
        response1 = client.post("/books", json=book_data)
        assert response1.status_code == 201

        # Try to create another book with same ISBN
        book_data2 = {
            "title": "Book 2",
            "author": "Author 2",
            "isbn": "1234567890"
        }
        response2 = client.post("/books", json=book_data2)
        assert response2.status_code == 400

class TestListBooks:
    """Tests for listing books."""

    def test_list_books_empty(self, client):
        """Test listing books when database is empty."""
        response = client.get("/books")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_books_multiple(self, client):
        """Test listing multiple books."""
        # Create test books
        books = [
            {"title": "Book 1", "author": "Author A", "year": 2020},
            {"title": "Book 2", "author": "Author B", "year": 2021},
            {"title": "Book 3", "author": "Author A", "year": 2022}
        ]
        for book in books:
            client.post("/books", json=book)

        response = client.get("/books")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client):
        """Test filtering books by author."""
        # Create test books
        books = [
            {"title": "Book 1", "author": "Author A", "year": 2020},
            {"title": "Book 2", "author": "Author B", "year": 2021},
            {"title": "Book 3", "author": "Author A", "year": 2022}
        ]
        for book in books:
            client.post("/books", json=book)

        # Filter by author
        response = client.get("/books?author=Author A")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for book in data:
            assert "Author A" in book["author"]

    def test_list_books_filter_no_match(self, client):
        """Test filtering with no matching author."""
        # Create a test book
        client.post("/books", json={"title": "Book 1", "author": "Author A"})

        response = client.get("/books?author=NonExistent")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

class TestGetBook:
    """Tests for getting a single book."""

    def test_get_book_success(self, client):
        """Test getting a book by ID."""
        # Create a book
        book_data = {"title": "Test Book", "author": "Test Author", "year": 2023}
        create_response = client.post("/books", json=book_data)
        book_id = create_response.json()["id"]

        # Get the book
        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id
        assert data["title"] == "Test Book"
        assert data["author"] == "Test Author"

    def test_get_book_not_found(self, client):
        """Test getting a non-existent book."""
        response = client.get("/books/999")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

class TestUpdateBook:
    """Tests for updating books."""

    def test_update_book_success(self, client):
        """Test successful book update."""
        # Create a book
        book_data = {"title": "Original Title", "author": "Original Author", "year": 2020}
        create_response = client.post("/books", json=book_data)
        book_id = create_response.json()["id"]

        # Update the book
        update_data = {"title": "Updated Title", "year": 2023}
        response = client.put(f"/books/{book_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id
        assert data["title"] == "Updated Title"
        assert data["author"] == "Original Author"  # Unchanged
        assert data["year"] == 2023

    def test_update_book_not_found(self, client):
        """Test updating a non-existent book."""
        update_data = {"title": "Updated Title"}
        response = client.put("/books/999", json=update_data)
        assert response.status_code == 404

    def test_update_book_partial(self, client):
        """Test partial update of a book."""
        # Create a book
        book_data = {"title": "Title", "author": "Author", "year": 2020, "isbn": "123"}
        create_response = client.post("/books", json=book_data)
        book_id = create_response.json()["id"]

        # Update only the year
        update_data = {"year": 2024}
        response = client.put(f"/books/{book_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2024
        assert data["title"] == "Title"  # Unchanged

class TestDeleteBook:
    """Tests for deleting books."""

    def test_delete_book_success(self, client):
        """Test successful book deletion."""
        # Create a book
        book_data = {"title": "To Delete", "author": "Author"}
        create_response = client.post("/books", json=book_data)
        book_id = create_response.json()["id"]

        # Delete the book
        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Test deleting a non-existent book."""
        response = client.delete("/books/999")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
