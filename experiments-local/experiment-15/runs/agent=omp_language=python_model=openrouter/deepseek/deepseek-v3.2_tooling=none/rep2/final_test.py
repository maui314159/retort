#!/usr/bin/env python3
"""
Final test for Book Collection API.
"""
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, BookDB, Base, get_db

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create tables
Base.metadata.create_all(bind=test_engine)

client = TestClient(app)

def run_test(name, test_func):
    """Run a test and report result."""
    try:
        test_func()
        print(f"✓ {name}")
        return True
    except AssertionError as e:
        print(f"✗ {name}: Assertion failed - {e}")
        return False
    except Exception as e:
        print(f"✗ {name}: Error - {e}")
        return False

def test_health():
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
    return data["id"]

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
    # Clean table first
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
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

def test_list_books_with_author_filter():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
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
    
    response = client.get("/books?author=Smith")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["author"] == "John Smith"

def test_get_book():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    create_response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2020
    })
    book_id = create_response.json()["id"]
    
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book_id

def test_get_book_not_found():
    response = client.get("/books/999")
    assert response.status_code == 404

def test_update_book():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    create_response = client.post("/books", json={
        "title": "Original Title",
        "author": "Original Author",
        "year": 2000
    })
    book_id = create_response.json()["id"]
    
    update_data = {"title": "Updated Title", "year": 2020}
    response = client.put(f"/books/{book_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["year"] == 2020

def test_update_book_not_found():
    response = client.put("/books/999", json={"title": "New Title"})
    assert response.status_code == 404

def test_delete_book():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    create_response = client.post("/books", json={
        "title": "To Delete",
        "author": "Author",
        "year": 2000
    })
    book_id = create_response.json()["id"]
    
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404

def test_delete_book_not_found():
    response = client.delete("/books/999")
    assert response.status_code == 404

def main():
    print("Running Book Collection API tests...")
    print("=" * 50)
    
    tests = [
        ("Health check", test_health),
        ("Create book", test_create_book),
        ("Create book validation", test_create_book_validation),
        ("List books", test_list_books),
        ("List books with author filter", test_list_books_with_author_filter),
        ("Get book", test_get_book),
        ("Get book not found", test_get_book_not_found),
        ("Update book", test_update_book),
        ("Update book not found", test_update_book_not_found),
        ("Delete book", test_delete_book),
        ("Delete book not found", test_delete_book_not_found),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        if run_test(name, test_func):
            passed += 1
        else:
            failed += 1
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())