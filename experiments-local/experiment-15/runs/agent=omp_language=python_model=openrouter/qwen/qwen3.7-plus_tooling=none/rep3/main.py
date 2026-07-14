import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "books.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT UNIQUE
            )
        """)
        conn.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Book Collection API", lifespan=lifespan)

class BookBase(BaseModel):
    title: str = Field(..., min_length=1, description="Book title")
    author: str = Field(..., min_length=1, description="Book author")
    year: Optional[int] = Field(default=None, description="Publication year")
    isbn: Optional[str] = Field(default=None, description="ISBN")

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    author: Optional[str] = Field(default=None, min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None

class Book(BookBase):
    id: int
    model_config = {"from_attributes": True}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book.title, book.author, book.year, book.isbn)
            )
            conn.commit()
            book_id = cursor.lastrowid
            return {"id": book_id, "title": book.title, "author": book.author, "year": book.year, "isbn": book.isbn}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="ISBN already exists")

@app.get("/books")
def list_books(author: Optional[str] = Query(None)):
    with get_db() as conn:
        if author:
            cursor = conn.execute("SELECT * FROM books WHERE author LIKE ?", (f"%{author}%",))
        else:
            cursor = conn.execute("SELECT * FROM books")
        rows = cursor.fetchall()
        return [{"id": row["id"], "title": row["title"], "author": row["author"], "year": row["year"], "isbn": row["isbn"]} for row in rows]

@app.get("/books/{book_id}")
def get_book(book_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")
        return {"id": row["id"], "title": row["title"], "author": row["author"], "year": row["year"], "isbn": row["isbn"]}

@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookUpdate):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")
        
        title = book.title if book.title is not None else row["title"]
        author = book.author if book.author is not None else row["author"]
        year = book.year if book.year is not None else row["year"]
        isbn = book.isbn if book.isbn is not None else row["isbn"]
        
        try:
            conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (title, author, year, isbn, book_id)
            )
            conn.commit()
            return {"id": book_id, "title": title, "author": author, "year": year, "isbn": isbn}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="ISBN already exists")

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
