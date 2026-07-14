import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    with db_cursor() as conn:
        init_db(conn)
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Book title (required)")
    author: str = Field(..., min_length=1, description="Book author (required)")
    year: Optional[int] = Field(None, ge=0, le=9999, description="Publication year")
    isbn: Optional[str] = Field(None, max_length=32, description="ISBN identifier")

    @field_validator("title", "author")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank or whitespace-only")
        return v.strip()


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = Field(None, ge=0, le=9999)
    isbn: Optional[str] = Field(None, max_length=32)

    @field_validator("title", "author")
    @classmethod
    def must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("must not be blank or whitespace-only")
        return v.strip() if v is not None else None


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
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
def db_cursor():
    conn = get_connection()
    try:
        init_db(conn)
        yield conn
    finally:
        conn.close()


def get_db():
    conn = get_connection()
    try:
        init_db(conn)
        yield conn
    finally:
        conn.close()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (payload.title, payload.author, payload.year, payload.isbn),
    )
    conn.commit()
    book_id = cur.lastrowid
    return BookOut(
        id=book_id,
        title=payload.title,
        author=payload.author,
        year=payload.year,
        isbn=payload.isbn,
    )


@app.get("/books", response_model=List[BookOut])
def list_books(
    author: Optional[str] = Query(None, description="Filter by exact author name"),
    conn: sqlite3.Connection = Depends(get_db),
):
    if author is not None:
        rows = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
            (author,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, author, year, isbn FROM books ORDER BY id"
        ).fetchall()
    return [BookOut(id=r["id"], title=r["title"], author=r["author"], year=r["year"], isbn=r["isbn"]) for r in rows]


@app.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")
    return BookOut(id=row["id"], title=row["title"], author=row["author"], year=row["year"], isbn=row["isbn"])


@app.put("/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, payload: BookUpdate, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")

    data = payload.model_dump(exclude_unset=True)
    new_title = data.get("title", row["title"])
    new_author = data.get("author", row["author"])
    new_year = data.get("year", row["year"])
    new_isbn = data.get("isbn", row["isbn"])

    conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (new_title, new_author, new_year, new_isbn, book_id),
    )
    conn.commit()
    return BookOut(id=book_id, title=new_title, author=new_author, year=new_year, isbn=new_isbn)


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
