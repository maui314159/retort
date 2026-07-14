#!/usr/bin/env python3
"""
Test suite for Book Collection API.
Run with: python pytest_test.py
"""
import os
import sys

# Set environment for in-memory database
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from main import app, BookDB, Base, engine, get_db
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

# Create test client
client = TestClient(app)

def setup_module():
    """Create tables before tests."""
    Base.metadata.create_all(bind=engine)

def teardown_module():
    """Clean up after tests."""
    Base.metadata.drop_all(bind=engine)

def test_health_endpoint():
    """Test GET /health returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    print("✓ Health endpoint test passed")

def test_create_and_retrieve_book():
    """Test creating a book and retrieving it."""
    # Create book
    book_data = {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "year": 1937,
        "isbn": "9780547928227"
    }
    create_response = client.post("/books", json=book_data)
    assert create_response.status_code == 201
    created_book = create_response.json()
    assert created_book["title"] == book_data["title"]
    assert created_book["author"] == book_data["author"]
    assert created_book["year"] == book_data["year"]
    assert created_book["isbn"] == book_data["isbn"]
    assert "id" in created_book
    
    # Retrieve book
    book_id = created_book["id"]
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 200
    retrieved_book = get_response.json()
    assert retrieved_book == created_book
    
    print("✓ Create and retrieve book test passed")
    return book_id

def test_list_books_with_filter():
    """Test listing books with author filter."""
    # Create test books
    client.post("/books", json={
        "title": "Book by Author A",
        "author": "Author A",
        "year": 2000
    })
    client.post("/books", json={
        "title": "Book by Author B",
        "author": "Author B",
        "year": 2010
    })
    
    # List all books
    all_books_response = client.get("/books")
    assert all_books_response.status_code == 200
    all_books = all_books_response.json()
    assert len(all_books) >= 2
    
    # Filter by author
    filtered_response = client.get("/books?author=Author+A")
    assert filtered_response.status_code == 200
    filtered_books = filtered_response.json()
    assert len(filtered_books) >= 1
    assert all("Author A" in book["author"] for book in filtered_books)
    
    print("✓ List books with filter test passed")

def test_update_book():
    """Test updating a book."""
    # Create book
    create_response = client.post("/books", json={
        "title": "Original Title",
        "author": "Original Author",
        "year": 2000
    })
    book_id = create_response.json()["id"]
    
    # Update book
    update_data = {"title": "Updated Title", "year": 2020}
    update_response = client.put(f"/books/{book_id}", json=update_data)
    assert update_response.status_code == 200
    updated_book = update_response.json()
    assert updated_book["title"] == "Updated Title"
    assert updated_book["year"] == 2020
    assert updated_book["author"] == "Original Author"  # unchanged
    
    # Verify update
    get_response = client.get(f"/books/{book_id}")
    assert get_response.json()["title"] == "Updated Title"
    
    print("✓ Update book test passed")

def test_delete_book():
    """Test deleting a book."""
    # Create book
    create_response = client.post("/books", json={
        "title": "Book to Delete",
        "author": "Author",
        "year": 2000
    })
    book_id = create_response.json()["id"]
    
    # Delete book
    delete_response = client.delete(f"/books/{book_id}")
    assert delete_response.status_code == 204
    
    # Verify deletion
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404
    
    print("✓ Delete book test passed")

def test_validation():
    """Test input validation."""
    # Missing required field
    response = client.post("/books", json={"title": "No Author"})
    assert response.status_code == 422
    
    # Invalid year
    response = client.post("/books", json={
        "title": "Bad Year",
        "author": "Author",
        "year": 50  # Too small
    })
    assert response.status_code == 422
    
    print("✓ Validation test passed")

def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("Running Book Collection API Test Suite")
    print("=" * 60)
    
    tests = [
        ("Health endpoint", test_health_endpoint),
        ("Create and retrieve book", test_create_and_retrieve_book),
        ("List books with filter", test_list_books_with_filter),
        ("Update book", test_update_book),
        ("Delete book", test_delete_book),
        ("Validation", test_validation),
    ]
    
    passed = 0
    failed = 0
    
    # Setup once
    setup_module()
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"  ✓ {test_name}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {test_name}: {e}")
            failed += 1
    
    # Cleanup
    teardown_module()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)