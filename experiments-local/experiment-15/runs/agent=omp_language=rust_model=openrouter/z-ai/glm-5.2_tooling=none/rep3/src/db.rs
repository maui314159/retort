use rusqlite::Connection;

use crate::models::Book;

/// Initialize the SQLite schema. Idempotent.
pub fn init(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year  INTEGER,
            isbn  TEXT
        )",
        [],
    )?;
    Ok(())
}

/// Insert a new book, returning the stored row with its assigned id.
pub fn insert(
    conn: &Connection,
    title: &str,
    author: &str,
    year: Option<i64>,
    isbn: Option<&str>,
) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![title, author, year, isbn],
    )?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title: title.to_string(),
        author: author.to_string(),
        year: year.map(|y| y as i32),
        isbn: isbn.map(String::from),
    })
}

/// List all books, optionally filtered by author (exact match).
pub fn list(conn: &Connection, author_filter: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    let mut stmt = if let Some(author) = author_filter {
        let mut s =
            conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1")?;
        let rows = s
            .query_map([author], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?;
        return Ok(rows);
    } else {
        conn.prepare("SELECT id, title, author, year, isbn FROM books")?
    };
    let rows = stmt.query_map([], row_to_book)?.collect::<rusqlite::Result<Vec<_>>>()?;
    Ok(rows)
}

/// Fetch a single book by id.
pub fn get(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    let mut stmt =
        conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let mut rows = stmt.query_map([id], row_to_book)?;
    match rows.next() {
        Some(book) => Ok(Some(book?)),
        None => Ok(None),
    }
}

/// Update a book by id. Returns the updated book, or None if no row matched.
pub fn update(
    conn: &Connection,
    id: i64,
    title: &str,
    author: &str,
    year: Option<i64>,
    isbn: Option<&str>,
) -> rusqlite::Result<Option<Book>> {
    let affected = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, year, isbn, id],
    )?;
    if affected == 0 {
        return Ok(None);
    }
    get(conn, id)
}

/// Delete a book by id. Returns true if a row was removed.
pub fn delete(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", [id])?;
    Ok(affected > 0)
}

fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get::<_, i64>(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get::<_, Option<i64>>(3)?.map(|y| y as i32),
        isbn: row.get(4)?,
    })
}
