from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from .db import init_db
from .models import (
    create_book,
    list_books,
    get_book,
    update_book,
    delete_book,
)


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class BookUpdate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


def create_app(db_path: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="Book Collection API")
    init_db(db_path)
    app.state.db_path = db_path

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok"}

    @app.post("/books", status_code=201)
    def create(payload: BookCreate) -> Dict[str, Any]:
        return create_book(
            title=payload.title,
            author=payload.author,
            year=payload.year,
            isbn=payload.isbn,
            db_path=app.state.db_path,
        )

    @app.get("/books")
    def list_all(author: Optional[str] = Query(default=None)) -> list:
        return list_books(author_filter=author, db_path=app.state.db_path)

    @app.get("/books/{book_id}")
    def get_one(book_id: int) -> Dict[str, Any]:
        book = get_book(book_id, db_path=app.state.db_path)
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

    @app.put("/books/{book_id}")
    def update(book_id: int, payload: BookUpdate) -> Dict[str, Any]:
        updated = update_book(
            book_id=book_id,
            title=payload.title,
            author=payload.author,
            year=payload.year,
            isbn=payload.isbn,
            db_path=app.state.db_path,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return updated

    @app.delete("/books/{book_id}", status_code=204)
    def remove(book_id: int):
        if not delete_book(book_id, db_path=app.state.db_path):
            raise HTTPException(status_code=404, detail="Book not found")
        return None

    return app


app = create_app()
