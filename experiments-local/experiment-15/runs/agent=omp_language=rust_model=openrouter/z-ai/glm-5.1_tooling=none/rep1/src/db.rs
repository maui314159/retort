use rusqlite::{params, Connection, Result as SqlResult};

use crate::models::Book;

pub fn init_db(path: &str) -> SqlResult<Connection> {
    let conn = Connection::open(path)?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id      TEXT PRIMARY KEY,
            title   TEXT NOT NULL,
            author  TEXT NOT NULL,
            year    INTEGER,
            isbn    TEXT
        );",
    )?;
    Ok(conn)
}

pub fn insert_book(conn: &Connection, book: &Book) -> SqlResult<()> {
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )?;
    Ok(())
}

pub fn list_books(conn: &Connection, author_filter: Option<&str>) -> SqlResult<Vec<Book>> {
    let mut sql = String::from("SELECT id, title, author, year, isbn FROM books");
    if author_filter.is_some() {
        sql.push_str(" WHERE author = ?1");
    }
    sql.push_str(" ORDER BY id");

    let mut stmt = conn.prepare(&sql)?;
    let mut rows = match author_filter {
        Some(author) => stmt.query(params![author])?,
        None => stmt.query([])?,
    };

    let mut books = Vec::new();
    while let Some(r) = rows.next()? {
        books.push(Book {
            id: r.get(0)?,
            title: r.get(1)?,
            author: r.get(2)?,
            year: r.get(3)?,
            isbn: r.get(4)?,
        });
    }
    Ok(books)
}

pub fn get_book(conn: &Connection, id: &str) -> SqlResult<Option<Book>> {
    let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let mut rows = stmt.query(params![id])?;
    match rows.next()? {
        Some(r) => Ok(Some(Book {
            id: r.get(0)?,
            title: r.get(1)?,
            author: r.get(2)?,
            year: r.get(3)?,
            isbn: r.get(4)?,
        })),
        None => Ok(None),
    }
}

pub fn update_book(conn: &Connection, id: &str, title: Option<&str>, author: Option<&str>, year: Option<i32>, isbn: Option<&str>) -> SqlResult<bool> {
    // Fetch current book to merge partial updates
    let current = match get_book(conn, id)? {
        Some(b) => b,
        None => return Ok(false),
    };

    let new_title = title.unwrap_or(&current.title);
    let new_author = author.unwrap_or(&current.author);
    let new_year = year.or(current.year);
    let new_isbn = isbn.or(current.isbn.as_deref());

    let affected = conn.execute(
        "UPDATE books SET title = ?2, author = ?3, year = ?4, isbn = ?5 WHERE id = ?1",
        params![id, new_title, new_author, new_year, new_isbn],
    )?;
    Ok(affected > 0)
}

pub fn delete_book(conn: &Connection, id: &str) -> SqlResult<bool> {
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(affected > 0)
}
