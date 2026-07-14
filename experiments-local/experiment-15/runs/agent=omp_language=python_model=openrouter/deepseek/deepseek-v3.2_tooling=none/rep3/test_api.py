import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db, Base, BookDB

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_books.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up after tests
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    """Test health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book():
    """Test creating a new book."""
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "isbn": "123-4567890123"
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == book_data["title"]
    assert data["author"] == book_data["author"]
    assert data["year"] == book_data["year"]
    assert data["isbn"] == book_data["isbn"]
    assert "id" in data

def test_create_book_validation():
    """Test validation for required fields."""
    # Missing title
    response = client.post("/books", json={"author": "Author Only"})
    assert response.status_code == 422
    
    # Missing author
    response = client.post("/books", json={"title": "Title Only"})
    assert response.status_code == 422
    
    # Invalid year
    response = client.post("/books", json={
        "title": "Test",
        "author": "Test",
        "year": 999  # Too low
    })
    assert response.status_code == 422

def test_list_books():
    """Test listing all books."""
    # Create test books
    books = [
        {"title": "Book 1", "author": "Author A", "year": 2020},
        {"title": "Book 2", "author": "Author B", "year": 2021},
        {"title": "Book 3", "author": "Author A", "year": 2022},
    ]
    
    for book in books:
        client.post("/books", json=book)
    
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

def test_list_books_with_author_filter():
    """Test filtering books by author."""
    # Create test books
    books = [
        {"title": "Book 1", "author": "John Doe", "year": 2020},
        {"title": "Book 2", "author": "Jane Smith", "year": 2021},
        {"title": "Book 3", "author": "John Doe", "year": 2022},
    ]
    
    for book in books:
        client.post("/books", json=book)
    
    # Filter by author
    response = client.get("/books?author=John")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("John" in book["author"] for book in data)

def test_get_book():
    """Test getting a single book by ID."""
    # Create a book first
    book_data = {"title": "Test Book", "author": "Test Author"}
    create_response = client.post("/books", json=book_data)
    book_id = create_response.json()["id"]
    
    # Get the book
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book_id
    assert data["title"] == book_data["title"]
    assert data["author"] == book_data["author"]

def test_get_book_not_found():
    """Test getting a non-existent book returns 404."""
    response = client.get("/books/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"

def test_update_book():
    """Test updating a book."""
    # Create a book first
    book_data = {"title": "Original Title", "author": "Original Author", "year": 2020}
    create_response = client.post("/books", json=book_data)
    book_id = create_response.json()["id"]
    
    # Update the book
    update_data = {"title": "Updated Title", "year": 2021}
    response = client.put(f"/books/{book_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["author"] == "Original Author"  # Unchanged
    assert data["year"] == 2021

def test_update_book_not_found():
    """Test updating a non-existent book returns 404."""
    response = client.put("/books/999", json={"title": "New Title"})
    assert response.status_code == 404

def test_delete_book():
    """Test deleting a book."""
    # Create a book first
    book_data = {"title": "To Delete", "author": "Author"}
    create_response = client.post("/books", json=book_data)
    book_id = create_response.json()["id"]
    
    # Delete the book
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    
    # Verify book is deleted
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404

def test_delete_book_not_found():
    """Test deleting a non-existent book returns 404."""
    response = client.delete("/books/999")
    assert response.status_code == 404

def test_isbn_validation():
    """Test ISBN validation pattern."""
    # Valid ISBN
    response = client.post("/books", json={
        "title": "Test",
        "author": "Test",
        "isbn": "978-3-16-148410-0"
    })
    assert response.status_code == 201
    
    # Invalid ISBN (contains letters)
    response = client.post("/books", json={
        "title": "Test",
        "author": "Test",
        "isbn": "ABC-123"
    })
    assert response.status_code == 422