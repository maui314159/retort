"""REST API for managing a book collection (FastAPI + SQLite)."""
import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from db import BookStore


class BookIn(BaseModel):
    title: str = Field(..., min_length=1, description="Required")
    author: str = Field(..., min_length=1, description="Required")
    year: Optional[int] = None
    isbn: Optional[str] = None


class Book(BookIn):
    id: int


def get_store() -> BookStore:
    return BookStore(os.environ.get("BOOKS_DB_PATH", "books.db"))


app = FastAPI(title="Book Collection API", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=201)
def create_book(book: BookIn, store: BookStore = Depends(get_store)) -> dict:
    return store.create(book.title, book.author, book.year, book.isbn)


@app.get("/books", response_model=list[Book])
def list_books(
    author: Optional[str] = Query(default=None),
    store: BookStore = Depends(get_store),
) -> list[dict]:
    return store.list(author=author)


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int, store: BookStore = Depends(get_store)) -> dict:
    book = store.get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=Book)
def update_book(
    book_id: int, book: BookIn, store: BookStore = Depends(get_store)
) -> dict:
    updated = store.update(book_id, book.title, book.author, book.year, book.isbn)
    if updated is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, store: BookStore = Depends(get_store)) -> None:
    if not store.delete(book_id):
        raise HTTPException(status_code=404, detail="Book not found")
