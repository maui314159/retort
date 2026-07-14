"""FastAPI service exposing a CRUD REST API for a book collection.

Endpoints
---------
* ``GET    /health``         — liveness probe
* ``POST   /books``          — create a book
* ``GET    /books``          — list books (optional ``?author=`` filter)
* ``GET    /books/{id}``     — fetch a single book
* ``PUT    /books/{id}``     — partial update of a book
* ``DELETE /books/{id}``     — remove a book
"""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from db import get_db, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class BookCreate(BaseModel):
    """Payload for ``POST /books``. ``title`` and ``author`` are required."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=200)
    year: Optional[int] = Field(None, ge=0, le=2100)
    isbn: Optional[str] = Field(None, max_length=32)

    @field_validator("title", "author")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class BookUpdate(BaseModel):
    """Payload for ``PUT /books/{id}``. All fields are optional — only those
    present in the request body are modified."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=200)
    year: Optional[int] = Field(None, ge=0, le=2100)
    isbn: Optional[str] = Field(None, max_length=32)

    @field_validator("title", "author")
    @classmethod
    def _not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.strip():
            raise ValueError("must not be blank")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    """Liveness probe — returns 200 when the database is reachable."""
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=503, detail=f"db unavailable: {exc}") from exc
    return {"status": "ok"}


@app.post("/books", status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate) -> dict:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    assert row is not None  # we just inserted it
    return _row_to_book(row)


@app.get("/books")
def list_books(author: Optional[str] = Query(None)) -> list[dict]:
    with get_db() as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE LOWER(author) = LOWER(?) ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [_row_to_book(r) for r in rows]


@app.get("/books/{book_id}")
def get_book(book_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="book not found")
    return _row_to_book(row)


@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookUpdate) -> dict:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="book not found")

        merged = {
            "title": book.title if book.title is not None else existing["title"],
            "author": book.author if book.author is not None else existing["author"],
            "year": book.year if book.year is not None else existing["year"],
            "isbn": book.isbn if book.isbn is not None else existing["isbn"],
        }
        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                merged["title"],
                merged["author"],
                merged["year"],
                merged["isbn"],
                book_id,
            ),
        )
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
    assert row is not None
    return _row_to_book(row)


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int) -> None:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="book not found")
    return None
