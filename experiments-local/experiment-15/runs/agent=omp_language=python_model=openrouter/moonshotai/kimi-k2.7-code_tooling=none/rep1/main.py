import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

DATABASE = os.environ.get("BOOKS_DB_PATH", "books.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
            """
        )
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Book Collection API", lifespan=lifespan)


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class Book(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]

    model_config = ConfigDict(from_attributes=True)


def row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=201)
def create_book(book: BookCreate):
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        conn.commit()
        book_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return row_to_book(row)


@app.get("/books", response_model=list[Book])
def list_books(author: Optional[str] = Query(None)):
    with get_db() as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ?", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books").fetchall()
        return [row_to_book(row) for row in rows]


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")
        return row_to_book(row)


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookUpdate):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Book not found")

        fields = {
            "title": book.title if book.title is not None else existing["title"],
            "author": book.author if book.author is not None else existing["author"],
            "year": book.year if book.year is not None else existing["year"],
            "isbn": book.isbn if book.isbn is not None else existing["isbn"],
        }
        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (fields["title"], fields["author"], fields["year"], fields["isbn"], book_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return row_to_book(row)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
