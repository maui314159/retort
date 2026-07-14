import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

DATABASE_URL = "books.db"

def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    """)
    conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Book title is required")
    author: str = Field(..., min_length=1, description="Author name is required")
    year: Optional[int] = Field(None, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN number")

class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None

class Book(BookCreate):
    id: int

    class Config:
        from_attributes = True

def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/books", status_code=201)
def create_book(book: BookCreate, conn: sqlite3.Connection = Depends(get_db)):
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn)
        )
        conn.commit()
        book_id = cursor.lastrowid
        
        new_book = cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return row_to_dict(new_book)
    finally:
        conn.close()

@app.get("/books")
def list_books(author: Optional[str] = Query(None), conn: sqlite3.Connection = Depends(get_db)):
    try:
        if author:
            books = conn.execute("SELECT * FROM books WHERE author LIKE ?", (f"%{author}%",)).fetchall()
        else:
            books = conn.execute("SELECT * FROM books").fetchall()
        return [row_to_dict(book) for book in books]
    finally:
        conn.close()

@app.get("/books/{book_id}")
def get_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)):
    try:
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return row_to_dict(book)
    finally:
        conn.close()

@app.put("/books/{book_id}")
def update_book(book_id: int, book_update: BookUpdate, conn: sqlite3.Connection = Depends(get_db)):
    try:
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        update_data = book_update.model_dump(exclude_unset=True)
        if not update_data:
            return row_to_dict(book)
            
        set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values()) + [book_id]
        
        conn.execute(f"UPDATE books SET {set_clause} WHERE id = ?", values)
        conn.commit()
        
        updated_book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return row_to_dict(updated_book)
    finally:
        conn.close()

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)):
    try:
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
    finally:
        conn.close()
    return Response(status_code=204)