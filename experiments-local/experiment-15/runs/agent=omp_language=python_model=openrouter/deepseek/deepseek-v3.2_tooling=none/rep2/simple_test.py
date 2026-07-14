import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, BookDB, Base, get_db

def run_tests():
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
    
    # Create tables on the test engine
    Base.metadata.create_all(bind=engine)
    
    tests_passed = 0
    tests_failed = 0
    
    def run_test(test_name, test_func, needs_clean=False):
        nonlocal tests_passed, tests_failed
        try:
            if needs_clean:
                # Clean tables and recreate for isolation
                Base.metadata.drop_all(bind=engine)
                Base.metadata.create_all(bind=engine)
            test_func(client)
            print(f"✓ {test_name} passed")
            tests_passed += 1
        except Exception as e:
            print(f"✗ {test_name} failed: {e}")
            tests_failed += 1

    # Test 1: Health check
    def test_health_check(client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    # Test 2: Create book
    def test_create_book(client):
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
    
    # Test 3: Create book validation
    def test_create_book_validation(client):
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
    
    # Test 4: List books
    def test_list_books(client):
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
    
    # Test 5: List books with author filter
    def test_list_books_with_author_filter(client):
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
    
    # Test 6: Get book
    def test_get_book(client):
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
    
    # Test 7: Get book not found
    def test_get_book_not_found(client):
        response = client.get("/books/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Book not found"
    
    # Test 8: Update book
    def test_update_book(client):
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
    
    # Test 9: Update book not found
    def test_update_book_not_found(client):
        response = client.put("/books/999", json={"title": "New Title"})
        assert response.status_code == 404
    
    # Test 10: Delete book
    def test_delete_book(client):
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
    
    # Test 11: Delete book not found
    def test_delete_book_not_found(client):
        response = client.delete("/books/999")
        assert response.status_code == 404
    
    # Run all tests - tests that modify data need clean tables
    tests = [
        ("Health check", test_health_check, False),
        ("Create book", test_create_book, True),
        ("Create book validation", test_create_book_validation, True),
        ("List books", test_list_books, True),
        ("List books with author filter", test_list_books_with_author_filter, True),
        ("Get book", test_get_book, True),
        ("Get book not found", test_get_book_not_found, True),
        ("Update book", test_update_book, True),
        ("Update book not found", test_update_book_not_found, True),
        ("Delete book", test_delete_book, True),
        ("Delete book not found", test_delete_book_not_found, True),
    ]
    
    for test_name, test_func, needs_clean in tests:
        run_test(test_name, test_func, needs_clean)
    
    print(f"\nTotal: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)