import sqlite3
import os
from typing import Optional, List, Dict, Any

DB_PATH = "books.db"

def get_db_connection() -> sqlite3.Connection:
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initialize the database with the books table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def create_book(title: str, author: str, year: Optional[int], isbn: Optional[str]) -> Dict[str, Any]:
    """Create a new book in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn)
        )
        book_id = cursor.lastrowid
        conn.commit()
        # Fetch the created book
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        return dict(row)
    except sqlite3.IntegrityError as e:
        raise ValueError(f"ISBN must be unique: {e}")
    finally:
        conn.close()

def get_all_books(author_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all books, optionally filtered by author."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if author_filter:
        cursor.execute("SELECT * FROM books WHERE author LIKE ?", (f"%{author_filter}%",))
    else:
        cursor.execute("SELECT * FROM books")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_book_by_id(book_id: int) -> Optional[Dict[str, Any]]:
    """Get a single book by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_book(book_id: int, title: str, author: str, year: Optional[int], isbn: Optional[str]) -> Optional[Dict[str, Any]]:
    """Update a book by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id)
        )
        if cursor.rowcount == 0:
            return None
        conn.commit()
        # Fetch the updated book
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.IntegrityError as e:
        raise ValueError(f"ISBN must be unique: {e}")
    finally:
        conn.close()

def delete_book(book_id: int) -> bool:
    """Delete a book by ID. Returns True if deleted, False if not found."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
