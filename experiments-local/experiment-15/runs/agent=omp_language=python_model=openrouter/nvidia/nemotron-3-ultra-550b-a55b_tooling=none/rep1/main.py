
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from contextlib import asynccontextmanager
from typing import List, Optional

from database import init_db, get_db
from models import BookCreate, BookUpdate, BookResponse, HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Book Collection API",
    description="REST API for managing a book collection",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post(
    "/books",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Books"],
)
async def create_book(book: BookCreate):
    """Create a new book."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
            """,
            (book.title, book.author, book.year, book.isbn),
        )
        book_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return BookResponse(**dict(row))


@app.get("/books", response_model=List[BookResponse], tags=["Books"])
async def list_books(author: Optional[str] = Query(None, description="Filter by author")):
    """List all books, optionally filtered by author."""
    with get_db() as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author LIKE ? ORDER BY id",
                (f"%{author}%",),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [BookResponse(**dict(row)) for row in rows]


@app.get("/books/{book_id}", response_model=BookResponse, tags=["Books"])
async def get_book(book_id: int):
    """Get a single book by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")
        return BookResponse(**dict(row))


@app.put("/books/{book_id}", response_model=BookResponse, tags=["Books"])
async def update_book(book_id: int, book_update: BookUpdate):
    """Update a book."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")

        update_data = book_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        set_clause = ", ".join(f"{k} = ?" for k in update_data.keys())
        values = list(update_data.values()) + [book_id]
        conn.execute(f"UPDATE books SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)

        updated_row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return BookResponse(**dict(updated_row))


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Books"])
async def delete_book(book_id: int):
    """Delete a book."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Book not found")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )
