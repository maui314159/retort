from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, AsyncIterator
import database
from models import BookCreate, BookUpdate, BookResponse

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the database on startup."""
    database.init_db()
    yield

app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = database.get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "error": str(e)})

@app.post("/books", response_model=BookResponse, status_code=201)
async def create_book(book: BookCreate):
    """Create a new book."""
    try:
        result = database.create_book(
            title=book.title,
            author=book.author,
            year=book.year,
            isbn=book.isbn
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/books", response_model=List[BookResponse])
async def list_books(author: Optional[str] = Query(None, description="Filter by author name")):
    """List all books, optionally filtered by author."""
    try:
        books = database.get_books(author=author)
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int):
    """Get a single book by ID."""
    book = database.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.put("/books/{book_id}", response_model=BookResponse)
async def update_book(book_id: int, book: BookUpdate):
    """Update a book by ID."""
    # Build update dict with only provided fields
    update_data = book.model_dump(exclude_unset=True)

    if not update_data:
        # No fields to update
        existing = database.get_book(book_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Book not found")
        return existing

    result = database.update_book(book_id, **update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Book not found")
    return result

@app.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: int):
    """Delete a book by ID."""
    deleted = database.delete_book(book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")
    return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
