import os
os.environ["TESTING"] = "1"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from main import app
# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
# Use a shared in-memory SQLite database for testing (allows multiple connections)
SQLALCHEMY_DATABASE_URL = "sqlite:///file::memory:?cache=shared"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
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

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    from sqlalchemy import inspect
    print('Engine URL:', engine.url)
    Base.metadata.create_all(bind=engine)
    print('Tables after create:', inspect(engine).get_table_names())
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_book():
    response = client.post(
        "/books/",
        json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "The Great Gatsby"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1925
    assert data["isbn"] == "978-0743273565"
    assert "id" in data
    assert "created_at" in data

def test_create_book_validation():
    # Missing title
    response = client.post(
        "/books/",
        json={
            "author": "Author",
            "year": 2000
        }
    )
    assert response.status_code == 422  # Validation error
    
    # Empty title
    response = client.post(
        "/books/",
        json={
            "title": "",
            "author": "Author"
        }
    )
    assert response.status_code == 422

def test_get_book():
    # Create a book first
    create_resp = client.post(
        "/books/",
        json={
            "title": "1984",
            "author": "George Orwell",
            "year": 1949
        }
    )
    book_id = create_resp.json()["id"]
    
    # Get the book
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "1984"
    assert data["author"] == "George Orwell"

def test_get_nonexistent_book():
    response = client.get("/books/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"

def test_list_books():
    # Create two books
    client.post(
        "/books/",
        json={
            "title": "Book 1",
            "author": "Author A",
            "year": 2000
        }
    )
    client.post(
        "/books/",
        json={
            "title": "Book 2",
            "author": "Author B",
            "year": 2010
        }
    )
    
    response = client.get("/books/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = [book["title"] for book in data]
    assert "Book 1" in titles
    assert "Book 2" in titles

def test_list_books_filter():
    # Create books with different authors
    client.post(
        "/books/",
        json={
            "title": "Book A",
            "author": "John Smith",
            "year": 2000
        }
    )
    client.post(
        "/books/",
        json={
            "title": "Book B",
            "author": "Jane Doe",
            "year": 2010
        }
    )
    
    # Filter by author
    response = client.get("/books/?author=john")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "John Smith"

def test_update_book():
    # Create a book
    create_resp = client.post(
        "/books/",
        json={
            "title": "Original Title",
            "author": "Original Author",
            "year": 2000
        }
    )
    book_id = create_resp.json()["id"]
    
    # Update the book
    response = client.put(
        f"/books/{book_id}",
        json={
            "title": "Updated Title",
            "year": 2020
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["author"] == "Original Author"  # unchanged
    assert data["year"] == 2020

def test_delete_book():
    # Create a book
    create_resp = client.post(
        "/books/",
        json={
            "title": "To Delete",
            "author": "Author",
            "year": 2000
        }
    )
    book_id = create_resp.json()["id"]
    
    # Delete the book
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    
    # Verify deletion
    get_resp = client.get(f"/books/{book_id}")
    assert get_resp.status_code == 404

def test_health_check():
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"