use std::path::Path;

use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;
use rusqlite::params;

use crate::error::{AppError, AppResult};
use crate::models::{Book, CreateBook, UpdateBook};

pub type DbPool = Pool<SqliteConnectionManager>;

/// Build a connection pool backed by a SQLite file (or `:memory:` for tests).
/// `:memory:` is shared across connections only because we keep the pool size at
/// 1 for in-memory databases — see [`open_pool`].
pub fn open_pool<P: AsRef<Path>>(path: P) -> AppResult<DbPool> {
    let manager = SqliteConnectionManager::file(path).with_init(|c| {
        c.execute_batch(
            "PRAGMA journal_mode = WAL; \
             PRAGMA foreign_keys = ON;",
        )
    });
    let pool = Pool::builder()
        .build(manager)
        .map_err(|e| AppError::Pool(e.to_string()))?;
    Ok(pool)
}

/// Create an in-memory pool. A single connection is kept so that all callers
/// see the same in-memory database (each connection to `:memory:` is isolated).
pub fn in_memory_pool() -> AppResult<DbPool> {
    let manager = SqliteConnectionManager::memory().with_init(|c| {
        c.execute_batch("PRAGMA foreign_keys = ON;")
    });
    let pool = Pool::builder()
        .max_size(1)
        .build(manager)
        .map_err(|e| AppError::Pool(e.to_string()))?;
    Ok(pool)
}

/// Run the schema migration. Idempotent.
pub fn migrate(pool: &DbPool) -> AppResult<()> {
    let conn = pool.get().map_err(|e| AppError::Pool(e.to_string()))?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books ( \
            id    INTEGER PRIMARY KEY AUTOINCREMENT, \
            title TEXT    NOT NULL, \
            author TEXT   NOT NULL, \
            year  INTEGER, \
            isbn  TEXT \
         );",
    )?;
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

pub fn insert_book(pool: &DbPool, input: &CreateBook) -> AppResult<Book> {
    let conn = pool.get().map_err(|e| AppError::Pool(e.to_string()))?;
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![
            input.title.trim(),
            input.author.trim(),
            input.year,
            input.isbn.as_ref().map(|s| s.trim()).filter(|s| !s.is_empty()),
        ],
    )?;
    let id = conn.last_insert_rowid();
    drop(conn);
    get_book_by_id(pool, id)
}

pub fn list_books(pool: &DbPool, author_filter: Option<&str>) -> AppResult<Vec<Book>> {
    let conn = pool.get().map_err(|e| AppError::Pool(e.to_string()))?;
    let books = match author_filter {
        Some(author) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books \
                 WHERE author LIKE ?1 COLLATE NOCASE \
                 ORDER BY id ASC",
            )?;
            let rows = stmt.query_map(params![format!("%{}%", author)], row_to_book)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()?
        }
        None => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books ORDER BY id ASC",
            )?;
            let rows = stmt.query_map([], row_to_book)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()?
        }
    };
    Ok(books)
}

pub fn get_book_by_id(pool: &DbPool, id: i64) -> AppResult<Book> {
    let conn = pool.get().map_err(|e| AppError::Pool(e.to_string()))?;
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            row_to_book,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => AppError::NotFound,
            other => AppError::Database(other),
        })?;
    Ok(book)
}

pub fn update_book(pool: &DbPool, id: i64, input: &UpdateBook) -> AppResult<Book> {
    let conn = pool.get().map_err(|e| AppError::Pool(e.to_string()))?;
    // Ensure the book exists first to return a clean 404.
    let exists: bool = conn
        .query_row("SELECT 1 FROM books WHERE id = ?1", params![id], |_| Ok(true))
        .unwrap_or(false);
    if !exists {
        return Err(AppError::NotFound);
    }

    // Build a dynamic UPDATE so only provided fields are touched.
    let mut sets: Vec<&str> = Vec::new();
    let mut params_vec: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();
    if let Some(title) = &input.title {
        sets.push("title = ?");
        params_vec.push(Box::new(title.trim().to_string()));
    }
    if let Some(author) = &input.author {
        sets.push("author = ?");
        params_vec.push(Box::new(author.trim().to_string()));
    }
    if let Some(year) = input.year {
        sets.push("year = ?");
        params_vec.push(Box::new(year));
    }
    if let Some(isbn) = &input.isbn {
        sets.push("isbn = ?");
        params_vec.push(Box::new(isbn.trim().to_string()));
    }

    let sql = format!("UPDATE books SET {} WHERE id = ?", sets.join(", "));
    params_vec.push(Box::new(id));
    let param_refs: Vec<&dyn rusqlite::ToSql> =
        params_vec.iter().map(|p| p.as_ref()).collect();
    conn.execute(&sql, param_refs.as_slice())?;

    drop(conn);
    get_book_by_id(pool, id)
}

pub fn delete_book(pool: &DbPool, id: i64) -> AppResult<()> {
    let conn = pool.get().map_err(|e| AppError::Pool(e.to_string()))?;
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if affected == 0 {
        Err(AppError::NotFound)
    } else {
        Ok(())
    }
}
