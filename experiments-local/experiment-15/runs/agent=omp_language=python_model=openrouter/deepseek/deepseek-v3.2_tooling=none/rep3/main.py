from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# Database model
class BookDB(Base):
    __tablename__ = "books"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    isbn: Mapped[Optional[str]] = mapped_column(String, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the book")
    author: str = Field(..., min_length=1, description="Author of the book")
    year: Optional[int] = Field(None, ge=1000, le=9999, description="Publication year")
    isbn: Optional[str] = Field(None, pattern=r"^[0-9\-]+$", description="ISBN number")

class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="Title of the book")
    author: Optional[str] = Field(None, min_length=1, description="Author of the book")
    year: Optional[int] = Field(None, ge=1000, le=9999, description="Publication year")
    isbn: Optional[str] = Field(None, pattern=r"^[0-9\-]+$", description="ISBN number")

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]

    model_config = ConfigDict(from_attributes=True)
# FastAPI app
app = FastAPI(title="Book Collection API", version="1.0.0")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Create book
@app.post("/books", response_model=BookResponse, status_code=201)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    db_book = BookDB(**book.model_dump())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

# List all books with optional author filter
@app.get("/books", response_model=List[BookResponse])
def list_books(author: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(BookDB)
    if author:
        query = query.filter(BookDB.author.ilike(f"%{author}%"))
    return query.all()

# Get single book
@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    db_book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

# Update book
@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    db_book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    update_data = book_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_book, field, value)
    
    db.commit()
    db.refresh(db_book)
    return db_book

# Delete book
@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    db_book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(db_book)
    db.commit()
    return