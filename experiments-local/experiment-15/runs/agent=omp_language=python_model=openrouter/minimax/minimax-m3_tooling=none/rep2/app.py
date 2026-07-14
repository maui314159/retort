"""Book Collection REST API.

A small FastAPI service that manages a book collection backed by SQLite.
Endpoints:
    GET    /health           - health check
    POST   /books            - create a book
    GET    /books            - list books (optional ?author= filter)
    GET    /books/{id}       - retrieve a single book
    PUT    /books/{id}       - update a book
    DELETE /books/{id}       - delete a book
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Iterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_PATH: str = os.environ.get("BOOKS_DB", "books.db")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT    NOT NULL,
    author TEXT   NOT NULL,
    year  INTEGER,
    isbn  TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DATABASE_PATH) -> None:
    """Create the schema if it doesn't exist."""
    conn = _connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency that yields a per-request SQLite connection."""
    conn = _connect(DATABASE_PATH)
    try:
        yield conn
    finally:
        conn.close()


def _row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _fetch_book(conn: sqlite3.Connection, book_id: int) -> Optional[dict]:
    cur = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cur.fetchone()
    return _row_to_book(row) if row else None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


def _strip_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


class BookBase(BaseModel):
    """Shared fields for create/update payloads."""

    title: str = Field(..., min_length=1, max_length=500)
    author: str = Field(..., min_length=1, max_length=300)
    year: Optional[int] = Field(default=None, ge=0, le=9999)
    isbn: Optional[str] = Field(default=None, max_length=32)

    _normalize_title = field_validator("title")(lambda cls, v: _strip_text(v) if v is not None else v)
    _normalize_author = field_validator("author")(lambda cls, v: _strip_text(v) if v is not None else v)


class BookCreate(BookBase):
    """Payload for POST /books (all required fields enforced by BookBase)."""


class BookUpdate(BaseModel):
    """Payload for PUT /books/{id}. All fields optional; blank strings rejected."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, max_length=500)
    author: Optional[str] = Field(default=None, max_length=300)
    year: Optional[int] = Field(default=None, ge=0, le=9999)
    isbn: Optional[str] = Field(default=None, max_length=32)

    _normalize_title = field_validator("title")(lambda cls, v: _strip_text(v) if v is not None else v)
    _normalize_author = field_validator("author")(lambda cls, v: _strip_text(v) if v is not None else v)


class Book(BookBase):
    """Full book representation returned by the API."""

    id: int


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Book Collection API",
    version="1.0.0",
    description="REST API for managing a book collection.",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", tags=["meta"])
def health(conn: sqlite3.Connection = Depends(get_db)) -> JSONResponse:
    try:
        conn.execute("SELECT 1").fetchone()
    except Exception as exc:  # pragma: no cover - defensive
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(exc)},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "healthy"})


@app.post(
    "/books",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    tags=["books"],
)
def create_book(
    payload: BookCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> Book:
    cur = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (payload.title, payload.author, payload.year, payload.isbn),
    )
    conn.commit()
    book = _fetch_book(conn, cur.lastrowid)
    assert book is not None  # inserted row must exist
    return Book(**book)


@app.get("/books", response_model=list[Book], tags=["books"])
def list_books(
    author: Optional[str] = Query(default=None, min_length=1, max_length=300),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[Book]:
    if author is not None:
        cur = conn.execute(
            "SELECT * FROM books WHERE LOWER(author) = LOWER(?) ORDER BY id",
            (author.strip(),),
        )
    else:
        cur = conn.execute("SELECT * FROM books ORDER BY id")
    return [Book(**_row_to_book(row)) for row in cur.fetchall()]


@app.get("/books/{book_id}", response_model=Book, tags=["books"])
def get_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Book:
    book = _fetch_book(conn, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found.",
        )
    return Book(**book)


@app.put("/books/{book_id}", response_model=Book, tags=["books"])
def update_book(
    book_id: int,
    payload: BookUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> Book:
    existing = _fetch_book(conn, book_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found.",
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update.",
        )

    set_clause = ", ".join(f"{field} = ?" for field in updates)
    values = list(updates.values()) + [book_id]
    conn.execute(f"UPDATE books SET {set_clause} WHERE id = ?", values)
    conn.commit()

    refreshed = _fetch_book(conn, book_id)
    assert refreshed is not None
    return Book(**refreshed)


@app.delete(
    "/books/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["books"],
)
def delete_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    existing = _fetch_book(conn, book_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found.",
        )
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
