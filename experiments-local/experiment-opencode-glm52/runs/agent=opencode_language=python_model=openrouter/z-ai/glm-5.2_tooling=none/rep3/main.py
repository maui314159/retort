"""Book collection REST API.

A small FastAPI service backed by SQLite for managing a collection of books.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from typing import Iterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    # check_same_thread=False: a single app instance may serve requests from
    # multiple threads (uvicorn threadpool / TestClient lifespan thread).
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
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


@contextmanager
def db_cursor(conn: sqlite3.Connection) -> Iterator[sqlite3.Cursor]:
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Title is required")
    author: str = Field(..., min_length=1, description="Author is required")
    year: Optional[int] = Field(default=None, ge=0, le=9999)
    isbn: Optional[str] = Field(default=None, max_length=32)

    @field_validator("title", "author")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class BookUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    author: Optional[str] = Field(default=None, min_length=1)
    year: Optional[int] = Field(default=None, ge=0, le=9999)
    isbn: Optional[str] = Field(default=None, max_length=32)

    @field_validator("title", "author")
    @classmethod
    def _not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("must not be blank")
        return v.strip() if v is not None else v


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app(db_path: str = DB_PATH) -> FastAPI:
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        conn = get_connection(db_path)
        init_db(conn)
        app.state.conn = conn
        try:
            yield
        finally:
            conn.close()

    app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=_lifespan)
    app.state.db_path = db_path

    def get_db() -> Iterator[sqlite3.Connection]:
        conn = getattr(app.state, "conn", None)
        if conn is None:
            conn = get_connection(app.state.db_path)
            init_db(conn)
            app.state.conn = conn
        yield conn

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
    def create_book(book: BookCreate, conn: sqlite3.Connection = Depends(get_db)) -> JSONResponse:
        with db_cursor(conn) as cur:
            cur.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book.title, book.author, book.year, book.isbn),
            )
            book_id = cur.lastrowid
            cur.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                (book_id,),
            )
            row = cur.fetchone()
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=dict(row))

    @app.get("/books", response_model=list[BookOut])
    def list_books(
        author: Optional[str] = Query(default=None),
        conn: sqlite3.Connection = Depends(get_db),
    ) -> list[dict]:
        if author:
            cur = conn.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
                (author,),
            )
        else:
            cur = conn.execute(
                "SELECT id, title, author, year, isbn FROM books ORDER BY id"
            )
        return [dict(r) for r in cur.fetchall()]

    @app.get("/books/{book_id}", response_model=BookOut)
    def get_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
        cur = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        return dict(row)

    @app.put("/books/{book_id}", response_model=BookOut)
    def update_book(
        book_id: int,
        book: BookUpdate,
        conn: sqlite3.Connection = Depends(get_db),
    ) -> dict:
        cur = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        )
        existing = cur.fetchone()
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        data = book.model_dump(exclude_unset=True)
        merged = dict(existing)
        merged.update(data)

        with db_cursor(conn) as cur:
            cur.execute(
                """
                UPDATE books
                SET title = ?, author = ?, year = ?, isbn = ?
                WHERE id = ?
                """,
                (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
            )
            cur.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                (book_id,),
            )
            row = cur.fetchone()
        return dict(row)

    @app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)):
        with db_cursor(conn) as cur:
            cur.execute("SELECT id FROM books WHERE id = ?", (book_id,))
            if cur.fetchone() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
                )
            cur.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
