"""Book Collection REST API.

A small FastAPI service for managing a book collection stored in SQLite.
"""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager, contextmanager
from typing import Iterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on startup."""
    init_db()
    yield


app = FastAPI(
    title="Book Collection API",
    description="A REST API for managing a book collection.",
    version="1.0.0",
    lifespan=lifespan,
)

DATABASE_PATH = "books.db"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection that commits on success and rolls back on error."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the books table if it does not already exist."""
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


def get_db_dependency() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency that yields a SQLite connection."""
    with get_db() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class BookCreate(BaseModel):
    title: str = Field(..., description="Title of the book (required)")
    author: str = Field(..., description="Author of the book (required)")
    year: Optional[int] = Field(None, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN identifier")

    @field_validator("title", "author")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace-only")
        return stripped

    @field_validator("year")
    @classmethod
    def _valid_year(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value < 0 or value > 9999:
            raise ValueError("year must be between 0 and 9999")
        return value


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Title of the book")
    author: Optional[str] = Field(None, description="Author of the book")
    year: Optional[int] = Field(None, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN identifier")

    @field_validator("title", "author")
    @classmethod
    def _not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace-only")
        return stripped

    @field_validator("year")
    @classmethod
    def _valid_year(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value < 0 or value > 9999:
            raise ValueError("year must be between 0 and 9999")
        return value


class Book(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookList(BaseModel):
    books: list[Book]
    count: int


class HealthStatus(BaseModel):
    status: str
    database: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthStatus, tags=["meta"])
def health_check() -> HealthStatus:
    """Return the service health, including database connectivity."""
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        db_state = "ok"
    except Exception:
        db_state = "error"
    return HealthStatus(status="ok", database=db_state)


@app.post(
    "/books",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    tags=["books"],
)
def create_book(book: BookCreate, conn: sqlite3.Connection = Depends(get_db_dependency)) -> Book:
    """Create a new book."""
    cursor = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book.title, book.author, book.year, book.isbn),
    )
    row = conn.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return Book.model_validate(dict(row))


@app.get("/books", response_model=BookList, tags=["books"])
def list_books(
    author: Optional[str] = Query(None, description="Filter books by author (case-insensitive substring)"),
    conn: sqlite3.Connection = Depends(get_db_dependency),
) -> BookList:
    """List all books, optionally filtered by author."""
    if author:
        rows = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? ORDER BY id",
            (f"%{author}%",),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, author, year, isbn FROM books ORDER BY id"
        ).fetchall()
    books = [Book.model_validate(dict(row)) for row in rows]
    return BookList(books=books, count=len(books))


@app.get("/books/{book_id}", response_model=Book, tags=["books"])
def get_book(book_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)) -> Book:
    """Retrieve a single book by ID."""
    row = conn.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
        (book_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return Book.model_validate(dict(row))


@app.put("/books/{book_id}", response_model=Book, tags=["books"])
def update_book(
    book_id: int,
    book: BookUpdate,
    conn: sqlite3.Connection = Depends(get_db_dependency),
) -> Book:
    """Update an existing book. Only provided fields are changed."""
    existing = conn.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
        (book_id,),
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    data = book.model_dump(exclude_unset=True)
    updated_title = data.get("title", existing["title"])
    updated_author = data.get("author", existing["author"])
    updated_year = data.get("year", existing["year"])
    updated_isbn = data.get("isbn", existing["isbn"])

    conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (updated_title, updated_author, updated_year, updated_isbn, book_id),
    )
    row = conn.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
        (book_id,),
    ).fetchone()
    return Book.model_validate(dict(row))


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["books"])
def delete_book(book_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)) -> None:
    """Delete a book by ID."""
    cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
