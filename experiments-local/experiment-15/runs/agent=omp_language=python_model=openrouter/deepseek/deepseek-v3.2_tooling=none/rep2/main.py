from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from pydantic import BaseModel, Field
from typing import Optional, List
import os

# SQLite database - configurable for testing
import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./books.db")
# For in-memory testing, use shared cache so connections can share the database
if DATABASE_URL == "sqlite:///:memory:":
    DATABASE_URL = "sqlite:///file:memdb1?mode=memory&cache=shared"
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

def create_tables():
    Base.metadata.create_all(bind=engine)

create_tables()

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)