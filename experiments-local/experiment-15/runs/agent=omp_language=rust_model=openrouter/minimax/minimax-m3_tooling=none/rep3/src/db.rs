//! SQLite database access for books.
//!
//! The schema is created lazily on pool initialization. All queries use
//! runtime-bound parameters (no compile-time `DATABASE_URL` required) so
//! the binary can be run against any path.

use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions};
use sqlx::SqlitePool;
use std::str::FromStr;

use crate::error::{AppError, AppResult};
use crate::models::{Book, ValidatedBookUpdate, ValidatedNewBook};

/// Build a connection pool against the given SQLite database URL and run
/// the schema migration.
///
/// The URL is anything `sqlx::sqlite::SqliteConnectOptions` accepts
/// (e.g. `sqlite::memory:` or `sqlite://./books.db`).
pub async fn init_pool(database_url: &str) -> AppResult<SqlitePool> {
    let options = SqliteConnectOptions::from_str(database_url)
        .map_err(|err| AppError::Internal(format!("invalid database url: {err}")))?
        .create_if_missing(true)
        .journal_mode(sqlx::sqlite::SqliteJournalMode::Wal)
        .busy_timeout(std::time::Duration::from_secs(5));

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect_with(options)
        .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            title   TEXT    NOT NULL,
            author  TEXT    NOT NULL,
            year    INTEGER,
            isbn    TEXT
        )
        "#,
    )
    .execute(&pool)
    .await?;

    sqlx::query(
        "CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)",
    )
    .execute(&pool)
    .await?;

    Ok(pool)
}

/// Insert a new book and return the persisted row (with id).
pub async fn create_book(pool: &SqlitePool, book: ValidatedNewBook) -> AppResult<Book> {
    let result = sqlx::query(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
    )
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .execute(pool)
    .await?;

    let id = result.last_insert_rowid();
    fetch_book(pool, id)
        .await?
        .ok_or_else(|| AppError::Internal("inserted book not found".to_string()))
}

/// Fetch a single book by id.
pub async fn fetch_book(pool: &SqlitePool, id: i64) -> AppResult<Option<Book>> {
    let row = sqlx::query_as::<_, BookRow>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_optional(pool)
    .await?;

    Ok(row.map(Book::from))
}

/// List books, optionally filtered by author (case-insensitive exact match).
pub async fn list_books(pool: &SqlitePool, author: Option<&str>) -> AppResult<Vec<Book>> {
    let rows = if let Some(author) = author {
        sqlx::query_as::<_, BookRow>(
            "SELECT id, title, author, year, isbn \
             FROM books \
             WHERE LOWER(author) = LOWER(?) \
             ORDER BY id",
        )
        .bind(author)
        .fetch_all(pool)
        .await?
    } else {
        sqlx::query_as::<_, BookRow>(
            "SELECT id, title, author, year, isbn FROM books ORDER BY id",
        )
        .fetch_all(pool)
        .await?
    };

    Ok(rows.into_iter().map(Book::from).collect())
}

/// Replace an existing book. Returns the updated row, or `None` if no book
/// with that id exists.
pub async fn update_book(
    pool: &SqlitePool,
    id: i64,
    update: ValidatedBookUpdate,
) -> AppResult<Option<Book>> {
    let result = sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
    )
    .bind(&update.title)
    .bind(&update.author)
    .bind(update.year)
    .bind(&update.isbn)
    .bind(id)
    .execute(pool)
    .await?;

    if result.rows_affected() == 0 {
        return Ok(None);
    }

    fetch_book(pool, id).await
}

/// Delete a book by id. Returns `true` if a row was removed.
pub async fn delete_book(pool: &SqlitePool, id: i64) -> AppResult<bool> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(pool)
        .await?;
    Ok(result.rows_affected() > 0)
}

#[derive(sqlx::FromRow)]
struct BookRow {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

impl From<BookRow> for Book {
    fn from(row: BookRow) -> Self {
        Self {
            id: row.id,
            title: row.title,
            author: row.author,
            year: row.year,
            isbn: row.isbn,
        }
    }
}
