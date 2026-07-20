//! SQLite persistence layer for the book collection.

use rusqlite::{params, Connection, OptionalExtension, Row};

use crate::models::Book;

/// Create the books table if it does not exist yet.
pub fn init_schema(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        );",
    )
}

fn row_to_book(row: &Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

/// Insert a new book and return it with its assigned id.
pub fn create_book(
    conn: &Connection,
    title: &str,
    author: &str,
    year: Option<i64>,
    isbn: Option<&str>,
) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, year, isbn],
    )?;
    Ok(Book {
        id: conn.last_insert_rowid(),
        title: title.to_owned(),
        author: author.to_owned(),
        year,
        isbn: isbn.map(str::to_owned),
    })
}

/// Return all books, optionally filtered by exact author match.
pub fn list_books(conn: &Connection, author: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    let mut books = Vec::new();
    match author {
        Some(author) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )?;
            let rows = stmt.query_map(params![author], row_to_book)?;
            for row in rows {
                books.push(row?);
            }
        }
        None => {
            let mut stmt =
                conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = stmt.query_map([], row_to_book)?;
            for row in rows {
                books.push(row?);
            }
        }
    }
    Ok(books)
}

/// Fetch a single book by id.
pub fn get_book(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()
}

/// Replace all fields of an existing book. Returns the updated book, or
/// `None` when no book with that id exists.
pub fn update_book(
    conn: &Connection,
    id: i64,
    title: &str,
    author: &str,
    year: Option<i64>,
    isbn: Option<&str>,
) -> rusqlite::Result<Option<Book>> {
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, year, isbn, id],
    )?;
    if changed == 0 {
        return Ok(None);
    }
    get_book(conn, id)
}

/// Delete a book by id. Returns whether a row was actually removed.
pub fn delete_book(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(changed > 0)
}
