from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Book
from schemas import BookCreate, BookResponse, BookUpdate

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Book Collection API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/books", response_model=BookResponse, status_code=201)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    if book.isbn:
        existing = db.query(Book).filter(Book.isbn == book.isbn).first()
        if existing:
            raise HTTPException(status_code=409, detail="A book with this ISBN already exists")
    db_book = Book(
        title=book.title,
        author=book.author,
        year=book.year,
        isbn=book.isbn,
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


@app.get("/books", response_model=List[BookResponse])
def list_books(author: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Book)
    if author:
        query = query.filter(Book.author == author)
    return query.all()


@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    update_data = book_update.model_dump(exclude_unset=True)
    if "isbn" in update_data and update_data["isbn"] is not None:
        existing = db.query(Book).filter(Book.isbn == update_data["isbn"], Book.id != book_id).first()
        if existing:
            raise HTTPException(status_code=409, detail="A book with this ISBN already exists")
    for field, value in update_data.items():
        setattr(book, field, value)
    db.commit()
    db.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
