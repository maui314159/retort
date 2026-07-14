import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, BookDB, Base, get_db

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book():
    book_data = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "9780743273565"
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
    # Missing required fields
    response = client.post("/books", json={"title": "Test"})
    assert response.status_code == 422
    
    # Invalid year
    response = client.post("/books", json={
        "title": "Test",
        "author": "Author",
        "year": 50
    })
    assert response.status_code == 422

def test_list_books():
    # Create two books
    client.post("/books", json={
        "title": "Book 1",
        "author": "Author A",
        "year": 2000
    })
    client.post("/books", json={
        "title": "Book 2",
        "author": "Author B",
        "year": 2010
    })
    
    response = client.get("/books")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 2
    assert books[0]["title"] == "Book 1"
    assert books[1]["title"] == "Book 2"

def test_list_books_with_author_filter():
    # Create books
    client.post("/books", json={
        "title": "Book A",
        "author": "John Smith",
        "year": 2000
    })
    client.post("/books", json={
        "title": "Book B",
        "author": "Jane Doe",
        "year": 2010
    })
    
    # Filter by author
    response = client.get("/books?author=Smith")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["author"] == "John Smith"

def test_get_book():
    # Create a book
    create_response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2020
    })
    book_id = create_response.json()["id"]
    
    # Retrieve it
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book_id
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"

def test_get_book_not_found():
    response = client.get("/books/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"

def test_update_book():
    # Create a book
    create_response = client.post("/books", json={
        "title": "Original Title",
        "author": "Original Author",
        "year": 2000
    })
    book_id = create_response.json()["id"]
    
    # Update it
    update_data = {"title": "Updated Title", "year": 2020}
    response = client.put(f"/books/{book_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["year"] == 2020
    assert data["author"] == "Original Author"  # Should remain unchanged
    
    # Verify update persisted
    get_response = client.get(f"/books/{book_id}")
    assert get_response.json()["title"] == "Updated Title"

def test_update_book_not_found():
    response = client.put("/books/999", json={"title": "New Title"})
    assert response.status_code == 404

def test_delete_book():
    # Create a book
    create_response = client.post("/books", json={
        "title": "To Delete",
        "author": "Author",
        "year": 2000
    })
    book_id = create_response.json()["id"]
    
    # Delete it
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404

def test_delete_book_not_found():
    response = client.delete("/books/999")
    assert response.status_code == 404