"""Book Collection REST API — FastAPI + SQLite."""

from contextlib import asynccontextmanager, contextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import sqlite3

@asynccontextmanager
async def _lifespan(application: FastAPI):
    init_db()
    yield


app = FastAPI(title="Book Collection API", lifespan=_lifespan)

DB_PATH = "books.db"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                title     TEXT NOT NULL,
                author    TEXT NOT NULL,
                year      INTEGER,
                isbn      TEXT
            )
            """
        )


@contextmanager
def db_conn():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Book title (required)")
    author: str = Field(..., min_length=1, description="Author name (required)")
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", status_code=200)
def health_check():
    return {"status": "ok"}


@app.post("/books", response_model=BookOut, status_code=201)
def create_book(book: BookCreate):
    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        row = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return dict(row)


@app.get("/books", response_model=list[BookOut])
def list_books(author: Optional[str] = Query(None)):
    with db_conn() as conn:
        if author:
            rows = conn.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?",
                (author,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, author, year, isbn FROM books"
            ).fetchall()
    return [dict(r) for r in rows]


@app.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return dict(row)


@app.put("/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, update: BookUpdate):
    with db_conn() as conn:
        existing = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found")

        title = update.title if update.title is not None else existing["title"]
        author = update.author if update.author is not None else existing["author"]
        year = update.year if update.year is not None else existing["year"]
        isbn = update.isbn if update.isbn is not None else existing["isbn"]

        conn.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (title, author, year, isbn, book_id),
        )
        row = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
    return dict(row)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with db_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
