#!/usr/bin/env python3
"""
Clean test that isolates the issue.
"""
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# First, let's create a fresh copy of the app without importing main.py
# We'll duplicate the essential parts but use in-memory database

from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import declarative_base, Session
from pydantic import BaseModel, Field
from typing import Optional, List

# Use in-memory SQLite
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Database model
class BookDB(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

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
    db = SessionLocal()
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

def run_tests():
    print("Testing Book Collection API...")
    print("=" * 50)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Health check
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
        print("✓ Health check")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Health check: {e}")
        tests_failed += 1
    
    # Test 2: Create book
    try:
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
        assert "id" in data
        book_id = data["id"]
        print(f"✓ Create book (ID: {book_id})")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Create book: {e}")
        tests_failed += 1
        book_id = None
    
    # Test 3: List books
    try:
        response = client.get("/books")
        assert response.status_code == 200
        books = response.json()
        assert len(books) == 1
        print(f"✓ List books ({len(books)} book(s))")
        tests_passed += 1
    except Exception as e:
        print(f"✗ List books: {e}")
        tests_failed += 1
    
    # Test 4: Get book
    if book_id:
        try:
            response = client.get(f"/books/{book_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == book_id
            print(f"✓ Get book {book_id}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ Get book: {e}")
            tests_failed += 1
    
    # Test 5: Update book
    if book_id:
        try:
            update_data = {"title": "Updated Title"}
            response = client.put(f"/books/{book_id}", json=update_data)
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Updated Title"
            print(f"✓ Update book {book_id}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ Update book: {e}")
            tests_failed += 1
    
    # Test 6: Delete book
    if book_id:
        try:
            response = client.delete(f"/books/{book_id}")
            assert response.status_code == 204
            print(f"✓ Delete book {book_id}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ Delete book: {e}")
            tests_failed += 1
    
    print("=" * 50)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    
    if tests_failed == 0:
        print("\n✅ All essential tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())