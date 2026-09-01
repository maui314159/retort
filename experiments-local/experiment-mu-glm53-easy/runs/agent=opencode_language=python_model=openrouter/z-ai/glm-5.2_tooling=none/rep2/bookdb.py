"""SQLite-backed book collection store.

Why: isolates persistence so the HTTP layer stays pure routing/JSON.
What: schema bootstrap + CRUD over a `books` table.
"""
import sqlite3
import threading
import contextlib

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


class BookDB:
    """Thread-safe SQLite wrapper for the books table.

    A single connection is shared and guarded by a re-entrant lock so the
    HTTP handler (which may serve concurrent requests in a ThreadingHTTPServer)
    can safely call any method.
    """

    def __init__(self, path=":memory:"):
        self._path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    @contextlib.contextmanager
    def _cursor(self):
        with self._lock:
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            finally:
                cur.close()

    def insert(self, title, author, year=None, isbn=None):
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (title, author, year, isbn),
            )
            return cur.lastrowid

    def list(self, author=None):
        with self._cursor() as cur:
            if author is None:
                cur.execute("SELECT * FROM books ORDER BY id")
            else:
                cur.execute(
                    "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
                )
            return [dict(r) for r in cur.fetchall()]

    def get(self, book_id):
        with self._cursor() as cur:
            cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            row = cur.fetchone()
            return dict(row) if row is not None else None

    def update(self, book_id, fields):
        if not fields:
            return self.get(book_id)
        allowed = ("title", "author", "year", "isbn")
        cols = [f"{k} = ?" for k in fields if k in allowed]
        vals = [fields[k] for k in fields if k in allowed]
        if not cols:
            return self.get(book_id)
        vals.append(book_id)
        with self._cursor() as cur:
            cur.execute(
                f"UPDATE books SET {', '.join(cols)} WHERE id = ?", vals
            )
            if cur.rowcount == 0:
                return None
        return self.get(book_id)

    def delete(self, book_id):
        with self._cursor() as cur:
            cur.execute("SELECT id FROM books WHERE id = ?", (book_id,))
            existed = cur.fetchone() is not None
            cur.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return existed

    def close(self):
        with self._lock:
            self._conn.close()
