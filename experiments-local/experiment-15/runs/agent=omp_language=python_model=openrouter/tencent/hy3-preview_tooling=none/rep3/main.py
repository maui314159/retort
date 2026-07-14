from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, field_validator, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Optional, List
import re

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database model
class BookDB(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True, unique=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class BookBase(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator('title', 'author')
    @classmethod
    def validate_required_fields(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} is required and cannot be empty")
        return v.strip()

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 0 or v > 2100:
                raise ValueError("year must be between 0 and 2100")
        return v

    @field_validator('isbn')
    @classmethod
    def validate_isbn(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.replace("-", "")
            if not re.match(r'^\d{10}(\d{3})?$', cleaned):
                raise ValueError("ISBN must be 10 or 13 digits (hyphens allowed)")
        return v


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator('title', 'author')
    @classmethod
    def validate_required_fields(cls, v: Optional[str], info) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError(f"{info.field_name} cannot be empty if provided")
        if v is not None:
            return v.strip()
        return v

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 0 or v > 2100:
                raise ValueError("year must be between 0 and 2100")
        return v

    @field_validator('isbn')
    @classmethod
    def validate_isbn(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.replace("-", "")
            if not re.match(r'^\d{10}(\d{3})?$', cleaned):
                raise ValueError("ISBN must be 10 or 13 digits (hyphens allowed)")
        return v


class BookResponse(BookBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# FastAPI app
app = FastAPI(title="Book Collection API", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/books", response_model=BookResponse, status_code=201)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    if book.isbn:
        existing = db.query(BookDB).filter(BookDB.isbn == book.isbn).first()
        if existing:
            raise HTTPException(status_code=400, detail="ISBN already exists")

    db_book = BookDB(**book.model_dump())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


@app.get("/books", response_model=List[BookResponse])
def list_books(
    author: Optional[str] = Query(None, description="Filter by author name"),
    db: Session = Depends(get_db)
):
    query = db.query(BookDB)
    if author:
        query = query.filter(BookDB.author.ilike(f"%{author}%"))
    return query.all()


@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    db_book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book_update.isbn and book_update.isbn != db_book.isbn:
        existing = db.query(BookDB).filter(
            BookDB.isbn == book_update.isbn,
            BookDB.id != book_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="ISBN already exists")

    update_data = book_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_book, field, value)

    db.commit()
    db.refresh(db_book)
    return db_book


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    db_book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(db_book)
    db.commit()
    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
