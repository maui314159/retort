"""Book collection REST API.

FastAPI service backed by an embedded SQLite database. Run with:

    uvicorn app:app --reload
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from typing import Iterator, Optional

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with sane defaults (WAL, FK, dict rows)."""
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: str | None = None) -> None:
    """Create the books table if it does not yet exist."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT    NOT NULL,
                author TEXT    NOT NULL,
                year   INTEGER,
                isbn   TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()


@contextmanager
def db_cursor(db_path: str | None = None) -> Iterator[sqlite3.Cursor]:
    conn = get_connection(db_path)
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Book title (required)")
    author: str = Field(..., min_length=1, description="Book author (required)")
    year: Optional[int] = Field(None, ge=0, le=9999, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN identifier")

    @field_validator("title", "author")
    @classmethod
    def _strip_nonempty(cls, v: str) -> str:
        if v is None or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = Field(None, ge=0, le=9999)
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def _strip_nonempty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class Book(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    """Liveness + DB reachability probe."""
    try:
        with db_cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(exc)},
        )
    return {"status": "healthy"}


@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate) -> dict:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        book_id = cur.lastrowid
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
    return row_to_book(row)


@app.get("/books", response_model=list[Book])
def list_books(author: Optional[str] = None) -> list[dict]:
    with db_cursor() as cur:
        if author:
            cur.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            )
        else:
            cur.execute("SELECT * FROM books ORDER BY id")
        rows = cur.fetchall()
    return [row_to_book(r) for r in rows]


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int) -> dict:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )
    return row_to_book(row)


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, patch: BookUpdate) -> dict:
    fields = patch.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided to update",
        )
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values())

    with db_cursor() as cur:
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        if cur.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with id {book_id} not found",
            )
        cur.execute(
            f"UPDATE books SET {set_clause}, updated_at = datetime('now') "
            f"WHERE id = ?",
            (*values, book_id),
        )
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
    return row_to_book(row)


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int) -> Response:
    with db_cursor() as cur:
        cur.execute("SELECT id FROM books WHERE id = ?", (book_id,))
        if cur.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with id {book_id} not found",
            )
        cur.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
