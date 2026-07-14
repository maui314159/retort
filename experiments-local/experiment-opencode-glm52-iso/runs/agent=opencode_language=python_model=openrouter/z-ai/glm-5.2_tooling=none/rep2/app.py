from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: int | None = None
    isbn: str | None = None

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1)
    author: str | None = Field(None, min_length=1)
    year: int | None = None
    isbn: str | None = None

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("must not be blank")
        return v.strip() if v is not None else None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/books", status_code=201)
def create_book(payload: BookCreate) -> dict:
    return db.insert_book(payload.model_dump())


@app.get("/books")
def list_books(author: str | None = Query(default=None)) -> list[dict]:
    return db.list_books(author=author)


@app.get("/books/{book_id}")
def get_book(book_id: int) -> dict:
    book = db.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}")
def update_book(book_id: int, payload: BookUpdate) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    updated = db.update_book(book_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int) -> None:
    if not db.delete_book(book_id):
        raise HTTPException(status_code=404, detail="Book not found")
