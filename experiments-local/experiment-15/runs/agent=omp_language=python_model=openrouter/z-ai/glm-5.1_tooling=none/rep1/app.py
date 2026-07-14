"""Book collection REST API — FastAPI + SQLite."""

import sqlite3
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

DB_PATH = Path(__file__).parent / "books.db"


# ── Database helpers ──────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def _db():
    conn = _get_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init_db() -> None:
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT    NOT NULL,
                author TEXT   NOT NULL,
                year  INTEGER,
                isbn  TEXT
            )
            """
        )


# ── Pydantic models ──────────────────────────────────────────────

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: int | None = None
    isbn: str | None = None


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1)
    author: str | None = Field(None, min_length=1)
    year: int | None = None
    isbn: str | None = None


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    year: int | None
    isbn: str | None


# ── Lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def _lifespan(application: FastAPI):
    _init_db()
    yield


# ── App ───────────────────────────────────────────────────────────

app = FastAPI(title="Book Collection API", lifespan=_lifespan)


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/books", status_code=201, response_model=BookOut)
def create_book(book: BookCreate):
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        row = conn.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.get("/books", response_model=list[BookOut])
def list_books(author: str | None = Query(None)):
    with _db() as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ?", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books").fetchall()
    return [dict(r) for r in rows]


@app.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int):
    with _db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return dict(row)


@app.put("/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, patch: BookUpdate):
    with _db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        updated = {
            "title": patch.title if patch.title is not None else row["title"],
            "author": patch.author if patch.author is not None else row["author"],
            "year": patch.year if patch.year is not None else row["year"],
            "isbn": patch.isbn if patch.isbn is not None else row["isbn"],
        }
        conn.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (updated["title"], updated["author"], updated["year"], updated["isbn"], book_id),
        )
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return dict(row)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with _db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
