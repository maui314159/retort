use rusqlite::{params, Connection};

use crate::models::{Book, CreateBook, UpdateBook};

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

pub fn insert_book(conn: &Connection, input: &CreateBook) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![input.title, input.author, input.year, input.isbn],
    )?;
    let id = conn.last_insert_rowid();
    get_book(conn, id).map(Option::unwrap)
}

pub fn list_books(conn: &Connection, author_filter: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    let mut sql = String::from("SELECT id, title, author, year, isbn FROM books");
    let mut params_vec: Vec<String> = Vec::new();
    if let Some(a) = author_filter {
        sql.push_str(" WHERE author = ?1");
        params_vec.push(a.to_string());
    }
    sql.push_str(" ORDER BY id ASC");

    let mut stmt = conn.prepare(&sql)?;
    let rows = if params_vec.is_empty() {
        stmt.query_map([], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?
    } else {
        stmt.query_map(params![params_vec[0]], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?
    };
    Ok(rows)
}

pub fn get_book(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let mut rows = stmt.query(params![id])?;
    match rows.next()? {
        Some(r) => Ok(Some(row_to_book(r)?)),
        None => Ok(None),
    }
}

pub fn update_book(
    conn: &Connection,
    id: i64,
    input: &UpdateBook,
) -> rusqlite::Result<Option<Book>> {
    let existing = match get_book(conn, id)? {
        Some(b) => b,
        None => return Ok(None),
    };

    let title = input.title.as_ref().unwrap_or(&existing.title);
    let author = input.author.as_ref().unwrap_or(&existing.author);
    let year = input.year.or(existing.year);
    let isbn = input.isbn.as_ref().or(existing.isbn.as_ref()).cloned();

    conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, year, isbn, id],
    )?;
    get_book(conn, id)
}

pub fn delete_book(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(affected > 0)
}

fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}
