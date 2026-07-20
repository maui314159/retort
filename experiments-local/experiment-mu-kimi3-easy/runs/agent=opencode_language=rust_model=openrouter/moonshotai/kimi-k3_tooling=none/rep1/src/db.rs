//! SQLite persistence layer.
//!
//! These functions take `&Connection` directly (no async, no HTTP types) so
//! they stay trivially unit-testable and independent of the web framework.

use rusqlite::{params, Connection, Row};

use crate::models::{Book, BookInput};

/// Create the `books` table if it does not exist yet.
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

fn row_to_book(row: &Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

const COLUMNS: &str = "id, title, author, year, isbn";

/// Insert a new book and return it with its generated id.
pub fn insert_book(conn: &Connection, input: &BookInput) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![input.title, input.author, input.year, input.isbn],
    )?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title: input.title.clone().expect("validated"),
        author: input.author.clone().expect("validated"),
        year: input.year,
        isbn: input.isbn.clone(),
    })
}

/// List all books, optionally filtered by exact author name.
pub fn list_books(conn: &Connection, author: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    let sql = format!("SELECT {COLUMNS} FROM books");
    match author {
        Some(a) => {
            let mut stmt = conn.prepare(&format!("{sql} WHERE author = ?1 ORDER BY id"))?;
            let rows = stmt.query_map(params![a], row_to_book)?;
            rows.collect()
        }
        None => {
            let mut stmt = conn.prepare(&format!("{sql} ORDER BY id"))?;
            let rows = stmt.query_map([], row_to_book)?;
            rows.collect()
        }
    }
}

/// Fetch a single book by id.
pub fn get_book(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    let mut stmt = conn.prepare(&format!("SELECT {COLUMNS} FROM books WHERE id = ?1"))?;
    let mut rows = stmt.query_map(params![id], row_to_book)?;
    rows.next().transpose()
}

/// Replace a book's fields. Returns `None` when no row with `id` exists.
pub fn update_book(
    conn: &Connection,
    id: i64,
    input: &BookInput,
) -> rusqlite::Result<Option<Book>> {
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![input.title, input.author, input.year, input.isbn, id],
    )?;
    if changed == 0 {
        return Ok(None);
    }
    get_book(conn, id)
}

/// Delete a book. Returns `true` when a row was actually removed.
pub fn delete_book(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(changed > 0)
}
