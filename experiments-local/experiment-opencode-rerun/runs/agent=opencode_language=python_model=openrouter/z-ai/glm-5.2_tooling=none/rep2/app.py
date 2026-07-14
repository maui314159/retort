from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from starlette.responses import JSONResponse

import db
from models import BookCreate, BookUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Books API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    created = db.insert_book(book.title, book.author, book.year, book.isbn)
    return created


@app.get("/books")
def list_books(author: Optional[str] = Query(default=None)):
    return db.list_books(author=author)


@app.get("/books/{book_id}")
def get_book(book_id: int):
    book = db.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookUpdate):
    existing = db.get_book(book_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Book not found")
    updated = db.update_book(
        book_id,
        book.title,
        book.author,
        book.year,
        book.isbn,
    )
    return updated


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    deleted = db.delete_book(book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")
    return JSONResponse(status_code=204, content=None)
