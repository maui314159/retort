import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

# Create test database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database model (copied from main.py to avoid import issues)
class BookDB(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)

# Pydantic models
class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    isbn: Optional[str] = Field(None, min_length=10, max_length=13)

class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    isbn: Optional[str] = Field(None, min_length=10, max_length=13)

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]

    class Config:
        from_attributes = True

# Dependency to get DB session
def get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI app
app = FastAPI(title="Book Collection API", version="1.0.0")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/books", response_model=BookResponse, status_code=201)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    db_book = BookDB(**book.model_dump())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.get("/books", response_model=List[BookResponse])
def list_books(
    author: Optional[str] = Query(None, description="Filter by author"),
    db: Session = Depends(get_db)
):
    query = select(BookDB)
    if author:
        query = query.where(BookDB.author.ilike(f"%{author}%"))
    books = db.execute(query).scalars().all()
    return books

@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(BookDB, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    db_book = db.get(BookDB, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    update_data = book_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_book, field, value)
    
    db.commit()
    db.refresh(db_book)
    return db_book

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    db_book = db.get(BookDB, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(db_book)
    db.commit()
    return None

# Test client
client = TestClient(app)

# Setup and teardown
def setup_module():
    Base.metadata.create_all(bind=engine)

def teardown_module():
    Base.metadata.drop_all(bind=engine)

# Tests
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

if __name__ == "__main__":
    # Run tests directly
    import traceback
    tests = [
        ("Health check", test_health_check),
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
    
    # Setup once
    Base.metadata.create_all(bind=engine)
    
    for test_name, test_func in tests:
        try:
            # Clean and recreate tables for each test
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            test_func()
            print(f"✓ {test_name} passed")
            passed += 1
        except Exception as e:
            print(f"✗ {test_name} failed: {e}")
            traceback.print_exc()
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)