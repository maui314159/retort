import os
import sqlite3
from contextlib import asynccontextmanager
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_cursor():
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield cur, conn
    finally:
        conn.close()


def init_db() -> None:
    with db_cursor() as (cur, conn):
        cur.execute(
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


class BookIn(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None


@app.get("/health", status_code=status.HTTP_200_OK)
def health() -> dict:
    return {"status": "ok"}


@app.post("/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(book: BookIn) -> BookOut:
    with db_cursor() as (cur, conn):
        cur.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        conn.commit()
        new_id = cur.lastrowid
        return BookOut(
            id=new_id,
            title=book.title,
            author=book.author,
            year=book.year,
            isbn=book.isbn,
        )


@app.get("/books", response_model=list[BookOut], status_code=status.HTTP_200_OK)
def list_books(author: Optional[str] = None) -> list[BookOut]:
    with db_cursor() as (cur, _):
        if author:
            cur.execute("SELECT * FROM books WHERE author = ?", (author,))
            rows = cur.fetchall()
        else:
            cur.execute("SELECT * FROM books")
            rows = cur.fetchall()
        return [BookOut(id=r["id"], title=r["title"], author=r["author"], year=r["year"], isbn=r["isbn"]) for r in rows]


@app.get("/books/{book_id}", response_model=BookOut, status_code=status.HTTP_200_OK)
def get_book(book_id: int) -> BookOut:
    with db_cursor() as (cur, _):
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return BookOut(id=row["id"], title=row["title"], author=row["author"], year=row["year"], isbn=row["isbn"])


@app.put("/books/{book_id}", response_model=BookOut, status_code=status.HTTP_200_OK)
def update_book(book_id: int, book: BookIn) -> BookOut:
    with db_cursor() as (cur, conn):
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        cur.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (book.title, book.author, book.year, book.isbn, book_id),
        )
        conn.commit()
        return BookOut(id=book_id, title=book.title, author=book.author, year=book.year, isbn=book.isbn)


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int) -> None:
    with db_cursor() as (cur, conn):
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        cur.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
