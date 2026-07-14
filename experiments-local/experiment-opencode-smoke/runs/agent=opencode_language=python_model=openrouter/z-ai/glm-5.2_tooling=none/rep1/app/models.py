from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

from .db import get_connection


@dataclass
class Book:
    id: Optional[int]
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def book_from_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_book(title: str, author: str, year: Optional[int] = None,
                isbn: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        book_id = cur.lastrowid
        return {
            "id": book_id,
            "title": title,
            "author": author,
            "year": year,
            "isbn": isbn,
        }


def list_books(author_filter: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        if author_filter:
            cur = conn.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
                (author_filter,),
            )
        else:
            cur = conn.execute(
                "SELECT id, title, author, year, isbn FROM books ORDER BY id"
            )
        rows = cur.fetchall()
        return [book_from_row(r) for r in rows]


def get_book(book_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return book_from_row(row)


def update_book(book_id: int, title: str, author: str, year: Optional[int],
                isbn: Optional[str], db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id),
        )
        if cur.rowcount == 0:
            return None
        return {
            "id": book_id,
            "title": title,
            "author": author,
            "year": year,
            "isbn": isbn,
        }


def delete_book(book_id: int, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0
