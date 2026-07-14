use sqlx::{SqlitePool, Error};
use crate::models::{Book, CreateBookRequest, UpdateBookRequest};

pub async fn init_db(pool: &SqlitePool) -> Result<(), Error> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        "#
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn create_book(
    pool: &SqlitePool,
    req: CreateBookRequest,
) -> Result<Book, Error> {
    let now = chrono::Utc::now().to_rfc3339();
    
    let result = sqlx::query(
        r#"
        INSERT INTO books (title, author, year, isbn, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        "#
    )
    .bind(&req.title)
    .bind(&req.author)
    .bind(req.year)
    .bind(&req.isbn)
    .bind(&now)
    .bind(&now)
    .execute(pool)
    .await?;

    let book = Book {
        id: Some(result.last_insert_rowid()),
        title: req.title,
        author: req.author,
        year: req.year,
        isbn: req.isbn,
        created_at: Some(now.clone()),
        updated_at: Some(now),
    };

    Ok(book)
}

pub async fn get_all_books(
    pool: &SqlitePool,
    author_filter: Option<String>,
) -> Result<Vec<Book>, Error> {
    let books = if let Some(author) = author_filter {
        sqlx::query_as::<_, Book>(
            r#"
            SELECT id, title, author, year, isbn, created_at, updated_at
            FROM books
            WHERE author LIKE ?
            ORDER BY created_at DESC
            "#
        )
        .bind(format!("%{}%", author))
        .fetch_all(pool)
        .await?
    } else {
        sqlx::query_as::<_, Book>(
            r#"
            SELECT id, title, author, year, isbn, created_at, updated_at
            FROM books
            ORDER BY created_at DESC
            "#
        )
        .fetch_all(pool)
        .await?
    };

    Ok(books)
}

pub async fn get_book_by_id(
    pool: &SqlitePool,
    id: i64,
) -> Result<Option<Book>, Error> {
    let book = sqlx::query_as::<_, Book>(
        r#"
        SELECT id, title, author, year, isbn, created_at, updated_at
        FROM books
        WHERE id = ?
        "#
    )
    .bind(id)
    .fetch_optional(pool)
    .await?;

    Ok(book)
}

pub async fn update_book(
    pool: &SqlitePool,
    id: i64,
    req: UpdateBookRequest,
) -> Result<Option<Book>, Error> {
    let existing = get_book_by_id(pool, id).await?;
    
    if existing.is_none() {
        return Ok(None);
    }

    let now = chrono::Utc::now().to_rfc3339();
    let existing = existing.unwrap();
    
    let title = req.title.unwrap_or(existing.title);
    let author = req.author.unwrap_or(existing.author);
    let year = req.year.or(existing.year);
    let isbn = req.isbn.or(existing.isbn);

    sqlx::query(
        r#"
        UPDATE books
        SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
        WHERE id = ?
        "#
    )
    .bind(&title)
    .bind(&author)
    .bind(year)
    .bind(&isbn)
    .bind(&now)
    .bind(id)
    .execute(pool)
    .await?;

    let updated_book = Book {
        id: Some(id),
        title,
        author,
        year,
        isbn,
        created_at: existing.created_at,
        updated_at: Some(now),
    };

    Ok(Some(updated_book))
}

pub async fn delete_book(
    pool: &SqlitePool,
    id: i64,
) -> Result<bool, Error> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(pool)
        .await?;

    Ok(result.rows_affected() > 0)
}
