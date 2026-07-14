#!/usr/bin/env python3
"""
Basic test that doesn't require pytest or external dependencies.
"""
import sys
import os

# Temporarily modify DATABASE_URL for testing
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from main import app, BookDB, Base, engine, get_db
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as create_engine_sql
from sqlalchemy.orm import sessionmaker
from main import app, BookDB, Base, engine, get_db, create_tables
# Override the engine with in-memory one for testing
test_engine = create_engine_sql('sqlite:///:memory:', connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
app.dependency_overrides[get_db] = override_get_db

# Create tables on test engine
Base.metadata.create_all(bind=test_engine)
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create tables on test engine
Base.metadata.create_all(bind=test_engine)

client = TestClient(app)

def test_health():
    print("Testing /health...")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    print("  ✓ Health check passed")

def test_create_and_list():
    print("\nTesting POST /books and GET /books...")
    
    # Create a book
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "isbn": "1234567890"
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == book_data["title"]
    assert created["author"] == book_data["author"]
    assert created["year"] == book_data["year"]
    assert created["isbn"] == book_data["isbn"]
    assert "id" in created
    print(f"  ✓ Created book ID: {created['id']}")
    
    # List books
    response = client.get("/books")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["id"] == created["id"]
    print(f"  ✓ Listed {len(books)} book(s)")
    
    return created["id"]

def test_get_book(book_id):
    print(f"\nTesting GET /books/{book_id}...")
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    book = response.json()
    assert book["id"] == book_id
    assert book["title"] == "Test Book"
    print(f"  ✓ Retrieved book {book_id}")

def test_update_book(book_id):
    print(f"\nTesting PUT /books/{book_id}...")
    update_data = {"title": "Updated Title", "year": 2024}
    response = client.put(f"/books/{book_id}", json=update_data)
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Updated Title"
    assert updated["year"] == 2024
    assert updated["author"] == "Test Author"  # unchanged
    print(f"  ✓ Updated book {book_id}")

def test_author_filter():
    print("\nTesting GET /books?author=Test...")
    response = client.get("/books?author=Test")
    assert response.status_code == 200
    books = response.json()
    assert len(books) >= 1
    print(f"  ✓ Found {len(books)} book(s) with author containing 'Test'")

def test_delete_book(book_id):
    print(f"\nTesting DELETE /books/{book_id}...")
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    print(f"  ✓ Deleted book {book_id}")
    
    # Verify deletion
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404
    print(f"  ✓ Book {book_id} not found (as expected)")

def test_validation():
    print("\nTesting validation...")
    
    # Missing required field
    response = client.post("/books", json={"title": "No Author"})
    assert response.status_code == 422
    print("  ✓ Validation failed for missing author (as expected)")
    
    # Invalid year
    response = client.post("/books", json={
        "title": "Bad Year",
        "author": "Author",
        "year": 50  # Too small
    })
    assert response.status_code == 422
    print("  ✓ Validation failed for invalid year (as expected)")

def run_all_tests():
    print("=" * 60)
    print("Running Book Collection API Tests")
    print("=" * 60)
    
    try:
        test_health()
        book_id = test_create_and_list()
        test_get_book(book_id)
        test_update_book(book_id)
        test_author_filter()
        test_delete_book(book_id)
        test_validation()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)