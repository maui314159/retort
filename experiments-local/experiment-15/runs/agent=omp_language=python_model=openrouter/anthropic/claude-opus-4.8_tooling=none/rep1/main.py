"""Book collection REST API (FastAPI + SQLite)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, status

import db
from db import get_conn, init_db, transaction
from models import Book, BookCreate, BookUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Respect a DB already configured by tests; otherwise open the default file.
    if db._conn is None:
        init_db()
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


def _row_to_book(row) -> Book:
    return Book(
        id=row["id"],
        title=row["title"],
        author=row["author"],
        year=row["year"],
        isbn=row["isbn"],
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate) -> Book:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (payload.title, payload.author, payload.year, payload.isbn),
        )
        book_id = cur.lastrowid
    row = get_conn().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _row_to_book(row)


@app.get("/books", response_model=list[Book])
def list_books(author: str | None = Query(default=None)) -> list[Book]:
    conn = get_conn()
    if author is not None:
        rows = conn.execute(
            "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [_row_to_book(r) for r in rows]


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int) -> Book:
    row = get_conn().execute(
        "SELECT * FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return _row_to_book(row)


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, payload: BookUpdate) -> Book:
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (payload.title, payload.author, payload.year, payload.isbn, book_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )
    row = get_conn().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _row_to_book(row)


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int) -> None:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )
