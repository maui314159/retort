use crate::error::AppError;
use crate::models::{Book, CreateBook, UpdateBook};
use rusqlite::{params, Connection};
use std::sync::{Arc, Mutex};

pub type Db = Arc<Mutex<Connection>>;

pub fn init_db() -> Result<Db, AppError> {
    let conn = Connection::open_in_memory()?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
        [],
    )?;
    Ok(Arc::new(Mutex::new(conn)))
}

pub fn create_book(db: &Db, input: &CreateBook) -> Result<Book, AppError> {
    let conn = db.lock().map_err(|e| AppError::Db(format!("lock error: {}", e)))?;
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![input.title, input.author, input.year, input.isbn],
    )?;
    let id = conn.last_insert_rowid();
    let book = Book {
        id,
        title: input.title.clone(),
        author: input.author.clone(),
        year: input.year,
        isbn: input.isbn.clone(),
    };
    Ok(book)
}

pub fn list_books(db: &Db, author_filter: Option<&str>) -> Result<Vec<Book>, AppError> {
    let conn = db.lock().map_err(|e| AppError::Db(format!("lock error: {}", e)))?;
    let mut stmt = if let Some(author) = author_filter {
        let mut s = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
        )?;
        let rows = s
            .query_map(params![author], row_to_book)?
            .collect::<Result<Vec<_>, _>>()?;
        return Ok(rows);
    } else {
        conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?
    };
    let books = stmt.query_map([], row_to_book)?.collect::<Result<Vec<_>, _>>()?;
    Ok(books)
}

pub fn get_book(db: &Db, id: i64) -> Result<Book, AppError> {
    let conn = db.lock().map_err(|e| AppError::Db(format!("lock error: {}", e)))?;
    let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let book = stmt
        .query_row(params![id], row_to_book)
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => AppError::NotFound,
            other => AppError::Db(other.to_string()),
        })?;
    Ok(book)
}

pub fn update_book(db: &Db, id: i64, input: &UpdateBook) -> Result<Book, AppError> {
    let existing = get_book(db, id)?;
    let updated = input.apply_to(&existing);
    let conn = db.lock().map_err(|e| AppError::Db(format!("lock error: {}", e)))?;
    let affected = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![updated.title, updated.author, updated.year, updated.isbn, id],
    )?;
    if affected == 0 {
        return Err(AppError::NotFound);
    }
    Ok(updated)
}

pub fn delete_book(db: &Db, id: i64) -> Result<(), AppError> {
    let conn = db.lock().map_err(|e| AppError::Db(format!("lock error: {}", e)))?;
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if affected == 0 {
        return Err(AppError::NotFound);
    }
    Ok(())
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
