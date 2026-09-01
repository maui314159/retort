"""SQLite data-access layer for the book collection API.

The :class:`Database` wraps a single sqlite3 connection guarded by a lock.
This keeps the service thread-safe (Flask's dev server and the test client
may use more than one thread) while also allowing in-memory databases
(``:memory:``) to persist for the lifetime of the application.
"""

import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""

_SELECT = "SELECT id, title, author, year, isbn FROM books"
_WRITABLE_FIELDS = ("title", "author", "year", "isbn")


def _row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


class Database:
    """Thread-safe wrapper around a SQLite connection for the books table."""

    def __init__(self, path="books.db"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()

    def ping(self):
        """Raise :class:`sqlite3.Error` if the database is unreachable."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def list_books(self, author=None):
        """Return all books ordered by id.

        When ``author`` is given, only books whose author contains that
        string (case-insensitive substring match) are returned.
        """
        query = _SELECT
        params = []
        if author:
            query += " WHERE instr(lower(author), lower(?)) > 0"
            params.append(author)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [_row_to_book(row) for row in rows]

    def get_book(self, book_id):
        """Return the book with the given id, or None if it does not exist."""
        with self._lock:
            row = self._conn.execute(
                _SELECT + " WHERE id = ?", (book_id,)
            ).fetchone()
        return _row_to_book(row) if row is not None else None

    def create_book(self, title, author, year=None, isbn=None):
        """Insert a book and return it (including its assigned id)."""
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (title, author, year, isbn),
            )
            self._conn.commit()
            book_id = cursor.lastrowid
        return self.get_book(book_id)

    def update_book(self, book_id, fields):
        """Update the given columns of a book.

        ``fields`` maps column names to new values; unknown column names
        are ignored. Returns the updated book, or None if the id does not
        exist. An empty ``fields`` dict simply returns the current book.
        """
        allowed = {
            name: fields[name] for name in _WRITABLE_FIELDS if name in fields
        }
        if allowed:
            assignments = ", ".join(f"{name} = ?" for name in allowed)
            params = [*allowed.values(), book_id]
            with self._lock:
                self._conn.execute(
                    f"UPDATE books SET {assignments} WHERE id = ?", params
                )
                self._conn.commit()
        return self.get_book(book_id)

    def delete_book(self, book_id):
        """Delete a book; return True if a row was removed, else False."""
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM books WHERE id = ?", (book_id,)
            )
            self._conn.commit()
            return cursor.rowcount > 0
