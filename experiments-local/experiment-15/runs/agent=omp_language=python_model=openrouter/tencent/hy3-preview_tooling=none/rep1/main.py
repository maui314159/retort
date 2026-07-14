from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import List, Optional
import database
from models import BookCreate, BookUpdate, BookResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    database.init_db()
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "book-collection-api"}


@app.post("/books", response_model=BookResponse, status_code=201)
async def create_book(book: BookCreate):
    """Create a new book."""
    try:
        db_book = database.create_book(
            title=book.title,
            author=book.author,
            year=book.year,
            isbn=book.isbn
        )
        return BookResponse(**db_book)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/books", response_model=List[BookResponse])
async def list_books(author: Optional[str] = Query(None, description="Filter by author name")):
    """List all books, optionally filtered by author."""
    books = database.get_all_books(author_filter=author)
    return [BookResponse(**book) for book in books]


@app.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int):
    """Get a single book by ID."""
    book = database.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookResponse(**book)


@app.put("/books/{book_id}", response_model=BookResponse)
async def update_book(book_id: int, book: BookUpdate):
    """Update a book by ID."""
    # Check if book exists
    existing = database.get_book_by_id(book_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Book not found")

    # Use existing values if not provided
    update_data = book.model_dump(exclude_unset=True)
    title = update_data.get('title', existing['title'])
    author = update_data.get('author', existing['author'])
    year = update_data.get('year', existing['year'])
    isbn = update_data.get('isbn', existing['isbn'])

    try:
        updated = database.update_book(
            book_id=book_id,
            title=title,
            author=author,
            year=year,
            isbn=isbn
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Book not found")
        return BookResponse(**updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: int):
    """Delete a book by ID."""
    deleted = database.delete_book(book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")
    return JSONResponse(status_code=204, content=None)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
