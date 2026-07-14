import sqlite3
import os
from typing import Optional, List, Dict, Any

DB_PATH = "books.db"

def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory set to dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the books table."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

def create_book(title: str, author: str, year: Optional[int] = None, isbn: Optional[str] = None) -> Dict[str, Any]:
    """Create a new book and return it with its ID."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn)
        )
        conn.commit()
        book_id = cursor.lastrowid
        return get_book(book_id)
    finally:
        conn.close()

def get_book(book_id: int) -> Optional[Dict[str, Any]]:
    """Get a single book by ID."""
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def get_books(author: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all books, optionally filtered by author."""
    conn = get_connection()
    try:
        if author:
            cursor = conn.execute(
                "SELECT * FROM books WHERE author LIKE ? ORDER BY id",
                (f"%{author}%",)
            )
        else:
            cursor = conn.execute("SELECT * FROM books ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def update_book(book_id: int, title: Optional[str] = None, author: Optional[str] = None,
                year: Optional[int] = None, isbn: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Update a book by ID. Returns the updated book or None if not found."""
    conn = get_connection()
    try:
        # Check if book exists
        existing = conn.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
        if not existing:
            return None

        # Build update query dynamically
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if author is not None:
            updates.append("author = ?")
            params.append(author)
        if year is not None:
            updates.append("year = ?")
            params.append(year)
        if isbn is not None:
            updates.append("isbn = ?")
            params.append(isbn)

        if updates:
            params.append(book_id)
            conn.execute(f"UPDATE books SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        return get_book(book_id)
    finally:
        conn.close()

def delete_book(book_id: int) -> bool:
    """Delete a book by ID. Returns True if deleted, False if not found."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
